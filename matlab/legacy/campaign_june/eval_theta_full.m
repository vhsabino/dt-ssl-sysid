function T = eval_theta_full(opts)
%EVAL_THETA_FULL Avaliacao do theta composto (vx/vy do sysid_initial +
% omega do candidato) no modelo limpo (zonas mortas = 0), contra o
% placeholder e o baseline ideal analitico. Eventos: square_01_01 +
% os 5 hold-outs da identificacao omega (seed 42, 2026-06-11).
% Metrica: rmse_pos_rebased, janela 2.5 s / overlap 0.5.

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

THETAS = { % nome, tipo, fonte
    'ideal_analytic',      'analytic', ''
    'procest_placeholder', 'mat', fullfile('models','sysid_initial.mat')
    'procest_w_cand',      'mat', fullfile('models','sysid_initial_v2_candidate.mat')
    };

repo_root = bootstrap_paths();
rng(opts.Seed);
ensure_model_ready(opts.ModelName);
sldd_restore = onCleanup(@() system(sprintf( ...
    'git -C "%s" restore config/ssl_robot.sldd', repo_root))); %#ok<NASGU>

rows = {};
for e = 1:size(opts.Events,1)
    [label_, event_] = opts.Events{e,:};
    cmd_path = fullfile(repo_root,'data','extracted','2026-05-18_19-2-15', ...
        'splits', label_, event_, 'commands.parquet');
    canon = canonical_split(cmd_path);
    s = load_split(canon);
    xt = s.pos_x_truth.Data;  yt = s.pos_y_truth.Data;  tt = s.t;
    for k = 1:size(THETAS,1)
        [tname, kind, src] = THETAS{k,:};
        try
            if strcmp(kind, 'analytic')
                [xs, ys] = ideal_deadreckoning(s);
            else
                out = run_one_mat(opts.ModelName, canon, src);
                [tsim, px, py] = extract_sim_position(out);
                xs = interp1(tsim, px, tt, 'linear', 'extrap');
                ys = interp1(tsim, py, tt, 'linear', 'extrap');
            end
            r = rmse_pos_rebased(tt, xs, ys, xt, yt, opts.WindowSec, opts.Overlap);
            rows(end+1,:) = {label_, event_, tname, opts.WindowSec, r, 'ok'}; %#ok<AGROW>
            fprintf('  %s x %-20s -> %.4f m\n', event_, tname, r);
        catch ME
            msg = regexprep(strrep(ME.message, newline, ' '), '<[^>]+>', '');
            rows(end+1,:) = {label_, event_, tname, opts.WindowSec, NaN, msg}; %#ok<AGROW>
            fprintf('  %s x %-20s -> ERRO: %s\n', event_, tname, msg);
        end
    end
end

T = cell2table(rows, 'VariableNames', ...
    {'label','event','theta','horizonte_s','rmse_pos_m','status'});

stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
outcsv = fullfile('results', sprintf('eval_theta_full_%s.csv', stamp));
writetable(T, outcsv);
fprintf('Salvo: %s\n', outcsv);
end
