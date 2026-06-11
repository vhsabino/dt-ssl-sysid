function dataByDOF = build_idData_per_dof(splitsRoots, opts)
% build_idData_per_dof - Monta iddata (u,y) por DOF a partir dos splits rotulados.
%
% USO:
%   d = build_idData_per_dof('extracted/logA/splits')                            % um log
%   d = build_idData_per_dof({'extracted/logA/splits','extracted/logB/splits'})  % vários
%   d = build_idData_per_dof(struct('train',{{'logA/splits','logB/splits'}}, ...
%                                   'val_out','logC/splits'))                   % com val out

    arguments
        splitsRoots
        opts.Ts            (1,1) double  = 1/60
        opts.robot_id      (1,1) double  = 0
        opts.team          (1,:) char    = 'allies'
        opts.detrend       (1,1) logical = true
        opts.omega_thresh  (1,1) double  = 0.5    % rad/s (relaxado: rotação dominante)
        opts.vxy_thresh_ms (1,1) double  = 0.3    % m/s
        opts.minSegSec     (1,1) double  = 0.5
        opts.theta_min_total_sec (1,1) double = 5.0
    end

    [trainRoots, valRoots] = parseRoots(splitsRoots);
    [bigCmd, bigRob] = loadAndConcat(trainRoots, opts.robot_id, opts.team);

    dataByDOF = struct();
    dataByDOF.x      = buildFromLabel(bigCmd, bigRob, 'front_to_back', 'x',  opts);
    dataByDOF.y      = buildFromLabel(bigCmd, bigRob, 'side_to_side',  'y',  opts);
    dataByDOF.square = buildFromLabel(bigCmd, bigRob, 'square',        'xy', opts);
    [dataByDOF.theta, dataByDOF.diag.theta] = buildTheta(bigCmd, bigRob, opts);

    if ~isempty(valRoots)
        [valCmd, valRob] = loadAndConcat(valRoots, opts.robot_id, opts.team);
        dataByDOF.val_out.x      = buildFromLabel(valCmd, valRob, 'front_to_back', 'x',  opts);
        dataByDOF.val_out.y      = buildFromLabel(valCmd, valRob, 'side_to_side',  'y',  opts);
        dataByDOF.val_out.square = buildFromLabel(valCmd, valRob, 'square',        'xy', opts);
        fprintf('\n--- val_out (logs out-of-distribution) carregados ---\n');
    end
end

function [train, val] = parseRoots(input)
    val = {};
    if ischar(input) || isstring(input)
        train = {char(input)};
    elseif iscell(input)
        train = cellfun(@char, input, 'UniformOutput', false);
    elseif isstruct(input)
        train = input.train;
        if ischar(train) || isstring(train), train = {char(train)}; end
        if isfield(input,'val_out'), val = input.val_out;
            if ischar(val) || isstring(val), val = {char(val)}; end
        end
    else
        error('splitsRoots deve ser char, cell ou struct');
    end
end

function [bigCmd, bigRob] = loadAndConcat(roots, rid, team)
    cmds = {}; robs = {};
    for r = 1:numel(roots)
        rt = roots{r};
        cf = fullfile(rt,'all_commands_labeled.parquet');
        rf = fullfile(rt,'all_processed_robots_labeled.parquet');
        if ~isfile(cf) || ~isfile(rf)
            warning('Pulando %s (parquets faltando)', rt); continue;
        end
        c = parquetread(cf); rr = parquetread(rf);
        c  = c(c.robot_id == rid, :);
        rr = rr(strcmp(rr.team,team) & rr.robot_id == rid, :);
        c.source_log  = repmat({rt}, height(c), 1);
        rr.source_log = repmat({rt}, height(rr), 1);
        cmds{end+1} = c; robs{end+1} = rr; %#ok<AGROW>
        fprintf('  %s: cmd=%d, rob=%d\n', rt, height(c), height(rr));
    end
    if isempty(cmds), error('Nenhum log carregado.'); end
    bigCmd = vertcat(cmds{:}); bigRob = vertcat(robs{:});
end

function data = buildFromLabel(cmdAll, robAll, label, axis, opts)
    S = 1/1000;  % mm -> m
    cmdL = cmdAll(strcmp(cmdAll.label, label), :);
    robL = robAll(strcmp(robAll.label, label), :);
    events = unique(cmdL.event_id);
    segs = {};
    for k = 1:numel(events)
        ev = events{k};
        c = cmdL(strcmp(cmdL.event_id, ev), :);
        r = robL(strcmp(robL.event_id, ev), :);
        if height(c) < 30 || height(r) < 30, continue; end
        tgrid = (c.timestamp_event(1):opts.Ts:c.timestamp_event(end))';
        % Interpola tudo no grid uniforme
        ux_cmd = interp1(c.timestamp_event, c.move_x, tgrid, 'previous', 0);
        uy_cmd = interp1(c.timestamp_event, c.move_y, tgrid, 'previous', 0);
        vx_w   = interp1(r.timestamp_event, r.velocity_x, tgrid, 'linear', NaN) * S;  % mundo
        vy_w   = interp1(r.timestamp_event, r.velocity_y, tgrid, 'linear', NaN) * S;
        th     = interp1(r.timestamp_event, unwrap(r.position_w), tgrid, 'linear', NaN);

        % Rotaciona velocidade do mundo -> referencial do robô
        ct = cos(th); st = sin(th);
        vx_r =  ct.*vx_w + st.*vy_w;
        vy_r = -st.*vx_w + ct.*vy_w;

        switch axis
            case 'x',  u = ux_cmd;        y = vx_r;
            case 'y',  u = uy_cmd;        y = vy_r;
            case 'xy', u = [ux_cmd uy_cmd]; y = [vx_r vy_r];
        end
        mask = all(~isnan([u y]), 2);
        u = u(mask,:); y = y(mask,:);
        if size(u,1) < round(opts.minSegSec/opts.Ts), continue; end
        if opts.detrend, u = u - mean(u,1); y = y - mean(y,1); end
        d = iddata(y, u, opts.Ts); d.ExperimentName = ev;
        segs{end+1} = d; %#ok<AGROW>
    end
    if isempty(segs)
        warning('Nenhum segmento utilizável para "%s" (axis %s).', label, axis);
        data = []; return;
    end
    data = merge(segs{:});
    fprintf('%s (axis=%s): %d segmentos, %d amostras\n', label, axis, numel(segs), ...
            sum(cellfun(@(d)size(d.y,1), segs)));
end

function [data, diag] = buildTheta(cmdAll, robAll, opts)
    events = unique(cmdAll.event_id);
    segs = {};
    diag = struct('candidate_evs', 0, 'usable_segs', 0, 'total_sec', 0);
    for k = 1:numel(events)
        ev = events{k};
        c = cmdAll(strcmp(cmdAll.event_id, ev), :);
        r = robAll(strcmp(robAll.event_id, ev), :);
        if height(c) < 30 || height(r) < 30, continue; end
        tgrid = (c.timestamp_event(1):opts.Ts:c.timestamp_event(end))';
        uw  = interp1(c.timestamp_event, c.move_w,     tgrid, 'previous', 0);% velocity_w não está no processed_frame — derivar de position_w
        pw  = interp1(r.timestamp_event, unwrap(r.position_w), tgrid, 'linear', NaN);
        yw  = [0; diff(pw)] / opts.Ts;
        if numel(yw) > 7
            yw = smoothdata(yw, 'sgolay', 5);
        end
        vx  = interp1(r.timestamp_event, r.velocity_x, tgrid, 'linear',   NaN) / 1000;
        vy  = interp1(r.timestamp_event, r.velocity_y, tgrid, 'linear',   NaN) / 1000;
        vxy = hypot(vx, vy);
        mask = (abs(uw) > opts.omega_thresh) & (vxy < opts.vxy_thresh_ms) & ~isnan(yw);
        if any(mask), diag.candidate_evs = diag.candidate_evs + 1; end
        groups = bwlabel_runs(mask);
        for g = 1:max(groups)
            idx = find(groups == g);
            if numel(idx) < round(opts.minSegSec/opts.Ts), continue; end
            u = uw(idx); y = yw(idx);
            if opts.detrend, u = u - mean(u); y = y - mean(y); end
            d = iddata(y, u, opts.Ts);
            d.ExperimentName = sprintf('%s_w%d', ev, g);
            segs{end+1} = d; %#ok<AGROW>
            diag.usable_segs = diag.usable_segs + 1;
            diag.total_sec   = diag.total_sec + numel(idx)*opts.Ts;
        end
    end
    fprintf('\n=== θ: diagnóstico ===\n');
    fprintf('  Eventos com candidatos: %d\n', diag.candidate_evs);
    fprintf('  Segmentos utilizáveis:  %d\n', diag.usable_segs);
    fprintf('  Tempo total efetivo:    %.2f s\n', diag.total_sec);
    if isempty(segs)
        warning('Sem segmentos para θ — recomendo coleta dedicada (30s rotacionando parado).');
        data = []; return;
    end
    if diag.total_sec < opts.theta_min_total_sec
        warning('θ tem só %.1f s (< %.1f s recomendado). Variância alta esperada.', ...
                diag.total_sec, opts.theta_min_total_sec);
    end
    data = merge(segs{:});
end

function lbl = bwlabel_runs(mask)
    lbl = zeros(size(mask)); cur = 0; inrun = false;
    for i = 1:numel(mask)
        if mask(i)
            if ~inrun, cur = cur+1; inrun = true; end
            lbl(i) = cur;
        else, inrun = false; end
    end
end
