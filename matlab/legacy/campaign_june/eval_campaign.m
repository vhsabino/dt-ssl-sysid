function [T, M, traj_file] = eval_campaign(opts)
%EVAL_CAMPAIGN Campanha completa: 3 thetas x TODOS os splits validos do log,
% duas metricas por linha (rmse_pos_rebased translacao-so e
% rmse_pos_rebased_se2 pose completa, janelas POR TEMPO, h=2.5 s/overlap
% 0.5). "Valido" = canonical_split + load_split + simulacao ok; falhas
% entram na tabela com status de erro (nao interrompem a campanha).
% Salva todas as trajetorias (results/traj_eval_campaign_<stamp>.mat),
% CSV por evento e CSV de medianas por label x theta. A tabela por evento
% e regravada apos cada evento (acompanhamento de progresso).

arguments
    opts.Log       (1,:) char   = '2026-05-18_19-2-15'
    opts.ModelName (1,:) char   = 'parameter_estimation_model_pid_v3'
    opts.WindowSec (1,1) double = 2.5
    opts.Overlap   (1,1) double = 0.5
    opts.Seed      (1,1) double = 42
end

THETAS = { % nome, tipo, fonte (mesmos tres de eval_theta_full_se2)
    'ideal_analytic',      'analytic', ''
    'procest_placeholder', 'mat', fullfile('models','sysid_initial.mat')
    'procest_w_cand',      'mat', fullfile('models','sysid_initial_v2_candidate.mat')
    };

repo_root = bootstrap_paths();
rng(opts.Seed);
[~, githash] = system(sprintf('git -C "%s" rev-parse --short HEAD', repo_root));
githash = strtrim(githash);
Simulink.data.dictionary.closeAll('-discard');
ensure_model_ready(opts.ModelName);
sldd_restore = onCleanup(@() system(sprintf( ...
    'git -C "%s" restore config/ssl_robot.sldd', repo_root))); %#ok<NASGU>

splits_root = fullfile(repo_root,'data','extracted',opts.Log,'splits');
L = dir(splits_root);  L = {L([L.isdir] & ~startsWith({L.name},'.')).name};
events = {};
for li = 1:numel(L)
    E = dir(fullfile(splits_root, L{li}));
    E = {E([E.isdir] & ~startsWith({E.name},'.')).name};
    for ei = 1:numel(E), events(end+1,:) = {L{li}, E{ei}}; end %#ok<AGROW>
end
fprintf('Campanha: %d eventos x %d thetas\n', size(events,1), size(THETAS,1));

stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
outcsv = fullfile('results', sprintf('eval_campaign_%s.csv', stamp));
rows = {};
traj = struct('label',{},'event',{},'theta',{},'t',{}, ...
    'x_sim',{},'y_sim',{},'th_sim',{},'x_truth',{},'y_truth',{},'th_truth',{});
for e = 1:size(events,1)
    [label_, event_] = events{e,:};
    fprintf('[%2d/%2d] %s/%s\n', e, size(events,1), label_, event_);
    try
        canon = canonical_split(fullfile(splits_root, label_, event_, ...
            'commands.parquet'));
        s = load_split(canon);
    catch ME
        msg = regexprep(strrep(ME.message, newline, ' '), '<[^>]+>', '');
        for k = 1:size(THETAS,1)
            rows(end+1,:) = {label_, event_, THETAS{k,1}, opts.WindowSec, ...
                NaN, NaN, ['split: ' msg]}; %#ok<AGROW>
        end
        writetable(cell2table(rows, 'VariableNames', {'label','event','theta', ...
            'horizonte_s','rmse_trans_m','rmse_se2_m','status'}), outcsv);
        continue
    end
    xt = s.pos_x_truth.Data;  yt = s.pos_y_truth.Data;
    tht = s.theta_truth.Data; tt = s.t;
    for k = 1:size(THETAS,1)
        [tname, kind, src] = THETAS{k,:};
        try
            if strcmp(kind, 'analytic')
                [xs, ys, ths] = ideal_deadreckoning(s);
            else
                out = run_one_mat(opts.ModelName, canon, src);
                [tsim, px, py] = extract_sim_position(out);
                pth = out.get('theta_aligned');
                xs  = interp1(tsim, px, tt, 'linear', 'extrap');
                ys  = interp1(tsim, py, tt, 'linear', 'extrap');
                ths = interp1(pth.Time, squeeze(pth.Data), tt, 'linear', 'extrap');
            end
            r_tr  = rmse_pos_rebased(tt, xs, ys, xt, yt, ...
                opts.WindowSec, opts.Overlap);
            r_se2 = rmse_pos_rebased_se2(tt, xs, ys, ths, xt, yt, tht, ...
                opts.WindowSec, opts.Overlap);
            traj(end+1) = struct('label',label_,'event',event_,'theta',tname, ...
                't',tt,'x_sim',xs,'y_sim',ys,'th_sim',ths, ...
                'x_truth',xt,'y_truth',yt,'th_truth',tht); %#ok<AGROW>
            rows(end+1,:) = {label_, event_, tname, opts.WindowSec, ...
                r_tr, r_se2, 'ok'}; %#ok<AGROW>
            fprintf('    %-20s trans %.4f | se2 %.4f\n', tname, r_tr, r_se2);
        catch ME
            msg = regexprep(strrep(ME.message, newline, ' '), '<[^>]+>', '');
            rows(end+1,:) = {label_, event_, tname, opts.WindowSec, ...
                NaN, NaN, msg}; %#ok<AGROW>
            fprintf('    %-20s ERRO: %s\n', tname, msg);
        end
    end
    T = cell2table(rows, 'VariableNames', {'label','event','theta', ...
        'horizonte_s','rmse_trans_m','rmse_se2_m','status'});
    writetable(T, outcsv);   % progresso incremental
end

% --- medianas por label x theta ---
okm = strcmp(T.status, 'ok');
M = groupsummary(T(okm,:), {'label','theta'}, 'median', ...
    {'rmse_trans_m','rmse_se2_m'});
% mediana global por theta
Mg = groupsummary(T(okm,:), 'theta', 'median', {'rmse_trans_m','rmse_se2_m'});
medcsv = fullfile('results', sprintf('eval_campaign_medianas_%s.csv', stamp));
writetable(M, medcsv);

traj_file = fullfile('results', sprintf('traj_eval_campaign_%s.mat', stamp));
meta = struct('script','automation/eval_campaign.m','commit',githash, ...
    'seed',opts.Seed,'window_sec',opts.WindowSec,'overlap',opts.Overlap, ...
    'model',opts.ModelName,'dataset',['data/extracted/' opts.Log], ...
    'thetas',{THETAS},'generated',char(datetime('now')));
save(traj_file, 'traj', 'meta', '-v7.3');
fprintf('Salvo: %s\n        %s\n        %s\n', outcsv, medcsv, traj_file);

fprintf('\nLinhas ok: %d/%d\n', nnz(okm), height(T));
disp(M); disp(Mg);
end
