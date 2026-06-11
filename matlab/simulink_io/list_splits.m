function T = list_splits(data_root, varargin)
% LIST_SPLITS  Indexa todos os chunks .parquet do dataset extraído.
%   T = list_splits('data/extracted')
%   T = list_splits('data/extracted', 'Label','square')
%
% Retorna table com colunas: log, label, event, chunk, path, n_rows, duration_s

ip = inputParser;
ip.addParameter('Label', '', @(s) ischar(s)||isstring(s));
ip.parse(varargin{:});
label_filter = string(ip.Results.Label);

files = dir(fullfile(data_root, '**', 'splits', '**', '*.parquet'));
files = files(~contains({files.folder}, 'all_'));  % ignora os agregados

rows = cell(numel(files), 1);
for k = 1:numel(files)
    fp = fullfile(files(k).folder, files(k).name);

    % Caminho relativo: <log>/splits/<label>/<event>/<chunk>.parquet
    rel = erase(fp, [data_root filesep]);
    parts = split(rel, filesep);
    if numel(parts) < 5, continue; end
    log_name = parts{1};  label = parts{3};
    event    = parts{4};  chunk = erase(parts{5}, '.parquet');

    if label_filter ~= "" && string(label) ~= label_filter, continue; end

    info = parquetinfo(fp);
    % R2026a: ParquetInfo nao tem NumRows; total de linhas = soma dos row groups
    rows{k} = {log_name, label, event, chunk, fp, sum(info.RowGroupHeights), NaN};
end
rows = rows(~cellfun('isempty', rows));
T = cell2table(vertcat(rows{:}), ...
    'VariableNames', {'log','label','event','chunk','path','n_rows','duration_s'});
T = sortrows(T, {'log','label','event','chunk'});
fprintf('list_splits: %d chunks indexados\n', height(T));
end