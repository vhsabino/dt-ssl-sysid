function ensure_model_ready(model_name)
%ENSURE_MODEL_READY Prepara o modelo para sim repetida via run_one.
% Carrega o modelo e desliga a checagem de consistencia de dados APENAS
% em memoria (o .slx em disco nunca e salvo aqui). Tambem remove do base
% workspace o 'Ts' que o InitFcn legado ('control_parameters') deixa para
% tras a cada sim — ele duplica e conflita com o Ts do SLDD canonico
% (config/ssl_robot.sldd) na sim seguinte.
if ~bdIsLoaded(model_name)
    load_system(model_name);
end
if ~strcmp(get_param(model_name, 'EnforceDataConsistency'), 'off')
    set_param(model_name, 'EnforceDataConsistency', 'off');
end
evalin('base', 'clear(''Ts'')');
end
