% Script: run_pso_optimization.m

% 1. Definir o número de variáveis a otimizar
num_vars = 12;

% Parâmetros: {K1_cin, K2_cin, K3_cin, K4_cin, Kp1, Ki1, Kp2, Ki2, Kp3, Ki3, Kp4, Ki4}
lb = [-0.50, -0.50, -0.50, -0.50, -1.00, -1.00, -1.00, -1.00, -1.00, -1.00, -1.00, -1.00]; 
ub = [ 0.50,  0.50,  0.50,  0.50,  1.00,  1.00,  1.00,  1.00,  1.00,  1.00,  1.00,  1.00];

% =========================================================================
% INSERÇÃO 1: ISOLAMENTO DO CACHE PARA OS WORKERS PARALELOS
% Isso deve ser feito ANTES de chamar as opções do PSO.
disp('Configurando pastas isoladas para os workers paralelos...');
poolobj = gcp('nocreate');
if isempty(poolobj)
    poolobj = parpool; % Inicia o pool se não estiver rodando
end

% O bloco spmd roda um comando dentro de cada núcleo do processador
spmd
    % Cria uma subpasta exclusiva para o cache de cada núcleo
    pasta_worker = fullfile(pwd, 'slprj_workers', num2str(spmdIndex));
    if ~exist(pasta_worker, 'dir')
        mkdir(pasta_worker);
    end
    % Redireciona o Simulink daquele núcleo para a sua pasta exclusiva
    Simulink.fileGenControl('set', 'CacheFolder', pasta_worker, ...
                                   'CodeGenFolder', pasta_worker, ...
                                   'KeepPreviousPath', true);
end
% =========================================================================

% 3. Configurar as opções do PSO
options = optimoptions('particleswarm', ...
    'SwarmSize', 36, ...           
    'MaxIterations', 10000, ...       
    'Display', 'iter', ...         
    'UseParallel', true);         

% 4. Chamar a função de otimização
disp('A iniciar a otimização do Gêmeo Digital...');
[melhores_deltas, menor_erro] = particleswarm(@(x) avaliar_gemeo_digital(x), num_vars, lb, ub, options);

% 5. Exibir os resultados finais
disp('Otimização Concluída!');
disp('Melhores Deltas Encontrados (Variação Percentual):');
disp(melhores_deltas);