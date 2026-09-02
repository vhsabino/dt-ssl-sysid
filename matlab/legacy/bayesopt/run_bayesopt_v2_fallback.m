function results = run_bayesopt_v2_fallback(opts)
%RUN_BAYESOPT_V2_FALLBACK Fase 1-2 (FALLBACK, se Fase 0 deu rho<0.85) — o proxy
% nao preserva o ranking; roda o bayesopt no SIMULINK FIEL (bo_cost, ApplyTheta)
% com config viavel: 100 avaliacoes, 9 eventos estratificados de treino cobrindo
% os 3 DOFs DELIBERADAMENTE (2 ftb + 3 sts + 4 stg, nao 5 aleatorios), warm-start
% igual ao v1. Saves incrementais (OutputFcn) p/ poll do _raw.mat. Mesmo gate
% hold-out da Fase 3 (eval_bayesopt_v2_holdout). Determinístico.
%
% Custo ~9.5 s/sim x 9 eventos => ~85 s/avaliacao; 100 avaliacoes ~ 2.4 h.
% Lancar em background; NAO usar '& echo' (mascara a conclusao). Poll do _raw.mat.

arguments
    opts.MaxEvals (1,1) double = 100
    opts.Lambda   (1,1) double = 1.171
    opts.Seed     (1,1) double = 42
    opts.NumSeed  (1,1) double = 15
    opts.OutTag   (1,:) char   = 'v2'
    opts.Dataset  (1,:) char   = '2026-05-18_19-2-15'
end

here = fileparts(mfilename('fullpath'));
addpath(fullfile(here,'..','..')); repo_root = bootstrap_paths('legacy'); cd(repo_root); %#ok<NASGU> % legado: caminhos relativos abaixo assumem pwd == raiz do repo
warning('off','all');
try, Simulink.data.dictionary.closeAll('-discard'); catch, end
try, bdclose('all'); catch, end
system('git restore config/ssl_robot.sldd');
ensure_model_ready('parameter_estimation_model_pid_v3');
sldd_restore = onCleanup(@() system('git restore config/ssl_robot.sldd'));

% --- 9 eventos estratificados (deliberado), fora do hold-out ----------------
trainEv = { ...
    'front_to_back','front_to_back_01_02'
    'front_to_back','front_to_back_01_03'
    'side_to_side','side_to_side_01_01'
    'side_to_side','side_to_side_01_08'
    'side_to_side','side_to_side_02_01'
    'shoot_to_goal','shoot_to_goal_01_01'
    'shoot_to_goal','shoot_to_goal_03_01'
    'shoot_to_goal','shoot_to_goal_07_01'
    'shoot_to_goal','shoot_to_goal_11_01'};
cacheTr = build_event_cache(trainEv, 'Dataset', opts.Dataset);
fprintf('FALLBACK Simulink: %d eventos de treino, lambda=%.3f, MaxEvals=%d\n', ...
    numel(cacheTr), opts.Lambda, opts.MaxEvals);

vv = [1.1192 0.071784 0.06905 1.0524 0.12733 0.056483 1 0.1 0];
pv = [0.98859 0.12817 0.17075 0.9493 0.24158 0.10445 1 0.1 0];
vc = vv; vc(7:9) = [1.307 0.0222 0.1179];
names = {'Kvx','tauvx','Tdvx','Kvy','tauvy','Tdvy','Kw','tauw','Tdw'};
initialX = array2table([vv; pv; vc], 'VariableNames', names);

vars = [
    optimizableVariable('Kvx',  [0.5 2.0])
    optimizableVariable('tauvx',[0.02 0.5], 'Transform','log')
    optimizableVariable('Tdvx', [0 0.15])
    optimizableVariable('Kvy',  [0.5 2.0])
    optimizableVariable('tauvy',[0.02 0.5], 'Transform','log')
    optimizableVariable('Tdvy', [0 0.15])
    optimizableVariable('Kw',   [0.5 2.0])
    optimizableVariable('tauw', [0.02 0.5], 'Transform','log')
    optimizableVariable('Tdw',  [0 0.15])];

lam = opts.Lambda;  cc = cacheTr;
obj = @(t) safe_cost([t.Kvx t.tauvx t.Tdvx t.Kvy t.tauvy t.Tdvy t.Kw t.tauw t.Tdw], cc, lam);

progFile = fullfile('results', sprintf('bo_progress_%s_fallback.mat', opts.OutTag));
rng(opts.Seed);
results = bayesopt(obj, vars, ...
    'InitialX', initialX, ...
    'MaxObjectiveEvaluations', opts.MaxEvals, ...
    'NumSeedPoints', opts.NumSeed, ...
    'AcquisitionFunctionName', 'expected-improvement-plus', ...
    'IsObjectiveDeterministic', true, ...
    'Verbose', 1, 'PlotFcn', {}, ...
    'OutputFcn', @(r,s) save_progress(r,s,progFile));

best = bestPoint(results);
theta_opt = [best.Kvx best.tauvx best.Tdvx best.Kvy best.tauvy best.Tdvy best.Kw best.tauw best.Tdw];
J_opt = results.MinObjective;
ard = ard_lengthscales(results, names);
meta = struct('lambda',lam,'seed',opts.Seed,'maxevals',opts.MaxEvals, ...
    'train_events',{ {cacheTr.event} }, 'train_labels',{ {cacheTr.label} }, 'names',{names}, ...
    'warmstart',[vv;pv;vc], 'J_train_proxy',J_opt, 'mode','FALLBACK_SIMULINK', ...
    'commit',strtrim(evalc('!git rev-parse --short HEAD')),'created',char(datetime('now')));
outmat = fullfile('models', sprintf('sysid_bayesopt_%s_raw.mat', opts.OutTag));
save(outmat, 'results','theta_opt','J_opt','ard','meta','-v7.3');
save(fullfile('build', sprintf('bo_proxy_train_%s.mat', opts.OutTag)), ...
    'cacheTr','trainEv','vv','pv','vc','lam','theta_opt','J_opt','-v7.3');
fprintf('\n==== bayesopt v2 (FALLBACK Simulink) done: J=%.4f ====\n', J_opt);
fprintf('theta_opt = %s\nSalvo: %s\n', mat2str(round(theta_opt,4)), outmat);
end

% =========================================================================
function J = safe_cost(theta, cache, lambda)
try
    J = bo_cost(theta, cache, 'Lambda', lambda, 'ApplyTheta', true);
    if ~isfinite(J), J = 1e3; end
catch
    J = 1e3;
end
end
function stop = save_progress(results, state, file)
stop = false;
if ~strcmp(state, 'done'), try, save(file, 'results'); catch, end, end
end
function ard = ard_lengthscales(results, names)
ard = struct('names',{names},'lengthscale',nan(1,numel(names)),'sensitivity',nan(1,numel(names)));
try
    X = results.XTrace; Y = results.ObjectiveTrace;
    gp = fitrgp(X, Y, 'KernelFunction','ardsquaredexponential','Standardize',true);
    ls = gp.KernelInformation.KernelParameters(1:width(X)).';
    ard.lengthscale = ls; ard.sensitivity = 1 ./ ls;
catch ME
    ard.error = ME.message;
end
end
