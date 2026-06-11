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
end
