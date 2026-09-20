% Script: run_pso_optimization.m (ESTÁGIO 1: Cinemática Isolada)

% 1. Definir o número de variáveis a otimizar (AGORA SÃO APENAS 4)
num_vars = 4;

% Parâmetros Otimizados: {K1_cin, K2_cin, K3_cin, K4_cin}
% Permitindo variação de até +/- 30% para encontrar escorregamento e raios efetivos
%lb = [-0.30, -0.30, -0.30, -0.30]; % Limite inferior de -30%
%ub = [ 0.30,  0.30,  0.30,  0.30]; % Limite superior de +30%
lb = [-0.99, -0.99, -0.99, -0.99]; % Limite inferior de -30%
ub = [ 0.99,  0.99,  0.99,  0.99]; % Limite superior de +30%
warning('off','all');

% =========================================================================
% 2. PREPARAÇÃO DOS WORKERS PARALELOS E SIMULINK (ISOLAMENTO E FAST RESTART)
% =========================================================================
disp('Configurando pastas isoladas e ativando FastRestart nos workers...');
poolobj = gcp('nocreate');
if isempty(poolobj)
    poolobj = parpool; 
end

% spmd executa o código abaixo simultaneamente dentro de CADA worker
spmd
    % 2.1 Isolamento de Cache 
    pasta_worker = fullfile(pwd, 'slprj_workers', num2str(spmdIndex));
    if ~exist(pasta_worker, 'dir')
        mkdir(pasta_worker);
    end
    Simulink.fileGenControl('set', 'CacheFolder', pasta_worker, ...
                                   'CodeGenFolder', pasta_worker, ...
                                   'KeepPreviousPath', true);
                                   
    % 2.2 Carregar o modelo e ativar o Fast Restart na memória de cada worker
    load_system('parameter_estimation_model_pid_v2');
    
    % FORÇA o Simulink a entender que o modelo está "limpo" (não modificado)
    set_param('parameter_estimation_model_pid_v2', 'Dirty', 'off');
    
    % LIGA a simulação de alta performance
    set_param('parameter_estimation_model_pid_v2', 'FastRestart', 'on');
    
    % 2.3 Silencia TODAS as variações do aviso de arquivo alterado no disco
    warning('off', 'Simulink:Commands:SimulinkModelChangedOnDisk');
    warning('off', 'Simulink:Engine:MdlFileChangedOnDisk');
end

% =========================================================================
% 3. Configurar as opções do PSO
options = optimoptions('particleswarm', ...
    'SwarmSize', 36, ...           
    'MaxIterations', 10000, ...       
    'Display', 'iter', ...         
    'UseParallel', true);         

% =========================================================================
% 4. Chamar a função de otimização
disp('A iniciar o Estágio 1: Otimização EXCLUSIVA da Cinemática...');
[melhores_deltas, menor_erro] = particleswarm(@(x) avaliar_gemeo_digital_stage_1(x), num_vars, lb, ub, options);

% =========================================================================
% 5. Exibir os resultados finais
disp('Otimização Concluída!');
disp('Melhores Deltas Encontrados para a Cinemática (Variação Percentual):');
disp(melhores_deltas);

% =========================================================================
% 6. LIMPEZA DOS WORKERS (OBRIGATÓRIO AO FIM DA EXECUÇÃO)
% =========================================================================
disp('Limpando memória e desligando Fast Restart nos workers...');
spmd
    set_param('parameter_estimation_model_pid_v2', 'FastRestart', 'off');
    close_system('parameter_estimation_model_pid_v2', 0); % 0 = não salvar alterações
end
disp('Limpeza concluída! Modelo pronto para edições manuais.');