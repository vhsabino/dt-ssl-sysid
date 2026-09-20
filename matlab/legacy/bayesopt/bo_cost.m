function [J, info] = bo_cost(theta, cache, opts)
%BO_COST Custo de fidelidade COMPORTAMENTAL p/ bayesopt (Cenario B).
% Dado theta (9 params) e um cache de eventos, simula no MESMO pipeline
% Simulink dos baselines (apply_theta -> SimulationInput -> sim -> alinhamento
% SE(2) idempotente de run_one_mat) e retorna:
%
%   J = mediana_eventos[ wmean_h( RMSE_pos_SE2(h) ) ] + lambda * mediana_eventos[ wmean_h( RMSE_heading(h) ) ]
%
% h in {0.5,1,2,2.5,4} s, peso por horizonte w_h ∝ 1/h (normalizado), ancora
% SE(2) com theta truth filtrado (rmse_pos_rebased_se2 / rmse_heading_rebased).
% Posicao em m, heading em rad; lambda converte rad->m-equivalente (Fase 1).
% Determinístico (sim deterministica; sem aleatoriedade). apply_theta UMA vez
% por avaliacao (nao por evento); eventos vem de build_event_cache.

arguments
    theta (1,9) double
    cache (1,:) struct
    opts.Lambda   (1,1) double = 0
    opts.Horizons (1,:) double = [0.5 1 2 2.5 4]
    opts.Overlap  (1,1) double = 0.5
    opts.FiltS    (1,1) double = 0.2
    opts.Model    (1,:) char   = 'parameter_estimation_model_pid_v3'
    opts.ApplyTheta (1,1) logical = true
end

if opts.ApplyTheta
    apply_theta('config/ssl_robot.sldd', theta);
end
H = opts.Horizons;  wts = (1./H) / sum(1./H);
ne = numel(cache);
pos_e = nan(ne,1);  head_e = nan(ne,1);
SE2 = nan(ne, numel(H));  HEAD = nan(ne, numel(H));
for i = 1:ne
    s = cache(i).s;
    [xa, ya, tha] = sim_aligned(opts.Model, s);
    for k = 1:numel(H)
        SE2(i,k)  = rmse_pos_rebased_se2(cache(i).t, xa, ya, tha, ...
            cache(i).xt, cache(i).yt, cache(i).tht, H(k), opts.Overlap, opts.FiltS);
        HEAD(i,k) = rmse_heading_rebased(cache(i).t, tha, cache(i).tht, ...
            H(k), opts.Overlap, opts.FiltS);
    end
    pos_e(i)  = wts * SE2(i,:).';
    head_e(i) = wts * HEAD(i,:).';
end
J_pos  = median(pos_e, 'omitnan');
J_head = median(head_e, 'omitnan');
J = J_pos + opts.Lambda * J_head;

info = struct('J',J,'J_pos',J_pos,'J_head',J_head,'lambda',opts.Lambda, ...
    'pos_e',pos_e,'head_e',head_e,'SE2',SE2,'HEAD',HEAD, ...
    'horizons',H,'weights',wts,'events',{ {cache.event} }, ...
    'se2_med_h', median(SE2,1,'omitnan'), 'head_med_h', median(HEAD,1,'omitnan'));
end

% =========================================================================
function [xa, ya, tha] = sim_aligned(model, s)
%SIM_ALIGNED Simula 1 evento (theta JA aplicado no SLDD) e devolve a pose
% alinhada SE(2) na grade do split (replica run_one_mat sem apply_theta).
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
