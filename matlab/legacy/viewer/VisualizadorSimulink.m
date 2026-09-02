function VisualizadorSimulink(out)
% VisualizadorSimulink - Reproduz a simulação do robot0 e robot0_truth 
% Requer: GUI Layout Toolbox

    %% 1. Extração de Dados da Simulação (Objeto 'out')
    % O squeeze garante que matrizes 3D (ex: 1x1xN) virem vetores 1D
    try
        pos_x = squeeze(out.pos_x_out.Data);
        pos_y = squeeze(out.pos_y_out.Data);
        theta = squeeze(out.theta_out.Data);
        
        pos_x_truth = squeeze(out.pos_x_truth_out.Data);
        pos_y_truth = squeeze(out.pos_y_truth_out.Data);
        theta_truth = squeeze(out.theta_truth_out.Data);
    catch ME
        error('Erro ao ler os dados do Simulink. Verifique se o formato de exportação (Data Import/Export) está como "Dataset" ou "Structure with Time". Detalhes: %s', ME.message);
    end

    total_pontos = length(pos_x);
    current_idx = 1; % Índice de reprodução

    %% 2. Configurações do Campo
    FIELD_X_MIN = -6000; FIELD_X_MAX = 6000;
    FIELD_Y_MIN = -4500; FIELD_Y_MAX = 4500;
    FIELD_LENGTH = FIELD_X_MAX - FIELD_X_MIN;
    GOAL_WIDTH = 1800;
    GOAL_DEPTH = 180;
    
    % Fator de Conversão: Isaac/Simulink (Metros) -> Visualizador (Milímetros)
    SCALE_FACTOR = 1000; 
    
    %% 3. Interface Gráfica (GUI Layout)
    hFig = figure('Name', 'Visualizador Simulink - Playback', ...
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
    % hBallPlot = plot(hAx, 0, 0, 'o', 'MarkerSize', 8, 'MarkerFaceColor', 'r', 'MarkerEdgeColor', 'w');
    
    % Linhas de Rastro (Trails)
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
    
    % Barra de Progresso
    hProgressoText = uicontrol('Parent', controlsPanel, 'Style', 'text', 'String', 'PLAYBACK DA SIMULAÇÃO: 0%', ...
              'FontSize', 12, 'FontWeight', 'bold', 'ForegroundColor', 'w', 'BackgroundColor', [0.2 0.2 0.2]);
    
    % --- PAINEL DE FEATURES ---
    statsPanel = uipanel('Parent', rootLayout, 'Title', 'Telemetria do Playback (Robot0)', ...
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
    
    %% 4. Loop de Atualização (Timer para Animação)
    % Reproduz a 60 FPS (Avança o array de dados)
    hTimer = timer('ExecutionMode', 'fixedRate', 'Period', 1/60, 'TimerFcn', @updateLoop);
    start(hTimer);
    
    %% Callback Principal
    function updateLoop(~, ~)
        try
            if current_idx > total_pontos
                stop(hTimer);
                set(hProgressoText, 'String', 'PLAYBACK CONCLUÍDO', 'ForegroundColor', 'g');
                return; % Simulação chegou ao fim
            end

            targetGoalX = FIELD_LENGTH/2; % Referência para a telemetria do gol
            
            % --- 1. Atualizar Robô 0 (Azul) usando dados Simulink ---
            rx = pos_x(current_idx) * SCALE_FACTOR;
            ry = pos_y(current_idx) * SCALE_FACTOR;
            rth = theta(current_idx); % Assume-se que theta já esteja em radianos do Simulink
            
            % Atualiza Transformada do Robô 0
            M = makehgtform('translate', [rx, ry, 0], 'zrotate', rth);
            set(hRobotPlot, 'Matrix', M);
            
            % Adiciona ponto ao rastro azul
            addpoints(hTrail0, rx, ry);
            
            % Atualizar Textos de Telemetria
            set(hTxt_PosX, 'String', sprintf('%.0f', rx));
            set(hTxt_PosY, 'String', sprintf('%.0f', ry));
            set(hTxt_Theta, 'String', sprintf('%.1f', rad2deg(rth)));
            
            distGoal = sqrt((rx - targetGoalX)^2 + (ry - 0)^2);
            angleGoal = atan2(0 - ry, targetGoalX - rx);
            
            set(hTxt_DistGoal, 'String', sprintf('%.0f', distGoal));
            set(hTxt_AngGoal, 'String', sprintf('%.1f', rad2deg(angleGoal)));

            % --- 2. Atualizar Robô Truth (Amarelo) usando dados Simulink ---
            rx_t = pos_x_truth(current_idx) * SCALE_FACTOR;
            ry_t = pos_y_truth(current_idx) * SCALE_FACTOR;
            rth_t = theta_truth(current_idx); 
            
            % Atualiza Transformada do Robô Truth
            M_t = makehgtform('translate', [rx_t, ry_t, 0], 'zrotate', rth_t);
            set(hRobotTruthPlot, 'Matrix', M_t);
            
            % Adiciona ponto ao rastro amarelo
            addpoints(hTrailTruth, rx_t, ry_t);
            
            % --- 3. Bola ---
            % Se houver dados da bola no 'out', descomente e ajuste:
            % bx = out.ball_x.Data(current_idx) * SCALE_FACTOR;
            % by = out.ball_y.Data(current_idx) * SCALE_FACTOR;
            % set(hBallPlot, 'XData', bx, 'YData', by);
            
            % Atualiza porcentagem
            pct_completo = (current_idx / total_pontos) * 100;
            set(hProgressoText, 'String', sprintf('PLAYBACK: %.1f%%', pct_completo));
            
            drawnow limitrate;
            
            % Avança para o próximo frame
            % Se o playback estiver muito lento, você pode mudar para current_idx = current_idx + 5, por exemplo.
            current_idx = current_idx + 1; 
            
        catch ME
            fprintf('Erro no loop de animação: %s\n', ME.message);
            stop(hTimer);
        end
    end

    function closeApp(~, ~)
        if isvalid(hTimer)
            stop(hTimer); 
            delete(hTimer);
        end
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