function fig_f3_compare_omega(opts)
%FIG_F3_COMPARE_OMEGA F3: montagem do compare() da identificacao omega nos
% 14 eventos qualificados (modelo candidato P1D de
% models/sysid_initial_v2_candidate.mat), com fit% NRMSE por evento e
% rotulo TREINO/HOLD-OUT (particao do report, seed 42). O iddata por evento
% e reconstruido com o MESMO processamento de
% identify_omega_from_splits>build_omega_iddata (regrade uniforme Ts=1/60,
% u=move_w ZOH, y=d/dt unwrap(position_w) sgolay, detrend) — manter em
% sincronia com aquele local function (nao exportada). PNG+PDF em
% results/figs/.

arguments
    opts.Log  (1,:) char   = '2026-05-18_19-2-15'
    opts.Ts   (1,1) double = 1/60
    opts.Team (1,:) char   = 'allies'
end

repo_root = bootstrap_paths();
C = load(fullfile('models','sysid_initial_v2_candidate.mat'), 'model_w', 'report');
evs = [C.report.events_train(:); C.report.events_holdout(:)];
tags = [repmat({'TREINO'}, numel(C.report.events_train), 1); ...
        repmat({'HOLD-OUT'}, numel(C.report.events_holdout), 1)];
[evs, si] = sort(evs);  tags = tags(si);

f = figure('Visible','off','Position',[40 40 1500 950]);
tl = tiledlayout(f, 4, 4, 'TileSpacing','compact', 'Padding','compact');
for i = 1:numel(evs)
    ev = evs{i};
    d = build_omega_iddata_local(repo_root, opts.Log, 'shoot_to_goal', ev, ...
        opts.Ts, opts.Team);
    ax = nexttile(tl);
    if isempty(d)
        title(ax, sprintf('%s — sem dados', ev), 'Interpreter','none');
        continue
    end
    [ysim, fit] = compare(d, C.model_w);
    tgrid = (0:numel(d.y)-1) * opts.Ts;
    hold(ax,'on');
    plot(ax, tgrid, d.y, '-', 'Color', [0 0 0], 'LineWidth', 1.0);
    plot(ax, tgrid, ysim.OutputData, '--', 'Color', [.85 .2 .1], 'LineWidth', 1.0);
    grid(ax,'on'); set(ax,'FontSize',7);
    short = strrep(ev, 'shoot_to_goal_', 'stg ');
    title(ax, sprintf('%s — %s — fit %.1f%%', short, tags{i}, fit(1)), ...
        'FontSize', 8, 'Interpreter','none');
    if mod(i-1,4)==0, ylabel(ax,'\omega [rad/s]'); end
    if i > 10, xlabel(ax,'t [s]'); end
end
lg = legend({'\omega medido (sgolay)','modelo P1D candidato'}, ...
    'Orientation','horizontal', 'FontSize', 9);
lg.Layout.Tile = 'south';
title(tl, sprintf(['F3 — compare() da identificacao \\omega ' ...
    '(K=%.3f, \\tau=%.4f, Td=%.4f) nos 14 eventos qualificados'], ...
    C.model_w.Kp, C.model_w.Tp1, C.model_w.Td), 'FontSize', 11);

figdir = fullfile('results','figs');
if ~isfolder(figdir), mkdir(figdir); end
stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
exportgraphics(f, fullfile(figdir, sprintf('F3_compare_omega_%s.png', stamp)), ...
    'Resolution', 180);
exportgraphics(f, fullfile(figdir, sprintf('F3_compare_omega_%s.pdf', stamp)));
close(f);
fprintf('F3 salva em %s (F3_compare_omega_%s.{png,pdf})\n', figdir, stamp);
end

% =========================================================================
function d = build_omega_iddata_local(repo_root, log_, label_, event_, Ts, team)
% Copia 1:1 de identify_omega_from_splits>build_omega_iddata (local, nao
% exportavel sem tocar naquele arquivo).
ev_dir = fullfile(repo_root, 'data','extracted', log_, 'splits', label_, event_);
C = parquetread(fullfile(ev_dir, 'commands.parquet'));
rid = mode(double(C.robot_id));
C = C(double(C.robot_id) == rid, :);
R = parquetread(fullfile(ev_dir, 'processed_robots.parquet'));
R = R(strcmp(R.team, team) & double(R.robot_id) == rid, :);
d = [];
if height(C) < 30 || height(R) < 30, return; end
t0 = max(C.timestamp_event(1), R.timestamp_event(1));
t1 = min(C.timestamp_event(end), R.timestamp_event(end));
tg = (t0:Ts:t1)';
if numel(tg) < 30, return; end
uw = interp1(C.timestamp_event, C.move_w, tg, 'previous', 0);
pw = interp1(R.timestamp_event, unwrap(R.position_w), tg, 'linear');
yw = [0; diff(pw)] / Ts;
if numel(yw) > 7, yw = smoothdata(yw, 'sgolay', 5); end
mask = ~isnan(uw) & ~isnan(yw);
uw = uw(mask); yw = yw(mask);
if numel(uw) < 30, return; end
uw = uw - mean(uw);  yw = yw - mean(yw);
d = iddata(yw, uw, Ts);
d.ExperimentName = event_;
end
