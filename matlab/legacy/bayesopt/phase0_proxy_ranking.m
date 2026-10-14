%PHASE0_PROXY_RANKING Fase 0 (GATE) — o proxy analitico preserva o RANKING de
% candidatos do custo Simulink fiel? Gera ~25 theta variados (LHS nas faixas do
% SLDD + pontos conhecidos), e para cada um calcula J pelo proxy (bo_cost_proxy)
% e J pelo Simulink fiel (bo_cost, ApplyTheta) num conjunto FIXO de 6 eventos
% cobrindo os 3 DOFs. Reporta Spearman rho entre os dois rankings + scatter.
% DECISAO: rho>=0.85 -> Caminho 2 (proxy no loop); rho<0.85 -> Fallback.
%
% Determinístico (rng 42 no LHS). Salva incremental em build/phase0_ranking.mat
% (campo .done=true no fim) p/ polling de processo em background.

clearvars; close all;
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here,'..','..')); repo_root = bootstrap_paths('legacy'); cd(repo_root); %#ok<NASGU> % legado: caminhos relativos abaixo assumem pwd == raiz do repo
warning('off','all');
try, Simulink.data.dictionary.closeAll('-discard'); catch, end
try, bdclose('all'); catch, end
system('git restore config/ssl_robot.sldd');
model = 'parameter_estimation_model_pid_v3';
ensure_model_ready(model);
sldd_restore = onCleanup(@() system('git restore config/ssl_robot.sldd'));

LAMBDA = 1.171;
outmat = fullfile('build','phase0_ranking.mat');

% --- 6 eventos fixos cobrindo os 3 DOFs (do POOL de treino, fora do hold-out) -
events6 = { ...
    'front_to_back','front_to_back_01_02'
    'front_to_back','front_to_back_01_03'
    'side_to_side','side_to_side_02_01'
    'side_to_side','side_to_side_01_08'
    'shoot_to_goal','shoot_to_goal_03_01'
    'shoot_to_goal','shoot_to_goal_07_01'};
cache = build_event_cache(events6);

% --- pontos conhecidos ----------------------------------------------------
vv = [1.1192 0.071784 0.06905 1.0524 0.12733 0.056483 1 0.1 0];     % vx/vy v2 + omega placeholder
pv = [0.98859 0.12817 0.17075 0.9493 0.24158 0.10445 1 0.1 0];      % placeholder antigo
vc = vv; vc(7:9) = [1.307 0.0222 0.1179];                           % vx/vy v2 + omega candidato (reprovado)
known = [vv; pv; vc];
knownLbl = {'vxvy_v2','placeholder','omega_cand'};

% --- LHS nas faixas do SLDD: K[0.5,2] lin, tau[0.02,0.5] LOG, Td[0,0.15] lin --
nLHS = 22;
rng(42);
U = lhsdesign(nLHS, 9);
lo = [0.5 0.02 0   0.5 0.02 0   0.5 0.02 0  ];
hi = [2.0 0.50 0.15 2.0 0.50 0.15 2.0 0.50 0.15];
isTau = [2 5 8];
TH = lo + U.*(hi-lo);
for c = isTau   % log-uniforme nas colunas de tau
    TH(:,c) = 10.^(log10(lo(c)) + U(:,c).*(log10(hi(c))-log10(lo(c))));
end
THETA = [TH; known];
labels = [repmat({'LHS'},nLHS,1); knownLbl(:)];
nT = size(THETA,1);
fprintf('Phase 0: %d theta (%d LHS + %d conhecidos) x %d eventos\n', nT, nLHS, numel(knownLbl), numel(cache));

% --- loop: J_proxy e J_sim por theta, salvo incremental --------------------
J_proxy = nan(nT,1); J_sim = nan(nT,1);
Jp_pos  = nan(nT,1); Js_pos = nan(nT,1);
Jp_head = nan(nT,1); Js_head= nan(nT,1);
tstart = tic;
for i = 1:nT
    th = THETA(i,:);
    try
        [J_proxy(i), ip] = bo_cost_proxy(th, cache, 'Lambda', LAMBDA);
        Jp_pos(i) = ip.J_pos; Jp_head(i) = ip.J_head;
    catch ME
        fprintf('  [proxy %d] ERRO: %s\n', i, ME.message);
    end
    try
        [J_sim(i), is] = bo_cost(th, cache, 'Lambda', LAMBDA, 'ApplyTheta', true);
        Js_pos(i) = is.J_pos; Js_head(i) = is.J_head;
    catch ME
        fprintf('  [sim %d] ERRO: %s\n', i, ME.message);
    end
    fprintf('[%2d/%2d] %-11s Jproxy=%.4f  Jsim=%.4f  (elapsed %.0fs)\n', ...
        i, nT, labels{i}, J_proxy(i), J_sim(i), toc(tstart));
    save(outmat, 'THETA','labels','J_proxy','J_sim','Jp_pos','Js_pos', ...
        'Jp_head','Js_head','LAMBDA','events6','nLHS','i','nT');
end

% --- correlacao de Spearman (ranking) --------------------------------------
ok = isfinite(J_proxy) & isfinite(J_sim);
rho      = corr(J_proxy(ok), J_sim(ok), 'type','Spearman');
rho_pos  = corr(Jp_pos(ok),  Js_pos(ok), 'type','Spearman');
rho_pear = corr(J_proxy(ok), J_sim(ok), 'type','Pearson');
GATE = 0.85;
decision = ternary(rho >= GATE, 'CAMINHO_2 (proxy no loop)', 'FALLBACK (bayesopt no Simulink)');

fprintf('\n================ FASE 0 — RESULTADO DO GATE ================\n');
fprintf('n=%d theta avaliados (full J)\n', nnz(ok));
fprintf('Spearman rho (J full)  = %.4f\n', rho);
fprintf('Spearman rho (J_pos)   = %.4f\n', rho_pos);
fprintf('Pearson  r   (J full)  = %.4f\n', rho_pear);
fprintf('LIMIAR = %.2f  =>  DECISAO: %s\n', GATE, decision);
fprintf('===========================================================\n');

% --- scatter J_proxy vs J_sim ----------------------------------------------
figdir = fullfile('results','figs'); if ~isfolder(figdir), mkdir(figdir); end
stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
f = figure('Color','w','Position',[100 100 720 600]);
isK = ~strcmp(labels,'LHS');
scatter(J_proxy(~isK), J_sim(~isK), 46, [0.30 0.45 0.75], 'filled', ...
    'MarkerFaceAlpha',0.7, 'DisplayName','LHS'); hold on;
mk = {'p','s','d'}; cols = [0.85 0.20 0.20; 0.10 0.55 0.25; 0.55 0.30 0.70];
ki = find(isK);
for j = 1:numel(ki)
    scatter(J_proxy(ki(j)), J_sim(ki(j)), 130, cols(j,:), mk{j}, 'filled', ...
        'MarkerEdgeColor','k', 'DisplayName', labels{ki(j)});
end
lims = [min([J_proxy(ok);J_sim(ok)])*0.95, max([J_proxy(ok);J_sim(ok)])*1.05];
plot(lims, lims, 'k--', 'HandleVisibility','off');
grid on; box on; axis square; xlim(lims); ylim(lims);
xlabel('J_{proxy} (dead-reckoning P1D)'); ylabel('J_{Simulink} (fiel)');
title(sprintf('Fase 0: ranking proxy vs Simulink — \\rho_{Spearman}=%.3f (n=%d)', rho, nnz(ok)));
legend('Location','southeast');
fp = fullfile(figdir, sprintf('F0_proxy_ranking_%s', stamp));
exportgraphics(f,[fp '.png'],'Resolution',150); exportgraphics(f,[fp '.pdf'],'ContentType','vector');

% --- CSV + mat final -------------------------------------------------------
T = table((1:nT).', labels, THETA, J_proxy, J_sim, Jp_pos, Js_pos, Jp_head, Js_head, ...
    'VariableNames', {'idx','kind','theta','J_proxy','J_sim','Jp_pos','Js_pos','Jp_head','Js_head'});
writetable(splitvars(T,'theta'), fullfile('results', sprintf('phase0_proxy_ranking_%s.csv', stamp)));
done = true; %#ok<NASGU>
save(outmat, 'THETA','labels','J_proxy','J_sim','Jp_pos','Js_pos','Jp_head','Js_head', ...
    'LAMBDA','events6','nLHS','nT','rho','rho_pos','rho_pear','GATE','decision','stamp','done');
fprintf('Salvo: %s | fig F0_proxy_ranking_%s | csv phase0_proxy_ranking_%s.csv\n', outmat, stamp, stamp);

function s = ternary(c,a,b), if c, s=a; else, s=b; end, end
