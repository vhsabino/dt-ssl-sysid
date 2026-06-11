function out = run_one(model_name, split_path, theta_name)
% RUN_ONE  Roda uma simulação pra um split + um θ.
%   out = run_one('parameter_estimation_model_pid_v3', ...
%                 'data/extracted/foo/splits/square/ev_01/chunk_01.parquet', ...
%                 'bayesopt')
%
% theta_name: 'ideal' | 'procest' | 'bayesopt'

sldd = 'config/ssl_robot.sldd';

% 1) Aplica θ ao SLDD
theta = load_theta(theta_name);   % helper abaixo
apply_theta(sldd, theta);

% 2) Carrega split
s = load_split(split_path);

% 3) Monta SimulationInput
simIn = Simulink.SimulationInput(model_name);
simIn = simIn.setVariable('cmd_vx_ts', s.cmd_vx_ts);
simIn = simIn.setVariable('cmd_vy_ts', s.cmd_vy_ts);
simIn = simIn.setVariable('cmd_vw_ts', s.cmd_vw_ts);
simIn = simIn.setVariable('x0',     s.pos0.x0);     % se modelo expõe IC
simIn = simIn.setVariable('y0',     s.pos0.y0);
simIn = simIn.setVariable('theta0', s.pos0.theta0);
simIn = simIn.setModelParameter('StopTime', num2str(s.Tsim));

% 4) Roda
out = sim(simIn);
out.SplitInfo = s;     % carrega contexto pro pós-processamento
end

% =========================================================================
function theta = load_theta(name)
    switch lower(name)
        case 'ideal'
            theta = struct('K_vx',1,'tau_vx',1e-6,'Td_vx',0, ...
                           'K_vy',1,'tau_vy',1e-6,'Td_vy',0, ...
                           'K_w', 1,'tau_w', 1e-6,'Td_w', 0);
        case 'procest'
            theta = load_theta_mat('results/sysid_initial.mat');
        case 'bayesopt'
            theta = load_theta_mat('results/sysid_bayesopt.mat');
        otherwise
            error('theta_name desconhecido: %s', name);
    end
end