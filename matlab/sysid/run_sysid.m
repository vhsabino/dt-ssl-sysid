%% run_sysid.m - Pipeline: System ID inicial + objetivo em posição + val cruzada
clear; clc;

%% Configuração: log de treino + log de val out-of-distribution
splits = struct();
splits.train   = { 'extracted/2026-05-18_19-2-15/splits' };   % log A
%splits.val_out =   'extracted/2025-04-02_xx-xx-xx/splits';     % log B (troque)

ROBOT_ID = 3;        % ou o ID que apareceu
TEAM     = 'allies'; % ou o nome que apareceu (verifique exato, é case-sensitive)

%% 1) Montar iddata por DOF
dataByDOF = build_idData_per_dof(splits, ...
    'Ts',1/60, 'robot_id',ROBOT_ID, 'team',TEAM, 'detrend',true, ...
    'omega_thresh',0.5, 'vxy_thresh_ms',0.3, 'minSegSec',0.5);

%% 2) Identificação inicial por DOF (chute pra BO)
params0 = identify_per_dof(dataByDOF, 'maxIter', 80);

theta0 = [params0.x.K     params0.x.tau     params0.x.Td  ...
          params0.y.K     params0.y.tau     params0.y.Td  ...
          NaN NaN NaN];   % θ pulado — coletar log dedicado
fprintf('⚠ θ não identificado (dados insuficientes). Use valores manuais ou colete log dedicado.\n');
          %params0.theta.K params0.theta.tau params0.theta.Td];

fprintf('\n--- chute inicial (System ID) ---\n');
disp(array2table(theta0, 'VariableNames', ...
    {'Kx','tau_x','Td_x','Ky','tau_y','Td_y','Kt','tau_t','Td_t'}));

%% 3) Avaliar função objetivo (posição, janelas deslizantes)
% Se θ não foi identificado, neutraliza no objetivo
if any(isnan(theta0(7:9)))
    theta0(7:9) = [1 0.1 0];   % placeholder
    weight_th = 0;
else
    weight_th = 0.5;
end

J0 = compute_rmse_position(theta0, dataByDOF, 'window_sec',2.5, 'weight_th',weight_th);
J0_val = compute_rmse_position(theta0, dataByDOF, 'use_val_out',true, 'window_sec',2.5, 'weight_th',weight_th)
fprintf('\nJ(theta0) treino   = %.2f mm\n', J0);
fprintf('J(theta0) val_out  = %.2f mm  (degradação %.1f%%)\n', ...
    J0_val, 100*(J0_val/J0 - 1));

%% 4) Validação cruzada por DOF
report = cross_log_validation(theta0, dataByDOF, 'window_sec',2.5);

%% 5) Salvar pro BO
save('sysid_initial.mat', 'theta0', 'params0', 'dataByDOF', 'report');
fprintf('\n✅ theta0 + dataByDOF salvos em sysid_initial.mat\n');
fprintf('   Próximo passo: rodar BO com objFcn = @(t) compute_rmse_position(t, dataByDOF)\n');

%% --- Snippet para BO (descomente quando rodar) ---
% vars = [
%   optimizableVariable('Kx',    [0.3 3.0])
%   optimizableVariable('tau_x', [0.01 0.5])
%   optimizableVariable('Td_x',  [0 0.1])
%   optimizableVariable('Ky',    [0.3 3.0])
%   optimizableVariable('tau_y', [0.01 0.5])
%   optimizableVariable('Td_y',  [0 0.1])
%   optimizableVariable('Kt',    [0.3 3.0])
%   optimizableVariable('tau_t', [0.01 0.5])
%   optimizableVariable('Td_t',  [0 0.1])
% ];
% objFcn = @(t) compute_rmse_position( ...
%   [t.Kx t.tau_x t.Td_x t.Ky t.tau_y t.Td_y t.Kt t.tau_t t.Td_t], dataByDOF);
% results = bayesopt(objFcn, vars, ...
%   'MaxObjectiveEvaluations', 80, ...
%   'AcquisitionFunctionName','expected-improvement-plus');
