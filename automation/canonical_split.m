function [canon_path, map_applied] = canonical_split(commands_path, opts)
%CANONICAL_SPLIT Constroi o parquet canonico exigido por run_one/load_split
% a partir dos streams REAIS de um evento, sem tocar em data/ (o derivado
% e um cache reconstruivel em build/canonical_splits/).
%
% Contrato de run_one -> load_split (matlab/simulink_io/load_split.m):
%   colunas {timestamp_event, move_vx, move_vy, move_w, pos_x, pos_y, theta}
%   com pos_x/pos_y em mm (load_split divide por 1000) e theta em rad.
%
% Mapa explicito real -> contrato, derivado de parquetinfo nos dados reais
% (inspecao 2026-06-10, log 2026-05-18_19-2-15):
%   commands.parquet:         timestamp_event -> timestamp_event  [s]
%                             move_x          -> move_vx          [m/s]
%                             move_y          -> move_vy          [m/s]
%                             move_w          -> move_w           [rad/s]
%   processed_robots.parquet: position_x      -> pos_x            [mm]
%                             position_y      -> pos_y            [mm]
%                             position_w      -> theta            [rad, unwrap]
%
% A pose e interpolada linearmente no grid de tempo dos comandos (a entrada
% dirige a simulacao); amostras fora da sobreposicao temporal sao descartadas.
%
% USO:
%   [p, m] = canonical_split('...\<evento>\commands.parquet');
%   out = run_one(model, p, 'ideal');

arguments
    commands_path (1,:) char
    opts.Team    (1,:) char   = 'allies'
    opts.RobotId (1,1) double = NaN   % NaN = unico robot_id presente em commands
    opts.OutRoot (1,:) char   = fullfile('build','canonical_splits')
end

event_dir   = fileparts(commands_path);
robots_path = fullfile(event_dir, 'processed_robots.parquet');

% --- mapa explicito (origem real -> contrato do load_split) ---
CMD_MAP = ["timestamp_event" "timestamp_event"
           "move_x"          "move_vx"
           "move_y"          "move_vy"
           "move_w"          "move_w"];
ROB_MAP = ["position_x"      "pos_x"
           "position_y"      "pos_y"
           "position_w"      "theta"];

check_columns(commands_path, [CMD_MAP(:,1); "robot_id"]);
check_columns(robots_path,   [ROB_MAP(:,1); "robot_id"; "team"]);

C = parquetread(commands_path);
R = parquetread(robots_path);

% --- seleciona o robo ---
ids = unique(C.robot_id);
rid = opts.RobotId;
if isnan(rid)
    if numel(ids) ~= 1
        error(['canonical_split: commands tem varios robot_id {%s}; ' ...
            'desambigue com ''RobotId''.'], num2str(double(ids(:)).'));
    end
    rid = double(ids(1));
end
C = C(double(C.robot_id) == rid, :);
R = R(strcmp(R.team, opts.Team) & double(R.robot_id) == rid, :);
if height(C) < 2 || height(R) < 2
    error('canonical_split: sem amostras para robot_id=%g/team=%s em %s', ...
        rid, opts.Team, event_dir);
end

% --- alinha pose no grid dos comandos ---
tc = C.timestamp_event;
tr = R.timestamp_event;
px = interp1(tr, R.position_x,         tc, 'linear');
py = interp1(tr, R.position_y,         tc, 'linear');
th = interp1(tr, unwrap(R.position_w), tc, 'linear');
keep = ~isnan(px) & ~isnan(py) & ~isnan(th);
if nnz(keep) < 2
    error(['canonical_split: sem sobreposicao temporal entre commands ' ...
        '[%.3f,%.3f]s e processed_robots [%.3f,%.3f]s em %s'], ...
        tc(1), tc(end), tr(1), tr(end), event_dir);
end

T = table(tc(keep), C.move_x(keep), C.move_y(keep), C.move_w(keep), ...
          px(keep), py(keep), th(keep), 'VariableNames', ...
          {'timestamp_event','move_vx','move_vy','move_w','pos_x','pos_y','theta'});

% --- grava o derivado em build/ espelhando <log>/<label>/<evento> ---
parts = split(string(event_dir), filesep);
isp = find(parts == "splits", 1, 'last');
if ~isempty(isp) && isp >= 2 && isp + 2 <= numel(parts)
    sub = fullfile(parts(isp-1), parts(isp+1), parts(isp+2));
else
    sub = parts(end);   % fallback: so o nome do evento
end
out_dir = fullfile(opts.OutRoot, char(sub));
if ~isfolder(out_dir), mkdir(out_dir); end
canon_path = fullfile(out_dir, 'canonical.parquet');
parquetwrite(canon_path, T);

map_applied = table( ...
    ["commands";"commands";"commands";"commands";"processed_robots";"processed_robots";"processed_robots"], ...
    [CMD_MAP(:,1); ROB_MAP(:,1)], [CMD_MAP(:,2); ROB_MAP(:,2)], ...
    'VariableNames', {'stream_real','coluna_real','coluna_contrato'});
end

% =========================================================================
function check_columns(p, req)
%CHECK_COLUMNS Erro com faltantes vs. disponiveis (nao inventa nomes).
if ~isfile(p)
    error('canonical_split: stream ausente: %s', p);
end
avail = string(parquetinfo(p).VariableNames);
missing = setdiff(req(:), avail(:));
if ~isempty(missing)
    error('canonical_split: %s — faltam {%s}; disponiveis: {%s}', ...
        p, strjoin(missing, ','), strjoin(avail, ','));
end
end
