function out_path = export_resample_reference(event_dir, out_path, Ts)
%EXPORT_RESAMPLE_REFERENCE Exporta a grade reamostrada (1/60) de UM evento, usando
% EXATAMENTE as operacoes de reamostragem do pipeline de ID (build_idData_per_dof):
% grade = (tc(1):Ts:tc(end)); comandos ZOH (interp1 'previous',0); pose linear
% (interp1 'linear',NaN); theta = interp1(...,unwrap(position_w),...). Conversoes
% mm->m e mm/s->m/s. Serve de GOLDEN p/ o teste cross-linguagem do loader Python
% (phase0_replay): o loader deve reproduzir esta tabela a tolerancia.
%
% Selecao de robo IGUAL a do loader: unico robot_id presente em commands; team
% 'allies'. Trim ao bloco contiguo com pose valida (igual ao loader).
%
% USO: export_resample_reference('data\...\side_to_side_01_05', 'tests\fixtures\resample_ref_side_to_side_01_05.parquet')

arguments
    event_dir (1,:) char
    out_path  (1,:) char
    Ts (1,1) double = 1/60
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

cmd_vx = interp1(tc, C.move_x, grid, 'previous', 0);   % corpo, SI: NAO escala/rotaciona
cmd_vy = interp1(tc, C.move_y, grid, 'previous', 0);
cmd_w  = interp1(tc, C.move_w, grid, 'previous', 0);
theta  = interp1(tr, unwrap(R.position_w), grid, 'linear', NaN);
pos_x  = interp1(tr, R.position_x/1000, grid, 'linear', NaN);
pos_y  = interp1(tr, R.position_y/1000, grid, 'linear', NaN);
vel_x_world = interp1(tr, R.velocity_x/1000, grid, 'linear', NaN);
vel_y_world = interp1(tr, R.velocity_y/1000, grid, 'linear', NaN);

valid = ~isnan(pos_x) & ~isnan(pos_y) & ~isnan(theta);
i0 = find(valid,1,'first');  i1 = find(valid,1,'last');
keep = false(size(valid));  keep(i0:i1) = true;

T = table(grid(keep), cmd_vx(keep), cmd_vy(keep), cmd_w(keep), ...
          pos_x(keep), pos_y(keep), theta(keep), vel_x_world(keep), vel_y_world(keep), ...
          'VariableNames', {'t','cmd_vx','cmd_vy','cmd_w','pos_x','pos_y','theta', ...
                            'vel_x_world','vel_y_world'});
od = fileparts(out_path);
if ~isempty(od) && ~isfolder(od), mkdir(od); end
parquetwrite(out_path, T);
fprintf('export_resample_reference: %s (rid=%g, N=%d, dur=%.3f s)\n', ...
    out_path, rid, height(T), T.t(end)-T.t(1));
end
