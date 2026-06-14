function [G, W, info] = eval_bayesopt_holdout(opts)
%EVAL_BAYESOPT_HOLDOUT Fase 3 — validacao do theta_bayesopt no HOLD-OUT (nao
% visto no custo) vs (a) cinematica ideal e (b) vx/vy v2 + omega placeholder,
% RMSE SE(2) multi-horizonte + Wilcoxon pareado (por horizonte e pooled).
% Gate: promove se bater (b) significativamente (p<0.05, direcao certa).
%
% Simula APENAS o que e novo (theta_bayesopt e vx/vy v2 nos eventos de
% hold-out); a ideal e REUSADA das trajetorias salvas da campanha (sem
% re-rodar os 138 baselines). apply_theta UMA vez por modelo.

arguments
    opts.BoMat    (1,:) char = fullfile('models','sysid_bayesopt_v1_raw.mat')
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
    opts.Model    (1,:) char = 'parameter_estimation_model_pid_v3'
    opts.Dataset  (1,:) char = '2026-05-18_19-2-15'
end

bootstrap_paths();  warning('off','all');
try, Simulink.data.dictionary.closeAll('-discard'); catch, end
try, bdclose('all'); catch, end
system('git restore config/ssl_robot.sldd');
ensure_model_ready(opts.Model);
sldd_restore = onCleanup(@() system('git restore config/ssl_robot.sldd')); %#ok<NASGU>

B = load(opts.BoMat);  th_bo = B.theta_opt(:).';
vx = load_theta_mat(opts.VxvyMat);
th_vv = [vx.K_vx vx.tau_vx vx.Td_vx vx.K_vy vx.tau_vy vx.Td_vy vx.K_w vx.tau_w vx.Td_w];
C = load(opts.Campaign);  tr = C.traj;

cache = build_event_cache(opts.Holdout, 'Dataset', opts.Dataset);
ne = numel(cache);  H = opts.Horizons;  nh = numel(H);

% --- simula theta_bayesopt (apply 1x) ---
apply_theta('config/ssl_robot.sldd', th_bo);
BO = cell(ne,1);
for i = 1:ne, [x,y,t] = sim_aligned(opts.Model, cache(i).s); BO{i} = {x,y,t}; end
% --- simula vx/vy v2 (apply 1x) ---
apply_theta('config/ssl_robot.sldd', th_vv);
VV = cell(ne,1);
for i = 1:ne, [x,y,t] = sim_aligned(opts.Model, cache(i).s); VV{i} = {x,y,t}; end

% --- metrica SE2 por evento x horizonte (bo, vxvy, ideal) ------------------
rows = {};
for i = 1:ne
    ev = cache(i).event; t = cache(i).t;
    xt = cache(i).xt; yt = cache(i).yt; tht = cache(i).tht;
    id = tr(strcmp({tr.theta},'ideal_analytic') & strcmp({tr.event},ev));
    for k = 1:nh
        s_bo = rmse_pos_rebased_se2(t, BO{i}{1}, BO{i}{2}, BO{i}{3}, xt,yt,tht, H(k), opts.Overlap);
        s_vv = rmse_pos_rebased_se2(t, VV{i}{1}, VV{i}{2}, VV{i}{3}, xt,yt,tht, H(k), opts.Overlap);
        s_id = rmse_pos_rebased_se2(id.t, id.x_sim, id.y_sim, id.th_sim, ...
            id.x_truth, id.y_truth, id.th_truth, H(k), opts.Overlap);
        rows(end+1,:) = {ev, cache(i).label, H(k), s_bo, s_vv, s_id, s_bo-s_vv, s_bo-s_id}; %#ok<AGROW>
    end
end
G = cell2table(rows, 'VariableNames', {'event','label','horizonte_s', ...
    'se2_bo_m','se2_vxvy_m','se2_ideal_m','delta_bo_vxvy','delta_bo_ideal'});

% --- Wilcoxon por horizonte + pooled (bo vs vxvy ; bo vs ideal) ------------
wr = {};
for k = 1:nh
    sub = G(G.horizonte_s==H(k),:);
    wr(end+1,:) = wrow(H(k), sub); %#ok<AGROW>
end
wr(end+1,:) = wrow(NaN, G);
W = cell2table(wr, 'VariableNames', {'horizonte_s','n', ...
    'med_bo','med_vxvy','med_ideal','dlt_bo_vxvy','p_bo_vxvy','dlt_bo_ideal','p_bo_ideal'});

% --- gate ------------------------------------------------------------------
pooled = W(isnan(W.horizonte_s),:);
gate_vs_vxvy = (pooled.p_bo_vxvy < 0.05) && (pooled.dlt_bo_vxvy < 0);
verdict = ternary(gate_vs_vxvy, 'PROMOVER (bate vx/vy v2 em hold-out)', ...
    '_candidate (nao bate vx/vy v2 significativamente)');

fprintf('\n===== Fase 3: theta_bayesopt no HOLD-OUT (%d eventos) =====\n', ne);
fprintf('K_w(bayesopt)=%.4f vs 1.35 fisico -> %s\n', th_bo(7), ...
    ternary(th_bo(7)<1, 'K_w<1: tensao parametro-vs-comportamento (registrar)', 'K_w>=1'));
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
writetable(G, fullfile('results',sprintf('eval_bayesopt_holdout_%s.csv',stamp)));
writetable(W, fullfile('results',sprintf('eval_bayesopt_wilcoxon_%s.csv',stamp)));
info = struct('theta_bo',th_bo,'theta_vxvy',th_vv,'gate_vs_vxvy',gate_vs_vxvy, ...
    'verdict',verdict,'Kw_bo',th_bo(7),'BO',{BO},'VV',{VV},'cache',cache, ...
    'stamp',stamp,'J_opt',B.J_opt);
save(fullfile('results',sprintf('eval_bayesopt_holdout_%s.mat',stamp)),'G','W','info','-v7.3');
fprintf('Salvo: results/eval_bayesopt_holdout_%s.{csv,mat}\n', stamp);
end

% =========================================================================
function r = wrow(h, sub)
sg = @(a,b) sigp(a,b);
r = {h, height(sub), median(sub.se2_bo_m), median(sub.se2_vxvy_m), median(sub.se2_ideal_m), ...
     median(sub.delta_bo_vxvy), sg(sub.se2_bo_m, sub.se2_vxvy_m), ...
     median(sub.delta_bo_ideal), sg(sub.se2_bo_m, sub.se2_ideal_m)};
end
function p = sigp(a,b)
ok = ~isnan(a) & ~isnan(b);
if nnz(ok) >= 2, p = signrank(a(ok), b(ok)); else, p = NaN; end
end
function s = ternary(c,a,b), if c, s=a; else, s=b; end, end
