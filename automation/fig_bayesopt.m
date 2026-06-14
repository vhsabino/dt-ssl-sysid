function files = fig_bayesopt(holdoutMat, boMat)
%FIG_BAYESOPT Figuras da Fase 4: (F5) RMSE SE(2) x horizonte em hold-out para
% ideal / vx-vy v2 / bayesopt; (F6) curva de convergencia J_best x avaliacoes;
% (F7) sensibilidade ARD (1/lengthscale por parametro). Sem re-simular.
arguments
    holdoutMat (1,:) char
    boMat      (1,:) char
end
bootstrap_paths();
S = load(holdoutMat);  W = S.W;  B = load(boMat);
figdir = fullfile('results','figs'); if ~isfolder(figdir), mkdir(figdir); end
stamp = char(datetime('now','Format','yyyyMMdd_HHmm'));
files = {};

% ---- F5: SE(2) x horizonte (hold-out) ----
Wh = W(~isnan(W.horizonte_s), :);  h = Wh.horizonte_s;
f1 = figure('Color','w','Position',[100 100 720 460]);
plot(h, Wh.med_ideal, '-o','LineWidth',1.8,'Color',[0.40 0.40 0.40],'MarkerFaceColor',[0.40 0.40 0.40]); hold on;
plot(h, Wh.med_vxvy,  '-s','LineWidth',1.8,'Color',[0.10 0.45 0.30],'MarkerFaceColor',[0.10 0.45 0.30]);
plot(h, Wh.med_bo,    '-d','LineWidth',2.0,'Color',[0.10 0.30 0.65],'MarkerFaceColor',[0.10 0.30 0.65]);
grid on; box on; xlabel('horizonte h (s)'); ylabel('mediana RMSE SE(2) (m)');
legend({'cinem. ideal','vx/vy v2 + \omega placeholder','\theta bayesopt'},'Location','northwest');
title(sprintf('Fidelidade SE(2) x horizonte — HOLD-OUT (%d eventos)', numel(unique(S.G.event))));
fp = fullfile(figdir, sprintf('F5_bayesopt_holdout_horizons_%s', stamp));
exportgraphics(f1,[fp '.png'],'Resolution',150); exportgraphics(f1,[fp '.pdf'],'ContentType','vector');
files{end+1} = [fp '.png'];

% ---- F6: convergencia ----
tr = B.results.ObjectiveTrace;  bestSoFar = cummin(tr);
nInit = 3;  % InitialX warm-start
f2 = figure('Color','w','Position',[100 100 720 440]);
plot(1:numel(tr), tr, '.', 'Color',[0.7 0.75 0.85], 'MarkerSize',9); hold on;
plot(1:numel(bestSoFar), bestSoFar, '-','LineWidth',2,'Color',[0.10 0.30 0.65]);
xline(nInit+0.5, ':', 'fim warm-start', 'Color',[0.5 0.5 0.5]);
yline(min(tr), '--', sprintf('J_{best}=%.4f', min(tr)), 'Color',[0.1 0.5 0.2]);
grid on; box on; xlabel('avaliacao'); ylabel('J = SE(2) + \lambda\cdotRMSE_{heading}');
legend({'J observado','J_{best} (cummin)'}, 'Location','northeast');
title('Convergencia bayesopt (9 parametros)');
fp = fullfile(figdir, sprintf('F6_bayesopt_convergence_%s', stamp));
exportgraphics(f2,[fp '.png'],'Resolution',150); exportgraphics(f2,[fp '.pdf'],'ContentType','vector');
files{end+1} = [fp '.png'];

% ---- F7: sensibilidade ARD ----
if isfield(B,'ard') && all(isfinite(B.ard.sensitivity))
    f3 = figure('Color','w','Position',[100 100 760 420]);
    sens = B.ard.sensitivity / max(B.ard.sensitivity);
    bar(categorical(B.ard.names, B.ard.names), sens, 'FaceColor',[0.20 0.40 0.70]);
    ylabel('sensibilidade relativa (1/lengthscale ARD)'); grid on;
    title('Sensibilidade do custo por parametro (GP ARD)');
    fp = fullfile(figdir, sprintf('F7_bayesopt_ard_%s', stamp));
    exportgraphics(f3,[fp '.png'],'Resolution',150); exportgraphics(f3,[fp '.pdf'],'ContentType','vector');
    files{end+1} = [fp '.png'];
end
fprintf('Figuras salvas:\n'); fprintf('  %s\n', files{:});
end
