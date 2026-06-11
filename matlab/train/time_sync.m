%% Configuração Inicial
clear; clc;
filename = 'group_phase_robodragons_robocin.log.gz.txt'; % Substitua pelo nome do seu arquivo exportado
target_team = 'robots_blue';       % 'robots_yellow' ou 'robots_blue'
target_id = 7;                       % ID do robô que você quer modelar

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
            
            % Usamos o timestamp raiz (em nanosegundos) para garantir a 
            % mesma base de tempo entre câmera e comandos
            raw_ts = double(data.timestamp);
            if isempty(time_ref)
                time_ref = raw_ts;
            end
            t_sec = (raw_ts - time_ref) / 1e9;
            
            % --- Extração da Câmera (Ground Truth) ---
            if isfield(data, 'raw_frame') && ~isempty(data.raw_frame)
                % O raw_frame é um array, pegamos o primeiro pacote
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
                        % Pode usar t_sec da raiz ou o publish_timestamp interno
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

%% 3. Pré-processamento e Remoção de Duplicatas
% Interpolação no MATLAB exige que os timestamps sejam estritamente crescentes
[cam_data.t, unique_cam_idx] = unique(cam_data.t);
cam_data.x = cam_data.x(unique_cam_idx);
cam_data.y = cam_data.y(unique_cam_idx);
cam_data.w = cam_data.w(unique_cam_idx);

[cmd_data.t, unique_cmd_idx] = unique(cmd_data.t);
cmd_data.vx = cmd_data.vx(unique_cmd_idx);
cmd_data.vy = cmd_data.vy(unique_cmd_idx);
cmd_data.vw = cmd_data.vw(unique_cmd_idx);

% Desdobra o ângulo para evitar saltos de PI para -PI na interpolação
cam_data.w_unwrapped = unwrap(cam_data.w);

%% 4. Sincronização para 60Hz (Digital Twin Grid)
fprintf('Sincronizando para a malha de %d Hz...\n', sim_freq);

% Define o tempo final como o menor tempo máximo entre as duas fontes
t_max = min(max(cam_data.t), max(cmd_data.t));
t_sim = 0 : dt_sim : t_max; % Vetor de tempo síncrono

% A. Ground Truth (Interpolação Linear)
% Usamos 'extrap' para evitar NaN nas bordas, caso t_sim ultrapasse milissegundos
sim_x = interp1(cam_data.t, cam_data.x, t_sim, 'linear', 'extrap');
sim_y = interp1(cam_data.t, cam_data.y, t_sim, 'linear', 'extrap');
sim_w_unwrapped = interp1(cam_data.t, cam_data.w_unwrapped, t_sim, 'linear', 'extrap');

% Re-enrola o ângulo para o intervalo [-PI, PI]
sim_w = atan2(sin(sim_w_unwrapped), cos(sim_w_unwrapped));

% B. Comandos de Controle (Zero-Order Hold)
% A tag 'previous' garante que o comando se mantenha em degrau até o próximo pacote chegar
sim_cmd_vx = interp1(cmd_data.t, cmd_data.vx, t_sim, 'previous', 'extrap');
sim_cmd_vy = interp1(cmd_data.t, cmd_data.vy, t_sim, 'previous', 'extrap');
sim_cmd_vw = interp1(cmd_data.t, cmd_data.vw, t_sim, 'previous', 'extrap');

%% 5. Consolidação dos Dados de Treinamento
% Tabela final perfeitamente síncrona pronta para alimentar o otimizador
digital_twin_data = table(t_sim', sim_x', sim_y', sim_w', sim_cmd_vx', sim_cmd_vy', sim_cmd_vw', ...
    'VariableNames', {'time', 'pos_x', 'pos_y', 'pos_w', 'cmd_vx', 'cmd_vy', 'cmd_vw'});

disp(head(digital_twin_data));

%% 6. Visualização do Zero-Order Hold vs Interpolação
figure('Name', 'Sincronização do Robô');
subplot(2,1,1);
plot(cam_data.t, cam_data.x, 'o', 'MarkerSize', 4, 'DisplayName', 'Câmera (Assíncrono)');
hold on;
plot(t_sim, sim_x, '.-', 'DisplayName', 'Digital Twin (60Hz)');
title('Sincronização de Posição (Interpolação)');
xlabel('Tempo (s)'); ylabel('Posição X (mm)');
legend; grid on;

subplot(2,1,2);
plot(cmd_data.t, cmd_data.vx, 'o', 'MarkerSize', 4, 'DisplayName', 'Rádio (Assíncrono)');
hold on;
plot(t_sim, sim_cmd_vx, '.-', 'DisplayName', 'Digital Twin (ZOH)');
title('Sincronização de Comando (Zero-Order Hold)');
xlabel('Tempo (s)'); ylabel('Velocidade X (m/s)');
legend; grid on;