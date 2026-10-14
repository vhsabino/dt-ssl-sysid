function ensure_model_ready(model_name)
%ENSURE_MODEL_READY Garante o modelo carregado antes de run_one/run_one_mat.
% Historico: ate 2026-06-11 esta funcao desligava EnforceDataConsistency em
% memoria e limpava 'Ts' do base workspace — workarounds para o InitFcn
% legado 'control_parameters' (que definia Ts conflitante com o SLDD e
% exigia um .mat local). Com o InitFcn minimo (so K_Matrix = zeros(1,12)),
% nada disso e mais necessario.
if ~bdIsLoaded(model_name)
    load_system(model_name);
end
end
