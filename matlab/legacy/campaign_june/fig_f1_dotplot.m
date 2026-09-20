function fig_f1_dotplot(campaign_csv)
%FIG_F1_DOTPLOT F1: dot-plot de RMSE por evento — 3 modelos x 2 metricas
% (forma do marcador = modelo; cheio = re-ancora translacao, vazado =
% re-ancora pose SE(2)), cores por label. PNG+PDF em results/figs/.

T = readtable(campaign_csv);
T = T(strcmp(T.status,'ok'), :);
[ev_list, ~, iev] = unique(strcat(T.label, '/', T.event), 'stable');
nev = numel(ev_list);

labels = unique(T.label, 'stable');
cols = lines(numel(labels));
thetas  = {'ideal_analytic','procest_placeholder','procest_w_cand'};
marks   = {'o','s','^'};

f = figure('Visible','off','Position',[50 50 950 1400]);
ax = axes(f); hold(ax,'on');
for i = 1:height(T)
    y = iev(i);
    ci = cols(strcmp(labels, T.label{i}), :);
    mk = marks{strcmp(thetas, T.theta{i})};
    plot(ax, T.rmse_trans_m(i), y, mk, 'MarkerEdgeColor', ci, ...
        'MarkerFaceColor', ci, 'MarkerSize', 6);
    plot(ax, T.rmse_se2_m(i), y, mk, 'MarkerEdgeColor', ci, ...
        'MarkerFaceColor', 'none', 'MarkerSize', 6, 'LineWidth', 1.1);
end
set(ax, 'YTick', 1:nev, 'YTickLabel', strrep(ev_list,'_','\_'), ...
    'YDir','reverse', 'FontSize', 7, 'TickLabelInterpreter','tex');
ylim(ax, [0.5 nev+0.5]); grid(ax,'on');
xlabel(ax, 'RMSE de posicao re-ancorado, h=2.5 s [m]', 'FontSize', 9);

% legenda composta (cores=label, forma=modelo, preenchimento=metrica)
h = gobjects(0); leg = {};
for li = 1:numel(labels)
    h(end+1) = plot(ax, NaN, NaN, 'o', 'MarkerEdgeColor', cols(li,:), ...
        'MarkerFaceColor', cols(li,:)); leg{end+1} = strrep(labels{li},'_','\_'); %#ok<AGROW>
end
for k = 1:numel(thetas)
    h(end+1) = plot(ax, NaN, NaN, marks{k}, 'Color', [.3 .3 .3]); %#ok<AGROW>
    leg{end+1} = strrep(thetas{k},'_','\_'); %#ok<AGROW>
end
h(end+1) = plot(ax, NaN, NaN, 'o', 'MarkerEdgeColor',[.3 .3 .3], ...
    'MarkerFaceColor',[.3 .3 .3]); leg{end+1} = 'cheio: trans';
h(end+1) = plot(ax, NaN, NaN, 'o', 'MarkerEdgeColor',[.3 .3 .3], ...
    'MarkerFaceColor','none'); leg{end+1} = 'vazado: SE(2)';
legend(ax, h, leg, 'Location','southeast', 'FontSize', 8);
title(ax, 'F1 — RMSE re-ancorado por evento (janela por tempo)', 'FontSize', 10);

[~, base] = fileparts(campaign_csv);
figdir = fullfile('results','figs');
if ~isfolder(figdir), mkdir(figdir); end
exportgraphics(f, fullfile(figdir, ['F1_dotplot_' base '.png']), 'Resolution', 200);
exportgraphics(f, fullfile(figdir, ['F1_dotplot_' base '.pdf']));
close(f);
fprintf('F1 salva em %s (F1_dotplot_%s.{png,pdf})\n', figdir, base);
end
