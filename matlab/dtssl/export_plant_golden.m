function [out_path, theta_json] = export_plant_golden(event_dir, opts)
%EXPORT_PLANT_GOLDEN Exporta a trajetoria de deadreckoning_p1d (a REFERENCIA
% promovida) para UM evento, avaliada na grade uniforme 1/60 — golden do
% AnalyticFOPDTPlant (dtssl.models.fopdt). A reamostragem 1/60 e identica a do
% loader / de export_resample_reference (colon 1/60, comandos ZOH, pose
% linear+unwrap), e entao deadreckoning_p1d roda sobre essa grade.
%
% USO
%   export_plant_golden(event_dir)                      % theta = models/sysid_vxvy_v2.mat
%                                                       % (omega placeholder; reproduz os
%                                                       %  goldens plant_golden_<event>.parquet de 2026-06-16)
%   export_plant_golden(event_dir, 'theta', 'promoted', 'tag', 'v2')
%       -> tests/fixtures/plant_golden_v2_<event>.parquet
%          + tests/fixtures/plant_golden_v2_theta.json  (theta usado, formato de
%            config/twin_params.json; lido por tests/test_plant_golden.py)
%
% OPCOES (name-value)
%   'theta'   : origem do theta (9 params, ordem fixa do SLDD):
%                 - caminho de .mat (theta0/theta_opt/theta, via load_theta_mat);
%                 - caminho de .json no formato de config/twin_params.json;
%                 - vetor 1x9 [K_vx tau_vx Td_vx K_vy tau_vy Td_vy K_w tau_w Td_w];
%                 - struct com os 9 campos;
%                 - 'promoted' (= 'official'): vx/vy de models/sysid_vxvy_v2.mat
%                   + omega de models/sysid_omega_rotate_v1.mat (mesma fusao
%                   de run_td_quantization_case.m, 2026-07-24), i.e. o theta
%                   oficial de config/twin_params.json.
%               Default: fullfile('models','sysid_vxvy_v2.mat') (compatibilidade).
%   'outdir'  : pasta de saida (default tests/fixtures, relativo a raiz do repo).
%   'tag'     : sufixo do nome: plant_golden_<tag>_<event>.parquet ('' = sem tag).
%   'outpath' : caminho completo do parquet (sobrepoe outdir/tag).
%   'ts'      : passo da grade (default 1/60).
%   'thetajson': gravar o sidecar plant_golden_<tag>_theta.json (default true
%               quando 'tag' nao e vazio; false caso contrario).
%
% Caminhos relativos sao resolvidos contra a raiz do repositorio (nao contra
% pwd). Saidas: out_path (parquet) e theta_json ('' se nao gravado).

arguments
    event_dir (1,:) char
    opts.theta = fullfile('models','sysid_vxvy_v2.mat')
    opts.outdir (1,:) char = fullfile('tests','fixtures')
    opts.tag (1,:) char = ''
    opts.outpath (1,:) char = ''
    opts.ts (1,1) double = 1/60
    opts.thetajson logical = logical([])
end

Ts = opts.ts;
event_dir = resolve_repo_path(event_dir);
[~, ev] = fileparts(event_dir);
if isempty(opts.tag), stem = 'plant_golden'; else, stem = ['plant_golden_' opts.tag]; end
if isempty(opts.outpath)
    out_path = fullfile(resolve_repo_path(opts.outdir), [stem '_' ev '.parquet']);
else
    out_path = resolve_repo_path(opts.outpath);
end
if isempty(opts.thetajson), write_json = ~isempty(opts.tag); else, write_json = opts.thetajson; end

% --- theta (struct com os 9 campos) + proveniencia ---
[th, source] = resolve_theta(opts.theta);

% --- reamostragem 1/60 (identica a export_resample_reference / loader) ---
C = parquetread(fullfile(event_dir,'commands.parquet'));
R = parquetread(fullfile(event_dir,'processed_robots.parquet'));
ids = unique(double(C.robot_id));
assert(isscalar(ids), 'commands tem varios robot_id {%s}', num2str(ids(:).'));
rid = ids(1);
C = sortrows(C(double(C.robot_id)==rid,:), 'timestamp_event');
R = sortrows(R(strcmp(R.team,'allies') & double(R.robot_id)==rid,:), 'timestamp_event');

tc = C.timestamp_event;  tr = R.timestamp_event;
grid = (tc(1):Ts:tc(end))';
cmd_vx = interp1(tc, C.move_x, grid, 'previous', 0);
cmd_vy = interp1(tc, C.move_y, grid, 'previous', 0);
cmd_w  = interp1(tc, C.move_w, grid, 'previous', 0);
theta_h = interp1(tr, unwrap(R.position_w), grid, 'linear', NaN);
pos_x   = interp1(tr, R.position_x/1000, grid, 'linear', NaN);
pos_y   = interp1(tr, R.position_y/1000, grid, 'linear', NaN);
valid = ~isnan(pos_x) & ~isnan(pos_y) & ~isnan(theta_h);
i0 = find(valid,1,'first'); i1 = find(valid,1,'last');
keep = false(size(valid)); keep(i0:i1) = true;
grid = grid(keep); cmd_vx = cmd_vx(keep); cmd_vy = cmd_vy(keep); cmd_w = cmd_w(keep);
pos_x = pos_x(keep); pos_y = pos_y(keep); theta_h = theta_h(keep);

% --- struct 's' no formato do load_split, JA na grade 1/60 ---
s = struct();
s.t = grid;
s.cmd_vx_ts = timeseries(cmd_vx, grid, 'Name','cmd_vx');
s.cmd_vy_ts = timeseries(cmd_vy, grid, 'Name','cmd_vy');
s.cmd_vw_ts = timeseries(cmd_w,  grid, 'Name','cmd_vw');
s.pos0 = struct('x0', pos_x(1), 'y0', pos_y(1), 'theta0', theta_h(1));

[xs, ys, ths, vbody] = deadreckoning_p1d(s, th);

T = table(grid, cmd_vx, cmd_vy, cmd_w, xs, ys, ths, vbody(:,1), vbody(:,2), vbody(:,3), ...
    'VariableNames', {'t','cmd_vx','cmd_vy','cmd_w','xs','ys','ths','vbx','vby','vbw'});
od = fileparts(out_path); if ~isempty(od) && ~isfolder(od), mkdir(od); end
parquetwrite(out_path, T);
fprintf('export_plant_golden: %s (rid=%g, N=%d, dur=%.3f s, theta=%s)\n', ...
    out_path, rid, height(T), grid(end)-grid(1), source);

% --- sidecar JSON com o theta usado (formato de config/twin_params.json) ---
theta_json = '';
if write_json
    theta_json = fullfile(fileparts(out_path), [stem '_theta.json']);
    write_theta_json(theta_json, th, source, stem);
    fprintf('export_plant_golden: theta -> %s\n', theta_json);
end
end

% =========================================================================
function [th, source] = resolve_theta(spec)
%RESOLVE_THETA Normaliza a opcao 'theta' para struct com os 9 campos.
NAMES = {'K_vx','tau_vx','Td_vx','K_vy','tau_vy','Td_vy','K_w','tau_w','Td_w'};
if isstruct(spec)
    missing = setdiff(NAMES, fieldnames(spec));
    if ~isempty(missing), error('theta struct sem campos: %s', strjoin(missing, ', ')); end
    th = spec; source = 'struct';
    return
end
if isnumeric(spec)
    v = double(spec(:).');
    if numel(v) ~= 9, error('theta vetor tem %d elementos, esperado 9.', numel(v)); end
    th = cell2struct(num2cell(v), NAMES, 2); source = 'vector';
    return
end
spec = char(spec);
if any(strcmpi(spec, {'promoted','official'}))
    vxvy = load_theta_mat(fullfile(dtssl_root(),'models','sysid_vxvy_v2.mat'));
    w    = load_theta_mat(fullfile(dtssl_root(),'models','sysid_omega_rotate_v1.mat'));
    th = vxvy;
    th.K_w = w.K_w; th.tau_w = w.tau_w; th.Td_w = w.Td_w;
    source = 'models/sysid_vxvy_v2.mat (vx,vy) + models/sysid_omega_rotate_v1.mat (w)';
    return
end
p = resolve_repo_path(spec);
if ~isfile(p), error('theta: arquivo nao encontrado: %s', p); end
[~, ~, ext] = fileparts(p);
if strcmpi(ext, '.json')
    J = jsondecode(fileread(p));
    th = struct();
    for d = {'vx','vy','w'}
        th.(['K_' d{1}])   = J.dof.(d{1}).K;
        th.(['tau_' d{1}]) = J.dof.(d{1}).tau;
        th.(['Td_' d{1}])  = J.dof.(d{1}).Td;
    end
else
    th = load_theta_mat(p);
end
source = spec;
end

% =========================================================================
function write_theta_json(path, th, source, stem)
J = struct();
J.source = source;
J.note = sprintf(['theta that generated %s_<event>.parquet (matlab/dtssl/export_plant_golden.m, %s). ' ...
    'Same key layout as config/twin_params.json; order is the fixed SLDD order.'], ...
    stem, char(datetime('now','Format','yyyy-MM-dd')));
J.dof = struct();
for d = {'vx','vy','w'}
    J.dof.(d{1}) = struct('K', th.(['K_' d{1}]), 'tau', th.(['tau_' d{1}]), ...
        'Td', th.(['Td_' d{1}]), 'placeholder', is_placeholder(th, d{1}));
end
J.order = {'K_vx','tau_vx','Td_vx','K_vy','tau_vy','Td_vy','K_w','tau_w','Td_w'};
txt = jsonencode(J, 'PrettyPrint', true);
fid = fopen(path, 'w'); assert(fid > 0, 'nao consegui abrir %s', path);
fwrite(fid, txt, 'char'); fprintf(fid, '\n'); fclose(fid);
end

function tf = is_placeholder(th, d)
% placeholder historico de omega: K=1, tau=0.1, Td=0 (sysid_vxvy_v2.mat)
tf = strcmp(d, 'w') && th.K_w == 1 && abs(th.tau_w - 0.1) < 1e-12 && th.Td_w == 0;
end
