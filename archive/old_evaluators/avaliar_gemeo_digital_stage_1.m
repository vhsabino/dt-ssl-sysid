% =========================================================================
% FUNÇÃO DE AVALIAÇÃO
% =========================================================================
function custo = avaliar_gemeo_digital_stage_1(action)
    % 1. Reconstrução da Matriz: 4 Variáveis do PSO + 8 Zeros
    % Os zeros garantem que parâmetros não otimizados rodem com 0% de variação
    K_Matrix = [action(1), action(2), action(3), action(4), ...
                0, 0, 0, 0, ...
                0, 0, 0, 0];
            
    % 2. Preparar o Simulink 
    % CRÍTICO: NÃO USE A EXTENSÃO .slx AQUI!
    % Isso obriga o comando sim a usar a versão da RAM com FastRestart ativado.
    simIn = Simulink.SimulationInput('parameter_estimation_model_pid_v2');
    
    % Injeta as variáveis no modelo
    simIn = simIn.setVariable('K_Matrix', K_Matrix);
    
    % 3. Executar a Simulação
    try
        out = sim(simIn);
        ts1 = out.get('rmse'); 
        
        if isempty(ts1) || isempty(ts1.Data)
            custo = 1e6;
            return; 
        end
        
        custo = ts1.Data(end);
        
        if isnan(custo) || isinf(custo) || custo <= 0.0001
            custo = 1e6; 
        end
        
    catch 
        custo = 1e6; 
    end
end