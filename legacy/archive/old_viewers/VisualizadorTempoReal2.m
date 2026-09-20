function VisualizadorTempoReal2()
% VisualizadorTempoReal - Visualiza robot0, robot0_truth e bola via ROS 2 em Tempo Real
% Requer: MATLAB ROS Toolbox e GUI Layout Toolbox
    clear;
    % 1. Crie o modelo com um nome ÚNICO (não use 'tf')
    Kp = 0.3194;
    Ki = 6.434;
    Kd = 0;
    df = 0.3;
    dm = 1000;
    max_i = 2.527100000000000e+03;
    
    % Definição do sistema contínuo
    num_motor = [1.732715862170721e+05];
    den_motor = [1 2.299096640113972e+04 1.858402702347436e+05];
    motor_sys = tf(num_motor, den_motor);
    
    % Definição das taxas de amostragem
    Ts_real = 0.002;     % 2ms (Frequência do mundo real: 500Hz)
    Ts_sim  = 0.0167;    % ~16.6ms (Frequência da simulação / 60Hz)
    
    % Discretização para a simulação
    motor_sys_d = c2d(motor_sys, Ts_sim, 'zoh');
    [num_d, den_d] = tfdata(motor_sys_d, 'v');
    
    %% 1. Configurações de Rede ROS (AJUSTE AQUI)
    ROBOT_TOPIC       = '/robot0/pose';        
    ROBOT_TRUTH_TOPIC = '/robot0_truth/pose';  % Tópico do robô truth
    BALL_TOPIC        = '/vision/ball';        
    NODE_NAME         = '/matlab_viz_node';
    
    %% 2. Configurações do Campo
    FIELD_X_MIN = -6000; FIELD_X_MAX = 6000;
    FIELD_Y_MIN = -4500; FIELD_Y_MAX = 4500;
    FIELD_LENGTH = FIELD_X_MAX - FIELD_X_MIN;
    GOAL_WIDTH = 1800;
    GOAL_DEPTH = 180;
    
    % Fator de Conversão: Isaac (Metros) -> Visualizador (Milímetros)
    SCALE_FACTOR = 1000; 
    
    %% 3. Inicialização ROS
    fprintf('Iniciando Nó ROS 2...\n');
    try
        node = ros2node(NODE_NAME);
    catch
        fprintf('Nó já existe ou erro de rede. Tentando reconectar...\n');
        ros2('shutdown'); 
        node = ros2node(NODE_NAME);
    end
    
    % Assinantes (Subscribers)
    fprintf('Assinando tópicos...\n');
    subRobot      = ros2subscriber(node, ROBOT_TOPIC, 'geometry_msgs/Pose');
    subRobotTruth = ros2subscriber(node, ROBOT_TRUTH_TOPIC, 'geometry_msgs/Pose');
    
    hasBall = false;
    try
        subBall = ros2subscriber(node, BALL_TOPIC, 'geometry_msgs/Pose'); 
        hasBall = true;
    catch
        fprintf('Aviso: Tópico da bola não detectado ou configurado.\n');
        subBall = [];
    end
    
    %% 4. Interface Gráfica (GUI Layout)
    hFig = figure('Name', 'Visualizador Tempo Real - Robot0 e Truth', ...
                  'NumberTitle', 'off', ...
                  'Units', 'pixels', 'Position', [50, 50, 1200, 700], ...
                  'CloseRequestFcn', @closeApp);
              
    % Layout Principal
    rootLayout = uix.HBox('Parent', hFig, 'Padding', 10, 'Spacing', 10);
    leftLayout = uix.VBox('Parent', rootLayout, 'Spacing', 5);
    
    % Painel do Campo
    fieldPanel = uipanel('Parent', leftLayout, 'BorderType', 'none', 'BackgroundColor', [0 0.5 0]);
    hAx = axes('Parent', fieldPanel, 'Units', 'normalized', 'Position', [0.05 0.05 0.9 0.9], ...
                 'Color', [0 0.6 0], 'XColor', 'w', 'YColor', 'w', 'DataAspectRatio', [1 1 1]);
    hold(hAx, 'on'); grid(hAx, 'on');
    set(hAx, 'GridColor', 'w', 'GridAlpha', 0.3);
    xlim(hAx, [FIELD_X_MIN - 500, FIELD_X_MAX + 500]);
    ylim(hAx, [FIELD_Y_MIN - 500, FIELD_Y_MAX + 500]);
    
    drawSoccerField(hAx, FIELD_X_MIN, FIELD_X_MAX, FIELD_Y_MIN, FIELD_Y_MAX, GOAL_WIDTH, GOAL_DEPTH);
    
    % Elementos Gráficos
    hBallPlot = plot(hAx, 0, 0, 'o', 'MarkerSize', 8, 'MarkerFaceColor', 'r', 'MarkerEdgeColor', 'w');
    hLineDistGoal = plot(hAx, [0 0], [0 0], 'r--', 'LineWidth', 1.5);       
    
    % Linhas de Rastro (Trails) - Limite de 10.000 pontos para não estourar a memória RAM
    hTrail0 = animatedline(hAx, 'Color', [0.2, 0.6, 1], 'LineWidth', 1.5, 'MaximumNumPoints', 10000);
    hTrailTruth = animatedline(hAx, 'Color', [1, 1, 0], 'LineWidth', 1.5, 'MaximumNumPoints', 10000);

    robotRadius = 180; 
    
    % Desenhar o Robô 0 (Quadrado Azul)
    hRobotPlot = hgtransform('Parent', hAx); 
    rectangle('Parent', hRobotPlot, 'Position', [-robotRadius, -robotRadius, 2*robotRadius, 2*robotRadius], ...
              'Curvature', [1 1], 'FaceColor', [0.2, 0.6, 1], 'EdgeColor', 'k');
    line('Parent', hRobotPlot, 'XData', [0, robotRadius], 'YData', [0, 0], 'Color', 'k', 'LineWidth', 2);

    % Desenhar o Robô Truth (Quadrado Amarelo)
    hRobotTruthPlot = hgtransform('Parent', hAx); 
    rectangle('Parent', hRobotTruthPlot, 'Position', [-robotRadius, -robotRadius, 2*robotRadius, 2*robotRadius], ...
              'Curvature', [1 1], 'FaceColor', [1, 1, 0], 'EdgeColor', 'k');
    line('Parent', hRobotTruthPlot, 'XData', [0, robotRadius], 'YData', [0, 0], 'Color', 'k', 'LineWidth', 2);
    
    % Painel de Controles
    controlsPanel = uix.HBox('Parent', leftLayout, 'Padding', 5, 'Spacing', 10);
    leftLayout.Heights = [-1, 40]; 
    uicontrol('Parent', controlsPanel, 'Style', 'text', 'String', 'LIVE STREAMING', ...
              'FontSize', 14, 'FontWeight', 'bold', 'ForegroundColor', 'r');
    
    % --- PAINEL DE FEATURES ---
    statsPanel = uipanel('Parent', rootLayout, 'Title', 'Telemetria em Tempo Real (Robot0)', ...
        'FontSize', 12, 'BackgroundColor', 'k', 'ForegroundColor', 'w');
    statsLayout = uix.VBox('Parent', statsPanel, 'Padding', 10, 'Spacing', 5);
    
    function h = createStatLabel(parent, label)
        uicontrol('Parent', parent, 'Style', 'text', 'String', label, 'FontWeight', 'bold', ...
            'FontSize', 10, 'HorizontalAlignment', 'left', 'BackgroundColor', 'k', 'ForegroundColor', 'w');
        h = uicontrol('Parent', parent, 'Style', 'text', 'String', '-', 'FontSize', 10, ...
            'BackgroundColor', [1 1 1], 'ForegroundColor', [0 0 0], 'HorizontalAlignment', 'center');
    end
    
    hTxt_PosX     = createStatLabel(statsLayout, 'Posição X (mm):');
    hTxt_PosY     = createStatLabel(statsLayout, 'Posição Y (mm):');
    hTxt_Theta    = createStatLabel(statsLayout, 'Orientação (°):');
    hTxt_DistGoal = createStatLabel(statsLayout, 'Distância Gol (mm):');
    hTxt_AngGoal  = createStatLabel(statsLayout, 'Ângulo Gol (°):');
    
    rootLayout.Widths = [-0.7, -0.3];
    
    %% 5. Loop de Atualização (Timer)
    % Atualiza a 60 FPS (1/60 = ~0.0167 segundos)
    hTimer = timer('ExecutionMode', 'fixedRate', 'Period', 1/60, 'TimerFcn', @updateLoop);
    start(hTimer);
    
    %% Callback Principal
    function updateLoop(~, ~)
        try
            targetGoalX = FIELD_LENGTH/2; % Referência para a telemetria do gol
            
            % --- 1. Ler e Atualizar Robô 0 (Azul) ---
            robotMsg = subRobot.LatestMessage;
            if ~isempty(robotMsg)
                rx = robotMsg.position.x * SCALE_FACTOR;
                ry = robotMsg.position.y * SCALE_FACTOR;
                
                quat = [robotMsg.orientation.w, robotMsg.orientation.x, ...
                        robotMsg.orientation.y, robotMsg.orientation.z];
                eul = quat2eul(quat); 
                rth = eul(1); % Yaw
                
                % Atualiza Transformada do Robô 0
                M = makehgtform('translate', [rx, ry, 0], 'zrotate', rth);
                set(hRobotPlot, 'Matrix', M);
                
                % Adiciona ponto ao rastro azul
                addpoints(hTrail0, rx, ry);
                
                % Linha Robô -> Gol 
                %set(hLineDistGoal, 'XData', [rx, targetGoalX], 'YData', [ry, 0]);
                
                % Atualizar Textos de Telemetria
                set(hTxt_PosX, 'String', sprintf('%.0f', rx));
                set(hTxt_PosY, 'String', sprintf('%.0f', ry));
                set(hTxt_Theta, 'String', sprintf('%.1f', rad2deg(rth)));
                
                distGoal = sqrt((rx - targetGoalX)^2 + (ry - 0)^2);
                angleGoal = atan2(0 - ry, targetGoalX - rx);
                
                set(hTxt_DistGoal, 'String', sprintf('%.0f', distGoal));
                set(hTxt_AngGoal, 'String', sprintf('%.1f', rad2deg(angleGoal)));
            end

            % --- 2. Ler e Atualizar Robô Truth (Amarelo) ---
            truthMsg = subRobotTruth.LatestMessage;
            if ~isempty(truthMsg)
                rx_t = truthMsg.position.x * SCALE_FACTOR;
                ry_t = truthMsg.position.y * SCALE_FACTOR;
                
                quat_t = [truthMsg.orientation.w, truthMsg.orientation.x, ...
                          truthMsg.orientation.y, truthMsg.orientation.z];
                eul_t = quat2eul(quat_t); 
                rth_t = eul_t(1); % Yaw
                
                % Atualiza Transformada do Robô Truth
                M_t = makehgtform('translate', [rx_t, ry_t, 0], 'zrotate', rth_t);
                set(hRobotTruthPlot, 'Matrix', M_t);
                
                % Adiciona ponto ao rastro amarelo
                addpoints(hTrailTruth, rx_t, ry_t);
            end
            
            % --- 3. Ler Bola (Se houver) ---
            if hasBall
                ballMsg = subBall.LatestMessage;
                if ~isempty(ballMsg)
                    bx = ballMsg.position.x * SCALE_FACTOR;
                    by = ballMsg.position.y * SCALE_FACTOR;
                    set(hBallPlot, 'XData', bx, 'YData', by);
                end
            end
            
            drawnow limitrate;
            
        catch ME
            fprintf('Erro no loop: %s\n', ME.message);
        end
    end

    function closeApp(~, ~)
        stop(hTimer); delete(hTimer);
        delete(hFig);
    end
end

%% FUNÇÃO AUXILIAR DE DESENHO (Mantida Original)
function drawSoccerField(ax, xmin, xmax, ymin, ymax, goalW, goalD)
    lineColor = 'w'; lineWidth = 2;
    rectangle(ax, 'Position', [xmin, ymin, xmax-xmin, ymax-ymin], ...
              'EdgeColor', lineColor, 'LineWidth', lineWidth, 'FaceColor', 'none');
    line(ax, [0, 0], [ymin, ymax], 'Color', lineColor, 'LineWidth', lineWidth);
    centerRadius = 500; 
    rectangle(ax, 'Position', [-centerRadius, -centerRadius, 2*centerRadius, 2*centerRadius], ...
              'Curvature', [1,1], 'EdgeColor', lineColor, 'LineWidth', lineWidth);
    rectangle(ax, 'Position', [xmin - goalD, -goalW/2, goalD, goalW], ...
              'EdgeColor', lineColor, 'LineWidth', lineWidth);
    rectangle(ax, 'Position', [xmax, -goalW/2, goalD, goalW], ...
              'EdgeColor', lineColor, 'LineWidth', lineWidth);
    defenseDepth = 1800; defenseWidth = 3600;
    rectangle(ax, 'Position', [xmin, -defenseWidth/2, defenseDepth, defenseWidth], ...
              'EdgeColor', lineColor, 'LineWidth', lineWidth);
    rectangle(ax, 'Position', [xmax - defenseDepth, -defenseWidth/2, defenseDepth, defenseWidth], ...
              'EdgeColor', lineColor, 'LineWidth', lineWidth);
end