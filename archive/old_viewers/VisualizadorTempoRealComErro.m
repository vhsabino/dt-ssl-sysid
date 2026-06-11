function VisualizadorTempoRealComErro()
% VisualizadorTempoReal - Visualiza robot0, robot0_truth, Bola e Erro (RMSE)
% Requer: MATLAB ROS Toolbox e GUI Layout Toolbox
    clear;
    
    %% 1. Configurações de Rede ROS
    ROBOT_TOPIC       = '/robot0/pose';        
    ROBOT_TRUTH_TOPIC = '/robot0_truth/pose';  
    BALL_TOPIC        = '/vision/ball';        
    NODE_NAME         = '/matlab_viz_node';
    
    %% 2. Configurações do Campo e Escala
    FIELD_X_MIN = -6000; FIELD_X_MAX = 6000;
    FIELD_Y_MIN = -4500; FIELD_Y_MAX = 4500;
    FIELD_LENGTH = FIELD_X_MAX - FIELD_X_MIN;
    GOAL_WIDTH = 1800; GOAL_DEPTH = 180;
    
    SCALE_FACTOR = 1000; % Metros -> Milímetros
    
    %% 3. Inicialização ROS
    fprintf('Iniciando Nó ROS 2...\n');
    try
        node = ros2node(NODE_NAME);
    catch
        fprintf('Nó já existe ou erro de rede. Tentando reconectar...\n');
        ros2('shutdown'); 
        node = ros2node(NODE_NAME);
    end
    
    fprintf('Assinando tópicos...\n');
    subRobot      = ros2subscriber(node, ROBOT_TOPIC, 'geometry_msgs/Pose');
    subRobotTruth = ros2subscriber(node, ROBOT_TRUTH_TOPIC, 'geometry_msgs/Pose');
    
    hasBall = false;
    try
        subBall = ros2subscriber(node, BALL_TOPIC, 'geometry_msgs/Pose'); 
        hasBall = true;
    catch
        fprintf('Aviso: Tópico da bola não detectado.\n');
        subBall = [];
    end
    
    %% 4. Variáveis Globais de Erro (Acumuladores)
    total_sq_err = 0; % Soma dos erros quadráticos
    metric_count = 0; % Contador de amostras
    t_start = tic;    % Cronômetro para o eixo X do gráfico de erro
    
    %% 5. Interface Gráfica (GUI Layout)
    hFig = figure('Name', 'Visualizador Digital Twin com Análise de Erro', ...
                  'NumberTitle', 'off', ...
                  'Units', 'pixels', 'Position', [50, 50, 1200, 900], ...
                  'CloseRequestFcn', @closeApp);
              
    % Layout Principal (Vertical: Topo = Campo/Stats, Base = Gráfico de Erro)
    mainVBox = uix.VBox('Parent', hFig, 'Padding', 10, 'Spacing', 10);
    
    % --- PARTE SUPERIOR (Campo e Stats) ---
    topLayout = uix.HBox('Parent', mainVBox, 'Spacing', 10);
    leftLayout = uix.VBox('Parent', topLayout, 'Spacing', 5);
    
    % Painel do Campo
    fieldPanel = uipanel('Parent', leftLayout, 'BorderType', 'none', 'BackgroundColor', [0 0.5 0]);
    hAxField = axes('Parent', fieldPanel, 'Units', 'normalized', 'Position', [0.05 0.05 0.9 0.9], ...
                 'Color', [0 0.6 0], 'XColor', 'w', 'YColor', 'w', 'DataAspectRatio', [1 1 1]);
    hold(hAxField, 'on'); grid(hAxField, 'on'); set(hAxField, 'GridColor', 'w', 'GridAlpha', 0.3);
    xlim(hAxField, [FIELD_X_MIN - 500, FIELD_X_MAX + 500]);
    ylim(hAxField, [FIELD_Y_MIN - 500, FIELD_Y_MAX + 500]);
    drawSoccerField(hAxField, FIELD_X_MIN, FIELD_X_MAX, FIELD_Y_MIN, FIELD_Y_MAX, GOAL_WIDTH, GOAL_DEPTH);
    
    % Elementos Visuais do Campo
    hBallPlot = plot(hAxField, 0, 0, 'o', 'MarkerSize', 8, 'MarkerFaceColor', 'r', 'MarkerEdgeColor', 'w');
    hTrail0 = animatedline(hAxField, 'Color', [0.2, 0.6, 1], 'LineWidth', 1.5, 'MaximumNumPoints', 10000);
    hTrailTruth = animatedline(hAxField, 'Color', [1, 1, 0], 'LineWidth', 1.5, 'MaximumNumPoints', 10000);
    
    robotRadius = 180; 
    hRobotPlot = hgtransform('Parent', hAxField); 
    rectangle('Parent', hRobotPlot, 'Position', [-robotRadius, -robotRadius, 2*robotRadius, 2*robotRadius], ...
              'Curvature', [1 1], 'FaceColor', [0.2, 0.6, 1], 'EdgeColor', 'k');
              
    hRobotTruthPlot = hgtransform('Parent', hAxField); 
    rectangle('Parent', hRobotTruthPlot, 'Position', [-robotRadius, -robotRadius, 2*robotRadius, 2*robotRadius], ...
              'Curvature', [1 1], 'FaceColor', [1, 1, 0], 'EdgeColor', 'k');
    
    % Painel de Controles
    controlsPanel = uix.HBox('Parent', leftLayout, 'Padding', 5, 'Spacing', 10);
    leftLayout.Heights = [-1, 40]; 
    uicontrol('Parent', controlsPanel, 'Style', 'text', 'String', 'LIVE STREAMING', ...
              'FontSize', 14, 'FontWeight', 'bold', 'ForegroundColor', 'r');
    
    % --- PAINEL DE FEATURES E ERROS ---
    statsPanel = uipanel('Parent', topLayout, 'Title', 'Telemetria e Erros', ...
        'FontSize', 12, 'BackgroundColor', 'k', 'ForegroundColor', 'w');
    statsLayout = uix.VBox('Parent', statsPanel, 'Padding', 10, 'Spacing', 5);
    
    function h = createStatLabel(parent, label, color)
        if nargin < 3, color = 'w'; end
        uicontrol('Parent', parent, 'Style', 'text', 'String', label, 'FontWeight', 'bold', ...
            'FontSize', 10, 'HorizontalAlignment', 'left', 'BackgroundColor', 'k', 'ForegroundColor', color);
        h = uicontrol('Parent', parent, 'Style', 'text', 'String', '-', 'FontSize', 10, ...
            'BackgroundColor', [1 1 1], 'ForegroundColor', [0 0 0], 'HorizontalAlignment', 'center');
    end
    
    hTxt_PosX     = createStatLabel(statsLayout, 'Posição X (mm):');
    hTxt_PosY     = createStatLabel(statsLayout, 'Posição Y (mm):');
    hTxt_ErrInst  = createStatLabel(statsLayout, 'Erro Instantâneo (mm):', 'y');
    hTxt_MSE      = createStatLabel(statsLayout, 'MSE (mm²):', 'r');
    hTxt_RMSE     = createStatLabel(statsLayout, 'RMSE (mm):', 'g');
    
    topLayout.Widths = [-0.7, -0.3];
    
    % --- PARTE INFERIOR (Gráfico de Erro) ---
    errorPanel = uipanel('Parent', mainVBox, 'Title', 'Métricas de Erro de Posição (Estimação vs Ground Truth)');
    hAxError = axes('Parent', errorPanel);
    hold(hAxError, 'on'); grid(hAxError, 'on');
    title(hAxError, 'Evolução do Erro no Tempo');
    xlabel(hAxError, 'Tempo (s)');
    ylabel(hAxError, 'Erro (mm)');
    
    % Linhas Animadas para o Gráfico de Erro
    hLineInstErr = animatedline(hAxError, 'Color', [0.8 0.8 0], 'LineWidth', 1, 'DisplayName', 'Erro Instantâneo');
    hLineRMSE    = animatedline(hAxError, 'Color', [0 0.8 0], 'LineWidth', 2, 'DisplayName', 'RMSE Acumulado');
    legend(hAxError, 'Location', 'northwest');
    
    % Proporção da Janela: 65% Campo superior, 35% Gráfico inferior
    mainVBox.Heights = [-0.65, -0.35]; 
    
    %% 6. Loop de Atualização (60Hz)
    hTimer = timer('ExecutionMode', 'fixedRate', 'Period', 1/60, 'TimerFcn', @updateLoop);
    start(hTimer);
    
    %% Callback Principal
    function updateLoop(~, ~)
        try
            robotMsg = subRobot.LatestMessage;
            truthMsg = subRobotTruth.LatestMessage;
            
            % Só calcula se possuir mensagens de AMBOS os robôs
            if ~isempty(robotMsg) && ~isempty(truthMsg)
                
                % 1. Posições Estimação (Azul)
                rx = robotMsg.position.x * SCALE_FACTOR;
                ry = robotMsg.position.y * SCALE_FACTOR;
                q_est = [robotMsg.orientation.w, robotMsg.orientation.x, robotMsg.orientation.y, robotMsg.orientation.z];
                eul_est = quat2eul(q_est); rth = eul_est(1);
                
                % 2. Posições Ground Truth (Amarelo)
                rx_t = truthMsg.position.x * SCALE_FACTOR;
                ry_t = truthMsg.position.y * SCALE_FACTOR;
                q_truth = [truthMsg.orientation.w, truthMsg.orientation.x, truthMsg.orientation.y, truthMsg.orientation.z];
                eul_truth = quat2eul(q_truth); rth_t = eul_truth(1);
                
                % --- CÁLCULO DE ERRO (MSE e RMSE) ---
                % Erro Euclidiano (Distância entre os dois centros)
                err_x = rx - rx_t;
                err_y = ry - ry_t;
                sq_err = err_x^2 + err_y^2;          % Erro Quadrático
                inst_err = sqrt(sq_err);             % Erro Instantâneo (mm)
                
                % Atualiza os acumuladores
                total_sq_err = total_sq_err + sq_err;
                metric_count = metric_count + 1;
                
                % Cálculos Finais
                mse = total_sq_err / metric_count;   % Mean Squared Error (mm²)
                rmse = sqrt(mse);                    % Root Mean Squared Error (mm)
                
                % Tempo atual para o gráfico
                t_atual = toc(t_start);
                
                % --- ATUALIZAÇÃO VISUAL ---
                % Gráficos do Campo
                set(hRobotPlot, 'Matrix', makehgtform('translate', [rx, ry, 0], 'zrotate', rth));
                set(hRobotTruthPlot, 'Matrix', makehgtform('translate', [rx_t, ry_t, 0], 'zrotate', rth_t));
                addpoints(hTrail0, rx, ry);
                addpoints(hTrailTruth, rx_t, ry_t);
                
                % Gráficos de Erro
                addpoints(hLineInstErr, t_atual, inst_err);
                addpoints(hLineRMSE, t_atual, rmse);
                
                % Limite dinâmico do eixo X para o gráfico correr com o tempo (Janela de 10s)
                if t_atual > 10
                    xlim(hAxError, [t_atual - 10, t_atual + 1]);
                else
                    xlim(hAxError, [0, 10]);
                end
                
                % Textos
                set(hTxt_PosX, 'String', sprintf('%.0f', rx));
                set(hTxt_PosY, 'String', sprintf('%.0f', ry));
                set(hTxt_ErrInst, 'String', sprintf('%.1f', inst_err));
                set(hTxt_MSE, 'String', sprintf('%.1f', mse));
                set(hTxt_RMSE, 'String', sprintf('%.1f', rmse));
            end
            
            % Bola
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
        stop(hTimer); delete(hTimer); delete(hFig);
    end
end

%% FUNÇÃO AUXILIAR DE DESENHO
function drawSoccerField(ax, xmin, xmax, ymin, ymax, goalW, goalD)
    lineColor = 'w'; lineWidth = 2;
    rectangle(ax, 'Position', [xmin, ymin, xmax-xmin, ymax-ymin], 'EdgeColor', lineColor, 'LineWidth', lineWidth);
    line(ax, [0, 0], [ymin, ymax], 'Color', lineColor, 'LineWidth', lineWidth);
    centerRadius = 500; 
    rectangle(ax, 'Position', [-centerRadius, -centerRadius, 2*centerRadius, 2*centerRadius], 'Curvature', [1,1], 'EdgeColor', lineColor, 'LineWidth', lineWidth);
    rectangle(ax, 'Position', [xmin - goalD, -goalW/2, goalD, goalW], 'EdgeColor', lineColor, 'LineWidth', lineWidth);
    rectangle(ax, 'Position', [xmax, -goalW/2, goalD, goalW], 'EdgeColor', lineColor, 'LineWidth', lineWidth);
end