function [xs, ys, ths] = ideal_deadreckoning(s)
%IDEAL_DEADRECKONING Baseline cinematica IDEAL oficial (analitico, sem Simulink).
% Dead-reckoning dos comandos de corpo do split com resposta instantanea
% (K=1, tau=0, Td=0) — o que o "theta ideal" representa de fato, sem os
% bounds do SLDD (tau >= 0.01) que impedem simula-lo no modelo:
%   th(t)    = theta0 + int cmd_vw dt
%   [x;y](t) = p0 + int R(th(t)) * [cmd_vx; cmd_vy] dt
% Avaliar com rmse_pos_rebased (mesma metrica dos demais thetas).
%
% s: struct de load_split (cmd_*_ts na grade s.t, pos0). Saidas na grade s.t.

t = s.t;
ux = series_on_grid(s.cmd_vx_ts, t);
uy = series_on_grid(s.cmd_vy_ts, t);
uw = series_on_grid(s.cmd_vw_ts, t);

ths = s.pos0.theta0 + cumtrapz(t, uw);
xs  = s.pos0.x0 + cumtrapz(t, cos(ths).*ux - sin(ths).*uy);
ys  = s.pos0.y0 + cumtrapz(t, sin(ths).*ux + cos(ths).*uy);
end

function u = series_on_grid(ts, t)
% load_split constroi as timeseries na propria grade do split; o interp1
% 'previous' (ZOH) cobre o caso geral sem alterar o caso identico.
if numel(ts.Time) == numel(t) && all(ts.Time == t)
    u = ts.Data;
else
    u = interp1(ts.Time, ts.Data, t, 'previous', 0);
end
u = u(:);
end
