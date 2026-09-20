%% 1. Configurações Iniciais e Ambiente
mdl = 'rl_model_with_ros'; % Substitua pelo nome exato do seu arquivo .slx
open_system(mdl);
agentBlk = [mdl '/RL Agent']; % Ajuste o caminho até o bloco RL Agent

Ts = 0.0167;          % Frequência de 60Hz
maxSteps = 60 * 10; % 3600 passos = 60 segundos de episódio

%% 2. Espaços de Observação e Ação (Os Limites do Residual)
% OBSERVATION: 9 dimensões (Erros X, Y, Theta nas versões P, I, D)
obsInfo = rlNumericSpec([9 1], 'LowerLimit', -inf, 'UpperLimit', inf);
obsInfo.Name = 'observations';

% ACTION: 8 dimensões (Delta_Kp e Delta_Ki para os 4 motores)
% Definindo os limites máximos e mínimos do Residual (Ajuste fino)
lim_delta_Kp_min = -0.3;  lim_delta_Kp_max = 3.0;
lim_delta_Ki_min = -6.0;  lim_delta_Ki_max = 6.0;

% Vetores de limites para as 8 saídas: [dKp1, dKi1, dKp2, dKi2, dKp3, dKi3, dKp4, dKi4]
limite_inferior = [lim_delta_Kp_min; lim_delta_Ki_min; lim_delta_Kp_min; lim_delta_Ki_min; ...
    lim_delta_Kp_min; lim_delta_Ki_min; lim_delta_Kp_min; lim_delta_Ki_min];

limite_superior = [lim_delta_Kp_max; lim_delta_Ki_max; lim_delta_Kp_max; lim_delta_Ki_max; ...
    lim_delta_Kp_max; lim_delta_Ki_max; lim_delta_Kp_max; lim_delta_Ki_max];

actInfo = rlNumericSpec([8 1], 'LowerLimit', limite_inferior, 'UpperLimit', limite_superior);
actInfo.Name = 'Residual_PID_gains';

env = rlSimulinkEnv(mdl, agentBlk, obsInfo, actInfo);

%% 3. Redes Neurais (Actor e Critic)
fcSize = 32; % Tamanho da camada oculta baseado no artigo

% --- CRÍTICO (Avalia a qualidade da Ação dado o Estado) ---
criticNetwork = [
    featureInputLayer(obsInfo.Dimension(1), 'Name', 'obs')
    fullyConnectedLayer(fcSize, 'Name', 'fc1')
    concatenationLayer(1, 2, 'Name', 'concat')
    fullyConnectedLayer(fcSize, 'Name', 'fc2')
    fullyConnectedLayer(1, 'Name', 'Q_value')];
criticNetwork = layerGraph(criticNetwork); 
criticNetwork = addLayers(criticNetwork, featureInputLayer(actInfo.Dimension(1), 'Name', 'act'));
criticNetwork = connectLayers(criticNetwork, 'act', 'concat/in2');

criticOpts = rlRepresentationOptions('LearnRate', 0.01, ...
                                     'Optimizer', 'adam', ...
                                     'UseDevice', 'gpu'); % <-- Joga a matemática pesada para a placa de vídeo



% ---> CORREÇÃO: CRIANDO OS DOIS CRÍTICOS GÊMEOS <---
% Cria o Crítico 1
critic1 = rlQValueRepresentation(criticNetwork, obsInfo, actInfo, ...
    'Observation', {'obs'}, 'Action', {'act'}, criticOpts);

% Cria o Crítico 2 (Usa a mesma rede, mas é um objeto neural independente)
critic2 = rlQValueRepresentation(criticNetwork, obsInfo, actInfo, ...
    'Observation', {'obs'}, 'Action', {'act'}, criticOpts);

% --- ATOR (Gera a Ação dado o Estado) ---
actorNetwork = [
    featureInputLayer(obsInfo.Dimension(1), 'Name', 'obs')
    fullyConnectedLayer(fcSize, 'Name', 'fc1')
    fullyConnectedLayer(actInfo.Dimension(1), 'Name', 'gains_raw')
    tanhLayer('Name', 'tanh_scale')]; 

actorOpts = rlRepresentationOptions('LearnRate', 0.01, ...
                                    'Optimizer', 'adam', ...
                                    'UseDevice', 'gpu');  % <-- Joga a matemática pesada para a placa de vídeo
actor = rlDeterministicActorRepresentation(actorNetwork, obsInfo, actInfo, ...
    'Observation', {'obs'}, 'Action', {'gains_raw'}, actorOpts);

%% 4. Hiperparâmetros do TD3 
agentOpts = rlTD3AgentOptions(...
    'SampleTime', Ts, ...
    'DiscountFactor', 0.97, ...
    'MiniBatchSize', 128, ...
    'ExperienceBufferLength', 500000);

agentOpts.ExplorationModel.Variance = 0.1;

agent = rlTD3Agent(actor, [critic1, critic2], agentOpts);

% Cria o objeto exigido pela sua versão do MATLAB
parallelOpts = rl.option.ParallelTraining();
parallelOpts.Mode = 'async';
parallelOpts.DataToSendFromWorkers = 'Experiences';

% Cria o nome da pasta onde os checkpoints serão salvos (no diretório atual)
pasta_checkpoints = pwd + "/Checkpoints_Agente_TD3";

pontuacao_excelente = -500; 

trainOpts = rlTrainingOptions(...
    'MaxEpisodes', 100000, ...              
    'MaxStepsPerEpisode', maxSteps, ...     
    'ScoreAveragingWindowLength', 50, ...
    'Plots', 'training-progress', ...
    'StopTrainingCriteria', 'AverageReward', ...
    'StopTrainingValue', -0.1, ...          
    'UseParallel', true, ...                
    'ParallelizationOptions', parallelOpts, ...
    ... % --- CONFIGURAÇÕES DE CHECKPOINT POR RECOMPENSA ---
    'SaveAgentCriteria', 'EpisodeReward', ...  % Agora salva baseado no desempenho da rede neural!
    'SaveAgentValue', pontuacao_excelente, ... % Só salva se a recompensa for MAIOR ou IGUAL a este valor
    'SaveAgentDirectory', pasta_checkpoints);

%% 6. Inicializar Pool Paralelo Otimizado e Iniciar Treinamento
pool = gcp('nocreate'); % Verifica se já existe um pool aberto

if isempty(pool)
    fprintf('Iniciando o Pool Paralelo turbinado (12 workers). Isso leva uns segundos...\n');
    % Pega o cluster local e altera o limite máximo de workers
    meuCluster = parcluster('local'); 
    meuCluster.NumWorkers = 12; % Força o uso de 12 núcleos do seu i7-13700H
    
    % Inicia os 12 clones do Simulink
    parpool(meuCluster, 12); 
end

fprintf('Iniciando o Treinamento TD3 PARALELIZADO com GPU...\n');
trainStats = train(agent, env, trainOpts);