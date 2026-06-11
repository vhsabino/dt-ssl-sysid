function VisualizadorTempoReal()
% VisualizadorTempoReal - Visualiza robot0 e bola via ROS 2 em Tempo Real
% Requer: MATLAB ROS Toolbox e GUI Layout Toolbox

    clear;
    % 1. Crie o modelo com um nome ÚNICO (não use 'tf')
    %motor_sys = tf([1.732715862170721e+05], [1 2.299096640113972e+04 1.858402702347436e+05]); % Exemplo: 1 / (0.05s + 1)

    % 2. Extraia os números limpos para vetores
    % O flag 'v' garante que venha como vetor, não como célula
    %[num_motor, den_motor] = tfdata(motor_sys, 'v');

    Kp = 0.3194;
    Ki = 6.434;
    Kd = 0;

    df = 0.3;
    dm = 1000;
    max_i = 2.527100000000000e+03;

    % 1. Definição do sistema contínuo (o que você já tem)
    num_motor = [1.732715862170721e+05];
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
    
    %% 1. Configurações de Rede ROS (AJUSTE AQUI)
    ROBOT_TOPIC = '/robot0/pose';        % Tópico de Pose do Robô (geometry_msgs/Pose)
    BALL_TOPIC  = '/vision/ball';        % Tópico da Bola (opcional, se houver)
    NODE_NAME   = '/matlab_viz_node';
    
    %% 2. Configurações do Campo
    FIELD_X_MIN = -6000; FIELD_X_MAX = 6000;
    FIELD_Y_MIN = -4500; FIELD_Y_MAX = 4500;
    FIELD_LENGTH = FIELD_X_MAX - FIELD_X_MIN;
    GOAL_WIDTH = 1800;
    GOAL_DEPTH = 180;
    GOAL_Y = 0;
    
    % Fator de Conversão: Isaac (Metros) -> Visualizador (Milímetros)
    SCALE_FACTOR = 1000; 

    %% 3. Inicialização ROS
    fprintf('Iniciando Nó ROS 2...\n');
    try
        node = ros2node(NODE_NAME);
    catch
        % Se o nó já existir, tenta reutilizar ou recriar
        fprintf('Nó já existe ou erro de rede. Tentando reconectar...\n');
        ros2('shutdown'); % Mata nós antigos
        node = ros2node(NODE_NAME);
    end

    % Assinantes (Subscribers)
    fprintf('Assinando tópicos...\n');
    subRobot = ros2subscriber(node, ROBOT_TOPIC, 'geometry_msgs/Pose');
    
    % Tenta assinar bola (se não existir, cria dummy)
    hasBall = false;
    try
        subBall = ros2subscriber(node, BALL_TOPIC, 'geometry_msgs/Pose'); % Ajuste o tipo se for Point
        hasBall = true;
    catch
        fprintf('Aviso: Tópico da bola não detectado ou configurado.\n');
        subBall = [];
    end

    %% 4. Interface Gráfica (GUI Layout) - Mantida Original
    hFig = figure('Name', 'Visualizador Tempo Real - Robot0', ...
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
    hRobotPlot = hgtransform('Parent', hAx); % Transform para o robô
    
    % Desenhar o Robô (Quadrado Azul)
    robotRadius = 180; 
    rectangle('Parent', hRobotPlot, 'Position', [-robotRadius, -robotRadius, 2*robotRadius, 2*robotRadius], ...
              'Curvature', [1 1], 'FaceColor', [0.2, 0.6, 1], 'EdgeColor', 'k');
    line('Parent', hRobotPlot, 'XData', [0, robotRadius], 'YData', [0, 0], 'Color', 'k', 'LineWidth', 2);

    % Painel de Controles (Simplificado para Tempo Real)
    controlsPanel = uix.HBox('Parent', leftLayout, 'Padding', 5, 'Spacing', 10);
    leftLayout.Heights = [-1, 40]; 
    uicontrol('Parent', controlsPanel, 'Style', 'text', 'String', 'LIVE STREAMING', ...
              'FontSize', 14, 'FontWeight', 'bold', 'ForegroundColor', 'r');
    
    % --- PAINEL DE FEATURES ---
    statsPanel = uipanel('Parent', rootLayout, 'Title', 'Telemetria em Tempo Real', ...
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
    % Atualiza a 30 FPS
    hTimer = timer('ExecutionMode', 'fixedRate', 'Period', 0.033, 'TimerFcn', @updateLoop);
    start(hTimer);

    %% Callback Principal
    function updateLoop(~, ~)
        try
            % 1. Ler Robô
            robotMsg = subRobot.LatestMessage;
            if isempty(robotMsg)
                return; % Sem dados ainda
            end
            
            % Conversão Metros -> Milímetros
            rx = robotMsg.position.x * SCALE_FACTOR;
            ry = robotMsg.position.y * SCALE_FACTOR;
            
            % Conversão Quaternion -> Euler (Yaw)
            quat = [robotMsg.orientation.w, robotMsg.orientation.x, ...
                    robotMsg.orientation.y, robotMsg.orientation.z];
            eul = quat2eul(quat); % Retorna [Yaw, Pitch, Roll] ou ZYX
            rth = eul(1); % Yaw
            
            % 2. Ler Bola (Se houver)
            bx = 0; by = 0;
            if hasBall
                ballMsg = subBall.LatestMessage;
                if ~isempty(ballMsg)
                    bx = ballMsg.position.x * SCALE_FACTOR;
                    by = ballMsg.position.y * SCALE_FACTOR;
                end
            end
            
            % 3. Atualizar Gráficos
            % Posição do Robô (Matriz de Transformação)
            M = makehgtform('translate', [rx, ry, 0], 'zrotate', rth);
            set(hRobotPlot, 'Matrix', M);
            
            % Posição da Bola
            set(hBallPlot, 'XData', bx, 'YData', by);
            
            % Linha Robô -> Gol (Assume Gol Direito X+)
           % targetGoalX = FIELD_LENGTH/2; 
           % set(hLineDistGoal, 'XData', [rx, targetGoalX], 'YData', [ry, 0]);
            
            % 4. Atualizar Textos
            set(hTxt_PosX, 'String', sprintf('%.0f', rx));
            set(hTxt_PosY, 'String', sprintf('%.0f', ry));
            set(hTxt_Theta, 'String', sprintf('%.1f', rad2deg(rth)));
            
            % Features simples
            %distGoal = sqrt((rx - targetGoalX)^2 + (ry - 0)^2);
            %angleGoal = atan2(0 - ry, targetGoalX - rx);
            
            %set(hTxt_DistGoal, 'String', sprintf('%.0f', distGoal));
            %set(hTxt_AngGoal, 'String', sprintf('%.1f', rad2deg(angleGoal)));
            
            drawnow limitrate;
            
        catch ME
            fprintf('Erro no loop: %s\n', ME.message);
        end
    end

    function closeApp(~, ~)
        stop(hTimer); delete(hTimer);
        delete(hFig);
        % Opcional: Não limpar o nó ROS para não travar outras coisas
        % ros2('shutdown'); 
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