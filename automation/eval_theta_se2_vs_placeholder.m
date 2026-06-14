function [W, T, traj_file] = eval_theta_se2_vs_placeholder(candMat, label, opts)
%EVAL_THETA_SE2_VS_PLACEHOLDER Fase 3 (gate) — custo SE(2) multi-horizonte de
% um theta candidato vs o placeholder, nos eventos de um label, com Wilcoxon
% pareado. Simula APENAS o candidato (run_one_mat, mesmo pipeline da campanha);
% o placeholder e REUSADO das trajetorias Simulink salvas
% (results/traj_eval_campaign_*.mat) — NAO re-roda os 138 baselines.
% Generaliza eval_omega_v3_se2 para qualquer candidato/label.

arguments
    candMat (1,:) char
    label   (1,:) char
    opts.Campaign (1,:) char = fullfile('results','traj_eval_campaign_20260611_2238.mat')
    opts.Model    (1,:) char = 'parameter_estimation_model_pid_v3'
    opts.Horizons (1,:) double = [0.5 1 2 2.5 4]
    opts.Overlap  (1,1) double = 0.5
    opts.Seed     (1,1) double = 42
    opts.Dataset  (1,:) char = '2026-05-18_19-2-15'
    opts.Tag      (1,:) char = 'cand'
end

repo_root = bootstrap_paths();  rng(opts.Seed);
C = load(opts.Campaign);  traj = C.traj;
isP = strcmp({traj.theta},'procest_placeholder') & strcmp({traj.label},label);
idxP = find(isP);
fprintf('Eventos %s (placeholder salvo): %d\n', label, numel(idxP));

[~, githash] = system(sprintf('git -C "%s" rev-parse --short HEAD', repo_root));
githash = strtrim(githash);
Simulink.data.dictionary.closeAll('-discard');
ensure_model_ready(opts.Model);
sldd_restore = onCleanup(@() system(sprintf( ...
    'git -C "%s" restore config/ssl_robot.sldd', repo_root))); %#ok<NASGU>

rows = {};
traj_c = struct('label',{},'event',{},'t',{},'x_sim',{},'y_sim',{},'th_sim',{});
for j = 1:numel(idxP)
    tr = traj(idxP(j));  ev = tr.event;
    try
        cmd = fullfile(repo_root,'data','extracted',opts.Dataset,'splits',label,ev,'commands.parquet');
        canon = canonical_split(cmd);
        out = run_one_mat(opts.Model, canon, candMat);
        [tsim, px, py] = extract_sim_position(out);
        pth = out.get('theta_aligned');
        xc = interp1(tsim, px, tr.t, 'linear', 'extrap');
        yc = interp1(tsim, py, tr.t, 'linear', 'extrap');
        thc= interp1(pth.Time, squeeze(pth.Data), tr.t, 'linear', 'extrap');
        traj_c(end+1) = struct('label',label,'event',ev,'t',tr.t, ...
            'x_sim',xc,'y_sim',yc,'th_sim',thc); %#ok<AGROW>
        for h = opts.Horizons
            rc = rmse_pos_rebased_se2(tr.t, xc,yc,thc, tr.x_truth,tr.y_truth,tr.th_truth, h, opts.Overlap);
            rp = rmse_pos_rebased_se2(tr.t, tr.x_sim,tr.y_sim,tr.th_sim, tr.x_truth,tr.y_truth,tr.th_truth, h, opts.Overlap);
            rows(end+1,:) = {ev, h, rc, rp, rc-rp}; %#ok<AGROW>
        end
        fprintf('  %-22s ok\n', ev);
    catch ME
        fprintf('  %-22s ERRO: %s\n', ev, regexprep(strrep(ME.message,newline,' '),'<[^>]+>',''));
    end
end
T = cell2table(rows, 'VariableNames', {'event','horizonte_s','se2_cand_m','se2_plac_m','delta_m'});

wr = {};
for h = opts.Horizons
    sub = T(T.horizonte_s==h, :); rc = sub.se2_cand_m; rp = sub.se2_plac_m;
    ok = ~isnan(rc) & ~isnan(rp);
    p = NaN; if nnz(ok) >= 2, p = signrank(rc(ok), rp(ok)); end
    wr(end+1,:) = {h, nnz(ok), median(rc(ok)), median(rp(ok)), median(rc(ok)-rp(ok)), p}; %#ok<AGROW>
end
okall = ~isnan(T.se2_cand_m) & ~isnan(T.se2_plac_m);
wr(end+1,:) = {NaN, nnz(okall), median(T.se2_cand_m(okall)), median(T.se2_plac_m(okall)), ...
    median(T.delta_m(okall)), signrank(T.se2_cand_m(okall), T.se2_plac_m(okall))};
W = cell2table(wr, 'VariableNames', ...
    {'horizonte_s','n','median_cand_m','median_plac_m','median_delta_m','p_wilcoxon'});

fprintf('\n===== SE(2) multi-horizonte: %s candidato vs placeholder (%s) =====\n', opts.Tag, label);
fprintf('%-8s %4s %12s %12s %12s %10s\n','h(s)','n','med_cand','med_plac','med_delta','p_wilcox');
for k = 1:height(W)
    if isnan(W.horizonte_s(k)), hs='pool'; else, hs=sprintf('%.1f',W.horizonte_s(k)); end
    fprintf('%-8s %4d %12.4f %12.4f %+12.4f %10.3g\n', hs, W.n(k), ...
        W.median_cand_m(k), W.median_plac_m(k), W.median_delta_m(k), W.p_wilcoxon(k));
end
fprintf('(delta<0 = candidato MELHOR que placeholder)\n');

stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
csv  = fullfile('results', sprintf('eval_%s_se2_%s.csv', opts.Tag, stamp));
wcsv = fullfile('results', sprintf('eval_%s_wilcoxon_%s.csv', opts.Tag, stamp));
writetable(T, csv); writetable(W, wcsv);
traj_file = fullfile('results', sprintf('traj_eval_%s_%s.mat', opts.Tag, stamp));
meta = struct('script','automation/eval_theta_se2_vs_placeholder.m','commit',githash, ...
    'seed',opts.Seed,'overlap',opts.Overlap,'model',opts.Model,'cand_mat',candMat, ...
    'label',label,'campaign',opts.Campaign,'tag',opts.Tag,'generated',char(datetime('now')));
save(traj_file, 'traj_c','T','W','meta','-v7.3');
fprintf('Salvo: %s\n        %s\n        %s\n', csv, wcsv, traj_file);
end
