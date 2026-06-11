bootstrap_paths();          % autodetecta raiz, ajusta pwd
setup_sldd('config/ssl_robot.sldd', 'results/sysid_initial.mat');
link_sldd_to_model('parameter_estimation_model_pid_v3', 'config/ssl_robot.sldd');