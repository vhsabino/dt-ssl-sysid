load('sysid_initial.mat')

% Testa duas vezes com params MUITO diferentes:
theta_good = [0.989 0.128 0.171  0.949 0.242 0.104  1 0.1 0];
theta_bad  = [5.000 0.005 0.500  0.100 0.005 0.500  1 0.1 0];   % patológico

J_good = compute_rmse_position(theta_good, dataByDOF, 'window_sec',2.5, 'weight_th',0.5);
J_bad  = compute_rmse_position(theta_bad,  dataByDOF, 'window_sec',2.5, 'weight_th',0.5);

fprintf('J_good = %.2f mm\n', J_good);
fprintf('J_bad  = %.2f mm\n', J_bad);

% Quanto tempo leva uma avaliação?
tic; compute_rmse_position(theta_good, dataByDOF, 'window_sec',2.5, 'weight_th',0.5); toc