function out = run_one_mat(model_name, split_path, mat_path)
%RUN_ONE_MAT Espelho de scripts/run_one.m para theta vindo de um .mat
% arbitrario. run_one so aceita os nomes fixos {'ideal','procest','bayesopt'}
% com caminhos hardcoded; este espelho reproduz exatamente os mesmos passos
% (apply_theta -> load_split -> SimulationInput -> sim) usando as MESMAS
% funcoes do pipeline, trocando apenas a origem do theta por load_theta_mat.
% Manter em sincronia com scripts/run_one.m (nao modificavel).

sldd = 'config/ssl_robot.sldd';

theta = load_theta_mat(mat_path);
apply_theta(sldd, theta);

s = load_split(split_path);

simIn = Simulink.SimulationInput(model_name);
simIn = simIn.setVariable('cmd_vx_ts', s.cmd_vx_ts);
simIn = simIn.setVariable('cmd_vy_ts', s.cmd_vy_ts);
simIn = simIn.setVariable('cmd_vw_ts', s.cmd_vw_ts);
simIn = simIn.setVariable('x0',     s.pos0.x0);
simIn = simIn.setVariable('y0',     s.pos0.y0);
simIn = simIn.setVariable('theta0', s.pos0.theta0);
simIn = simIn.setModelParameter('StopTime', num2str(s.Tsim));

out = sim(simIn);
out.SplitInfo = s;

% --- Correcao SE(2) pos-simulacao (sem tocar o .slx) ---
% Os integradores do modelo tinham IC hardcoded (x=0, y=0, theta=1.8039),
% ignorando x0/y0/theta0 do split. Como o modelo integra velocidades de
% corpo rotacionadas para o global, a trajetoria e equivariante sob SE(2):
% basta levar a pose inicial simulada (xs0,ys0,ths0) na pose inicial do
% split (x0,y0,theta0):
%   dth = theta0 - ths0
%   [xa;ya] = R(dth)*([xs;ys] - [xs0;ys0]) + [x0;y0],  tha = ths + dth
% Se o modelo ja partir da pose certa (Fase 3), dth=0 e a transformacao
% vira identidade — o alinhamento e idempotente.
psx = out.get('pos_x_out');  psy = out.get('pos_y_out');
pth = out.get('theta_out');
xs = squeeze(psx.Data);  ys = squeeze(psy.Data);  ths = squeeze(pth.Data);
dth = s.pos0.theta0 - ths(1);
c = cos(dth);  sn = sin(dth);
xa = c*(xs - xs(1)) - sn*(ys - ys(1)) + s.pos0.x0;
ya = sn*(xs - xs(1)) + c*(ys - ys(1)) + s.pos0.y0;
out.pos_x_aligned = timeseries(xa, psx.Time, 'Name', 'pos_x_aligned');
out.pos_y_aligned = timeseries(ya, psy.Time, 'Name', 'pos_y_aligned');
out.theta_aligned = timeseries(ths + dth, pth.Time, 'Name', 'theta_aligned');
end
