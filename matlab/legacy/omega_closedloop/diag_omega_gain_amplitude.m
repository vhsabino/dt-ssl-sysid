function [G, info] = diag_omega_gain_amplitude(opts)
%DIAG_OMEGA_GAIN_AMPLITUDE Etapa A — ganho efetivo de omega por faixa de |cmd_w|.
% Testa a hipotese da orientadora (robo responde bem a comandos grandes de
% omega e mal a pequenos = nao-linearidade estatica, zona morta/atrito).
% Para cada evento do label (default shoot_to_goal):
%   1. grade uniforme Ts=1/60 na intersecao commands x processed_robots;
%   2. u = move_w (ZOH 'previous'); heading = unwrap(position_w) suavizado
%      por Savitzky-Golay ANTES de derivar -> meas_w = d/dt(heading_suave);
%   3. meas_w defasado por Td0 (mediana, entre eventos, do lag de maxima
%      xcorr cmd->meas, ~0.15 s) para alinhar entrada e saida.
% Pool de (cmd_w, meas_w) alinhados de todos os eventos, binado por |cmd_w|
% nas faixas [0-0.1],[0.1-0.2],[0.2-0.3],[0.3-0.5],[0.5-1],[1-1.5],[>1.5].
% Em cada faixa o GANHO EFETIVO = inclinacao de robustfit(meas_w ~ cmd_w).
%
% Assinatura esperada (zona morta): ganho ~0 nas faixas baixas, subindo a
% um plato K nas altas; a meia-altura aproxima a largura d da zona morta.
%
% NAO promove nada, NAO toca em data/. Salva:
%   results/diag_omega_gain_by_band_<stamp>.csv   (faixa->ganho->n_amostras)
%   results/diag_omega_gain_amplitude_<stamp>.mat (pool + per-evento, p/ Etapa C)
%   results/figs/diag_omega_gain_amplitude_<stamp>.{png,pdf}
%
% USO:
%   [G, info] = diag_omega_gain_amplitude();

arguments
    opts.Label    (1,:) char    = 'shoot_to_goal'
    opts.Ts       (1,1) double  = 1/60
    opts.Team     (1,:) char    = 'allies'
    opts.SgWin    (1,1) double  = 7        % janela sgolay do heading (amostras)
    opts.SgOrder  (1,1) double  = 2        % ordem do polinomio sgolay
    opts.MaxLagS  (1,1) double  = 1.0      % busca de Td0 em 0..MaxLagS
    opts.Edges    (1,:) double  = [0 0.1 0.2 0.3 0.5 1 1.5 Inf]  % rad/s
    opts.MinN     (1,1) double  = 10       % min amostras p/ regressao por faixa
    opts.SaveCsv  (1,1) logical = true
    opts.SaveFig  (1,1) logical = true
end

repo_root = bootstrap_paths();
data_root = fullfile(repo_root, 'data', 'extracted');

% ----- lista os eventos do label (chunk commands traz o caminho) ----------
S = list_splits(data_root, 'Label', opts.Label);
S = S(strcmp(S.chunk, 'commands'), :);
if isempty(S)
    error('diag_omega_gain_amplitude: nenhum evento "%s" indexado em %s.', ...
        opts.Label, data_root);
end

% ----- processa cada evento: grade Ts, u=cmd, y=meas (sgolay->derivada) ----
nev = height(S);
ev  = struct('log',{},'event',{},'u',{},'y',{},'Td0',{},'xc',{}, ...
             'n',{},'std_u',{});
for i = 1:nev
    C = parquetread(S.path{i});
    rid = mode(double(C.robot_id));
    C = C(double(C.robot_id) == rid, :);
    rp = fullfile(fileparts(S.path{i}), 'processed_robots.parquet');
    if ~isfile(rp) || height(C) < 30, continue; end
    R = parquetread(rp);
    R = R(strcmp(R.team, opts.Team) & double(R.robot_id) == rid, :);
    if height(R) < 30, continue; end

    t  = C.timestamp_event;
    t0 = max(t(1), R.timestamp_event(1));
    t1 = min(t(end), R.timestamp_event(end));
    tg = (t0:opts.Ts:t1)';
    if numel(tg) < 30, continue; end

    u  = interp1(t, C.move_w, tg, 'previous', 0);                 % cmd_w (ZOH)
    pw = interp1(R.timestamp_event, unwrap(R.position_w), tg, 'linear');
    % --- Savitzky-Golay no HEADING antes de derivar (instrucao da Etapa A) --
    win = min(opts.SgWin, 2*floor((numel(pw)-1)/2)+1);           % impar, <= N
    if win > opts.SgOrder
        pws = sgolayfilt(pw, opts.SgOrder, win);
    else
        pws = pw;
    end
    y  = gradient(pws) / opts.Ts;                                % meas_w
    m  = ~isnan(u) & ~isnan(y);
    u  = u(m);  y = y(m);
    if numel(u) < 30, continue; end

    [Td0, xc] = xcorr_delay(u, y, opts.Ts, opts.MaxLagS);
    ev(end+1) = struct('log',S.log{i}, 'event',S.event{i}, ...
        'u',u, 'y',y, 'Td0',Td0, 'xc',xc, 'n',numel(u), 'std_u',std(u)); %#ok<AGROW>
end
if isempty(ev)
    error('diag_omega_gain_amplitude: nenhum evento processavel para "%s".', opts.Label);
end

% ----- defasagem global = mediana dos Td0 por evento ----------------------
Td0_all   = [ev.Td0];
Td0_glob  = median(Td0_all, 'omitnan');
if ~isfinite(Td0_glob), Td0_glob = 0.15; end
k = round(Td0_glob / opts.Ts);

% ----- alinha (y atrasado por k) e empilha o pool --------------------------
U = []; Y = [];
for j = 1:numel(ev)
    u = ev(j).u; y = ev(j).y;
    if k > 0 && numel(u) > k
        u = u(1:end-k);  y = y(1+k:end);
    end
    U = [U; u(:)];  Y = [Y; y(:)]; %#ok<AGROW>
end
au = abs(U);

% ----- ganho efetivo por faixa de |cmd_w| (robustfit) ----------------------
edges = opts.Edges;
nb = numel(edges) - 1;
band   = strings(nb,1);  cmd_lo = zeros(nb,1);  cmd_hi = zeros(nb,1);
gain   = nan(nb,1);  gain_se = nan(nb,1);  intercept = nan(nb,1);
nsamp  = zeros(nb,1);  mean_abs_cmd = nan(nb,1);  mean_abs_meas = nan(nb,1);
med_ratio = nan(nb,1);
for b = 1:nb
    lo = edges(b); hi = edges(b+1);
    if isinf(hi)
        sel = au >= lo;
        band(b) = sprintf('>%.2g', lo);
    else
        sel = au >= lo & au < hi;
        band(b) = sprintf('%.2g-%.2g', lo, hi);
    end
    cmd_lo(b) = lo;  cmd_hi(b) = hi;
    ub = U(sel);  yb = Y(sel);
    nsamp(b) = numel(ub);
    mean_abs_cmd(b)  = mean(abs(ub), 'omitnan');
    mean_abs_meas(b) = mean(abs(yb), 'omitnan');
    rok = abs(ub) > 0.05;                         % razao so onde cmd nao ~0
    if any(rok), med_ratio(b) = median(yb(rok)./ub(rok), 'omitnan'); end
    if numel(ub) >= opts.MinN && (max(ub)-min(ub)) > 0.02
        [bcoef, st] = robustfit(ub, yb);          % [intercept; slope]
        intercept(b) = bcoef(1);
        gain(b)      = bcoef(2);
        gain_se(b)   = st.se(2);
    end
end

G = table(band, cmd_lo, cmd_hi, nsamp, gain, gain_se, intercept, ...
    mean_abs_cmd, mean_abs_meas, med_ratio, 'VariableNames', ...
    {'band','cmd_lo','cmd_hi','n_samples','gain','gain_se','intercept', ...
     'mean_abs_cmd','mean_abs_meas','median_ratio'});

% ----- tabela por evento (proveniencia) -----------------------------------
EV = table(string({ev.log}'), string({ev.event}'), [ev.n]', ...
    [ev.std_u]', [ev.Td0]', [ev.xc]', 'VariableNames', ...
    {'log','event','n','std_cmd_w','Td0_s','xcorr_max'});

stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
commit = strtrim(evalc('!git rev-parse --short HEAD'));
info = struct('label', opts.Label, 'Ts', opts.Ts, 'SgWin', opts.SgWin, ...
    'SgOrder', opts.SgOrder, 'Td0_global', Td0_glob, 'lag_samples', k, ...
    'n_events', numel(ev), 'events', EV, 'edges', edges, ...
    'commit', commit, 'created_at', datetime('now'), 'stamp', stamp);

% ----- relatorio no console -----------------------------------------------
fprintf('\n===== Etapa A: ganho efetivo de omega x faixa de |cmd_w| =====\n');
fprintf('Label=%s | eventos=%d | Ts=%.4f s | sgolay(heading) ordem %d janela %d\n', ...
    opts.Label, numel(ev), opts.Ts, opts.SgOrder, opts.SgWin);
fprintf('Td0 por evento (s): %s\n', mat2str(round(Td0_all,3)));
fprintf('Td0 GLOBAL (mediana) = %.3f s -> defasagem %d amostras\n', Td0_glob, k);
fprintf('Pool alinhado: %d amostras\n\n', numel(U));
fprintf('%-9s %9s %8s %8s %9s %10s\n', 'faixa','n','ganho','se','razao','mean|cmd|');
for b = 1:nb
    fprintf('%-9s %9d %8.3f %8.3f %9.3f %10.3f\n', band(b), nsamp(b), ...
        gain(b), gain_se(b), med_ratio(b), mean_abs_cmd(b));
end
fprintf('\n');

% ----- artefatos ----------------------------------------------------------
if opts.SaveCsv
    if ~isfolder('results'), mkdir('results'); end
    csv = fullfile('results', sprintf('diag_omega_gain_by_band_%s.csv', stamp));
    writetable(G, csv);
    matp = fullfile('results', sprintf('diag_omega_gain_amplitude_%s.mat', stamp));
    save(matp, 'G', 'EV', 'info', 'U', 'Y', 'Td0_glob', 'edges');
    fprintf('Salvo: %s\n', csv);
    fprintf('Salvo: %s\n', matp);
end

if opts.SaveFig
    fig = plot_gain_vs_band(G, info);
    if ~isfolder(fullfile('results','figs')), mkdir(fullfile('results','figs')); end
    fp = fullfile('results','figs', sprintf('diag_omega_gain_amplitude_%s', stamp));
    exportgraphics(fig, [fp '.png'], 'Resolution', 150);
    exportgraphics(fig, [fp '.pdf'], 'ContentType', 'vector');
    fprintf('Salvo: %s.{png,pdf}\n', fp);
end
end

% =========================================================================
function fig = plot_gain_vs_band(G, info)
nb = height(G);
x  = 1:nb;
fig = figure('Color','w','Position',[100 100 820 460]);
% barras de contagem (eixo direito) + ganho com erro (eixo esquerdo)
yyaxis right
bar(x, G.n_samples, 0.6, 'FaceColor',[0.85 0.88 0.95], ...
    'EdgeColor',[0.6 0.65 0.78]);
ylabel('n amostras');
set(gca, 'YColor', [0.45 0.5 0.62]);
for i = 1:nb
    text(x(i), double(G.n_samples(i)), sprintf('%d', G.n_samples(i)), ...
        'HorizontalAlignment','center','VerticalAlignment','bottom', ...
        'FontSize',8,'Color',[0.4 0.45 0.55]);
end
yyaxis left
errorbar(x, G.gain, G.gain_se, '-o', 'LineWidth',1.8, ...
    'Color',[0.10 0.30 0.65], 'MarkerFaceColor',[0.10 0.30 0.65], ...
    'MarkerSize',6, 'CapSize',8);
ylabel('ganho efetivo  meas\_\omega / cmd\_\omega  (inclinacao robustfit)');
set(gca, 'YColor', [0.10 0.30 0.65]);
yline(1, ':', 'ganho 1', 'Color',[0.4 0.4 0.4], 'LabelHorizontalAlignment','left');
yline(0, '-', 'Color',[0.7 0.7 0.7]);
xlim([0.4 nb+0.6]);
xticks(x); xticklabels(cellstr(G.band));
xlabel('faixa de |cmd\_\omega|  (rad/s)');
title(sprintf(['Etapa A — ganho efetivo de \\omega x amplitude  (%s, %d eventos)\n' ...
    'Td0=%.3f s, sgolay ord %d/janela %d  —  assinatura de zona morta'], ...
    strrep(info.label,'_','\_'), info.n_events, info.Td0_global, info.SgOrder, info.SgWin), ...
    'FontSize',10);
grid on; box on;
end

% =========================================================================
function [Td0, xcm] = xcorr_delay(u, y, Ts, max_lag_s)
%XCORR_DELAY Lag (s) que maximiza corr(u(t), y(t+lag)), lags 0..max_lag_s.
% Identico ao usado em check_excitation (sem Signal Processing Toolbox).
K = min(round(max_lag_s / Ts), numel(u) - 10);
r = -inf(K+1, 1);
for kk = 0:K
    a = u(1:end-kk); b = y(1+kk:end);
    if std(a) > 0 && std(b) > 0
        r(kk+1) = corr(a, b);
    end
end
[xcm, idx] = max(r);
Td0 = (idx - 1) * Ts;
if ~isfinite(xcm), Td0 = NaN; xcm = NaN; end
end
