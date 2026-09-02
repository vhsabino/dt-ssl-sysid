% 1. Roda a simulação no Simulink
out = sim('parameter_estimation_model_pid_v2');

% 2. Chama a GUI passando os resultados para ver o playback
VisualizadorSimulink(out);