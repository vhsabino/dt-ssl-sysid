function results = run_bayesopt(dataByDOF, theta0, opts)
% run_bayesopt - BO sobre os 9 params da Rota B usando RMSE em posição.
%
% USO típico:
%   load('sysid_initial.mat')
%   results = run_bayesopt(dataByDOF, theta0)
%
% Saída:
%   results  - objeto BayesianOptimization (use bestPoint(results) e plot(results))
%
% Salva automaticamente: sysid_bayesopt.mat com theta_opt + tabela completa.

    arguments
        dataByDOF       (1,1) struct
        theta0          (1,:) double = []
        opts.MaxIter    (1,1) double = 100
        opts.NumSeed    (1,1) double = 30     % Latin Hypercube inicial
        opts.WindowSec  (1,1) double = 2.5
        opts.WeightTh   (1,1) double = 0.5    % ← coloca 0 se quiser ignorar θ
        opts.Verbose    (1,1) double = 1
    end

    % --- handle do theta0 (substitui NaN por placeholders ---
    if isempty(theta0)
        theta0 = [1 0.1 0  1 0.1 0  1 0.1 0];
    end
    nan_mask = isnan(theta0);
    if any(nan_mask)
        placeholders = [1 0.1 0  1 0.1 0  1 0.1 0];
        theta0(nan_mask) = placeholders(nan_mask);
        fprintf('⚠ theta0 tinha NaN — substituídos por placeholders.\n');
    end

    %% --- Bounds largos absolutos (defensáveis fisicamente) ---
    vars = [
        optimizableVariable('Kx',    [0.1  5.0])
        optimizableVariable('tau_x', [0.005 1.0],  'Transform','log')
        optimizableVariable('Td_x',  [0    0.5])
        optimizableVariable('Ky',    [0.1  5.0])
        optimizableVariable('tau_y', [0.005 1.0],  'Transform','log')
        optimizableVariable('Td_y',  [0    0.5])
        optimizableVariable('Kt',    [0.1  5.0])
        optimizableVariable('tau_t', [0.005 1.0],  'Transform','log')
        optimizableVariable('Td_t',  [0    0.5])
    ];
    % 'log' em τ porque escala é multiplicativa (10× entre min e max);
    % BO explora melhor em log-space pra hiperparâmetros que cruzam ordens de grandeza.

    %% --- Função objetivo ---
    objFcn = @(t) compute_rmse_position( ...
        [t.Kx t.tau_x t.Td_x  t.Ky t.tau_y t.Td_y  t.Kt t.tau_t t.Td_t], ...
        dataByDOF, ...
        'window_sec', opts.WindowSec, ...
        'weight_th',  opts.WeightTh);

    %% --- Ponto inicial (warmstart no theta0 do System ID) ---
    initialTable = table(theta0(1),theta0(2),theta0(3), ...
                         theta0(4),theta0(5),theta0(6), ...
                         theta0(7),theta0(8),theta0(9), ...
        'VariableNames', {'Kx','tau_x','Td_x','Ky','tau_y','Td_y','Kt','tau_t','Td_t'});

    fprintf('\n========== BAYESIAN OPTIMIZATION ==========\n');
    fprintf('Bounds: K∈[0.1,5], τ∈[0.005,1.0] (log), Td∈[0,0.5]\n');
    fprintf('Iter total: %d | Seed (LHS): %d | window: %.1fs | weight_th: %.2f\n\n', ...
            opts.MaxIter, opts.NumSeed, opts.WindowSec, opts.WeightTh);

    %% --- Rodar BO ---
    results = bayesopt(objFcn, vars, ...
        'InitialX',                        initialTable, ...
        'MaxObjectiveEvaluations',         opts.MaxIter, ...
        'NumSeedPoints',                   opts.NumSeed, ...
        'AcquisitionFunctionName',         'expected-improvement-plus', ...
        'IsObjectiveDeterministic',        true, ...
        'ExplorationRatio',                0.5, ...
        'UseParallel',                     false, ...
        'Verbose',                         opts.Verbose, ...
        'PlotFcn',                         {@plotObjectiveModel, @plotMinObjective});
    % 'expected-improvement-plus' tem proteção embutida contra overexploitation
    % 'IsObjectiveDeterministic',true porque a função é determinística (mesmos dados)

    %% --- Resultados ---
    best = bestPoint(results);
    theta_opt = [best.Kx best.tau_x best.Td_x  ...
                 best.Ky best.tau_y best.Td_y  ...
                 best.Kt best.tau_t best.Td_t];
    J_opt = results.MinObjective;

    fprintf('\n========== RESULTADO BO ==========\n');
    fprintf('J_opt = %.2f mm  (chute inicial: %.2f mm — redução de %.1f%%)\n', ...
            J_opt, ...
            compute_rmse_position(theta0, dataByDOF, 'window_sec', opts.WindowSec, 'weight_th', opts.WeightTh), ...
            100 * (1 - J_opt / compute_rmse_position(theta0, dataByDOF, 'window_sec', opts.WindowSec, 'weight_th', opts.WeightTh)));

    paramsTable = array2table(theta_opt, 'VariableNames', ...
        {'Kx','tau_x','Td_x','Ky','tau_y','Td_y','Kt','tau_t','Td_t'});
    disp(paramsTable);

    %% --- Verificação out-of-distribution se houver val_out ---
    if isfield(dataByDOF, 'val_out')
        J_val = compute_rmse_position(theta_opt, dataByDOF, ...
            'use_val_out', true, ...
            'window_sec',  opts.WindowSec, ...
            'weight_th',   opts.WeightTh);
        fprintf('\nVerificação val_out: J = %.2f mm (gap vs treino: %+.1f%%)\n', ...
                J_val, 100 * (J_val / J_opt - 1));
    end

    %% --- Salvar ---
    save('sysid_bayesopt.mat', 'theta_opt', 'J_opt', 'results', ...
         'paramsTable', 'theta0', 'opts');
    fprintf('\n✅ Resultados salvos em sysid_bayesopt.mat\n');
    fprintf('   theta_opt pronto para carregar no Simulink (Rota B).\n');
end
