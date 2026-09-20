function [theta_w, report] = identify_omega_from_splits(opts)
%IDENTIFY_OMEGA_FROM_SPLITS Identificacao do DOF omega a partir dos splits.
% Seleciona eventos com excitacao suficiente (check_excitation), monta
% iddata multi-experimento (u = move_w; y = omega medido, derivada sgolay
% de unwrap(position_w) na grade Ts=1/60 — mesmo processamento de
% build_idData_per_dof/buildTheta, porem no evento inteiro), estima
% G_w(s) = K/(tau s+1) e^{-Td s} via procest('P1D') com InputDelay inicial
% = mediana dos Td0_s (xcorr) do treino, e valida em hold-out.
%
% Criterios de aceite (CLAUDE.md): fit_val >= 60%, K_w in [0.5,2.0],
% tau_w in [0.02,0.5] s, Td_w <= 0.15 s. O resultado e salvo como
% CANDIDATO (models/sysid_initial_v2_candidate.mat) — promocao a
% sysid_initial_v2.mat so apos revisao humana.

arguments
    opts.Label        (1,:) char   = 'shoot_to_goal'
    opts.MinActiveSec (1,1) double = 1.0    % w_ativo_s >= 1 s
    opts.MinStdW      (1,1) double = 0.7    % std_move_w >= 0.7 rad/s
    opts.NHoldout     (1,1) double = 5
    opts.Ts           (1,1) double = 1/60
    opts.Team         (1,:) char   = 'allies'
    opts.Seed         (1,1) double = 42
    opts.TdMax        (1,1) double = 0.15   % criterio de aceite
    opts.SaveCandidate (1,1) logical = true
end

repo_root = bootstrap_paths();
rng(opts.Seed);

% --- 1) selecao de eventos por excitacao ---
E = check_excitation(opts.Label);
q = E(E.w_ativo_s >= opts.MinActiveSec & E.std_move_w >= opts.MinStdW, :);
fprintf('\nEventos qualificados (w_ativo>=%.1fs, std>=%.2f): %d de %d\n', ...
    opts.MinActiveSec, opts.MinStdW, height(q), height(E));
if height(q) < 4
    error('identify_omega_from_splits: so %d eventos qualificados — sem dados para treino+validacao.', height(q));
end

nho = min(opts.NHoldout, height(q) - 3);   % garante >=3 eventos de treino
idx = randperm(height(q));
ival = sort(idx(1:nho));  itr = sort(idx(nho+1:end));
fprintf('Treino: %d eventos | Hold-out: %d eventos {%s}\n', numel(itr), ...
    numel(ival), strjoin(q.event(ival), ', '));

% --- 2) iddata por evento ---
mk = @(i) build_omega_iddata(repo_root, q.log{i}, q.label{i}, q.event{i}, ...
                             opts.Ts, opts.Team);
dtr = cellfun(mk, num2cell(itr),  'UniformOutput', false);
dvl = cellfun(mk, num2cell(ival), 'UniformOutput', false);
dtr = dtr(~cellfun('isempty', dtr));  dvl = dvl(~cellfun('isempty', dvl));
dtrain = merge(dtr{:});  dval = merge(dvl{:});

% --- 3) estimacao P1D com Td inicial = mediana dos Td0 do treino ---
Td0 = median(q.Td0_s(itr), 'omitnan');
if isnan(Td0), Td0 = 0.05; end
init = idproc('P1D');
init.Structure.Kp.Value  = 1;
init.Structure.Tp1.Value = 0.1;
init.Structure.Td.Value    = min(Td0, opts.TdMax);
init.Structure.Td.Maximum  = opts.TdMax;
init.Structure.Td.Minimum  = 0;
fprintf('Td inicial (mediana xcorr treino): %.4f s\n', Td0);
m = procest(dtrain, init);

% --- 4) validacao em hold-out ---
[~, fit_val] = compare(dval, m);
fit_val = fit_as_vector(fit_val);
[~, fit_tr] = compare(dtrain, m);
fit_tr = fit_as_vector(fit_tr);

theta_w = struct('K_w', m.Kp, 'tau_w', m.Tp1, 'Td_w', m.Td);

% --- 5) criterios de aceite (CLAUDE.md) ---
ok = struct( ...
    'fit_val', mean(fit_val,'omitnan') >= 60, ...
    'K_w',     theta_w.K_w  >= 0.5  && theta_w.K_w  <= 2.0, ...
    'tau_w',   theta_w.tau_w >= 0.02 && theta_w.tau_w <= 0.5, ...
    'Td_w',    theta_w.Td_w  <= opts.TdMax);
fprintf('\n===== RESULTADO omega =====\n');
fprintf('theta_w: K=%.4f tau=%.4f Td=%.4f\n', theta_w.K_w, theta_w.tau_w, theta_w.Td_w);
fprintf('fit treino (mediana): %.1f%% | fit VALIDACAO (media): %.1f%% (por evento: %s)\n', ...
    median(fit_tr,'omitnan'), mean(fit_val,'omitnan'), mat2str(round(fit_val(:).',1)));
crit = fieldnames(ok);
for k = 1:numel(crit)
    fprintf('  %-8s: %s\n', crit{k}, string(ok.(crit{k})));
end
aprovado = all(structfun(@(x) x, ok));
fprintf('APROVADO nos criterios? %s\n', string(aprovado));

% --- 6) salvar candidato (nunca sobrescrever; promocao manual) ---
report = struct('label', opts.Label, 'events_train', {q.event(itr)}, ...
    'events_holdout', {q.event(ival)}, 'fit_train', fit_tr, ...
    'fit_val', fit_val, 'Td0_xcorr', Td0, 'opts', opts, ...
    'criterios_ok', ok, 'aprovado', aprovado, ...
    'commit', strtrim(evalc('system(''git rev-parse --short HEAD'');')), ...
    'created_at', datetime('now'));
if opts.SaveCandidate
    outmat = fullfile('models','sysid_initial_v2_candidate.mat');
    assert(~isfile(outmat), '%s ja existe — nao sobrescrever.', outmat);
    % theta completo: vx/vy do sysid_initial atual + omega novo
    theta0 = load_theta_mat(fullfile('models','sysid_initial.mat'));
    theta0.K_w = theta_w.K_w;  theta0.tau_w = theta_w.tau_w;
    theta0.Td_w = theta_w.Td_w;
    model_w = m;
    save(outmat, 'theta0', 'theta_w', 'model_w', 'report');
    fprintf('Candidato salvo: %s (promocao so apos revisao)\n', outmat);
end
end

% =========================================================================
function f = fit_as_vector(f)
% compare() devolve cell (1 por experimento) em iddata multi-experimento.
if iscell(f), f = cellfun(@(x) x(1), f); end
f = double(f(:));
end

% =========================================================================
function d = build_omega_iddata(repo_root, log_, label_, event_, Ts, team)
%BUILD_OMEGA_IDDATA u = move_w (ZOH), y = d/dt unwrap(position_w) (sgolay),
% grade uniforme Ts na intersecao temporal, detrend por experimento
% (igual build_idData_per_dof).
ev_dir = fullfile(repo_root, 'data','extracted', log_, 'splits', label_, event_);
C = parquetread(fullfile(ev_dir, 'commands.parquet'));
rid = mode(double(C.robot_id));
C = C(double(C.robot_id) == rid, :);
R = parquetread(fullfile(ev_dir, 'processed_robots.parquet'));
R = R(strcmp(R.team, team) & double(R.robot_id) == rid, :);
d = [];
if height(C) < 30 || height(R) < 30, return; end
t0 = max(C.timestamp_event(1), R.timestamp_event(1));
t1 = min(C.timestamp_event(end), R.timestamp_event(end));
tg = (t0:Ts:t1)';
if numel(tg) < 30, return; end
uw = interp1(C.timestamp_event, C.move_w, tg, 'previous', 0);
pw = interp1(R.timestamp_event, unwrap(R.position_w), tg, 'linear');
yw = [0; diff(pw)] / Ts;
if numel(yw) > 7, yw = smoothdata(yw, 'sgolay', 5); end
mask = ~isnan(uw) & ~isnan(yw);
uw = uw(mask); yw = yw(mask);
if numel(uw) < 30, return; end
uw = uw - mean(uw);  yw = yw - mean(yw);   % detrend, como o pipeline
d = iddata(yw, uw, Ts);
d.ExperimentName = event_;
end
