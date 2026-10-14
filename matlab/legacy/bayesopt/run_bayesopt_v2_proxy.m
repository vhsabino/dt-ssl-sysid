function results = run_bayesopt_v2_proxy(opts)
%RUN_BAYESOPT_V2_PROXY Fases 1-2 (Caminho 2) — bayesopt dos 9 params otimizando
% a fidelidade COMPORTAMENTAL avaliada pelo PROXY ANALITICO (bo_cost_proxy),
% com TREINO AMPLO (~18 eventos estratificados nos 3 DOFs, fora do hold-out).
% Como o proxy custa ~1.6 ms/evento, o orcamento e generoso (300-500 avaliacoes)
% — resolve o overfit do v1 (5 eventos / 9 params) por DADO, nao por metodo.
%
% Mesma FORMULA de custo do bo_cost (SE(2) multi-h + lambda*heading, lambda=1.171),
% faixas do SLDD (K[0.5,2], tau[0.02,0.5] log, Td[0,0.15]), EI-plus, determinístico,
% warm-start (vx/vy v2 + omega placeholder ; placeholder antigo ; omega candidato
% reprovado) — semeia o GP, nao fixa nada. NAO escreve o SLDD (proxy analitico).
% A confirmacao no Simulink fiel + gate hold-out e a Fase 3 (eval_bayesopt_v2_holdout).

arguments
    opts.MaxEvals (1,1) double = 400
    opts.Lambda   (1,1) double = 1.171
    opts.Seed     (1,1) double = 42
    opts.NumSeed  (1,1) double = 20
    opts.OutTag   (1,:) char   = 'v2'
    opts.Dataset  (1,:) char   = '2026-05-18_19-2-15'
end

here = fileparts(mfilename('fullpath'));
addpath(fullfile(here,'..','..')); repo_root = bootstrap_paths('legacy'); cd(repo_root); %#ok<NASGU> % legado: caminhos relativos abaixo assumem pwd == raiz do repo
warning('off','all');

% --- conjunto de treino amplo (deterministico, seed=42; exclui hold-out) ----
trainEv = build_train_events(opts.Seed);
fprintf('Treino amplo: %d eventos\n', size(trainEv,1));
cacheTr = build_event_cache(trainEv, 'Dataset', opts.Dataset);

% --- warm-start (NAO fixa; semeia o GP) ------------------------------------
vv = [1.1192 0.071784 0.06905 1.0524 0.12733 0.056483 1 0.1 0];     % vx/vy v2 + omega placeholder
pv = [0.98859 0.12817 0.17075 0.9493 0.24158 0.10445 1 0.1 0];      % placeholder antigo
vc = vv; vc(7:9) = [1.307 0.0222 0.1179];                           % omega candidato (reprovado)
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
obj = @(t) safe_cost_proxy([t.Kvx t.tauvx t.Tdvx t.Kvy t.tauvy t.Tdvy t.Kw t.tauw t.Tdw], cc, lam);

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

best = bestPoint(results);
theta_opt = [best.Kvx best.tauvx best.Tdvx best.Kvy best.tauvy best.Tdvy best.Kw best.tauw best.Tdw];
J_opt = results.MinObjective;
[J_check, info_train] = bo_cost_proxy(theta_opt, cacheTr, 'Lambda', lam); %#ok<ASGLU>
ard = ard_lengthscales(results, names);

meta = struct('lambda',lam,'seed',opts.Seed,'maxevals',opts.MaxEvals, ...
    'train_events',{ {cacheTr.event} }, 'train_labels',{ {cacheTr.label} }, 'names',{names}, ...
    'warmstart',[vv;pv;vc], 'J_train_proxy',J_opt, 'J_train_proxy_check',J_check, ...
    'commit',strtrim(evalc('!git rev-parse --short HEAD')),'created',char(datetime('now')));
outmat = fullfile('models', sprintf('sysid_bayesopt_%s_raw.mat', opts.OutTag));
save(outmat, 'results','theta_opt','J_opt','ard','meta','info_train','-v7.3');

% cache de treino p/ Fase 3 (comparar J_sim vs J_proxy no MESMO conjunto)
save(fullfile('build', sprintf('bo_proxy_train_%s.mat', opts.OutTag)), ...
    'cacheTr','trainEv','vv','pv','vc','lam','theta_opt','J_opt','-v7.3');

fprintf('\n==== bayesopt v2 (proxy) done: J_train_proxy=%.4f ====\n', J_opt);
fprintf('theta_opt = %s\n', mat2str(round(theta_opt,4)));
fprintf('K_w(opt)=%.4f (vs 1.35 fisico, 1.0 placeholder)\n', theta_opt(7));
if isfield(ard,'sensitivity') && all(isfinite(ard.sensitivity))
    [~,ord] = sort(ard.sensitivity,'descend');
    fprintf('ARD sensibilidade (desc): %s\n', strjoin(arrayfun(@(k) ...
        sprintf('%s=%.2f',names{ord(k)},ard.sensitivity(ord(k))), 1:numel(ord),'uni',0), '  '));
end
fprintf('Salvo: %s\n', outmat);
end

% =========================================================================
function ev = build_train_events(seed)
%BUILD_TRAIN_EVENTS ~18 eventos estratificados (ftb/sts/stg), deterministico,
% excluindo os 10 do hold-out. ftb: todos os 3 disponiveis (vx so excita em
% front_to_back); sts: 6 de 9; stg: 9 de 13. Total 18.
holdout = { ...
    'front_to_back_01_01', ...
    'side_to_side_01_05','side_to_side_01_06','side_to_side_01_07','side_to_side_02_03', ...
    'shoot_to_goal_05_02','shoot_to_goal_08_01','shoot_to_goal_09_01','shoot_to_goal_12_01','shoot_to_goal_14_02'};

ftb = {'front_to_back_01_02','front_to_back_01_03','front_to_back_01_04'};
sts = {'side_to_side_01_01','side_to_side_01_02','side_to_side_01_03','side_to_side_01_04', ...
       'side_to_side_01_08','side_to_side_02_01','side_to_side_02_02','side_to_side_02_04','side_to_side_02_05'};
stg = {'shoot_to_goal_01_01','shoot_to_goal_02_01','shoot_to_goal_03_01','shoot_to_goal_04_01', ...
       'shoot_to_goal_05_01','shoot_to_goal_06_01','shoot_to_goal_07_01','shoot_to_goal_10_01', ...
       'shoot_to_goal_11_01','shoot_to_goal_11_02','shoot_to_goal_13_01','shoot_to_goal_14_01','shoot_to_goal_15_01'};
ftb = setdiff(ftb, holdout); sts = setdiff(sts, holdout); stg = setdiff(stg, holdout);

rng(seed);
pick = @(c,n) c(sort(randperm(numel(c), min(n,numel(c)))));
selF = pick(ftb, 3); selS = pick(sts, 6); selG = pick(stg, 9);

evnames = [selF(:); selS(:); selG(:)];
ev = cell(numel(evnames),2);
for i = 1:numel(evnames)
    nm = evnames{i};
    ev{i,1} = regexprep(nm, '_\d+_\d+$', '');   % label = prefixo antes de _NN_NN
    ev{i,2} = nm;
end
end

% =========================================================================
function J = safe_cost_proxy(theta, cache, lambda)
try
    J = bo_cost_proxy(theta, cache, 'Lambda', lambda);
    if ~isfinite(J), J = 1e3; end
catch
    J = 1e3;
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
