function s = load_split(parquet_path, varargin)
% LOAD_SPLIT  Lê um chunk .parquet e devolve struct pronto pro Simulink.
%   s = load_split('data/extracted/foo/splits/square/ev_03/chunk_001.parquet')
%
% Saída:
%   s.cmd_vx_ts, s.cmd_vy_ts, s.cmd_vw_ts        (timeseries em m/s, rad/s)
%   s.pos_x_truth, s.pos_y_truth, s.theta_truth  (timeseries em m, rad)
%   s.pos0        struct com x0, y0, theta0 (condição inicial)
%   s.Tsim        duração da simulação (s)
%   s.t           vetor de tempo bruto

% --- Schema (único ponto de configuração) ---
cols = struct( ...
    'time',  'timestamp_event', ...
    'cmd_x', 'move_vx', 'cmd_y', 'move_vy', 'cmd_w', 'move_w', ...
    'pos_x', 'pos_x',   'pos_y', 'pos_y',   'theta', 'theta');

T = parquetread(parquet_path);
t = T.(cols.time);
if t(1) ~= 0, t = t - t(1); end

% --- Comandos (entrada do modelo) ---
s.cmd_vx_ts = timeseries(T.(cols.cmd_x), t, 'Name', 'cmd_vx');
s.cmd_vy_ts = timeseries(T.(cols.cmd_y), t, 'Name', 'cmd_vy');
s.cmd_vw_ts = timeseries(T.(cols.cmd_w), t, 'Name', 'cmd_vw');

% --- Truth (referência pra comparação; converte mm→m) ---
s.pos_x_truth = timeseries(T.(cols.pos_x)/1000, t, 'Name', 'pos_x_truth');
s.pos_y_truth = timeseries(T.(cols.pos_y)/1000, t, 'Name', 'pos_y_truth');
s.theta_truth = timeseries(T.(cols.theta),       t, 'Name', 'theta_truth');

% --- Condição inicial ---
s.pos0 = struct('x0',     T.(cols.pos_x)(1)/1000, ...
    'y0',     T.(cols.pos_y)(1)/1000, ...
    'theta0', T.(cols.theta)(1));

s.Tsim = t(end);
s.t    = t;
s.path = parquet_path;
end