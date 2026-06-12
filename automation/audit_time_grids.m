function A = audit_time_grids(opts)
%AUDIT_TIME_GRIDS Auditoria da grade temporal dos splits canonicos (todos os
% labels). Para cada evento: estatisticas de dT (mediana/quantis), numero de
% janelas da metrica no esquema AMOSTRAL antigo (win = round(2.5/median dT))
% vs no esquema POR TEMPO, e flag de irregularidade. Motivacao: no
% square_01_01 a grade dos comandos e irregular (mediana dT=2.2 ms) e o
% esquema amostral colapsava a metrica para janela unica (ver CHANGELOG
% 2026-06-11 22:02). Gera tabela em results/ e histograma de dT por label
% em results/figs/.

arguments
    opts.Log       (1,:) char   = '2026-05-18_19-2-15'
    opts.WindowSec (1,1) double = 2.5
    opts.Overlap   (1,1) double = 0.5
end

repo_root = bootstrap_paths();
splits_root = fullfile(repo_root, 'data', 'extracted', opts.Log, 'splits');
labels = dir(splits_root);
labels = {labels([labels.isdir] & ~startsWith({labels.name}, '.')).name};

rows = {};
dT_by_label = containers.Map();
for li = 1:numel(labels)
    label_ = labels{li};
    evs = dir(fullfile(splits_root, label_));
    evs = {evs([evs.isdir] & ~startsWith({evs.name}, '.')).name};
    pool = [];
    for ei = 1:numel(evs)
        event_ = evs{ei};
        try
            canon = canonical_split(fullfile(splits_root, label_, event_, ...
                'commands.parquet'));
            T = parquetread(canon);
            t = T.timestamp_event;  t = t - t(1);
            dt = diff(t);
            n = numel(t);  dur = t(end);
            md = median(dt);  p10 = quantile(dt, .10);  p90 = quantile(dt, .90);
            % janelas no esquema amostral antigo (rmse_pos_rebased pre-fix)
            win = max(2, round(opts.WindowSec / md));
            if n < win
                nw_amostral = 1;
            else
                nw_amostral = numel(1:max(1, round(win*(1-opts.Overlap))):(n - win + 1));
            end
            % janelas no esquema por tempo
            t0s = t(1):opts.WindowSec*(1-opts.Overlap):(t(end) - opts.WindowSec);
            if isempty(t0s), nw_tempo = 1; else, nw_tempo = numel(t0s); end
            irregular = (p90/p10 > 3) || (nw_amostral <= 1 && dur > opts.WindowSec);
            rows(end+1,:) = {label_, event_, n, dur, md*1e3, p10*1e3, p90*1e3, ...
                min(dt)*1e3, max(dt)*1e3, p90/p10, nw_amostral, nw_tempo, ...
                irregular, 'ok'}; %#ok<AGROW>
            pool = [pool; dt(:)]; %#ok<AGROW>
        catch ME
            msg = regexprep(strrep(ME.message, newline, ' '), '<[^>]+>', '');
            rows(end+1,:) = {label_, event_, NaN, NaN, NaN, NaN, NaN, NaN, NaN, ...
                NaN, NaN, NaN, false, msg}; %#ok<AGROW>
        end
    end
    dT_by_label(label_) = pool;
end

A = cell2table(rows, 'VariableNames', {'label','event','n_amostras','dur_s', ...
    'dT_mediana_ms','dT_p10_ms','dT_p90_ms','dT_min_ms','dT_max_ms', ...
    'razao_p90_p10','n_jan_amostral','n_jan_tempo','irregular','status'});

stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
outcsv = fullfile('results', sprintf('grid_audit_%s.csv', stamp));
writetable(A, outcsv);
fprintf('Salvo: %s\n', outcsv);

% --- histograma de dT por label (escala log) ---
figdir = fullfile('results','figs');
if ~isfolder(figdir), mkdir(figdir); end
f = figure('Visible','off','Position',[100 100 1100 700]);
tl = tiledlayout(f, 2, 2, 'TileSpacing','compact');
for li = 1:numel(labels)
    ax = nexttile(tl);
    dt = dT_by_label(labels{li});
    histogram(ax, log10(dt*1e3), 60);
    xline(ax, log10(1000/60), 'r--', '1/60 s');
    title(ax, sprintf('%s (mediana %.2f ms)', strrep(labels{li},'_','\_'), ...
        median(dt)*1e3));
    xlabel(ax, 'log_{10} dT [ms]');  ylabel(ax, 'contagem');
    grid(ax, 'on');
end
title(tl, sprintf('Distribuicao de dT da grade canonica por label — log %s', ...
    opts.Log), 'Interpreter','none');
exportgraphics(f, fullfile(figdir, sprintf('grid_audit_dT_hist_%s.png', stamp)), ...
    'Resolution', 200);
exportgraphics(f, fullfile(figdir, sprintf('grid_audit_dT_hist_%s.pdf', stamp)));
close(f);
fprintf('Figuras: %s\n', fullfile(figdir, sprintf('grid_audit_dT_hist_%s.{png,pdf}', stamp)));

% --- resumo no console ---
okm = strcmp(A.status,'ok');
fprintf('\nEventos: %d ok / %d total | irregulares: %d\n', nnz(okm), height(A), ...
    nnz(A.irregular(okm)));
disp(sortrows(A(okm & A.irregular, {'label','event','dT_mediana_ms', ...
    'razao_p90_p10','n_jan_amostral','n_jan_tempo'}), 'razao_p90_p10', 'descend'));
end
