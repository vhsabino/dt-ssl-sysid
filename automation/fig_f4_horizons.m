function fig_f4_horizons(medians_csv)
%FIG_F4_HORIZONS F4: curvas de RMSE mediano x horizonte de previsao,
% 3 modelos, painel por label + global, duas metricas (linha cheia =
% re-ancora translacao; tracejada = re-ancora pose SE(2) com theta truth
% filtrado). Consome o CSV de medianas de eval_horizons. PNG+PDF em
% results/figs/.

M = readtable(medians_csv);
panels = [setdiff(unique(M.label), {'global'}); {'global'}];
thetas = {'ideal_analytic','procest_placeholder','procest_w_cand'};
cols   = [.35 .35 .35; 0 .35 .75; .85 .2 .1];

f = figure('Visible','off','Position',[60 60 1500 650]);
tl = tiledlayout(f, 2, 3, 'TileSpacing','compact', 'Padding','compact');
for p = 1:numel(panels)
    ax = nexttile(tl); hold(ax,'on');
    for k = 1:numel(thetas)
        m = strcmp(M.label, panels{p}) & strcmp(M.theta, thetas{k});
        sub = sortrows(M(m,:), 'horizonte_s');
        plot(ax, sub.horizonte_s, sub.median_rmse_trans_m, '-o', ...
            'Color', cols(k,:), 'MarkerFaceColor', cols(k,:), 'MarkerSize', 4);
        plot(ax, sub.horizonte_s, sub.median_rmse_se2_m, '--s', ...
            'Color', cols(k,:), 'MarkerSize', 4);
    end
    grid(ax,'on'); set(ax,'FontSize',8);
    n = M.GroupCount(find(strcmp(M.label, panels{p}), 1));
    title(ax, sprintf('%s (n=%d)', strrep(panels{p},'_','\_'), n), 'FontSize', 10);
    xlabel(ax,'horizonte h [s]'); ylabel(ax,'RMSE mediano [m]');
end
% legenda no tile vago
ax = nexttile(tl); hold(ax,'on'); axis(ax,'off');
h = gobjects(0); leg = {};
for k = 1:numel(thetas)
    h(end+1) = plot(ax, NaN, NaN, '-', 'Color', cols(k,:), 'LineWidth', 1.5); %#ok<AGROW>
    leg{end+1} = strrep(thetas{k},'_','\_'); %#ok<AGROW>
end
h(end+1) = plot(ax, NaN, NaN, '-ok', 'MarkerFaceColor','k', 'MarkerSize',4);
leg{end+1} = 'cheia: re-ancora translacao';
h(end+1) = plot(ax, NaN, NaN, '--sk', 'MarkerSize',4);
leg{end+1} = 'tracejada: re-ancora pose SE(2)';
legend(ax, h, leg, 'Location','west', 'FontSize', 10);
title(tl, 'F4 — RMSE mediano de posicao x horizonte (janelas por tempo, overlap 0.5)', ...
    'FontSize', 12);

[~, base] = fileparts(medians_csv);
figdir = fullfile('results','figs');
if ~isfolder(figdir), mkdir(figdir); end
exportgraphics(f, fullfile(figdir, ['F4_horizons_' base '.png']), 'Resolution', 200);
exportgraphics(f, fullfile(figdir, ['F4_horizons_' base '.pdf']));
close(f);
fprintf('F4 salva em %s (F4_horizons_%s.{png,pdf})\n', figdir, base);
end
