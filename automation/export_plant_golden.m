function out_path = export_plant_golden(event_dir, theta_mat, out_path, Ts)
%EXPORT_PLANT_GOLDEN Exporta a trajetoria de deadreckoning_p1d (a REFERENCIA
% promovida) para UM evento, avaliada na grade uniforme 1/60 — golden do
% AnalyticFOPDTPlant. A reamostragem 1/60 e identica a do loader / de
% export_resample_reference (colon 1/60, comandos ZOH, pose linear+unwrap),
% e entao deadreckoning_p1d roda sobre essa grade. Theta vem do .mat promovido
% (mesma fonte do config/twin_params.json), garantindo paridade Python<->MATLAB.

arguments
    event_dir (1,:) char
    theta_mat (1,:) char = fullfile('models','sysid_vxvy_v2.mat')
    out_path  (1,:) char = ''
    Ts (1,1) double = 1/60
end
if isempty(out_path)
    [~,ev] = fileparts(event_dir);
    out_path = fullfile('tests','fixtures', ['plant_golden_' ev '.parquet']);
end

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

th = load_theta_mat(theta_mat);
[xs, ys, ths, vbody] = deadreckoning_p1d(s, th);

T = table(grid, cmd_vx, cmd_vy, cmd_w, xs, ys, ths, vbody(:,1), vbody(:,2), vbody(:,3), ...
    'VariableNames', {'t','cmd_vx','cmd_vy','cmd_w','xs','ys','ths','vbx','vby','vbw'});
od = fileparts(out_path); if ~isempty(od) && ~isfolder(od), mkdir(od); end
parquetwrite(out_path, T);
fprintf('export_plant_golden: %s (rid=%g, N=%d, dur=%.3f s)\n', out_path, rid, height(T), grid(end)-grid(1));
end
