function [theta_w, R] = identify_omega_v3_linear(opts)
%IDENTIFY_OMEGA_V3_LINEAR Etapa C — bloco LINEAR de omega no regime de alta
% amplitude (a parte que os dados de malha fechada PERMITEM identificar).
%
% Motivacao (Etapas A/A2/B): o ganho rotacional e plano ~1.35 acima de
% |cmd_w|~0.3 rad/s e a zona morta e POR RODA no firmware (1.567 rad/s de
% roda, PID_Controller.cpp:94) — invisivel no omega de corpo sob translacao.
% Logo identifica-se SO o linear K_w,tau_w,Td_w no regime alto; a largura da
% zona morta d NAO se ajusta nestes dados (seria ajuste de ruido).
%
% Metodo: procest('P1D') sobre segmentos contiguos com |cmd_w| > Thr
% (com pre/pos-roll p/ conter os transientes de subida/descida que
% identificam tau e Td), multi-experimento, hold-out por evento
% (9 treino / 5 validacao, seed 42 — mesmos eventos qualificados de
% identify_omega_from_splits). y = d/dt do heading suavizado por
% Savitzky-Golay (mesmo processamento da Etapa A). SEM detrend (ancora o
% ganho pelo degrau de onset).
%
% Valida (criterios novos do §6): (i) Ljung-Box nos residuos do regime alto;
% (ii) parametros em faixa fisica; (iv) fit por regime (alto vs baixo).
% O criterio (iii) — custo SE(2) multi-horizonte vs placeholder com Wilcoxon
% — roda em eval_omega_v3_se2 (precisa do Simulink) e e anexado depois.
%
% NAO promove; NAO ajusta d. Retorna theta_w e R (report).

arguments
    opts.Label      (1,:) char   = 'shoot_to_goal'
    opts.Thr        (1,1) double = 0.3    % joelho de |cmd_w| (rad/s) — Etapa A
    opts.PadS       (1,1) double = 0.20   % pre/pos-roll por segmento (s)
    opts.MinCoreS   (1,1) double = 0.25   % duracao minima do nucleo > Thr (s)
    opts.GapMergeS  (1,1) double = 0.10   % funde nucleos separados por < isso (s)
    opts.Ts         (1,1) double = 1/60
    opts.Team       (1,:) char   = 'allies'
    opts.SgWin      (1,1) double = 7
    opts.SgOrder    (1,1) double = 2
    opts.NHoldout   (1,1) double = 5
    opts.Seed       (1,1) double = 42
    opts.MinActiveSec (1,1) double = 1.0  % qualificacao (= identify_omega_from_splits)
    opts.MinStdW      (1,1) double = 0.7
    opts.TdInit     (1,1) double = 0.14   % init InputDelay (mediana xcorr, Etapa A)
    opts.TdMax      (1,1) double = 0.15
    opts.SaveTmp    (1,1) logical = true  % cache build/ p/ a etapa (iii) Simulink
end

repo_root = bootstrap_paths();
rng(opts.Seed);

% --- 1) eventos qualificados (mesmos da ID anterior, p/ comparabilidade) ---
E = check_excitation(opts.Label);
q = E(E.w_ativo_s >= opts.MinActiveSec & E.std_move_w >= opts.MinStdW, :);
fprintf('\nQualificados (w_ativo>=%.1fs, std>=%.2f): %d de %d eventos\n', ...
    opts.MinActiveSec, opts.MinStdW, height(q), height(E));
nho = min(opts.NHoldout, height(q) - 3);
idx = randperm(height(q));
ival = sort(idx(1:nho));  itr = sort(idx(nho+1:end));
fprintf('Treino: %d | Hold-out: %d {%s}\n', numel(itr), numel(ival), ...
    strjoin(q.event(ival), ', '));

% --- 2) processa eventos: grade Ts, u=cmd_w, y=d/dt(heading sgolay) ---------
EV = struct('event',{},'u',{},'y',{},'t',{},'hi',{},'lo',{});
for i = 1:height(q)
    [u, y, tt] = load_uy(repo_root, q.log{i}, q.label{i}, q.event{i}, ...
        opts.Ts, opts.Team, opts.SgWin, opts.SgOrder);
    if isempty(u), continue; end
    hi = highamp_segments(abs(u), opts.Thr, round(opts.PadS/opts.Ts), ...
        round(opts.MinCoreS/opts.Ts), round(opts.GapMergeS/opts.Ts));
    lo = lowamp_segments(abs(u), opts.Thr, round(opts.MinCoreS/opts.Ts));
    EV(end+1) = struct('event',q.event{i},'u',u,'y',y,'t',tt,'hi',{hi},'lo',{lo}); %#ok<AGROW>
end
qev = string({EV.event});
itr2 = find(ismember(qev, string(q.event(itr))));
iva2 = find(ismember(qev, string(q.event(ival))));

% --- 3) iddata multi-experimento dos segmentos ALTOS (sem detrend) ---------
dtr = segs_to_iddata(EV(itr2), 'hi', opts.Ts);
dvl = segs_to_iddata(EV(iva2), 'hi', opts.Ts);
fprintf('Segmentos altos: treino=%d exp (%.1f s) | val=%d exp (%.1f s)\n', ...
    size(dtr,'Ne'), sum(size(dtr,'N'))*opts.Ts, ...
    size(dvl,'Ne'), sum(size(dvl,'N'))*opts.Ts);

% --- 4) procest('P1D') -----------------------------------------------------
init = idproc('P1D');
init.Structure.Kp.Value  = 1.35;     % chute pela Etapa A
init.Structure.Tp1.Value = 0.08;
init.Structure.Td.Value   = min(opts.TdInit, opts.TdMax);
init.Structure.Td.Minimum = 0;
init.Structure.Td.Maximum = opts.TdMax;
m = procest(dtr, init);
theta_w = struct('K_w', m.Kp, 'tau_w', m.Tp1, 'Td_w', m.Td);

[~, fit_tr] = compare(dtr, m);  fit_tr = fitvec(fit_tr);
[~, fit_vl] = compare(dvl, m);  fit_vl = fitvec(fit_vl);

% --- 5) criterio (i): Ljung-Box nos residuos do regime alto ----------------
res = resid(dtr, m);                         % iddata de residuos (1 saida)
e = cell2mat(res.OutputData(:));             % pool dos residuos
e = e(~isnan(e));
nlags = 20;
[hLB, pLB, statLB, cLB] = lbqtest(e, 'Lags', nlags);

% --- 6) criterio (ii): faixa fisica ---------------------------------------
phys = struct( ...
    'K_w',   theta_w.K_w  >= 0.5  && theta_w.K_w  <= 2.0, ...
    'tau_w', theta_w.tau_w >= 0.02 && theta_w.tau_w <= 0.5, ...
    'Td_w',  theta_w.Td_w  >= 0    && theta_w.Td_w  <= opts.TdMax);

% --- 7) criterio (iv): fit por regime (alto vs baixo), por evento ----------
fit_hi = nan(numel(EV),1);  fit_lo = nan(numel(EV),1);
for k = 1:numel(EV)
    dh = segs_to_iddata(EV(k), 'hi', opts.Ts);
    dl = segs_to_iddata(EV(k), 'lo', opts.Ts);
    if ~isempty(dh) && size(dh,'Ne') >= 1, [~,f]=compare(dh,m); fit_hi(k)=mean(fitvec(f),'omitnan'); end
    if ~isempty(dl) && size(dl,'Ne') >= 1, [~,f]=compare(dl,m); fit_lo(k)=mean(fitvec(f),'omitnan'); end
end

% --- relatorio -------------------------------------------------------------
fprintf('\n===== Etapa C: omega LINEAR (regime alto) =====\n');
fprintf('theta_w: K=%.4f  tau=%.4f s  Td=%.4f s\n', ...
    theta_w.K_w, theta_w.tau_w, theta_w.Td_w);
fprintf('fit treino (mediana) %.1f%% | fit VAL (media) %.1f%% [%s]\n', ...
    median(fit_tr,'omitnan'), mean(fit_vl,'omitnan'), mat2str(round(fit_vl(:).',1)));
fprintf('(i)  Ljung-Box L=%d: h=%d p=%.3g stat=%.1f (crit %.1f) -> %s\n', ...
    nlags, hLB, pLB, statLB, cLB, ternary(hLB==0,'residuo branco','autocorrelacao'));
fprintf('(ii) faixa fisica: K %s | tau %s | Td %s\n', ...
    tf(phys.K_w), tf(phys.tau_w), tf(phys.Td_w));
fprintf('(iv) fit por regime: alto mediana %.1f%% (n=%d) | baixo mediana %.1f%% (n=%d)\n', ...
    median(fit_hi,'omitnan'), nnz(~isnan(fit_hi)), ...
    median(fit_lo,'omitnan'), nnz(~isnan(fit_lo)));

% D9 (2026-07-24): R/r=3.3208 (0.0880/0.0265) sem rastreabilidade, refutada
% por CAD + firmware/telemetria + K_w medido; fonte unica agora e
% config/robot_geometry.json (results/CHANGELOG.md 2026-07-24). d_body vira
% INTERVALO (nunca ponto).
geom = jsondecode(fileread(fullfile(repo_root,'config','robot_geometry.json')));
d_wheel_rad_s = geom.firmware.motor_min_speed_rad_s;
d_body_range_rad_s = geom.firmware.omega_cmd_deadzone_rad_s_range(:).';

R = struct('theta_w',theta_w,'model_w',m, ...
    'events_train',{q.event(itr)},'events_holdout',{q.event(ival)}, ...
    'fit_train',fit_tr,'fit_val',fit_vl, ...
    'ljungbox',struct('lags',nlags,'h',hLB,'p',pLB,'stat',statLB,'crit',cLB), ...
    'phys',phys,'fit_hi',fit_hi,'fit_lo',fit_lo, ...
    'fit_hi_med',median(fit_hi,'omitnan'),'fit_lo_med',median(fit_lo,'omitnan'), ...
    'opts',opts,'seed',opts.Seed, ...
    'deadzone_firmware',struct('d_wheel_rad_s',d_wheel_rad_s,'d_body_purerot_rad_s_range', ...
        d_body_range_rad_s,'applied','per-wheel (firmware PID_Controller.cpp:94)', ...
        'model_active_d',0,'rationale',['per-roda; aplicar no omega de corpo ' ...
        'corromperia eventos com translacao. Default 0 ate coleta de rotacao pura. ' ...
        'D9: d_body_purerot_rad_s_range = intervalo [CAD, firmware-implicito], ' ...
        'nunca valor pontual (ver config/robot_geometry.json).']), ...
    'commit',strtrim(evalc('!git rev-parse --short HEAD')),'created_at',datetime('now'));

% --- cache temporario p/ a etapa (iii) Simulink (build/, reconstruivel) ----
if opts.SaveTmp
    theta0 = load_theta_mat(fullfile('models','sysid_initial.mat'));
    theta0.K_w = theta_w.K_w; theta0.tau_w = theta_w.tau_w; theta0.Td_w = theta_w.Td_w;
    if ~isfolder('build'), mkdir('build'); end
    save(fullfile('build','sysid_omega_v3_linear_tmp.mat'), 'theta0', 'theta_w', 'm', 'R');
    fprintf('Cache p/ eval (iii): build/sysid_omega_v3_linear_tmp.mat\n');
end
end

% =========================================================================
function [u, y, t] = load_uy(repo_root, log_, label_, event_, Ts, team, sgw, sgo)
%LOAD_UY u=cmd_w (ZOH) e y=d/dt(heading sgolay) na grade Ts (= Etapa A).
ev_dir = fullfile(repo_root,'data','extracted',log_,'splits',label_,event_);
C = parquetread(fullfile(ev_dir,'commands.parquet'));
rid = mode(double(C.robot_id)); C = C(double(C.robot_id)==rid,:);
R = parquetread(fullfile(ev_dir,'processed_robots.parquet'));
R = R(strcmp(R.team,team) & double(R.robot_id)==rid,:);
u=[]; y=[]; t=[];
if height(C)<30 || height(R)<30, return; end
t0=max(C.timestamp_event(1),R.timestamp_event(1));
t1=min(C.timestamp_event(end),R.timestamp_event(end));
t=(t0:Ts:t1)';
if numel(t)<30, t=[]; return; end
u = interp1(C.timestamp_event, C.move_w, t, 'previous', 0);
pw= interp1(R.timestamp_event, unwrap(R.position_w), t, 'linear');
win = min(sgw, 2*floor((numel(pw)-1)/2)+1);
if win>sgo, pw = sgolayfilt(pw, sgo, win); end
y = gradient(pw)/Ts;
m = ~isnan(u) & ~isnan(y); u=u(m); y=y(m); t=t(m);
end

% =========================================================================
function segs = highamp_segments(au, thr, pad_n, mincore_n, gap_n)
%HIGHAMP_SEGMENTS nucleos contiguos |u|>thr (>= mincore_n), fundidos se
% separados por < gap_n, expandidos por pad_n p/ conter os transientes.
m = au(:) > thr;
d = diff([false; m; false]);
s = find(d==1); e = find(d==-1)-1;
keep = (e-s+1) >= mincore_n;  s=s(keep); e=e(keep);
segs = {};
if isempty(s), return; end
cs=s(1); ce=e(1);
for k=2:numel(s)
    if s(k)-ce-1 <= gap_n, ce=e(k); else, segs{end+1}=[cs ce]; cs=s(k); ce=e(k); end %#ok<AGROW>
end
segs{end+1}=[cs ce];
N=numel(au);
for k=1:numel(segs)
    segs{k}=[max(1,segs{k}(1)-pad_n), min(N,segs{k}(2)+pad_n)];
end
end

% =========================================================================
function segs = lowamp_segments(au, thr, mincore_n)
%LOWAMP_SEGMENTS nucleos contiguos |u|<thr (>= mincore_n), sem pad.
m = au(:) < thr;
d = diff([false; m; false]);
s = find(d==1); e = find(d==-1)-1;
keep = (e-s+1) >= mincore_n;  s=s(keep); e=e(keep);
segs = arrayfun(@(a,b)[a b], s, e, 'UniformOutput', false);
end

% =========================================================================
function d = segs_to_iddata(EVset, field, Ts)
%SEGS_TO_IDDATA monta iddata multi-exp dos segmentos (SEM detrend).
ys={}; us={};
for k=1:numel(EVset)
    segk = EVset(k).(field);
    for j=1:numel(segk)
        r = segk{j}(1):segk{j}(2);
        if numel(r) < 5, continue; end
        ys{end+1}=EVset(k).y(r); us{end+1}=EVset(k).u(r); %#ok<AGROW>
    end
end
if isempty(ys), d=[]; return; end
d = iddata(ys, us, Ts);
end

% =========================================================================
function f = fitvec(f), if iscell(f), f=cellfun(@(x)x(1),f); end, f=double(f(:)); end
function s = tf(b), if b, s='OK'; else, s='FORA'; end, end
function s = ternary(c,a,b), if c, s=a; else, s=b; end, end
