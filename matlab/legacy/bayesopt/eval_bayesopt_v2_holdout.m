function [G, W, info] = eval_bayesopt_v2_holdout(opts)
%EVAL_BAYESOPT_V2_HOLDOUT Fase 3 (Caminho 2) — confirma o theta otimo do PROXY
% no SIMULINK FIEL: (1) gate hold-out vs (a) cinematica ideal e (b) vx/vy v2 +
% omega placeholder, RMSE SE(2) multi-horizonte + Wilcoxon pareado (por horizonte
% e pooled); (2) quao perto o proxy estava — J_Simulink vs J_proxy de theta_opt
% no MESMO conjunto (treino amplo e hold-out).
%
% Simula APENAS o novo (theta_bo nos 18 de treino + 10 de hold-out; vx/vy v2 nos
% 10 de hold-out). A ideal e REUSADA das trajetorias salvas da campanha (sem
% re-rodar os 138 baselines). apply_theta UMA vez por modelo. Gate: promove se
% bater (b) significativamente (p<0.05, direcao certa) no hold-out, no Simulink.

arguments
    opts.BoMat    (1,:) char = fullfile('models','sysid_bayesopt_v2_raw.mat')
    opts.TrainMat (1,:) char = fullfile('build','bo_proxy_train_v2.mat')
    opts.VxvyMat  (1,:) char = fullfile('models','sysid_vxvy_v2.mat')
    opts.Campaign (1,:) char = fullfile('results','traj_eval_campaign_20260611_2238.mat')
    opts.Holdout  cell = { ...
        'front_to_back','front_to_back_01_01'
        'side_to_side','side_to_side_01_05'
        'side_to_side','side_to_side_01_06'
        'side_to_side','side_to_side_01_07'
        'side_to_side','side_to_side_02_03'
        'shoot_to_goal','shoot_to_goal_05_02'
        'shoot_to_goal','shoot_to_goal_08_01'
        'shoot_to_goal','shoot_to_goal_09_01'
        'shoot_to_goal','shoot_to_goal_12_01'
        'shoot_to_goal','shoot_to_goal_14_02'}
    opts.Horizons (1,:) double = [0.5 1 2 2.5 4]
    opts.Overlap  (1,1) double = 0.5
    opts.Lambda   (1,1) double = 1.171
    opts.Model    (1,:) char = 'parameter_estimation_model_pid_v3'
    opts.Dataset  (1,:) char = '2026-05-18_19-2-15'
end

here = fileparts(mfilename('fullpath'));
addpath(fullfile(here,'..','..')); repo_root = bootstrap_paths('legacy'); cd(repo_root); %#ok<NASGU> % legado: caminhos relativos abaixo assumem pwd == raiz do repo
warning('off','all');
try, Simulink.data.dictionary.closeAll('-discard'); catch, end
try, bdclose('all'); catch, end
system('git restore config/ssl_robot.sldd');
ensure_model_ready(opts.Model);
sldd_restore = onCleanup(@() system('git restore config/ssl_robot.sldd'));

B = load(opts.BoMat);  th_bo = B.theta_opt(:).';
J_train_proxy = B.J_opt;
vx = load_theta_mat(opts.VxvyMat);
th_vv = [vx.K_vx vx.tau_vx vx.Td_vx vx.K_vy vx.tau_vy vx.Td_vy vx.K_w vx.tau_w vx.Td_w];
C = load(opts.Campaign);  tr = C.traj;
T = load(opts.TrainMat);  cacheTr = T.cacheTr;

cache = build_event_cache(opts.Holdout, 'Dataset', opts.Dataset);
ne = numel(cache);  H = opts.Horizons;  nh = numel(H);  lam = opts.Lambda;

% ===== theta_bayesopt: apply 1x, simula treino (J_sim_train) e hold-out =====
apply_theta('config/ssl_robot.sldd', th_bo);
[J_sim_train, ~] = bo_cost(th_bo, cacheTr, 'Lambda', lam, 'ApplyTheta', false);  % 18 sims
BO = cell(ne,1); se2_bo = nan(ne,nh); head_bo = nan(ne,nh);
for i = 1:ne
    [x,y,th] = sim_aligned(opts.Model, cache(i).s);  BO{i} = {x,y,th};
    for k = 1:nh
        se2_bo(i,k)  = rmse_pos_rebased_se2(cache(i).t, x,y,th, cache(i).xt,cache(i).yt,cache(i).tht, H(k), opts.Overlap);
        head_bo(i,k) = rmse_heading_rebased(cache(i).t, th, cache(i).tht, H(k), opts.Overlap);
    end
end
% ===== vx/vy v2: apply 1x, simula hold-out =====
apply_theta('config/ssl_robot.sldd', th_vv);
VV = cell(ne,1);
for i = 1:ne, [x,y,th] = sim_aligned(opts.Model, cache(i).s); VV{i} = {x,y,th}; end

% ===== J proxy vs Simulink (treino amplo e hold-out) =====
wts = (1./H)/sum(1./H);
J_sim_hold   = median(se2_bo*wts.','omitnan') + lam*median(head_bo*wts.','omitnan');
J_proxy_hold = bo_cost_proxy(th_bo, cache,   'Lambda', lam);
J_proxy_tr   = bo_cost_proxy(th_bo, cacheTr, 'Lambda', lam);

% ===== metrica SE(2) por evento x horizonte (bo, vxvy, ideal) =====
rows = {};
for i = 1:ne
    ev = cache(i).event; t = cache(i).t;
    xt = cache(i).xt; yt = cache(i).yt; tht = cache(i).tht;
    id = tr(strcmp({tr.theta},'ideal_analytic') & strcmp({tr.event},ev));
    for k = 1:nh
        s_bo = se2_bo(i,k);
        s_vv = rmse_pos_rebased_se2(t, VV{i}{1}, VV{i}{2}, VV{i}{3}, xt,yt,tht, H(k), opts.Overlap);
        s_id = rmse_pos_rebased_se2(id.t, id.x_sim, id.y_sim, id.th_sim, ...
            id.x_truth, id.y_truth, id.th_truth, H(k), opts.Overlap);
        rows(end+1,:) = {ev, cache(i).label, H(k), s_bo, s_vv, s_id, s_bo-s_vv, s_bo-s_id}; %#ok<AGROW>
    end
end
G = cell2table(rows, 'VariableNames', {'event','label','horizonte_s', ...
    'se2_bo_m','se2_vxvy_m','se2_ideal_m','delta_bo_vxvy','delta_bo_ideal'});

% ===== Wilcoxon por horizonte + pooled =====
wr = {};
for k = 1:nh, wr(end+1,:) = wrow(H(k), G(G.horizonte_s==H(k),:)); end %#ok<AGROW>
wr(end+1,:) = wrow(NaN, G);
W = cell2table(wr, 'VariableNames', {'horizonte_s','n', ...
    'med_bo','med_vxvy','med_ideal','dlt_bo_vxvy','p_bo_vxvy','dlt_bo_ideal','p_bo_ideal'});

% ===== gate =====
pooled = W(isnan(W.horizonte_s),:);
gate_vs_vxvy = (pooled.p_bo_vxvy < 0.05) && (pooled.dlt_bo_vxvy < 0);
verdict = ternary(gate_vs_vxvy, 'PROMOVER (bate vx/vy v2 em hold-out, Simulink)', ...
    '_candidate (nao bate vx/vy v2 significativamente)');

fprintf('\n===== Fase 3 (v2): theta_bayesopt PROXY confirmado no SIMULINK FIEL =====\n');
fprintf('theta_opt = %s\n', mat2str(round(th_bo,4)));
fprintf('K_w(bayesopt)=%.4f vs 1.35 fisico -> %s\n', th_bo(7), ...
    ternary(th_bo(7)<1, 'K_w<1: tensao parametro-vs-comportamento (registrar)', 'K_w>=1'));
fprintf('--- Proxy vs Simulink no theta_opt (quao perto o proxy estava) ---\n');
fprintf('  TREINO (18 ev):  J_proxy=%.4f  J_sim=%.4f  (dif %+.4f)  [proxy recheck=%.4f]\n', ...
    J_train_proxy, J_sim_train, J_sim_train-J_train_proxy, J_proxy_tr);
fprintf('  HOLD-OUT (10 ev): J_proxy=%.4f  J_sim=%.4f  (dif %+.4f)\n', J_proxy_hold, J_sim_hold, J_sim_hold-J_proxy_hold);
fprintf('--- Gate hold-out (SE(2) multi-horizonte) ---\n');
fprintf('%-6s %3s %8s %8s %8s | %9s %9s | %9s %9s\n','h','n','med_bo','med_vv','med_id', ...
    'd(bo-vv)','p(bo-vv)','d(bo-id)','p(bo-id)');
for k=1:height(W)
    if isnan(W.horizonte_s(k)), hs='pool'; else, hs=sprintf('%.1f',W.horizonte_s(k)); end
    fprintf('%-6s %3d %8.4f %8.4f %8.4f | %+9.4f %9.3g | %+9.4f %9.3g\n', hs, W.n(k), ...
        W.med_bo(k),W.med_vxvy(k),W.med_ideal(k),W.dlt_bo_vxvy(k),W.p_bo_vxvy(k), ...
        W.dlt_bo_ideal(k),W.p_bo_ideal(k));
end
fprintf('GATE (vs vx/vy v2): %s\n', verdict);

stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
writetable(G, fullfile('results',sprintf('eval_bayesopt_v2_holdout_%s.csv',stamp)));
writetable(W, fullfile('results',sprintf('eval_bayesopt_v2_wilcoxon_%s.csv',stamp)));
info = struct('theta_bo',th_bo,'theta_vxvy',th_vv,'gate_vs_vxvy',gate_vs_vxvy, ...
    'verdict',verdict,'Kw_bo',th_bo(7),'BO',{BO},'VV',{VV},'cache',cache, ...
    'J_train_proxy',J_train_proxy,'J_sim_train',J_sim_train, ...
    'J_proxy_hold',J_proxy_hold,'J_sim_hold',J_sim_hold,'stamp',stamp);
save(fullfile('results',sprintf('eval_bayesopt_v2_holdout_%s.mat',stamp)),'G','W','info','-v7.3');
fprintf('Salvo: results/eval_bayesopt_v2_holdout_%s.{csv,mat}\n', stamp);
end

% =========================================================================
function r = wrow(h, sub)
r = {h, height(sub), median(sub.se2_bo_m), median(sub.se2_vxvy_m), median(sub.se2_ideal_m), ...
     median(sub.delta_bo_vxvy), sigp(sub.se2_bo_m, sub.se2_vxvy_m), ...
     median(sub.delta_bo_ideal), sigp(sub.se2_bo_m, sub.se2_ideal_m)};
end
function p = sigp(a,b)
ok = ~isnan(a) & ~isnan(b);
if nnz(ok) >= 2, p = signrank(a(ok), b(ok)); else, p = NaN; end
end
function s = ternary(c,a,b), if c, s=a; else, s=b; end, end
