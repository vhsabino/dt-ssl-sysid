function T = run_all_experiments(opts)
%RUN_ALL_EXPERIMENTS Orquestra a comparacao de thetas (ideal_v2, procest,
% bayesopt...) sobre os splits indexados por list_splits, com RMSE de
% posicao em janelas RE-ANCORADAS multi-horizonte (mesmo esquema do custo
% real em matlab/sysid/compute_rmse_position.m: window_sec=2.5, overlap=0.5).
% Gera a tabela mestra e a base da FIGURA CENTRAL do artigo (Gate G3).
%
% Assinaturas reais usadas (NAO alterar os arquivos do pipeline):
%   repo_root = bootstrap_paths()                       % scripts/bootstrap_paths.m
%   S   = list_splits(data_root_abs, 'Label', lbl)      % matlab/simulink_io/list_splits.m
%         -> table: log,label,event,chunk,path,n_rows,duration_s
%         -> data_root PRECISA ser absoluto (erase() sobre paths do dir())
%   out = run_one(model_name, split_path, theta_name)   % scripts/run_one.m
%         -> theta_name: 'ideal' | 'procest' | 'bayesopt' (nomes fixos)
%   s   = load_split(p)  % chamado por run_one; exige parquet com colunas:
%         timestamp_event, move_vx, move_vy, move_w, pos_x, pos_y, theta
%   [theta, meta] = load_theta_mat(mat)                 % matlab/sldd/load_theta_mat.m
%
% Pontes locais (automation/, pipeline intocado):
%   canonical_split  — streams reais -> parquet do contrato de load_split
%   run_one_mat      — espelho de run_one p/ theta de .mat arbitrario
%                      (ex.: models/sysid_ideal_v2.mat via opts.ThetaMats)
%   ensure_model_ready, rmse_pos_rebased
%
% MODOS:
%   'full'  (default) — saida em results/, entrada no CHANGELOG, hash de
%                       commit OBRIGATORIO (erro se ausente; '-dirty' se suja)
%   'smoke'           — saida em results/debug/, SEM CHANGELOG, hash tolerante
%
% USO:
%   T = run_all_experiments();                                    % tudo
%   T = run_all_experiments('Mode','smoke','Label','square', ...  % smoke
%         'MaxSplits',1,'ThetaNames',{'ideal_v2','procest'});

arguments
    opts.DataRoot   (1,:) char   = fullfile('data','extracted')
    opts.ModelName  (1,:) char   = 'parameter_estimation_model_pid_v3'
    % 'ideal_analytic' = baseline ideal OFICIAL (dead-reckoning analitico,
    % sem Simulink — os bounds do SLDD impedem tau<0.01 no modelo)
    opts.ThetaNames (1,:) cell   = {'ideal_analytic','procest','bayesopt'}
    % nomes de theta resolvidos por .mat (rota run_one_mat, que aplica a
    % correcao SE(2) pos-sim); os demais nomes sao delegados a run_one.
    % procest/bayesopt apontam para os MESMOS .mat que run_one usa.
    % ideal_v2 (tau=1e-3) e insimulavel pelos bounds; ideal_v3 (tau=0.01)
    % e o ideal simulavel minimo.
    opts.ThetaMats  (1,1) struct = struct( ...
        'ideal_v2', fullfile('models','sysid_ideal_v2.mat'), ...
        'ideal_v3', fullfile('models','sysid_ideal_v3.mat'), ...
        'procest',  fullfile('results','sysid_initial.mat'), ...
        'bayesopt', fullfile('results','sysid_bayesopt.mat'))
    opts.Label      (1,:) char   = ''      % '' = todos os labels
    opts.Chunk      (1,:) char   = 'commands'  % chunk de origem do canonical_split
    opts.HorizonsSec (1,:) double = 2.5    % janela(s) de re-ancoragem do custo real
    opts.Overlap    (1,1) double = 0.5     % igual compute_rmse_position
    opts.MaxSplits  (1,1) double = Inf
    opts.Seed       (1,1) double = 42
    opts.MakeFigure (1,1) logical = true
    opts.Mode       (1,:) char {mustBeMember(opts.Mode, {'full','smoke'})} = 'full'
end

repo_root = bootstrap_paths();   % adiciona paths e faz cd na raiz
rng(opts.Seed);
smoke = strcmp(opts.Mode, 'smoke');

% Proveniencia capturada ANTES das sims: apply_theta (dentro de run_one/
% run_one_mat) escreve no SLDD versionado durante a rodada, o que sujaria
% o hash se capturado no fim. O hash de inicio identifica o codigo/dados
% que produziram a rodada.
githash = get_git_hash(repo_root, ~smoke);   % fail-loud no modo 'full'

% list_splits exige raiz ABSOLUTA pra recortar log/label/event/chunk do path
data_root = opts.DataRoot;
if ~startsWith(data_root, repo_root)
    data_root = fullfile(repo_root, data_root);
end

S = list_splits(data_root, 'Label', opts.Label);
S = S(strcmp(S.chunk, opts.Chunk), :);
if height(S) > opts.MaxSplits
    S = S(1:opts.MaxSplits, :);
end
fprintf('run_all_experiments[%s]: %d splits (chunk=%s), thetas={%s}, horizontes=[%s] s\n', ...
    opts.Mode, height(S), opts.Chunk, strjoin(opts.ThetaNames, ','), num2str(opts.HorizonsSec));

% --- Pre-requisitos do modelo (workarounds documentados; .slx NUNCA e salvo) ---
% O InitFcn legado 'control_parameters' carrega um .mat de caminho local;
% o original versionado vive em data/recorded — copia (cache) se faltar.
init_mat = fullfile(repo_root,'scripts','local','train','robocin_tests_id5.mat');
if ~isfile(init_mat)
    src_mat = fullfile(repo_root,'data','recorded','robocin_tests_id5.mat');
    if ~isfile(src_mat)
        error('InitFcn do modelo exige %s e a origem %s nao existe.', init_mat, src_mat);
    end
    if ~isfolder(fileparts(init_mat)), mkdir(fileparts(init_mat)); end
    copyfile(src_mat, init_mat);
    fprintf('Cache local p/ InitFcn: %s\n', init_mat);
end
ensure_model_ready(opts.ModelName);

rows = {};
for i = 1:height(S)
    % Etapa canonica: traduz os streams reais (commands+processed_robots)
    % para o contrato exigido por load_split (chamado dentro de run_one).
    % Em caso de falta de coluna, o erro lista faltantes vs. disponiveis.
    try
        [canon_path, map_applied] = canonical_split(S.path{i});
        if i == 1
            fprintf('Mapa real -> contrato aplicado (canonical_split):\n');
            disp(map_applied);
        end
    catch ME
        status = sprintf('erro_canonico: %s', clean_msg(ME.message));
        fprintf('  [%d/%d] %s/%s/%s -> %s\n', i, height(S), ...
            S.label{i}, S.event{i}, S.chunk{i}, status);
        for k = 1:numel(opts.ThetaNames)
            for h = opts.HorizonsSec
                rows(end+1,:) = {S.log{i}, S.label{i}, S.event{i}, ...
                    opts.ThetaNames{k}, h, NaN, status}; %#ok<AGROW>
            end
        end
        continue;
    end

    for k = 1:numel(opts.ThetaNames)
        tname = opts.ThetaNames{k};
        try
            if strcmp(tname, 'ideal_analytic')
                % baseline ideal: dead-reckoning analitico, sem Simulink
                s = load_split(canon_path);
                [xs, ys] = ideal_deadreckoning(s);
                xt = s.pos_x_truth.Data;  yt = s.pos_y_truth.Data;  tt = s.t;
            else
                ensure_model_ready(opts.ModelName);
                if isfield(opts.ThetaMats, tname)
                    out = run_one_mat(opts.ModelName, canon_path, opts.ThetaMats.(tname));
                else
                    out = run_one(opts.ModelName, canon_path, tname);
                end
                s = out.SplitInfo;
                [tsim, px, py] = extract_sim_position(out);
                % truth na grade do split; sim interpolada na mesma grade
                xt = s.pos_x_truth.Data;  yt = s.pos_y_truth.Data;  tt = s.t;
                xs = interp1(tsim, px, tt, 'linear', 'extrap');
                ys = interp1(tsim, py, tt, 'linear', 'extrap');
            end
            for h = opts.HorizonsSec
                r = rmse_pos_rebased(tt, xs, ys, xt, yt, h, opts.Overlap);
                rows(end+1,:) = {S.log{i}, S.label{i}, S.event{i}, ...
                    tname, h, r, 'ok'}; %#ok<AGROW>
            end
            fprintf('  [%d/%d] %s/%s x %s -> ok\n', i, height(S), ...
                S.label{i}, S.event{i}, tname);
        catch ME
            status = sprintf('erro: %s', clean_msg(ME.message));
            fprintf('  [%d/%d] %s/%s x %s -> %s\n', i, height(S), ...
                S.label{i}, S.event{i}, tname, status);
            for h = opts.HorizonsSec
                rows(end+1,:) = {S.log{i}, S.label{i}, S.event{i}, ...
                    tname, h, NaN, status}; %#ok<AGROW>
            end
        end
    end
end

if isempty(rows), rows = cell(0,7); end
T = cell2table(rows, 'VariableNames', ...
    {'log','label','event','theta','horizonte_s','rmse_pos_m','status'});

% --- salvar com proveniencia (Definition of Done do CLAUDE.md) ---
stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));

if smoke
    outdir = fullfile('results','debug');
    csvname = sprintf('tabela_mestra_smoke_%s.csv', stamp);
else
    outdir = 'results';
    csvname = sprintf('tabela_mestra_%s.csv', stamp);
end
if ~isfolder(outdir), mkdir(outdir); end
outcsv = fullfile(outdir, csvname);
writetable(T, outcsv);

n_ok = sum(strcmp(T.status,'ok'));
if ~smoke
    fid = fopen(fullfile('results','CHANGELOG.md'), 'a');
    fprintf(fid, ['- %s | automation/run_all_experiments.m | commit %s | seed %d | ' ...
        'modelo %s | thetas {%s} | horizontes [%s] s | dataset %s | ' ...
        '%d/%d linhas ok | %s\n'], ...
        char(datetime('now','Format','yyyy-MM-dd HH:mm')), githash, ...
        opts.Seed, opts.ModelName, strjoin(opts.ThetaNames,','), ...
        num2str(opts.HorizonsSec), data_root, n_ok, height(T), outcsv);
    fclose(fid);
end

if opts.MakeFigure && n_ok > 0
    make_central_figure(T(strcmp(T.status,'ok'),:), outdir, stamp);
end
fprintf('OK[%s]: %d linhas (%d ok), commit %s -> %s\n', ...
    opts.Mode, height(T), n_ok, githash, outcsv);
end

% =========================================================================
function githash = get_git_hash(repo_root, failloud)
%GET_GIT_HASH Hash curto do HEAD com sufixo -dirty se a arvore estiver suja.
% Diagnostico (2026-06-11, MATLAB R2026a/Win11): git ESTA no PATH visto pelo
% MATLAB (rc=0 em 'git --version', C:\Program Files\Git\cmd) e a raiz esta
% correta via -C; rev-parse falha (rc=128, 'Needed a single revision')
% quando o repo nao tem commit inicial — unica causa observada.
[rc, h] = system(sprintf('git -C "%s" rev-parse --short HEAD', repo_root));
if rc ~= 0
    [rcv, ~] = system('git --version');
    if rcv ~= 0
        why = 'git nao encontrado no PATH visto pelo MATLAB';
    else
        why = sprintf('HEAD nao resolvivel (repo sem commit inicial?): %s', ...
            clean_msg(strtrim(h)));
    end
    if failloud
        error('run_all_experiments:semCommit', ...
            ['Sem hash de commit para proveniencia — %s. ' ...
             'Crie o commit inicial ou use ''Mode'',''smoke''.'], why);
    end
    githash = 'no-commit';
    return;
end
githash = strtrim(h);
[rcs, st] = system(sprintf('git -C "%s" status --porcelain', repo_root));
if rcs == 0 && ~isempty(strtrim(st))
    githash = [githash '-dirty'];
end
end

% =========================================================================
function msg = clean_msg(msg)
%CLEAN_MSG Remove markup de hyperlink do MATLAB/Simulink e quebras de linha.
msg = regexprep(msg, '<[^>]+>', '');
msg = strrep(msg, newline, ' ');
end

% =========================================================================
function make_central_figure(T, outdir, stamp)
%MAKE_CENTRAL_FIGURE RMSE mediano por horizonte, uma curva por theta.
thetas = unique(T.theta, 'stable');
figure('Color','w'); hold on;
for k = 1:numel(thetas)
    Tk = T(strcmp(T.theta, thetas{k}), :);
    g = groupsummary(Tk, 'horizonte_s', 'median', 'rmse_pos_m');
    plot(g.horizonte_s, g.median_rmse_pos_m, '-o', ...
        'LineWidth', 1.5, 'DisplayName', thetas{k});
end
xlabel('Horizonte de predicao (s)');
ylabel('RMSE de posicao (m) — mediana entre splits');
legend('Location','northwest'); grid on; box on;
exportgraphics(gcf, fullfile(outdir, ...
    sprintf('fig_central_%s.pdf', stamp)), 'ContentType','vector');
end
