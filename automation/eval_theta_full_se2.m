function [T, traj_file] = eval_theta_full_se2(opts)
%EVAL_THETA_FULL_SE2 Re-execucao do eval de 2026-06-11 (6 eventos x 3 thetas,
% modelo limpo, zonas mortas = 0) computando DUAS metricas por linha:
%   rmse_trans_m — re-ancora de translacao por janela (rmse_pos_rebased,
%                  identica a do eval anterior, h=2.5 s / overlap 0.5);
%   rmse_se2_m   — re-ancora de pose completa (x,y,theta): transformacao
%                  rigida sim->truth em t0 de cada janela
%                  (rmse_pos_rebased_se2, mesma janela/pesos).
% Teste H-a do diagnostico aberto (deriva de heading em replay open-loop).
% Salva tambem as 18 trajetorias (t, sim x/y/theta, truth x/y/theta) em
% results/traj_eval_theta_full_se2_<stamp>.mat para reuso sem re-simular.

arguments
    opts.Events cell = { ...
        'square',        'square_01_01'
        'shoot_to_goal', 'shoot_to_goal_05_02'
        'shoot_to_goal', 'shoot_to_goal_08_01'
        'shoot_to_goal', 'shoot_to_goal_09_01'
        'shoot_to_goal', 'shoot_to_goal_12_01'
        'shoot_to_goal', 'shoot_to_goal_14_02'}
    opts.ModelName (1,:) char = 'parameter_estimation_model_pid_v3'
    opts.WindowSec (1,1) double = 2.5
    opts.Overlap   (1,1) double = 0.5
    opts.Seed      (1,1) double = 42
end

THETAS = { % nome, tipo, fonte (mesmos tres do eval de 17:30)
    'ideal_analytic',      'analytic', ''
    'procest_placeholder', 'mat', fullfile('results','sysid_initial.mat')
    'procest_w_cand',      'mat', fullfile('models','sysid_initial_v2_candidate.mat')
    };

repo_root = bootstrap_paths();
rng(opts.Seed);
% Proveniencia capturada ANTES da rodada (apply_theta suja o SLDD).
[~, githash] = system(sprintf('git -C "%s" rev-parse --short HEAD', repo_root));
githash = strtrim(githash);
% SLDD pode ter ficado stale de um git restore em sessao anterior.
Simulink.data.dictionary.closeAll('-discard');
ensure_model_ready(opts.ModelName);
sldd_restore = onCleanup(@() system(sprintf( ...
    'git -C "%s" restore config/ssl_robot.sldd', repo_root))); %#ok<NASGU>

rows = {};
traj = struct('label',{},'event',{},'theta',{},'t',{}, ...
    'x_sim',{},'y_sim',{},'th_sim',{},'x_truth',{},'y_truth',{},'th_truth',{});
for e = 1:size(opts.Events,1)
    [label_, event_] = opts.Events{e,:};
    cmd_path = fullfile(repo_root,'data','extracted','2026-05-18_19-2-15', ...
        'splits', label_, event_, 'commands.parquet');
    canon = canonical_split(cmd_path);
    s = load_split(canon);
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
            fprintf('  %s x %-20s -> trans %.4f m | se2 %.4f m\n', ...
                event_, tname, r_tr, r_se2);
        catch ME
            msg = regexprep(strrep(ME.message, newline, ' '), '<[^>]+>', '');
            rows(end+1,:) = {label_, event_, tname, opts.WindowSec, ...
                NaN, NaN, msg}; %#ok<AGROW>
            fprintf('  %s x %-20s -> ERRO: %s\n', event_, tname, msg);
        end
    end
end

T = cell2table(rows, 'VariableNames', ...
    {'label','event','theta','horizonte_s','rmse_trans_m','rmse_se2_m','status'});

stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
outcsv = fullfile('results', sprintf('eval_theta_full_se2_%s.csv', stamp));
writetable(T, outcsv);
traj_file = fullfile('results', sprintf('traj_eval_theta_full_se2_%s.mat', stamp));
meta = struct('script','automation/eval_theta_full_se2.m', ...
    'commit',githash,'seed',opts.Seed,'window_sec',opts.WindowSec, ...
    'overlap',opts.Overlap,'model',opts.ModelName, ...
    'dataset','data/extracted/2026-05-18_19-2-15', ...
    'thetas',{THETAS},'generated',char(datetime('now')));
save(traj_file, 'traj', 'meta', '-v7.3');
fprintf('Salvo: %s\n        %s\n', outcsv, traj_file);

fprintf('\nMedianas por theta (linhas ok):\n');
for k = 1:size(THETAS,1)
    m = strcmp(T.theta, THETAS{k,1}) & strcmp(T.status, 'ok');
    fprintf('  %-20s trans %.4f m | se2 %.4f m  (n=%d)\n', THETAS{k,1}, ...
        median(T.rmse_trans_m(m)), median(T.rmse_se2_m(m)), nnz(m));
end
end
