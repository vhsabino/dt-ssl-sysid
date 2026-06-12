function [T, M] = eval_horizons(traj_file, opts)
%EVAL_HORIZONS RMSE re-ancorado (translacao e pose SE(2) com theta truth
% filtrado na ancora) em multiplos horizontes, computado das TRAJETORIAS
% salvas da campanha (results/traj_eval_campaign_*.mat) — sem re-simular:
% a metrica e pos-processamento e as simulacoes sao deterministicas (seed
% e theta registrados no meta do .mat). Janelas POR TEMPO, overlap 0.5.
% Saidas: CSV por evento x theta x horizonte e CSV de medianas por
% (label + global) x theta x horizonte (consumido por fig_f4_horizons).

arguments
    traj_file (1,:) char
    opts.Horizons (1,:) double = [0.5 1 2 2.5 4]
    opts.Overlap  (1,1) double = 0.5
end

S = load(traj_file);  traj = S.traj;
rows = {};
for i = 1:numel(traj)
    tr = traj(i);
    for h = opts.Horizons
        r_tr  = rmse_pos_rebased(tr.t, tr.x_sim, tr.y_sim, ...
            tr.x_truth, tr.y_truth, h, opts.Overlap);
        r_se2 = rmse_pos_rebased_se2(tr.t, tr.x_sim, tr.y_sim, tr.th_sim, ...
            tr.x_truth, tr.y_truth, tr.th_truth, h, opts.Overlap);
        rows(end+1,:) = {tr.label, tr.event, tr.theta, h, r_tr, r_se2}; %#ok<AGROW>
    end
end
T = cell2table(rows, 'VariableNames', ...
    {'label','event','theta','horizonte_s','rmse_trans_m','rmse_se2_m'});

% medianas por label x theta x horizonte + global
M = groupsummary(T, {'label','theta','horizonte_s'}, 'median', ...
    {'rmse_trans_m','rmse_se2_m'});
Mg = groupsummary(T, {'theta','horizonte_s'}, 'median', ...
    {'rmse_trans_m','rmse_se2_m'});
Mg.label = repmat({'global'}, height(Mg), 1);
M = [M(:, {'label','theta','horizonte_s','GroupCount', ...
    'median_rmse_trans_m','median_rmse_se2_m'}); ...
     Mg(:, {'label','theta','horizonte_s','GroupCount', ...
    'median_rmse_trans_m','median_rmse_se2_m'})];

stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
outcsv = fullfile('results', sprintf('eval_horizons_%s.csv', stamp));
medcsv = fullfile('results', sprintf('eval_horizons_medianas_%s.csv', stamp));
writetable(T, outcsv);
writetable(M, medcsv);
fprintf('Fonte: %s (commit %s)\n', traj_file, S.meta.commit);
fprintf('Salvo: %s\n        %s\n', outcsv, medcsv);
end
