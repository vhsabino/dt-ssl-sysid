bootstrap_paths();          % LEGADO: nao ajusta mais pwd -- rode a partir da raiz do repo
setup_sldd('config/ssl_robot.sldd', 'models/sysid_initial.mat');
link_sldd_to_model('parameter_estimation_model_pid_v3', 'config/ssl_robot.sldd');