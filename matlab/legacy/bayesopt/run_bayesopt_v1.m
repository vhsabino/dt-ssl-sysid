function results = run_bayesopt_v1(opts)
%RUN_BAYESOPT_V1 Fase 2 — bayesopt dos 9 params otimizando fidelidade
% COMPORTAMENTAL (bo_cost: SE(2) multi-h + lambda*heading). Cenario B.
% Faixas do SLDD (K[0.5,2], tau[0.02,0.5] log, Td[0,0.15]); aquisicao EI-plus;
% determinístico; warm-start via InitialX (vx/vy v2 + omega placeholder; o
% placeholder antigo; e vx/vy v2 + omega candidato reprovado — o GP aprende
% com ele, NAO fixa nada). Salva incremental (OutputFcn) p/ monitorar/retomar.
%
% Custo ~9.4 s/sim (modelo lento, loop algebrico do TransportDelay com Td_w=0):
% por isso usa um subconjunto de eventos COBRINDO os 3 DOFs (build/bo_fase01.mat,
% 5 eventos: 1 ftb + 2 sts + 2 stg) — a validacao (Fase 3) usa o hold-out.

arguments
    opts.MaxEvals (1,1) double = 100
    opts.Lambda   (1,1) double = 1.171     % Fase 1 (contribuicao heading ~= posicao)
    opts.Seed     (1,1) double = 42
    opts.NumSeed  (1,1) double = 20
    opts.CacheMat (1,:) char   = fullfile('build','bo_fase01.mat')
    opts.OutTag   (1,:) char   = 'v1'
end

bootstrap_paths();
warning('off','all');
try, Simulink.data.dictionary.closeAll('-discard'); catch, end
try, bdclose('all'); catch, end
system('git restore config/ssl_robot.sldd');
ensure_model_ready('parameter_estimation_model_pid_v3');
sldd_restore = onCleanup(@() system('git restore config/ssl_robot.sldd')); %#ok<NASGU>

F = load(opts.CacheMat);  cacheTr = F.cacheTr;
fprintf('bayesopt: %d eventos de treino, lambda=%.3f, MaxEvals=%d, seed=%d\n', ...
    numel(cacheTr), opts.Lambda, opts.MaxEvals, opts.Seed);

% --- warm-start points (NAO fixam parametros; semeiam o GP) ----------------
vv = F.vv;                                   % vx/vy v2 + omega placeholder (promovido)
pv = F.pv;                                   % placeholder antigo
vc = vv; vc(7:9) = [1.307 0.0222 0.1179];    % vx/vy v2 + omega linear candidato (reprovado)
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

progFile = fullfile('results', sprintf('bo_progress_%s.mat', opts.OutTag));
rng(opts.Seed);
results = bayesopt(obj, vars, ...
    'InitialX', initialX, ...
    'MaxObjectiveEvaluations', opts.MaxEvals, ...
    'NumSeedPoints', opts.NumSeed, ...
    'AcquisitionFunctionName', 'expected-improvement-plus', ...
    'IsObjectiveDeterministic', true, ...
    'Verbose', 1, ...
    'PlotFcn', {}, ...
    'OutputFcn', @(r,s) save_progress(r,s,progFile));

% --- resultado + sensibilidade ARD -----------------------------------------
best = bestPoint(results);
theta_opt = [best.Kvx best.tauvx best.Tdvx best.Kvy best.tauvy best.Tdvy best.Kw best.tauw best.Tdw];
J_opt = results.MinObjective;
ard = ard_lengthscales(results, names);

outmat = fullfile('models', sprintf('sysid_bayesopt_%s_raw.mat', opts.OutTag));
meta = struct('lambda',lam,'seed',opts.Seed,'maxevals',opts.MaxEvals, ...
    'train_events',{ {cacheTr.event} }, 'names',{names}, ...
    'commit',strtrim(evalc('!git rev-parse --short HEAD')),'created',char(datetime('now')));
save(outmat, 'results','theta_opt','J_opt','ard','meta','-v7.3');
fprintf('\n==== bayesopt done: J_opt=%.4f ====\n', J_opt);
fprintf('theta_opt = %s\n', mat2str(round(theta_opt,4)));
fprintf('Salvo: %s\n', outmat);
end

% =========================================================================
function J = safe_cost(theta, cache, lambda)
try
    J = bo_cost(theta, cache, 'Lambda', lambda, 'ApplyTheta', true);
    if ~isfinite(J), J = 1e3; end
catch
    J = 1e3;   % theta invalido -> penalidade alta (nao derruba o bayesopt)
end
end

% =========================================================================
function stop = save_progress(results, state, file)
stop = false;
if ~strcmp(state, 'done')
    try, save(file, 'results'); catch, end
end
end

% =========================================================================
function ard = ard_lengthscales(results, names)
% Sensibilidade por parametro = 1/lengthscale de um GP ARD ajustado ao trace.
ard = struct('names',{names},'lengthscale',nan(1,numel(names)),'sensitivity',nan(1,numel(names)));
try
    X = results.XTrace; Y = results.ObjectiveTrace;
    gp = fitrgp(X, Y, 'KernelFunction','ardsquaredexponential','Standardize',true);
    ls = gp.KernelInformation.KernelParameters(1:width(X)).';
    ard.lengthscale = ls;
    ard.sensitivity = 1 ./ ls;
catch ME
    ard.error = ME.message;
end
end
