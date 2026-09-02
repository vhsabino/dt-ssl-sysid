% Valores iniciais para os 8 ganhos (4 motores, Kp e Ki)
Delta_kp1_inicial = 0.0; 
Delta_ki1_inicial = 0.0;
Delta_kp2_inicial = 0.0; 
Delta_ki2_inicial = 0.0;
Delta_kp3_inicial = 0.0; 
Delta_ki3_inicial = 0.0;
Delta_kp4_inicial = 0.0; 
Delta_ki4_inicial = 0.0;

% Vetor que entrará no bloco Constant do Simulink
ganhos_PID = [Delta_kp1_inicial, Delta_ki1_inicial, ...
    Delta_kp2_inicial, Delta_ki2_inicial, ...
    Delta_kp3_inicial, Delta_ki3_inicial, ...
    Delta_kp4_inicial, Delta_ki4_inicial];

clear;% 1. Definir o vetor de tempo da simulação (baseado no seu código anterior)
Ts = 0.0167;          % Passo de amostragem
tempo_total = 10;     % Segundos
t = (0:Ts:tempo_total)'; % Vetor coluna de tempo

% 2. Criar um array de zeros do mesmo tamanho do tempo
zeros_array = zeros(length(t), 1);

% 3. Criar objetos "timeseries" para os alvos (O App adora esse formato)
alvo_erro_x = timeseries(zeros_array, t);
alvo_erro_y = timeseries(zeros_array, t);
alvo_erro_theta = timeseries(zeros_array, t);

disp('Gabaritos de erro criados no workspace com sucesso!');

spetool('parameter_estimation_model_with_ros')