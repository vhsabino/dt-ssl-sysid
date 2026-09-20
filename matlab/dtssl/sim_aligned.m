function [xa, ya, tha] = sim_aligned(model, s)
%SIM_ALIGNED Simula 1 evento (theta JA aplicado no SLDD) e devolve a pose
% alinhada SE(2) na grade do split (replica run_one_mat sem apply_theta).
% Helper compartilhado (Fase 3 do bayesopt); identico ao local de bo_cost.
simIn = Simulink.SimulationInput(model);
simIn = simIn.setVariable('cmd_vx_ts', s.cmd_vx_ts);
simIn = simIn.setVariable('cmd_vy_ts', s.cmd_vy_ts);
simIn = simIn.setVariable('cmd_vw_ts', s.cmd_vw_ts);
simIn = simIn.setVariable('x0', s.pos0.x0);
simIn = simIn.setVariable('y0', s.pos0.y0);
simIn = simIn.setVariable('theta0', s.pos0.theta0);
simIn = simIn.setModelParameter('StopTime', num2str(s.Tsim));
out = sim(simIn);
psx = out.get('pos_x_out'); psy = out.get('pos_y_out'); pth = out.get('theta_out');
xs = squeeze(psx.Data); ys = squeeze(psy.Data); ths = squeeze(pth.Data);
dth = s.pos0.theta0 - ths(1); c = cos(dth); sn = sin(dth);
xaT = c*(xs - xs(1)) - sn*(ys - ys(1)) + s.pos0.x0;
yaT = sn*(xs - xs(1)) + c*(ys - ys(1)) + s.pos0.y0;
thaT = ths + dth;
xa  = interp1(psx.Time, xaT,  s.t, 'linear', 'extrap');
ya  = interp1(psy.Time, yaT,  s.t, 'linear', 'extrap');
tha = interp1(pth.Time, thaT, s.t, 'linear', 'extrap');
end
