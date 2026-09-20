% smoke_test_caminho2.m

mdl = 'parameter_estimation_model_pid_v3';
load_system(mdl);

%% 1. Setup mínimo dos parâmetros per-DOF (placeholder)
% Valores chutes razoáveis; serão substituídos pelo procest depois
K_vx = 1.0;   tau_vx = 0.15;  Td_vx = 0.0167;
K_vy = 1.0;   tau_vy = 0.15;  Td_vy = 0.0167;
K_w  = 1.0;   tau_w  = 0.12;  Td_w  = 0.0167;

load("C:\Users\victo\Documents\digitaltwin\scripts\local\train\robocin_tests_id5.mat")
% 1. Crie o modelo com um nome ÚNICO (não use 'tf')
%motor_sys = tf([1.732715862170721e+05], [1 2.299096640113972e+04 1.858402702347436e+05]); % Exemplo: 1 / (0.05s + 1)

% 2. Extraia os números limpos para vetores
% O flag 'v' garante que venha como vetor, não como célula
%[num_motor, den_motor] = tfdata(motor_sys, 'v');
% Tempo de amostragem do modelo
Ts = 0.0167;
Kp_initial = 0.3194;
Ki_initial = 6.434;
Kp1_action = 0;
Ki1_action = 0;
Kp2_action = 0;
Ki2_action = 0;
Kp3_action = 0;
Ki3_action = 0;
Kp4_action = 0;
Ki4_action = 0;
df = 0.3;
dm = 1000;
max_i = 2.527100000000000e+03;
K1_base = 34.990925405431859; 
K2_base = 20.2020202020202;   
K3_base = 28.569970957032222; 
K4_base = 3.324525253;      
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

% 1. Filtrar o intervalo e REMOVER qualquer linha corrompida (NaN)
filtro = digital_twin_data.time >= 0 & digital_twin_data.time <= 60;
dados_limpos = rmmissing(digital_twin_data(filtro, :));

% 2. Garantir que o vetor de tempo comece rigorosamente em 0.0
t_cru = dados_limpos.time - dados_limpos.time(1);

% 3. Remover tempos duplicados (que causam derivada infinita)
[t_unico, idx_unicos] = unique(t_cru);
dados_limpos = dados_limpos(idx_unicos, :);

% Deslocar a posição inicial para a origem (0,0)
dados_limpos.pos_x = dados_limpos.pos_x - dados_limpos.pos_x(1);
dados_limpos.pos_y = dados_limpos.pos_y - dados_limpos.pos_y(1);
% dados_limpos.pos_w = dados_limpos.pos_w - dados_limpos.pos_w(1); % Opcional para o ângulo inicial

% Dividir os campos por 1000 (Conversão de escala, ex: mm para metros)
dados_limpos.pos_x  = dados_limpos.pos_x  / 1000;
dados_limpos.pos_y  = dados_limpos.pos_y  / 1000;

% 4. Criar as timeseries para Inputs (Comandos)
cmd_vx_ts = timeseries(dados_limpos.cmd_vx, t_unico);
cmd_vy_ts = timeseries(dados_limpos.cmd_vy, t_unico);
cmd_vw_ts = timeseries(dados_limpos.cmd_vw, t_unico);

% O GRANDE TRUQUE: Forçar o método 'Zero-Order Hold'
% Isso impede o Simulink de tentar interpolar degraus e criar singularidades
cmd_vx_ts.DataInfo.Interpolation = tsdata.interpolation('zoh');
cmd_vy_ts.DataInfo.Interpolation = tsdata.interpolation('zoh');
cmd_vw_ts.DataInfo.Interpolation = tsdata.interpolation('zoh');

% 5. Criar as timeseries para Posições (Ground Truth)
pos_x_ts = timeseries(dados_limpos.pos_x, t_unico);
pos_y_ts = timeseries(dados_limpos.pos_y, t_unico);
pos_w_ts = timeseries(dados_limpos.pos_w, t_unico);

% Condições iniciais para os Discrete-Time Integrators
x0     = pos_x_ts(1);
y0     = pos_y_ts(1);
theta0 = pos_w_ts(1);

%% 3. Simula
simIn  = Simulink.SimulationInput(mdl);
simIn  = simIn.setVariable('cmd_vx_ts', cmd_vx_ts);
simIn  = simIn.setVariable('cmd_vy_ts', cmd_vy_ts);
simIn  = simIn.setVariable('cmd_vw_ts', cmd_vw_ts);
simIn  = simIn.setVariable('x0', x0);
simIn  = simIn.setVariable('y0', y0);
simIn  = simIn.setVariable('theta0', theta0);

out = sim(simIn);
N = 3601;
%% 4. Plota: modelo vs ground truth
figure;

% Plot 1: x
subplot(3,1,1);
plot(t_unico(1:N), pos_x_ts.Data(1:N), 'c-', 'LineWidth',1.5); hold on;
plot(out.tout, out.pos_x_out.Data, 'r--','LineWidth',1); % <-- Adicionado .Data
title('Posição X');
legend('Ground Truth', 'Modelo');

% Plot 2: y
subplot(3,1,2); % <-- Adicionado para não sobrescrever o gráfico de X
plot(t_unico(1:N), pos_y_ts.Data(1:N), 'c-', 'LineWidth',1.5); hold on;
plot(out.tout, out.pos_y_out.Data, 'r--','LineWidth',1); % <-- Adicionado .Data
title('Posição Y');

% Plot 3: theta
subplot(3,1,3); % <-- Adicionado para não sobrescrever
% Corrigido: 'theta_ts' alterado para 'pos_w_ts' conforme definido na seção 2
plot(t_unico(1:N), pos_w_ts.Data(1:N), 'c-', 'LineWidth',1.5); hold on;
plot(out.tout, out.theta_out.Data, 'r--','LineWidth',1); % <-- Adicionado .Data
title('Orientação Theta');

% Métricas
% Corrigido: Alterado _mdl para _out e adicionado .Data para o interp1 funcionar
ex = pos_x_ts.Data(1:N) - interp1(out.tout, out.pos_x_out.Data, t_unico(1:N));
ey = pos_y_ts.Data(1:N) - interp1(out.tout, out.pos_y_out.Data, t_unico(1:N));
rmse_pos = sqrt(mean(ex.^2 + ey.^2, 'omitnan')); % omitnan garante que não quebre se houver NaN na interpolação
fprintf('RMSE posição (10s): %.4f m\n', rmse_pos);