function custo = avaliar_gemeo_digital(action)

% 3. Reconstrução da Matriz Cinemática Simétrica
%K_Matrix = [
%    -K1,  K2,  K4; 
%    -K3, -K3,  K4; 
%    K3, -K3,  K4; 
%    K1,  K2,  K4  
%    ];

K_Matrix = [action(1),action(2),action(3),action(4), ...
    action(5),action(6),action(7),action(8), ...
    action(9),action(10),action(11),action(12)];

% 4. Preparar o Simulink sem poluir o Base Workspace
% Substitua 'nome_do_seu_modelo' pelo nome do seu ficheiro .slx
simIn = Simulink.SimulationInput('parameter_estimation_model_pid_v2.slx');

% Injeta a matriz calculada para dentro do modelo
simIn = simIn.setVariable('K_Matrix', K_Matrix);

% Pode forçar a simulação a correr em modo 'FastRestart' para acelerar os ciclos
simIn = simIn.setModelParameter('FastRestart', 'on');

% 5. Executar a Simulação
try
    out = sim(simIn);
    
% 6. Extrair os objetos (Timeseries) do Simulink
    ts1 = out.get('rmse'); 
    
    % O custo final é a soma de todos os RMSEs
    custo = ts1.Data(end);
    
    % Exibe os RMSEs individuais e o custo final para o seu debug
    %disp(['RMSE X: ', num2str(rmse1), ' | RMSE Y: ', num2str(rmse2), ' | RMSE Theta: ', num2str(rmse3)]);
    %disp(['Custo total calculado com sucesso: ', num2str(custo)]);
    
    % Opcional: Penalizações
    if isnan(custo) || isinf(custo)
        custo = 1e6; 
    end
catch ME
    custo = 1e6; 
    disp(['Saiu pelo catch: ', ME.message ]);
end
end