function [GS, info] = diag_omega_gain_sign(matpath)
%DIAG_OMEGA_GAIN_SIGN Etapa A2 — assimetria de sinal do ganho de omega.
% REUSA o pool ja alinhado (heading suavizado por sgolay, defasado por Td0)
% salvo por diag_omega_gain_amplitude (U=cmd_w, Y=meas_w). NAO re-suaviza,
% NAO re-defasa. Apenas separa o sentido do comando (cmd_w>0 vs cmd_w<0) e
% reestima o ganho efetivo por faixa de |cmd_w| (robustfit meas_w ~ cmd_w)
% em cada sentido, para checar assimetria (atrito/firmware costumam tratar
% sinais diferente).
%
% USO:
%   [GS, info] = diag_omega_gain_sign();           % usa o .mat mais recente
%   [GS, info] = diag_omega_gain_sign('results\diag_omega_gain_amplitude_XXXX.mat');

arguments
    matpath (1,:) char = ''
end

repo_root = bootstrap_paths(); %#ok<NASGU>

if isempty(matpath)
    d = dir(fullfile('results','diag_omega_gain_amplitude_*.mat'));
    assert(~isempty(d), 'diag_omega_gain_sign: nenhum diag_omega_gain_amplitude_*.mat em results/.');
    [~, ix] = max([d.datenum]);
    matpath = fullfile(d(ix).folder, d(ix).name);
end
S = load(matpath);                         % U, Y, edges, info, Td0_glob
U = S.U(:);  Y = S.Y(:);  edges = S.edges;
au = abs(U);

nb = numel(edges) - 1;
signs = [+1, -1];
rows = {};
for s = 1:numel(signs)
    sg = signs(s);
    smask = (sign(U) == sg);
    for b = 1:nb
        lo = edges(b); hi = edges(b+1);
        if isinf(hi)
            sel = smask & au >= lo;
            blab = sprintf('>%.2g', lo);
        else
            sel = smask & au >= lo & au < hi;
            blab = sprintf('%.2g-%.2g', lo, hi);
        end
        ub = U(sel); yb = Y(sel);
        n  = numel(ub);
        g = NaN; se = NaN; b0 = NaN; rr = NaN;
        if n >= 10 && (max(ub)-min(ub)) > 0.01
            [bc, st] = robustfit(ub, yb);
            b0 = bc(1); g = bc(2); se = st.se(2);
        end
        rok = abs(ub) > 0.05;
        if any(rok), rr = median(yb(rok)./ub(rok), 'omitnan'); end
        rows(end+1,:) = {blab, sg, n, g, se, b0, rr, ...
            mean(abs(ub),'omitnan'), mean(abs(yb),'omitnan')}; %#ok<AGROW>
    end
end
GS = cell2table(rows, 'VariableNames', ...
    {'band','sign','n','gain','gain_se','intercept','median_ratio', ...
     'mean_abs_cmd','mean_abs_meas'});

% --- vista pareada (foco nas faixas baixas) + delta de ganho --------------
bands = unique(GS.band, 'stable');
fprintf('\n===== Etapa A2: assimetria de sinal do ganho de omega =====\n');
fprintf('Pool reusado: %s  (Td0=%.3f s, %d amostras)\n', ...
    matpath, S.Td0_glob, numel(U));
fprintf('%-9s | %6s %6s %7s | %6s %6s %7s | %8s\n', 'faixa', ...
    'g(+)','n+','rat+','g(-)','n-','rat-','dg(+--)');
for k = 1:numel(bands)
    rp = GS(strcmp(GS.band,bands{k}) & GS.sign==+1, :);
    rn = GS(strcmp(GS.band,bands{k}) & GS.sign==-1, :);
    gp = rp.gain(1); gn = rn.gain(1);
    fprintf('%-9s | %6.2f %6d %7.2f | %6.2f %6d %7.2f | %8.2f\n', ...
        bands{k}, gp, rp.n(1), rp.median_ratio(1), ...
        gn, rn.n(1), rn.median_ratio(1), gp-gn);
end
fprintf('\nObs.: g(-) e a inclinacao meas/cmd no ramo negativo (>0 = mesmo sentido).\n');

stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
csv = fullfile('results', sprintf('diag_omega_gain_by_sign_band_%s.csv', stamp));
writetable(GS, csv);
fprintf('Salvo: %s\n', csv);

info = struct('source_mat', matpath, 'Td0_global', S.Td0_glob, ...
    'n_pool', numel(U), 'edges', edges, 'stamp', stamp, ...
    'created_at', datetime('now'));
end
