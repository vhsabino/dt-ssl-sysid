%% load_log_to_timeseries.m
% Carrega comandos (move_x/y/w) E posições (position_x/y/w) dos logs SSL
% e gera timeseries a 60Hz alinhados em t=0 pra alimentar o Simulink.
%
% Saídas no workspace:
%   cmd_vx_ts, cmd_vy_ts, cmd_vw_ts   <- comandos (m/s, m/s, rad/s)
%   pos_x_ts,  pos_y_ts,  pos_w_ts    <- posição truth (mm, mm, rad)
%
% Aceita dois tipos de SOURCE_DIR:
%   (A) Pasta de splits:    '.../splits'                          -> usa all_*_labeled.parquet
%   (B) Pasta de um chunk:  '.../splits/square/square_01_01'      -> usa {commands, processed_robots}.parquet

clear; clc;

% ---------------- CONFIG ----------------
SOURCE_DIR = 'extracted/2026-05-18_19-2-15'; %/splits/square/square_01_01';
ROBOT_ID   = 3;                       % usado só no modo splits
TEAM       = 'allies';                % 'allies' ou 'enemies'
SIM_FREQ   = 60;
USE_EVENT  = '';                       % modo splits: '' = todos; ex: 'square_01_03'
% ----------------------------------------

dt_sim = 1/SIM_FREQ;

%% --- detecta modo + carrega tabelas ---
% commands
chunk_cmd_pq  = fullfile(SOURCE_DIR, 'commands.parquet');
chunk_cmd_cs  = fullfile(SOURCE_DIR, 'commands.csv');
splits_cmd_pq = fullfile(SOURCE_DIR, 'all_commands_labeled.parquet');

% processed_robots
chunk_rob_pq  = fullfile(SOURCE_DIR, 'processed_robots.parquet');
chunk_rob_cs  = fullfile(SOURCE_DIR, 'processed_robots.csv');
splits_rob_pq = fullfile(SOURCE_DIR, 'all_processed_robots_labeled.parquet');

if isfile(chunk_cmd_pq) || isfile(chunk_cmd_cs)
    mode = 'chunk';
    if isfile(chunk_cmd_pq), cmd = parquetread(chunk_cmd_pq); else, cmd = readtable(chunk_cmd_cs); end
    if isfile(chunk_rob_pq), rob = parquetread(chunk_rob_pq); else, rob = readtable(chunk_rob_cs); end
    fprintf('Modo CHUNK: %s\n', SOURCE_DIR);

elseif isfile(splits_cmd_pq)
    mode = 'splits';
    cmd = parquetread(splits_cmd_pq);
    rob = parquetread(splits_rob_pq);
    cmd = cmd(cmd.robot_id == ROBOT_ID, :);
    rob = rob(strcmp(rob.team, TEAM) & rob.robot_id == ROBOT_ID, :);
    if ~isempty(USE_EVENT)
        cmd = cmd(strcmp(cmd.event_id, USE_EVENT), :);
        rob = rob(strcmp(rob.event_id, USE_EVENT), :);
    end
    fprintf('Modo SPLITS: %s (team=%s, robot=%d)\n', SOURCE_DIR, TEAM, ROBOT_ID);

else
    error('Não encontrei os parquets em %s', SOURCE_DIR);
end

%% --- escolhe coluna de tempo ---
tcol_cmd = pickTimeCol(cmd);
tcol_rob = pickTimeCol(rob);

cmd = sortrows(cmd, tcol_cmd);  [~, ui] = unique(cmd.(tcol_cmd));  cmd = cmd(ui,:);
rob = sortrows(rob, tcol_rob);  [~, ui] = unique(rob.(tcol_rob));  rob = rob(ui,:);

if height(cmd) < 2 || height(rob) < 2
    error('Poucas amostras: cmd=%d, rob=%d', height(cmd), height(rob));
end

%% --- grid uniforme comum entre os dois streams ---
% intersecção da janela temporal (evita extrapolar onde não há dado)
t0 = max(cmd.(tcol_cmd)(1),   rob.(tcol_rob)(1));
t1 = min(cmd.(tcol_cmd)(end), rob.(tcol_rob)(end));
if t1 <= t0
    error('Não há sobreposição temporal entre comandos e posições.');
end
t_sim = (t0 : dt_sim : t1)';

fprintf('Comandos: %d amostras | Posições: %d amostras | janela comum: %.2fs\n', ...
        height(cmd), height(rob), t1 - t0);

%% --- interpolar ---
% comandos: ZOH (rádio é discreto)
sim_vx = interp1(cmd.(tcol_cmd), cmd.move_x, t_sim, 'previous', 'extrap');
sim_vy = interp1(cmd.(tcol_cmd), cmd.move_y, t_sim, 'previous', 'extrap');
sim_vw = interp1(cmd.(tcol_cmd), cmd.move_w, t_sim, 'previous', 'extrap');

% posições: linear (visão é amostragem contínua)
sim_x = interp1(rob.(tcol_rob), rob.position_x,           t_sim, 'linear', NaN);
sim_y = interp1(rob.(tcol_rob), rob.position_y,           t_sim, 'linear', NaN);
sim_w = interp1(rob.(tcol_rob), unwrap(rob.position_w),   t_sim, 'linear', NaN);
sim_w = atan2(sin(sim_w), cos(sim_w));   % re-embrulha em [-pi, pi]

%% --- timeseries (tempo começa em 0) ---
t_ts = t_sim - t_sim(1);

cmd_vx_ts = ts(sim_vx, t_ts, 'cmd_vx', 'm/s');
cmd_vy_ts = ts(sim_vy, t_ts, 'cmd_vy', 'm/s');
cmd_vw_ts = ts(sim_vw, t_ts, 'cmd_vw', 'rad/s');
pos_x_ts  = ts(sim_x,  t_ts, 'pos_x',  'mm');
pos_y_ts  = ts(sim_y,  t_ts, 'pos_y',  'mm');
pos_w_ts  = ts(sim_w,  t_ts, 'pos_w',  'rad');

fprintf('\nTimeseries a 60Hz: %d pontos, dur=%.2fs\n', numel(t_ts), t_ts(end));

save('log_timeseries.mat', ...
     'cmd_vx_ts','cmd_vy_ts','cmd_vw_ts', ...
     'pos_x_ts','pos_y_ts','pos_w_ts');
fprintf('✅ Salvo em log_timeseries.mat\n');

%% --- visualização ---
figure('Name','Comandos + Posições a 60Hz');
subplot(3,2,1); plot(cmd_vx_ts); ylabel('cmd v_x (m/s)');  grid on; title('Comandos');
subplot(3,2,3); plot(cmd_vy_ts); ylabel('cmd v_y (m/s)');  grid on;
subplot(3,2,5); plot(cmd_vw_ts); ylabel('cmd \omega (rad/s)'); grid on; xlabel('t (s)');
subplot(3,2,2); plot(pos_x_ts);  ylabel('pos x (mm)');     grid on; title('Posições (truth)');
subplot(3,2,4); plot(pos_y_ts);  ylabel('pos y (mm)');     grid on;
subplot(3,2,6); plot(pos_w_ts);  ylabel('pos \theta (rad)'); grid on; xlabel('t (s)');

%% ============ helpers ============
function c = pickTimeCol(T)
    if ismember('timestamp_event', T.Properties.VariableNames)
        c = 'timestamp_event';
    else
        c = 'timestamp';
    end
end

function ts_obj = ts(data, t, name, unit)
    ts_obj = timeseries(data, t, 'Name', name);
    ts_obj.DataInfo.Units = unit;
    ts_obj.TimeInfo.Units = 'seconds';
end

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