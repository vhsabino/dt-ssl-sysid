%% 1. Configurações Iniciais e Criação do Ambiente
mdl = 'rl_model_with_ros'; % Substitua pelo nome exato do seu arquivo .slx (sem o .slx)
open_system(mdl);
agentBlk = [mdl '/RL Agent']; 
Ts = 0.0167;          
maxSteps = 60 * 10; 

% OBSERVATION: 9 dimensões (Erros X, Y, Theta nas versões P, I, D)
obsInfo = rlNumericSpec([9 1], 'LowerLimit', -inf, 'UpperLimit', inf);
obsInfo.Name = 'observations';

% ACTION: 8 dimensões (Delta_Kp e Delta_Ki para os 4 motores)
lim_delta_Kp_min = -0.3;  lim_delta_Kp_max = 3.0;
lim_delta_Ki_min = -6.0;  lim_delta_Ki_max = 6.0;

limite_inferior = [lim_delta_Kp_min; lim_delta_Ki_min; lim_delta_Kp_min; lim_delta_Ki_min; ...
    lim_delta_Kp_min; lim_delta_Ki_min; lim_delta_Kp_min; lim_delta_Ki_min];
limite_superior = [lim_delta_Kp_max; lim_delta_Ki_max; lim_delta_Kp_max; lim_delta_Ki_max; ...
    lim_delta_Kp_max; lim_delta_Ki_max; lim_delta_Kp_max; lim_delta_Ki_max];

actInfo = rlNumericSpec([8 1], 'LowerLimit', limite_inferior, 'UpperLimit', limite_superior);
actInfo.Name = 'Residual_PID_gains';

% Recria o ambiente (env) na memória
env = rlSimulinkEnv(mdl, agentBlk, obsInfo, actInfo);
fprintf('Ambiente (env) criado com sucesso!\n');

%% 2. Carregar o Agente do Checkpoint
caminho_arquivo = 'Checkpoints_Agente_TD3/Agent11000.mat';
fprintf('Carregando o checkpoint: %s\n', caminho_arquivo);

dados = load(caminho_arquivo);

% Verifica o nome da variável salva e a transfere para 'agent'
if isfield(dados, 'saved_agent')
    agent = dados.saved_agent;
elseif isfield(dados, 'agent')
    agent = dados.agent;
else
    error('Não foi possível encontrar o agente no arquivo .mat.');
end

fprintf('Agente carregado com sucesso!\n');

%% 3. Execução da Simulação
simOpts = rlSimulationOptions('MaxSteps', maxSteps);

fprintf('Iniciando a simulação do agente treinado (isso pode levar alguns segundos)...\n');
experiencia = sim(env, agent, simOpts);
fprintf('Simulação concluída!\n');