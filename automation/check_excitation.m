function E = check_excitation(label, opts)
%CHECK_EXCITATION Diagnostico de excitacao dos comandos por split/evento.
% Responde a pergunta dos criterios de aceite da identificacao omega
% (CLAUDE.md): "excitacao? std(cmd_vw)?" — nos dados reais o comando
% angular e a coluna `move_w` de commands.parquet (cmd_vw === move_w;
% idem cmd_vx === move_x, cmd_vy === move_y).
%
% Alem das estatisticas de comando, calcula por evento (usando o omega
% MEDIDO de processed_robots.parquet, derivada sgolay de unwrap(position_w)
% na grade Ts=1/60, como build_idData_per_dof):
%   n_freq_signif — n. de maximos locais do periodograma de move_w com
%                   potencia >= 10% do pico (riqueza espectral da excitacao)
%   Td0_s         — atraso da maxima correlacao cruzada cmd_vw -> omega
%                   medido (lags 0..1 s; chute inicial de Td_w)
%   xcorr_max     — valor dessa correlacao (qualidade do acoplamento u->y)
%
% Assinaturas reais usadas (NAO alterar os arquivos do pipeline):
%   repo_root = bootstrap_paths()
%   S = list_splits(data_root_abs, 'Label', lbl)   % data_root ABSOLUTO
%   commands.parquet: timestamp, robot_id, move_x, move_y, move_w, ...
%   processed_robots.parquet: team, robot_id, position_w, ...
%
% Limiares herdados do pipeline real (build_idData_per_dof):
%   OmegaThresh = 0.5 rad/s, MinTotalSec = 5.0 s
%
% USO:
%   E = check_excitation();                  % todos os labels
%   E = check_excitation('shoot_to_goal');   % so um label (posicional)
%   E = check_excitation('Label','square');  % equivalente name-value

arguments
    label            (1,:) char    = ''     % atalho posicional p/ Label
    opts.DataRoot    (1,:) char    = fullfile('data','extracted')
    opts.Label       (1,:) char    = ''     % '' = todos
    opts.RobotId     (1,1) double  = NaN    % NaN = unico/moda de commands
    opts.Team        (1,:) char    = 'allies'
    opts.OmegaThresh (1,1) double  = 0.5    % rad/s
    opts.MinTotalSec (1,1) double  = 5.0    % s de excitacao omega recomendados
    opts.Ts          (1,1) double  = 1/60   % grade p/ xcorr (igual pipeline)
    opts.SaveCsv     (1,1) logical = false
end

if isempty(opts.Label), opts.Label = label; end

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
    rid = opts.RobotId;
    if isnan(rid), rid = mode(double(C.robot_id)); end
    C = C(double(C.robot_id) == rid, :);
    if height(C) < 2, continue; end

    t   = C.timestamp_event;
    dur = t(end) - t(1);
    Tsm = median(diff(t));
    act = abs(C.move_w) > opts.OmegaThresh;

    % --- riqueza espectral do comando omega ---
    nfreq = count_significant_freqs(C.move_w);

    % --- xcorr cmd_vw -> omega medido (processed_robots do mesmo evento) ---
    Td0 = NaN; xcm = NaN;
    rp = fullfile(fileparts(S.path{i}), 'processed_robots.parquet');
    if isfile(rp)
        R = parquetread(rp);
        R = R(strcmp(R.team, opts.Team) & double(R.robot_id) == rid, :);
        if height(R) >= 3
            tg = (max(t(1), R.timestamp_event(1)) : opts.Ts : ...
                  min(t(end), R.timestamp_event(end)))';
            if numel(tg) > 30
                uw = interp1(t, C.move_w, tg, 'previous', 0);
                pw = interp1(R.timestamp_event, unwrap(R.position_w), tg, 'linear');
                yw = [0; diff(pw)] / opts.Ts;
                if numel(yw) > 7, yw = smoothdata(yw, 'sgolay', 5); end
                [Td0, xcm] = xcorr_delay(uw, yw, opts.Ts, 1.0);
            end
        end
    end

    rows{i} = {S.log{i}, S.label{i}, S.event{i}, height(C), dur, ...
        std(C.move_x), std(C.move_y), std(C.move_w), ...
        mean(act), sum(act) * Tsm, nfreq, Td0, xcm};
end
rows = rows(~cellfun('isempty', rows));
E = cell2table(vertcat(rows{:}), 'VariableNames', ...
    {'log','label','event','n_rows','duration_s', ...
     'std_move_x','std_move_y','std_move_w','frac_w_excitado','w_ativo_s', ...
     'n_freq_signif','Td0_s','xcorr_max'});

% --- resumo por label + veredito omega ---
fprintf('\n===== check_excitation (|move_w| > %.2f rad/s) =====\n', opts.OmegaThresh);
labels = unique(E.label, 'stable');
for k = 1:numel(labels)
    Ek = E(strcmp(E.label, labels{k}), :);
    fprintf(['%-15s | %2d eventos | std(move_w) max=%.3f mediana=%.3f | ' ...
        'w ativo total=%.1f s | Td0 mediana=%.3f s | xcorr mediana=%.2f\n'], ...
        labels{k}, height(Ek), max(Ek.std_move_w), median(Ek.std_move_w), ...
        sum(Ek.w_ativo_s), median(Ek.Td0_s,'omitnan'), median(Ek.xcorr_max,'omitnan'));
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

% =========================================================================
function n = count_significant_freqs(u)
%COUNT_SIGNIFICANT_FREQS Maximos locais do periodograma (janela de Hann)
% com potencia >= 10% do pico. Sem toolboxes.
u = double(u(:)); u = u - mean(u);
m = numel(u);
if m < 16 || all(u == 0), n = 0; return; end
w = 0.5 * (1 - cos(2*pi*(0:m-1)'/(m-1)));   % hann
P = abs(fft(u .* w)).^2;
P = P(2:floor(m/2));                        % unilateral, sem DC
if isempty(P) || max(P) == 0, n = 0; return; end
pk = (P(2:end-1) > P(1:end-2)) & (P(2:end-1) > P(3:end)) & ...
     (P(2:end-1) >= 0.1 * max(P));
n = nnz(pk);
end

% =========================================================================
function [Td0, xcm] = xcorr_delay(u, y, Ts, max_lag_s)
%XCORR_DELAY Lag (s) que maximiza corr(u(t), y(t+lag)), lags 0..max_lag_s.
% Implementacao manual (sem Signal Processing Toolbox).
K = min(round(max_lag_s / Ts), numel(u) - 10);
r = -inf(K+1, 1);
for k = 0:K
    a = u(1:end-k); b = y(1+k:end);
    if std(a) > 0 && std(b) > 0
        r(k+1) = corr(a, b);
    end
end
[xcm, idx] = max(r);
Td0 = (idx - 1) * Ts;
if ~isfinite(xcm), Td0 = NaN; xcm = NaN; end
end
