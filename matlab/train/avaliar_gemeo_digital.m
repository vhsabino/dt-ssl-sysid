% =========================================================================
% FUNÇÃO DE AVALIAÇÃO
% =========================================================================
function custo = avaliar_gemeo_digital(action)
    % 3. Reconstrução da Matriz Cinemática Simétrica
    K_Matrix = [action(1),action(2),action(3),action(4), ...
                action(5),action(6),action(7),action(8), ...
                action(9),action(10),action(11),action(12)];
            
    % 4. Preparar o Simulink sem poluir o Base Workspace
    simIn = Simulink.SimulationInput('parameter_estimation_model_pid_v2.slx');
    simIn = simIn.setVariable('K_Matrix', K_Matrix);
    
    % INSERÇÃO 2: DESLIGAR O FAST RESTART EM MODO PARALELO!
    % Isso evita que um erro em um worker corrompa as iterações seguintes.
    simIn = simIn.setModelParameter('FastRestart', 'off');
    
    % 5. Executar a Simulação
    try
        out = sim(simIn);
        
        % 6. Extrair os objetos do Simulink
        ts1 = out.get('rmse'); 
        
        % INSERÇÃO 3: PROTEÇÃO CONTRA SINAIS VAZIOS OU ZEROS FALSOS
        if isempty(ts1) || isempty(ts1.Data)
            custo = 1e6;
            return; % Aborta imediatamente se o Simulink não gerou dados
        end
        
        % O custo final é o último valor
        custo = ts1.Data(end);
        
        % Se a simulação falhou matematicamente (divergiu) ou deu exatamente zero (erro de execução)
        if isnan(custo) || isinf(custo) || custo == 0
            custo = 1e6; 
        end
        
    catch ME
        % Removi o disp daqui. Se você tiver 36 partículas e 6 derem erro, 
        % o console vai travar de tanta mensagem. Apenas penalize silenciosamente.
        custo = 1e6; 
    end
end