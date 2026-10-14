function fig_f2_overlays(traj_file)
%FIG_F2_OVERLAYS F2: montagem de overlays XY + theta(t) por evento da
% identificacao omega (14 eventos qualificados), truth vs procest_placeholder
% vs procest_w_cand, rotulando TREINO vs HOLD-OUT (particao seed 42 do
% report salvo em models/sysid_initial_v2_candidate.mat). Cada evento ocupa
% um par de tiles (esq: XY, dir: theta(t)). PNG+PDF em results/figs/.

S = load(traj_file);  traj = S.traj;
C = load(fullfile('models','sysid_initial_v2_candidate.mat'), 'report');
evs = [C.report.events_train(:); C.report.events_holdout(:)];
tags = [repmat({'TREINO'}, numel(C.report.events_train), 1); ...
        repmat({'HOLD-OUT'}, numel(C.report.events_holdout), 1)];
[evs, si] = sort(evs);  tags = tags(si);

cTr = [0 0 0]; cPl = [0 .35 .75]; cCa = [.85 .2 .1];
f = figure('Visible','off','Position',[20 20 1700 950]);
tl = tiledlayout(f, 4, 8, 'TileSpacing','compact', 'Padding','compact');
for i = 1:numel(evs)
    ev = evs{i};
    pl = traj(strcmp({traj.event}, ev) & strcmp({traj.theta}, 'procest_placeholder'));
    ca = traj(strcmp({traj.event}, ev) & strcmp({traj.theta}, 'procest_w_cand'));
    if isempty(pl) || isempty(ca)
        warning('fig_f2_overlays: sem trajetoria para %s — pulando.', ev);
        continue
    end
    short = strrep(ev, 'shoot_to_goal_', 'stg ');
    % --- XY ---
    ax = nexttile(tl);  hold(ax,'on');
    plot(ax, pl.x_truth, pl.y_truth, '-',  'Color', cTr, 'LineWidth', 1.2);
    plot(ax, pl.x_sim,   pl.y_sim,   '--', 'Color', cPl);
    plot(ax, ca.x_sim,   ca.y_sim,   '--', 'Color', cCa);
    plot(ax, pl.x_truth(1), pl.y_truth(1), 'k.', 'MarkerSize', 12);
    axis(ax, 'equal'); grid(ax,'on'); set(ax,'FontSize',6);
    title(ax, sprintf('%s — %s', short, tags{i}), 'FontSize', 7, ...
        'Interpreter','none');
    % --- theta(t) ---
    ax = nexttile(tl);  hold(ax,'on');
    plot(ax, pl.t, pl.th_truth, '-',  'Color', cTr, 'LineWidth', 1.2);
    plot(ax, pl.t, pl.th_sim,   '--', 'Color', cPl);
    plot(ax, ca.t, ca.th_sim,   '--', 'Color', cCa);
    grid(ax,'on'); set(ax,'FontSize',6);
    title(ax, '\theta(t) [rad]', 'FontSize', 7);
end
lg = legend({'truth','procest\_placeholder','procest\_w\_cand'}, ...
    'Orientation','horizontal', 'FontSize', 9);
lg.Layout.Tile = 'south';
title(tl, ['F2 — Overlays XY (esq) e \theta(t) (dir) por evento da ' ...
    'identificacao \omega — replay open-loop'], 'FontSize', 11);

[~, base] = fileparts(traj_file);
figdir = fullfile('results','figs');
if ~isfolder(figdir), mkdir(figdir); end
exportgraphics(f, fullfile(figdir, ['F2_overlays_' base '.png']), 'Resolution', 180);
exportgraphics(f, fullfile(figdir, ['F2_overlays_' base '.pdf']));
close(f);
fprintf('F2 salva em %s (F2_overlays_%s.{png,pdf})\n', figdir, base);
end
