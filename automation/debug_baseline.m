function out = debug_baseline(event_name, opts)
%DEBUG_BASELINE Overlay truth vs simulado para UM evento (debug visual).
% Roda o pipeline real (canonical_split -> run_one/run_one_mat), plota a
% trajetoria XY e x(t)/y(t) sobrepostas e salva em results/debug/.
% Reporta RMSE free-run (sem re-ancoragem) e RMSE re-ancorado (janela do
% custo real, 2.5 s / overlap 0.5).
%
% USO:
%   debug_baseline('square_01_01')                       % theta 'procest'
%   debug_baseline('square_01_01', 'Theta','ideal_v2')   % via ThetaMats

arguments
    event_name     (1,:) char
    opts.DataRoot  (1,:) char = fullfile('data','extracted')
    opts.ModelName (1,:) char = 'parameter_estimation_model_pid_v3'
    opts.Theta     (1,:) char = 'procest'
    % mesmo roteamento do orquestrador: .mat -> run_one_mat (com SE(2))
    opts.ThetaMats (1,1) struct = struct( ...
        'ideal_v2', fullfile('models','sysid_ideal_v2.mat'), ...
        'procest',  fullfile('results','sysid_initial.mat'), ...
        'bayesopt', fullfile('results','sysid_bayesopt.mat'))
    opts.WindowSec (1,1) double = 2.5
    opts.Overlap   (1,1) double = 0.5
    opts.OutDir    (1,:) char = fullfile('results','debug')
end

repo_root = bootstrap_paths();
data_root = opts.DataRoot;
if ~startsWith(data_root, repo_root)
    data_root = fullfile(repo_root, data_root);
end

S = list_splits(data_root);
S = S(strcmp(S.chunk, 'commands') & strcmp(S.event, event_name), :);
if height(S) ~= 1
    error('debug_baseline: evento "%s" casa com %d chunks commands (esperado 1).', ...
        event_name, height(S));
end

canon_path = canonical_split(S.path{1});
ensure_model_ready(opts.ModelName);
if isfield(opts.ThetaMats, opts.Theta)
    out = run_one_mat(opts.ModelName, canon_path, opts.ThetaMats.(opts.Theta));
else
    out = run_one(opts.ModelName, canon_path, opts.Theta);
end

% --- series na grade do split (posicao alinhada SE(2) se disponivel) ---
s  = out.SplitInfo;
tt = s.t;  xt = s.pos_x_truth.Data;  yt = s.pos_y_truth.Data;
[tsim, px, py] = extract_sim_position(out);
xs = interp1(tsim, px, tt, 'linear', 'extrap');
ys = interp1(tsim, py, tt, 'linear', 'extrap');
% theta simulado (alinhado se disponivel) e truth, na grade do split
candTh = ["theta_aligned","theta_out"];
nth = candTh(find(ismember(candTh, string(out.who)), 1));
pth = out.get(char(nth));
ths_t = interp1(pth.Time, squeeze(pth.Data), tt, 'linear', 'extrap');
tht   = s.theta_truth.Data;

% --- metricas ---
rmse_free = sqrt(mean((xs - xt).^2 + (ys - yt).^2));            % free-run, sem re-ancoragem
rmse_reanc = rmse_pos_rebased(tt, xs, ys, xt, yt, opts.WindowSec, opts.Overlap);
rmse_model = NaN;                                                % sinal 'rmse' do proprio modelo
if any(strcmp(out.who, 'rmse'))
    ts = out.get('rmse');
    if ~isempty(ts.Data), rmse_model = ts.Data(end); end
end
fprintf('debug_baseline %s x %s:\n', event_name, opts.Theta);
fprintf('  RMSE free-run (toda a trajetoria): %.4f m\n', rmse_free);
fprintf('  RMSE re-ancorado (janela %.1fs/overlap %.1f): %.4f m\n', ...
    opts.WindowSec, opts.Overlap, rmse_reanc);
fprintf('  Sinal ''rmse'' interno do modelo (ultimo valor): %.4f\n', rmse_model);

% --- figura overlay ---
fig = figure('Color','w', 'Position',[100 100 1000 760]);
tiledlayout(fig, 2, 2, 'Padding','compact');

nexttile; hold on;
plot(xt, yt, 'k-', 'LineWidth', 1.5, 'DisplayName','truth');
plot(xs, ys, 'r--', 'LineWidth', 1.2, 'DisplayName', ['sim ' opts.Theta]);
plot(xt(1), yt(1), 'ko', 'MarkerFaceColor','g', 'DisplayName','inicio');
axis equal; grid on; box on;
xlabel('x (m)'); ylabel('y (m)');
title(sprintf('%s — XY', event_name), 'Interpreter','none');
legend('Location','best');

nexttile; hold on;
plot(tt, xt, 'k-', tt, xs, 'r--', 'LineWidth', 1.2);
grid on; box on; xlabel('t (s)'); ylabel('x (m)'); title('x(t)');
legend({'truth', ['sim ' opts.Theta]}, 'Location','best');

nexttile; hold on;
plot(tt, yt, 'k-', tt, ys, 'r--', 'LineWidth', 1.2);
grid on; box on; xlabel('t (s)'); ylabel('y (m)'); title('y(t)');
legend({'truth', ['sim ' opts.Theta]}, 'Location','best');

nexttile; hold on;
plot(tt, tht, 'k-', tt, ths_t, 'r--', 'LineWidth', 1.2);
grid on; box on; xlabel('t (s)'); ylabel('\theta (rad)'); title('\theta(t)');
legend({'truth', ['sim ' opts.Theta]}, 'Location','best');

sgtitle(sprintf('%s x %s | free-run %.3f m | re-anc(%.1fs) %.3f m', ...
    event_name, opts.Theta, rmse_free, opts.WindowSec, rmse_reanc), ...
    'Interpreter','none');

if ~isfolder(opts.OutDir), mkdir(opts.OutDir); end
stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
figpath = fullfile(opts.OutDir, ...
    sprintf('overlay_%s_%s_%s.png', event_name, opts.Theta, stamp));
exportgraphics(fig, figpath, 'Resolution', 150);
fprintf('  Figura: %s\n', figpath);
end
