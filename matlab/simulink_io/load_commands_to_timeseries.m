%% load_commands_to_timeseries.m
% Carrega commands.move_x/y/w e gera timeseries a 60Hz para alimentar
% o modelo Simulink (cmd_vx_ts, cmd_vy_ts, cmd_vw_ts).
%
% Aceita dois tipos de SOURCE_DIR:
%   (A) Pasta de splits:  '.../splits'                            -> usa all_commands_labeled.parquet
%   (B) Pasta de um chunk: '.../splits/square/square_01_01'       -> usa commands.csv/parquet de dentro

clear; clc;

t_delay = 0.0167;
K_Matrix = [  0.0000,   0.0000,   0.0000,   0.0000,   0.0000,   0.0000,   0.0000,   0.0000,   0.0000, 0.0000,   0.0000,   0.0000];

% no init script ou no SLDD
% 1. Definição do sistema contínuo (o que você já tem)
num_motor = 1.732715862170721e+05;
den_motor = [1 2.299096640113972e+04 1.858402702347436e+05];
motor_sys = tf(num_motor, den_motor);

% 2. Definição das taxas de amostragem
Ts_real = 0.002;   % 2ms (Frequência do mundo real: 500Hz)
Ts_sim  = 0.0167;    % ~16.6ms (Frequência da simulação)

% 3. Discretização para a simulação (A Mágica acontece aqui)
% O comando c2d converte a física contínua para passos discretos de 60Hz
motor_sys_d = c2d(motor_sys, Ts_sim, 'zoh');

% Extrair numerador e denominador discretos para usar no bloco do Simulink
[num_d, den_d] = tfdata(motor_sys_d, 'v');
Ts = 0.0167;
Kp_initial = 0.3194;
Ki_initial = 6.434;

% ---------------- CONFIG ----------------
SOURCE_DIR = 'extracted/2026-05-18_19-2-15/splits/square/square_01_01';
ROBOT_ID   = 3;                       % usado só no modo splits
SIM_FREQ   = 60;
USE_EVENT  = '';                       % modo splits: '' = todos; ex: 'square_01_03'
% ----------------------------------------

dt_sim = 1/SIM_FREQ;

chunk_pq  = fullfile(SOURCE_DIR, 'commands.parquet');
chunk_cs  = fullfile(SOURCE_DIR, 'commands.csv');
splits_pq = fullfile(SOURCE_DIR, 'all_commands_labeled.parquet');

if isfile(chunk_pq) || isfile(chunk_cs)
    if isfile(chunk_pq), cmd = parquetread(chunk_pq); else, cmd = readtable(chunk_cs); end
    fprintf('Modo CHUNK: %s\n', SOURCE_DIR);

elseif isfile(splits_pq)
    cmd = parquetread(splits_pq);
    cmd = cmd(cmd.robot_id == ROBOT_ID, :);
    if ~isempty(USE_EVENT)
        cmd = cmd(strcmp(cmd.event_id, USE_EVENT), :);
    end
    fprintf('Modo SPLITS: %s (robot %d)\n', SOURCE_DIR, ROBOT_ID);

else
    error('Não encontrei commands.{csv,parquet} nem all_commands_labeled.parquet em %s', SOURCE_DIR);
end

if ismember('timestamp_event', cmd.Properties.VariableNames)
    tcol = 'timestamp_event';
else
    tcol = 'timestamp';
end

cmd = sortrows(cmd, tcol);
[~, ui] = unique(cmd.(tcol));
cmd = cmd(ui, :);

if height(cmd) < 2
    error('Poucas amostras (%d) — confira o filtro.', height(cmd));
end

t_raw  = cmd.(tcol);
vx_raw = cmd.move_x;
vy_raw = cmd.move_y;
vw_raw = cmd.move_w;

fprintf('Comandos: %d amostras, t=[%.3f, %.3f]s, dt~%.4fs\n', ...
        height(cmd), t_raw(1), t_raw(end), median(diff(t_raw)));

% grid uniforme a 60Hz + ZOH
t_sim  = (t_raw(1) : dt_sim : t_raw(end))';
sim_vx = interp1(t_raw, vx_raw, t_sim, 'previous', 'extrap');
sim_vy = interp1(t_raw, vy_raw, t_sim, 'previous', 'extrap');
sim_vw = interp1(t_raw, vw_raw, t_sim, 'previous', 'extrap');

% eixo de tempo do timeseries começa em 0
t_ts = t_sim - t_sim(1);
cmd_vx_ts = timeseries(sim_vx, t_ts, 'Name', 'cmd_vx');
cmd_vy_ts = timeseries(sim_vy, t_ts, 'Name', 'cmd_vy');
cmd_vw_ts = timeseries(sim_vw, t_ts, 'Name', 'cmd_vw');

cmd_vx_ts.DataInfo.Units = 'm/s';
cmd_vy_ts.DataInfo.Units = 'm/s';
cmd_vw_ts.DataInfo.Units = 'rad/s';
cmd_vx_ts.TimeInfo.Units = 'seconds';
cmd_vy_ts.TimeInfo.Units = 'seconds';
cmd_vw_ts.TimeInfo.Units = 'seconds';

fprintf('\nTimeseries a 60Hz: %d pontos, dur=%.2fs\n', ...
        numel(cmd_vx_ts.Time), cmd_vx_ts.Time(end));

save('cmd_timeseries.mat', 'cmd_vx_ts', 'cmd_vy_ts', 'cmd_vw_ts');
fprintf('✅ Salvo em cmd_timeseries.mat\n');

figure('Name','Comandos a 60Hz pro Simulink');
subplot(3,1,1); plot(cmd_vx_ts); ylabel('v_x (m/s)'); grid on; title('Comandos do robô');
subplot(3,1,2); plot(cmd_vy_ts); ylabel('v_y (m/s)'); grid on;
subplot(3,1,3); plot(cmd_vw_ts); ylabel('\omega (rad/s)'); grid on; xlabel('t (s)');
