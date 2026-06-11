function E = check_excitation(opts)
%CHECK_EXCITATION Diagnostico de excitacao dos comandos por split/evento.
% Responde a pergunta dos criterios de aceite da identificacao omega
% (CLAUDE.md): "excitacao? std(cmd_vw)?" — nos dados reais o comando
% angular e a coluna `move_w` de commands.parquet (cmd_vw === move_w;
% idem cmd_vx === move_x, cmd_vy === move_y).
%
% Assinaturas reais usadas (NAO alterar os arquivos do pipeline):
%   repo_root = bootstrap_paths()
%   S = list_splits(data_root_abs, 'Label', lbl)
%       -> table: log,label,event,chunk,path,n_rows,duration_s
%       -> data_root PRECISA ser absoluto
%   commands.parquet: timestamp, robot_id, move_x, move_y, move_w,
%                     actuation_*, timestamp_event
%
% Limiares herdados do pipeline real (build_idData_per_dof):
%   OmegaThresh = 0.5 rad/s  (opts.omega_thresh)
%   MinTotalSec = 5.0 s      (opts.theta_min_total_sec)
%
% USO:
%   E = check_excitation();                  % todos os labels
%   E = check_excitation('Label','square');  % so um label

arguments
    opts.DataRoot    (1,:) char    = fullfile('data','extracted')
    opts.Label       (1,:) char    = ''     % '' = todos
    opts.RobotId     (1,1) double  = NaN    % NaN = nao filtra
    opts.OmegaThresh (1,1) double  = 0.5    % rad/s
    opts.MinTotalSec (1,1) double  = 5.0    % s de excitacao omega recomendados
    opts.SaveCsv     (1,1) logical = false
end

repo_root = bootstrap_paths();
data_root = opts.DataRoot;
if ~startsWith(data_root, repo_root)
    data_root = fullfile(repo_root, data_root);
end

S = list_splits(data_root, 'Label', opts.Label);
S = S(strcmp(S.chunk, 'commands'), :);
if isempty(S)
    error('Nenhum chunk "commands" indexado em %s (Label="%s").', ...
        data_root, opts.Label);
end

rows = cell(height(S), 1);
for i = 1:height(S)
    C = parquetread(S.path{i});
    if ~isnan(opts.RobotId)
        C = C(C.robot_id == opts.RobotId, :);
    end
    if height(C) < 2, continue; end

    t   = C.timestamp_event;
    dur = t(end) - t(1);
    Ts  = median(diff(t));
    act = abs(C.move_w) > opts.OmegaThresh;

    rows{i} = {S.log{i}, S.label{i}, S.event{i}, height(C), dur, ...
        std(C.move_x), std(C.move_y), std(C.move_w), ...
        mean(act), sum(act) * Ts};
end
rows = rows(~cellfun('isempty', rows));
E = cell2table(vertcat(rows{:}), 'VariableNames', ...
    {'log','label','event','n_rows','duration_s', ...
     'std_move_x','std_move_y','std_move_w','frac_w_excitado','w_ativo_s'});

% --- resumo por label + veredito omega ---
fprintf('\n===== check_excitation (|move_w| > %.2f rad/s) =====\n', opts.OmegaThresh);
labels = unique(E.label, 'stable');
for k = 1:numel(labels)
    Ek = E(strcmp(E.label, labels{k}), :);
    tot_act = sum(Ek.w_ativo_s);
    fprintf('%-15s | %2d eventos | std(move_w) max=%.3f mediana=%.3f | w ativo total=%.1f s\n', ...
        labels{k}, height(Ek), max(Ek.std_move_w), median(Ek.std_move_w), tot_act);
end
tot = sum(E.w_ativo_s);
if tot >= opts.MinTotalSec
    fprintf('Veredito omega: OK — %.1f s de excitacao (>= %.1f s).\n', ...
        tot, opts.MinTotalSec);
else
    fprintf(['Veredito omega: INSUFICIENTE — %.1f s (< %.1f s). ' ...
        'Recomenda-se coleta dedicada (~30 s rotacionando parado).\n'], ...
        tot, opts.MinTotalSec);
end

if opts.SaveCsv
    stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
    outcsv = fullfile('results', sprintf('check_excitation_%s.csv', stamp));
    writetable(E, outcsv);
    fprintf('Salvo: %s\n', outcsv);
end
end
