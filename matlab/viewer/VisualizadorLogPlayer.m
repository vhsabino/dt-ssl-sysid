function VisualizadorLogPlayer(logDir, out)
% VisualizadorLogPlayer - Player de logs SSL (truth) com overlay opcional do Simulink.
%
% Uso:
%   VisualizadorLogPlayer('extracted/2025-04-01_16-38-42')        % só log (truth)
%   VisualizadorLogPlayer('extracted/2025-04-01_16-38-42', out)   % log + comparação Simulink
%
% Requer:
%   - ball.csv  e  processed_robots.csv  na pasta logDir
%     (gerados pelo notebook logExtractor.ipynb)
%   - GUI Layout Toolbox (uix.*)
%
% Atalhos de teclado:
%   Espaço .... Play/Pause
%   ←  /  →  .. Passo a passo (1 frame)
%   Home ..... Volta ao início
%   End ...... Vai pro fim

    if nargin < 2, out = []; end

    %% 1. Carregar logs (truth)
    ballPath   = fullfile(logDir, 'ball.csv');
    robotsPath = fullfile(logDir, 'processed_robots.csv');
    assert(isfile(ballPath),   'Não encontrei %s', ballPath);
    assert(isfile(robotsPath), 'Não encontrei %s', robotsPath);

    ballTbl   = readtable(ballPath);
    robotsTbl = readtable(robotsPath);

    % Garantir ordenação por tempo
    ballTbl   = sortrows(ballTbl,   'timestamp');
    robotsTbl = sortrows(robotsTbl, 'timestamp');

    %% 2. Timeline mestre = timestamps da bola
    master_t   = ballTbl.timestamp;          % [Nx1] em segundos a partir de t=0
    total_pts  = numel(master_t);
    if total_pts < 2
        error('Log com %d amostras de bola — insuficiente para playback.', total_pts);
    end

    % Período médio entre frames (pra controle de velocidade do timer)
    dt_log = median(diff(master_t));
    fprintf('Log: %d frames | t=[%.3f, %.3f]s | dt~%.4fs (~%.1f Hz)\n', ...
            total_pts, master_t(1), master_t(end), dt_log, 1/dt_log);

    %% 3. Pré-interpolar trajetórias dos robôs na timeline mestre
    robot_keys = unique(robotsTbl(:, {'team', 'robot_id'}));
    nRobots = height(robot_keys);
    robots = repmat(struct('team','','id',-1,'x',[],'y',[],'w',[]), nRobots, 1);

    for i = 1:nRobots
        team_i = robot_keys.team{i};
        id_i   = robot_keys.robot_id(i);
        mask   = strcmp(robotsTbl.team, team_i) & (robotsTbl.robot_id == id_i);
        sub    = robotsTbl(mask, :);
        % interp linear; fora do intervalo vira NaN -> robô "some"
        robots(i).team = team_i;
        robots(i).id   = id_i;
        robots(i).x    = interp1(sub.timestamp, sub.position_x, master_t, 'linear', NaN);
        robots(i).y    = interp1(sub.timestamp, sub.position_y, master_t, 'linear', NaN);
        robots(i).w    = interp1(sub.timestamp, sub.position_w, master_t, 'linear', NaN);
    end
    fprintf('Robôs detectados: %d (aliados+adversários)\n', nRobots);

    % Bola
    ball.x = ballTbl.position_x;
    ball.y = ballTbl.position_y;

    %% 4. Dados do Simulink (overlay opcional, comparado ao robot_id=0 aliado)
    SCALE_SIM = 1000;          % out em metros -> mm
    hasSim = ~isempty(out);
    sim = struct('x',[],'y',[],'w',[]);
    if hasSim
        try
            t_sim   = squeeze(out.pos_x_out.Time);
            sx_raw  = squeeze(out.pos_x_out.Data) * SCALE_SIM;
            sy_raw  = squeeze(out.pos_y_out.Data) * SCALE_SIM;
            sw_raw  = squeeze(out.theta_out.Data);
            % alinhar simulink ao tempo do log (assume ambos começam em ~0)
            sim.x = interp1(t_sim, sx_raw, master_t, 'linear', NaN);
            sim.y = interp1(t_sim, sy_raw, master_t, 'linear', NaN);
            sim.w = interp1(t_sim, sw_raw, master_t, 'linear', NaN);
            fprintf('Simulink overlay: %d amostras em [%.3f, %.3f]s\n', ...
                    numel(t_sim), t_sim(1), t_sim(end));
        catch ME
            warning('Falha ao ler "out": %s. Continuando só com truth.', ME.message);
            hasSim = false;
        end
    end

    %% 5. Estado do player
    state.idx       = 1;
    state.playing   = false;
    state.speed     = 1.0;      % 1x = velocidade real do log
    state.speeds    = [0.25 0.5 1 2 4];

    %% 6. GUI
    FIELD_X_MIN = -4500; FIELD_X_MAX = 4500;
    FIELD_Y_MIN = -3000; FIELD_Y_MAX = 3000;
    GOAL_WIDTH = 1000; GOAL_DEPTH = 180;

    hFig = figure('Name','Visualizador de Log + Simulink', 'NumberTitle','off', ...
                  'Units','pixels','Position',[50 50 1300 800], ...
                  'CloseRequestFcn',@closeApp, ...
                  'KeyPressFcn',@onKey);

    root = uix.VBox('Parent',hFig,'Padding',8,'Spacing',6);

    % --- topo: campo + painel de stats ---
    topRow = uix.HBox('Parent',root,'Spacing',8);

    fieldPanel = uipanel('Parent',topRow,'BorderType','none','BackgroundColor',[0 0.5 0]);
    hAx = axes('Parent',fieldPanel,'Units','normalized','Position',[0.04 0.04 0.92 0.92], ...
               'Color',[0 0.6 0],'XColor','w','YColor','w','DataAspectRatio',[1 1 1]);
    hold(hAx,'on'); grid(hAx,'on');
    set(hAx,'GridColor','w','GridAlpha',0.3);
    xlim(hAx,[FIELD_X_MIN-500 FIELD_X_MAX+500]);
    ylim(hAx,[FIELD_Y_MIN-500 FIELD_Y_MAX+500]);
    drawSoccerField(hAx, FIELD_X_MIN, FIELD_X_MAX, FIELD_Y_MIN, FIELD_Y_MAX, GOAL_WIDTH, GOAL_DEPTH);

    % painel de telemetria
    statsPanel = uipanel('Parent',topRow,'Title','Telemetria', ...
        'FontSize',11,'BackgroundColor','k','ForegroundColor','w');
    statsBox = uix.VBox('Parent',statsPanel,'Padding',8,'Spacing',4);
    hTxt.t       = addStat(statsBox,'Tempo (s):');
    hTxt.frame   = addStat(statsBox,'Frame:');
    hTxt.nRobots = addStat(statsBox,'Robôs visíveis:');
    addSep(statsBox);
    hTxt.r0x     = addStat(statsBox,'Truth robô 0 — X (mm):');
    hTxt.r0y     = addStat(statsBox,'Truth robô 0 — Y (mm):');
    hTxt.r0w     = addStat(statsBox,'Truth robô 0 — θ (°):');
    if hasSim
        addSep(statsBox);
        hTxt.simx = addStat(statsBox,'Sim robô 0 — X (mm):');
        hTxt.simy = addStat(statsBox,'Sim robô 0 — Y (mm):');
        hTxt.simw = addStat(statsBox,'Sim robô 0 — θ (°):');
        addSep(statsBox);
        hTxt.err  = addStat(statsBox,'Erro pos (mm):');
    end

    topRow.Widths = [-0.75 -0.25];

    % --- slider ---
    sliderRow = uix.HBox('Parent',root,'Spacing',6);
    hSlider = uicontrol('Parent',sliderRow,'Style','slider', ...
        'Min',1,'Max',total_pts,'Value',1, ...
        'SliderStep',[1/(total_pts-1) max(10/(total_pts-1),0.01)], ...
        'Callback',@onSlider);
    % listener pra arrasto contínuo (não só ao soltar)
    try
        addlistener(hSlider,'ContinuousValueChange',@onSlider);
    catch
        % alguma versão antiga sem o listener — sem problema
    end

    % --- controles ---
    ctrlRow = uix.HBox('Parent',root,'Spacing',6,'Padding',2);
    uicontrol('Parent',ctrlRow,'Style','pushbutton','String','⏮', ...
              'FontSize',12,'Callback',@(~,~)gotoIdx(1));
    uicontrol('Parent',ctrlRow,'Style','pushbutton','String','◀','FontSize',12, ...
              'Callback',@(~,~)stepBy(-1));
    hBtnPlay = uicontrol('Parent',ctrlRow,'Style','pushbutton','String','▶ Play', ...
              'FontSize',12,'FontWeight','bold','Callback',@(~,~)togglePlay());
    uicontrol('Parent',ctrlRow,'Style','pushbutton','String','▶','FontSize',12, ...
              'Callback',@(~,~)stepBy(+1));
    uicontrol('Parent',ctrlRow,'Style','pushbutton','String','⏭', ...
              'FontSize',12,'Callback',@(~,~)gotoIdx(total_pts));
    uix.Empty('Parent',ctrlRow);
    uicontrol('Parent',ctrlRow,'Style','text','String','Velocidade:', ...
              'FontSize',11,'HorizontalAlignment','right');
    hSpeed = uicontrol('Parent',ctrlRow,'Style','popupmenu', ...
              'String',{'0.25x','0.5x','1x','2x','4x'},'Value',3, ...
              'FontSize',11,'Callback',@onSpeed);

    root.Heights    = [-1 30 32];
    ctrlRow.Widths  = [40 40 90 40 40 -1 80 80];

    %% 7. Handles gráficos dos robôs
    % Cores: allies = azul claro; enemies = amarelo
    allyColor  = [0.2 0.6 1];
    enemyColor = [1 1 0];
    robotRadius = 180;

    hRobotG = gobjects(nRobots,1);
    hRobotLbl = gobjects(nRobots,1);
    for i = 1:nRobots
        c = ternary(strcmp(robots(i).team,'allies'), allyColor, enemyColor);
        hRobotG(i) = hgtransform('Parent',hAx);
        rectangle('Parent',hRobotG(i), ...
                  'Position',[-robotRadius -robotRadius 2*robotRadius 2*robotRadius], ...
                  'Curvature',[1 1],'FaceColor',c,'EdgeColor','k');
        line('Parent',hRobotG(i),'XData',[0 robotRadius],'YData',[0 0], ...
             'Color','k','LineWidth',2);
        hRobotLbl(i) = text('Parent',hAx,'String',sprintf('%d',robots(i).id), ...
            'Color','k','FontWeight','bold','FontSize',9, ...
            'HorizontalAlignment','center','VerticalAlignment','middle');
    end

    % bola
    hBall = plot(hAx, NaN, NaN, 'o', 'MarkerSize',8, ...
                 'MarkerFaceColor',[1 0.5 0],'MarkerEdgeColor','k');

    % overlay Simulink (sobreposto ao robô 0 aliado)
    hSimG = []; hSimTrail = [];
    if hasSim
        hSimG = hgtransform('Parent',hAx);
        rectangle('Parent',hSimG, ...
                  'Position',[-robotRadius -robotRadius 2*robotRadius 2*robotRadius], ...
                  'Curvature',[1 1],'FaceColor','none', ...
                  'EdgeColor','m','LineWidth',2.5,'LineStyle','--');
        line('Parent',hSimG,'XData',[0 robotRadius],'YData',[0 0], ...
             'Color','m','LineWidth',2,'LineStyle','--');
        hSimTrail = animatedline(hAx,'Color','m','LineWidth',1.2, ...
                                 'LineStyle','--','MaximumNumPoints',5000);
    end

    % rastro do robô 0 truth
    hTruthTrail = animatedline(hAx,'Color',allyColor,'LineWidth',1.2, ...
                               'MaximumNumPoints',5000);

    %% 8. Timer
    hTimer = timer('ExecutionMode','fixedRate','BusyMode','drop', ...
                   'Period',max(dt_log,0.01),'TimerFcn',@onTick);

    % desenha o primeiro frame
    redraw();

    %% ============== NESTED FUNCTIONS ==============
    function onTick(~,~)
        next = state.idx + max(1, round(state.speed));
        % obs: pra 0.25x e 0.5x, o "abaixar a velocidade" não é via passo,
        % é via Period do timer (ajustado em onSpeed)
        if next > total_pts
            gotoIdx(total_pts);
            setPlay(false);
        else
            gotoIdx(next);
        end
    end

    function redraw()
        k = state.idx;
        t = master_t(k);

        % robôs
        nVis = 0;
        for ii = 1:nRobots
            x = robots(ii).x(k); y = robots(ii).y(k); w = robots(ii).w(k);
            if isnan(x) || isnan(y)
                set(hRobotG(ii),'Visible','off');
                set(hRobotLbl(ii),'Visible','off');
                continue;
            end
            nVis = nVis + 1;
            if isnan(w), w = 0; end
            M = makehgtform('translate',[x y 0],'zrotate',w);
            set(hRobotG(ii),'Matrix',M,'Visible','on');
            set(hRobotLbl(ii),'Position',[x y 0],'Visible','on');
        end

        % bola
        set(hBall,'XData',ball.x(k),'YData',ball.y(k));

        % stats robô 0 aliado (se existir)
        r0 = findAlly0();
        if ~isempty(r0)
            rx = robots(r0).x(k); ry = robots(r0).y(k); rw = robots(r0).w(k);
            set(hTxt.r0x,'String',fmt(rx));
            set(hTxt.r0y,'String',fmt(ry));
            set(hTxt.r0w,'String',fmt(rad2deg(rw),'%.1f'));
            if ~isnan(rx)
                addpoints(hTruthTrail,rx,ry);
            end
        end

        % overlay Simulink
        if hasSim
            sx = sim.x(k); sy = sim.y(k); sw = sim.w(k);
            if isnan(sx) || isnan(sy)
                set(hSimG,'Visible','off');
            else
                if isnan(sw), sw = 0; end
                Ms = makehgtform('translate',[sx sy 0],'zrotate',sw);
                set(hSimG,'Matrix',Ms,'Visible','on');
                addpoints(hSimTrail,sx,sy);
            end
            set(hTxt.simx,'String',fmt(sx));
            set(hTxt.simy,'String',fmt(sy));
            set(hTxt.simw,'String',fmt(rad2deg(sw),'%.1f'));
            if ~isempty(r0) && ~isnan(sx) && ~isnan(robots(r0).x(k))
                e = hypot(sx-robots(r0).x(k), sy-robots(r0).y(k));
                set(hTxt.err,'String',fmt(e));
            else
                set(hTxt.err,'String','-');
            end
        end

        set(hTxt.t,      'String',sprintf('%.3f / %.3f', t, master_t(end)));
        set(hTxt.frame,  'String',sprintf('%d / %d', k, total_pts));
        set(hTxt.nRobots,'String',sprintf('%d', nVis));

        % slider sem disparar callback recursivo
        set(hSlider,'Value',k);

        drawnow limitrate;
    end

    function r0 = findAlly0()
        r0 = [];
        for ii = 1:nRobots
            if strcmp(robots(ii).team,'allies') && robots(ii).id == 0
                r0 = ii; return;
            end
        end
    end

    function gotoIdx(k)
        state.idx = max(1, min(total_pts, round(k)));
        redraw();
    end

    function stepBy(n)
        setPlay(false);
        gotoIdx(state.idx + n);
    end

    function togglePlay()
        setPlay(~state.playing);
    end

    function setPlay(on)
        state.playing = logical(on);
        if state.playing
            if state.idx >= total_pts
                gotoIdx(1);
                clearpoints(hTruthTrail);
                if hasSim, clearpoints(hSimTrail); end
            end
            set(hBtnPlay,'String','⏸ Pause');
            if strcmp(hTimer.Running,'off'), start(hTimer); end
        else
            set(hBtnPlay,'String','▶ Play');
            if strcmp(hTimer.Running,'on'), stop(hTimer); end
        end
    end

    function onSlider(~,~)
        setPlay(false);
        gotoIdx(get(hSlider,'Value'));
    end

    function onSpeed(~,~)
        state.speed = state.speeds(get(hSpeed,'Value'));
        % timer roda no período real do log; "speed" multiplica os passos
        % para 0.25x / 0.5x, prefiro reduzir o Period (mantendo step=1)
        wasOn = strcmp(hTimer.Running,'on');
        if wasOn, stop(hTimer); end
        if state.speed < 1
            hTimer.Period = max(dt_log / state.speed, 0.01);
        else
            hTimer.Period = max(dt_log, 0.01);
        end
        if wasOn, start(hTimer); end
    end

    function onKey(~,evt)
        switch evt.Key
            case 'space',     togglePlay();
            case 'rightarrow',stepBy(+1);
            case 'leftarrow', stepBy(-1);
            case 'home',      gotoIdx(1);
            case 'end',       gotoIdx(total_pts);
        end
    end

    function closeApp(~,~)
        try
            if isvalid(hTimer)
                stop(hTimer); delete(hTimer);
            end
        catch, end
        delete(hFig);
    end
end

%% ============ FUNÇÕES AUXILIARES ============
function h = addStat(parent, label)
    uicontrol('Parent',parent,'Style','text','String',label,'FontWeight','bold', ...
        'FontSize',10,'HorizontalAlignment','left', ...
        'BackgroundColor','k','ForegroundColor','w');
    h = uicontrol('Parent',parent,'Style','text','String','-','FontSize',10, ...
        'BackgroundColor',[1 1 1],'ForegroundColor',[0 0 0],'HorizontalAlignment','center');
end

function addSep(parent)
    uicontrol('Parent',parent,'Style','text','String','','BackgroundColor','k');
end

function s = fmt(v, f)
    if nargin < 2, f = '%.0f'; end
    if isnan(v), s = '-'; else, s = sprintf(f, v); end
end

function y = ternary(cond, a, b)
    if cond, y = a; else, y = b; end
end

function drawSoccerField(ax, xmin, xmax, ymin, ymax, goalW, goalD)
    lc = 'w'; lw = 2;
    rectangle(ax,'Position',[xmin ymin xmax-xmin ymax-ymin], ...
              'EdgeColor',lc,'LineWidth',lw,'FaceColor','none');
    line(ax,[0 0],[ymin ymax],'Color',lc,'LineWidth',lw);
    cr = 500;
    rectangle(ax,'Position',[-cr -cr 2*cr 2*cr], ...
              'Curvature',[1 1],'EdgeColor',lc,'LineWidth',lw);
    rectangle(ax,'Position',[xmin-goalD -goalW/2 goalD goalW], ...
              'EdgeColor',lc,'LineWidth',lw);
    rectangle(ax,'Position',[xmax -goalW/2 goalD goalW], ...
              'EdgeColor',lc,'LineWidth',lw);
    dD = 1000; dW = 2000;
    rectangle(ax,'Position',[xmin -dW/2 dD dW], ...
              'EdgeColor',lc,'LineWidth',lw);
    rectangle(ax,'Position',[xmax-dD -dW/2 dD dW], ...
              'EdgeColor',lc,'LineWidth',lw);
end
