%% Configuração Inicial
clear; clc;
filename = '2025-04-01_16-38-42.log.gz.txt'; % Substitua pelo nome do seu arquivo
target_team = 'robots_blue';       % 'robots_yellow' ou 'robots_blue'
target_id = 5;                       % ID do robô que você quer modelar
sim_freq = 60;                       % Frequência do Gêmeo Digital em Hz
dt_sim = 1 / sim_freq;

if ~isfile(filename)
    error('Arquivo não encontrado: %s', filename);
end

%% 1. Inicialização de Buffers
cam_data = struct('t', [], 'x', [], 'y', [], 'w', []);
cmd_data = struct('t', [], 'vx', [], 'vy', [], 'vw', []);
time_ref = [];
fid = fopen(filename, 'r');
fprintf('Lendo o log e extraindo dados do Robô %s %d...\n', target_team, target_id);

%% 2. Leitura e Extração Assíncrona
while ~feof(fid)
    tline = fgetl(fid);
    if ischar(tline) && ~isempty(tline)
        try
            data = jsondecode(tline);
            
            raw_ts = double(data.timestamp);
            if isempty(time_ref)
                time_ref = raw_ts;
            end
            t_sec = (raw_ts - time_ref) / 1e9;
            
            % --- Extração da Câmera (Ground Truth) ---
            if isfield(data, 'raw_frame') && ~isempty(data.raw_frame)
                packet = data.raw_frame(1).packet;
                if isfield(packet, 'detection') && isfield(packet.detection, target_team)
                    robots = packet.detection.(target_team);
                    for i = 1:length(robots)
                        if robots(i).robot_id == target_id
                            cam_data.t(end+1)  = t_sec; %#ok<SAGROW>
                            cam_data.x(end+1)  = robots(i).x; %#ok<SAGROW>
                            cam_data.y(end+1)  = robots(i).y; %#ok<SAGROW>
                            cam_data.w(end+1)  = robots(i).orientation; %#ok<SAGROW>
                            break;
                        end
                    end
                end
            end
            
            % --- Extração dos Comandos (Inputs) ---
            if isfield(data, 'robots_command') && isfield(data.robots_command, 'navigation')
                nav = data.robots_command.navigation;
                for i = 1:length(nav)
                    if nav(i).id == target_id
                        cmd_data.t(end+1)  = t_sec; %#ok<SAGROW>
                        cmd_data.vx(end+1) = nav(i).move.x; %#ok<SAGROW>
                        cmd_data.vy(end+1) = nav(i).move.y; %#ok<SAGROW>
                        cmd_data.vw(end+1) = nav(i).move.omega; %#ok<SAGROW>
                        break;
                    end
                end
            end
            
        catch
            continue;
        end
    end
end
fclose(fid);
fprintf('Extraídos %d frames de câmera e %d comandos.\n', length(cam_data.t), length(cmd_data.t));

%% Segurança: Verifica se encontrou dados
if isempty(cam_data.t) || isempty(cmd_data.t)
    error('Não foram encontrados dados suficientes para a câmera ou comandos no log.');
end

%% 3. Sincronização para 60Hz (Zero-Order Hold Manual)
fprintf('Sincronizando para a malha de %d Hz usando ZOH puro...\n', sim_freq);

% Define o tempo final baseado nos dados disponíveis
t_max = min(max(cam_data.t), max(cmd_data.t));
t_sim = 0 : dt_sim : t_max; % Vetor de tempo síncrono
N_sim = length(t_sim);

% Pré-alocação dos vetores síncronos
sim_x = zeros(1, N_sim); sim_y = zeros(1, N_sim); sim_w = zeros(1, N_sim);
sim_cmd_vx = zeros(1, N_sim); sim_cmd_vy = zeros(1, N_sim); sim_cmd_vw = zeros(1, N_sim);

% --- A. ZOH para Ground Truth (Câmera) ---
idx = 1;
for i = 1:N_sim
    % Avança o índice do dado bruto enquanto ele for menor ou igual ao tempo da simulação atual
    while idx < length(cam_data.t) && cam_data.t(idx + 1) <= t_sim(i)
        idx = idx + 1;
    end
    % Atribui o último valor válido encontrado (se não atualizou, mantém o anterior)
    sim_x(i) = cam_data.x(idx);
    sim_y(i) = cam_data.y(idx);
    sim_w(i) = cam_data.w(idx);
end

% --- B. ZOH para Comandos de Controle ---
idx = 1;
for i = 1:N_sim
    % Mesmo princípio: busca a última instrução dada até o tempo atual
    while idx < length(cmd_data.t) && cmd_data.t(idx + 1) <= t_sim(i)
        idx = idx + 1;
    end
    sim_cmd_vx(i) = cmd_data.vx(idx);
    sim_cmd_vy(i) = cmd_data.vy(idx);
    sim_cmd_vw(i) = cmd_data.vw(idx);
end

%% 4. Consolidação dos Dados de Treinamento
% Tabela final perfeitamente síncrona pronta para Simulink/Otimizador
digital_twin_data = table(t_sim', sim_x', sim_y', sim_w', sim_cmd_vx', sim_cmd_vy', sim_cmd_vw', ...
    'VariableNames', {'time', 'pos_x', 'pos_y', 'pos_w', 'cmd_vx', 'cmd_vy', 'cmd_vw'});
disp(head(digital_twin_data));

%% 5. Visualização do Zero-Order Hold
figure('Name', 'Sincronização do Robô (ZOH Puro)');
subplot(2,1,1);
plot(cam_data.t, cam_data.x, 'o', 'MarkerSize', 4, 'DisplayName', 'Câmera (Assíncrono)');
hold on;
stairs(t_sim, sim_x, '.-', 'DisplayName', 'Digital Twin (ZOH 60Hz)'); % Usando stairs para evidenciar o ZOH
title('Sincronização de Posição (Zero-Order Hold)');
xlabel('Tempo (s)'); ylabel('Posição X (mm)');
legend; grid on;

subplot(2,1,2);
plot(cmd_data.t, cmd_data.vx, 'o', 'MarkerSize', 4, 'DisplayName', 'Rádio (Assíncrono)');
hold on;
stairs(t_sim, sim_cmd_vx, '.-', 'DisplayName', 'Digital Twin (ZOH 60Hz)');
title('Sincronização de Comando (Zero-Order Hold)');
xlabel('Tempo (s)'); ylabel('Velocidade X (m/s)');
legend; grid on;

%% 6. Exportação para o Simulink (Solução do Erro de Array)
fprintf('Gerando objetos timeseries para o Simulink...\n');

% 1. Criar as timeseries para os comandos (Inputs do Simulink)
% O formato é timeseries(Dados, Tempo). Usamos a aspa (') para garantir que sejam colunas.
cmd_vx_ts = timeseries(sim_cmd_vx', t_sim');
cmd_vy_ts = timeseries(sim_cmd_vy', t_sim');
cmd_vw_ts = timeseries(sim_cmd_vw', t_sim');

% 2. Criar as timeseries para as posições (Ground Truth / Referência)
pos_x_ts = timeseries(sim_x', t_sim');
pos_y_ts = timeseries(sim_y', t_sim');
pos_w_ts = timeseries(sim_w', t_sim');

% 3. Trava de segurança: Forçar o método ZOH nos metadados da timeseries
% Isso impede que o Simulink tente suavizar as curvas por conta própria
cmd_vx_ts.DataInfo.Interpolation = tsdata.interpolation('zoh');
cmd_vy_ts.DataInfo.Interpolation = tsdata.interpolation('zoh');
cmd_vw_ts.DataInfo.Interpolation = tsdata.interpolation('zoh');

pos_x_ts.DataInfo.Interpolation = tsdata.interpolation('zoh');
pos_y_ts.DataInfo.Interpolation = tsdata.interpolation('zoh');
pos_w_ts.DataInfo.Interpolation = tsdata.interpolation('zoh');

fprintf('Variáveis criadas com sucesso! No Simulink, use: cmd_vx_ts, cmd_vy_ts, cmd_vw_ts.\n');