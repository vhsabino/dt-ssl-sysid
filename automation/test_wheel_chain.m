function G = test_wheel_chain(opts)
%TEST_WHEEL_CHAIN Teste unitario da cadeia de rodas do pid_v3.
% (a) Isolado: replica inverse_kinematics (zonas mortas + K) e
%     forward_kinematics (pinv(K)) extraidas dos charts do modelo
%     (inventario 2026-06-11) e mede o ganho estatico puro da cadeia.
% (b) Simulink: simula o modelo com comandos CONSTANTES e theta ideal_v3
%     (K=1, tau=0.01, Td=0) e mede o ganho DC por DOF em vx/vy/omega_out.
% Casos acima e ABAIXO das zonas mortas (|vx|,|vy|<0.1; |w|<0.3).
%
% Retorna table: caso, dof, cmd, ganho_isolado, ganho_simulink.

arguments
    opts.ModelName (1,:) char = 'parameter_estimation_model_pid_v3'
    opts.ThetaMat  (1,:) char = fullfile('models','sysid_ideal_v3.mat')
    opts.Tsim      (1,1) double = 2.0   % s — folga p/ regime (tau=0.01)
    opts.Tss       (1,1) double = 0.5   % s finais para media de regime
end

CASES = { % [cmd_vx cmd_vy cmd_vw]
    'vx_1',    [1    0    0  ]
    'vy_1',    [0    1    0  ]
    'w_1',     [0    0    1  ]
    'vx_005',  [0.05 0    0  ]   % abaixo da zona morta de vx (0.1)
    'vy_005',  [0    0.05 0  ]   % abaixo da zona morta de vy (0.1)
    'w_02',    [0    0    0.2]   % abaixo da zona morta de w (0.3)
    };

theta = load_theta_mat(opts.ThetaMat);
apply_theta('config/ssl_robot.sldd', theta);
ensure_model_ready(opts.ModelName);

rows = cell(size(CASES,1), 1);
for c = 1:size(CASES,1)
    cmd = CASES{c,2};
    % --- (a) cadeia isolada (sem dinamica: regime => entrada = cmd) ---
    v_iso = chain_static(cmd);
    % --- (b) Simulink DC ---
    t = (0:1/60:opts.Tsim)';
    simIn = Simulink.SimulationInput(opts.ModelName);
    simIn = simIn.setVariable('cmd_vx_ts', timeseries(cmd(1)*ones(size(t)), t));
    simIn = simIn.setVariable('cmd_vy_ts', timeseries(cmd(2)*ones(size(t)), t));
    simIn = simIn.setVariable('cmd_vw_ts', timeseries(cmd(3)*ones(size(t)), t));
    simIn = simIn.setVariable('x0', 0); simIn = simIn.setVariable('y0', 0);
    simIn = simIn.setVariable('theta0', 0);
    simIn = simIn.setModelParameter('StopTime', num2str(opts.Tsim));
    out = sim(simIn);
    v_sim = [dcval(out,'vx_out',opts.Tss), dcval(out,'vy_out',opts.Tss), ...
             dcval(out,'omega_out',opts.Tss)];
    % ganho no DOF comandado (cmd~=0)
    d = find(cmd ~= 0, 1);
    dofs = {'vx','vy','w'};
    rows{c} = {CASES{c,1}, dofs{d}, cmd(d), v_iso(d)/cmd(d), v_sim(d)/cmd(d)};
end
G = cell2table(vertcat(rows{:}), 'VariableNames', ...
    {'caso','dof','cmd','ganho_isolado','ganho_simulink'});
disp(G);
end

% =========================================================================
function v = chain_static(u)
% Replica fiel dos charts (inverse_kinematics -> forward_kinematics),
% Action = K_Matrix = zeros => K = K_base. NAO MODIFICAR sem re-extrair.
vx = u(1); vy = u(2); w = u(3);
if abs(vx) < 0.1, vx = 0; end          % zona morta vx
if abs(vy) < 0.1, vy = 0; end          % zona morta vy
if abs(w)  < 0.3, w  = 0; end          % zona morta omega
K1 = 34.990925405431859; K2 = 20.2020202020202;
K3 = 28.569970957032222; K4 = 3.324525253;
K = [-K1  K2  K4; -K3 -K3  K4; K3 -K3  K4; K1  K2  K4];
v = (pinv(K) * (K * [vx; vy; w])).';
end

% =========================================================================
function g = dcval(out, name, tss)
ts = out.get(name);
t = ts.Time; d = squeeze(ts.Data);
g = mean(d(t >= t(end) - tss));
end
