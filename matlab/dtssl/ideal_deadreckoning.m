function [xs, ys, ths] = ideal_deadreckoning(s, opts)
%IDEAL_DEADRECKONING Baseline cinematica IDEAL oficial (analitico, sem Simulink).
% Dead-reckoning dos comandos de corpo do split com resposta instantanea
% (K=1, tau=0, Td=0) — o que o "theta ideal" representa de fato, sem os
% bounds do SLDD (tau >= 0.01) que impedem simula-lo no modelo:
%   th(t)    = theta0 + int cmd_vw dt
%   [x;y](t) = p0 + int R(th(t)) * [cmd_vx; cmd_vy] dt
% Avaliar com rmse_pos_rebased (mesma metrica dos demais thetas).
%
% 'Tau' > 0 aplica lag de 1a ordem (ZOH exato, estado inicial nulo como o
% TransferFcn do modelo) aos comandos antes da integracao — usado para
% reconciliar o analitico com o ideal simulavel (tau=0.01).
%
% s: struct de load_split (cmd_*_ts na grade s.t, pos0). Saidas na grade s.t.
%
% Helpers series_on_grid e lag_filter em matlab/dtssl/private/ (compartilhados
% com deadreckoning_p1d). Porte Python: dtssl.models.ideal (IdealKinematicPlant).

arguments
    s        (1,1) struct
    opts.Tau (1,1) double {mustBeNonnegative} = 0
end

t = s.t;
ux = series_on_grid(s.cmd_vx_ts, t);
uy = series_on_grid(s.cmd_vy_ts, t);
uw = series_on_grid(s.cmd_vw_ts, t);

if opts.Tau > 0
    ux = lag_filter(ux, t, opts.Tau);
    uy = lag_filter(uy, t, opts.Tau);
    uw = lag_filter(uw, t, opts.Tau);
end

ths = s.pos0.theta0 + cumtrapz(t, uw);
xs  = s.pos0.x0 + cumtrapz(t, cos(ths).*ux - sin(ths).*uy);
ys  = s.pos0.y0 + cumtrapz(t, sin(ths).*ux + cos(ths).*uy);
end
