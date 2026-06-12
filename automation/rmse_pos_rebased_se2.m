function r = rmse_pos_rebased_se2(t, xs, ys, ths, xt, yt, tht, win_s, overlap, filt_s)
%RMSE_POS_REBASED_SE2 RMSE de posicao (m) em janelas RE-ANCORADAS em POSE
% COMPLETA: no inicio de cada janela aplica-se a transformacao rigida SE(2)
% que leva a pose simulada (x,y,theta) em t0 na pose truth em t0; o erro de
% posicao e medido no resto da janela ja sob esse alinhamento. Mesma
% janela/passo/pesos de rmse_pos_rebased (que re-ancora so a translacao,
% i.e. e o caso particular dth=0). Teste H-a do diagnostico de deriva de
% heading: se a diferenca entre as duas metricas for grande, o erro de
% posicao re-ancorado em translacao e dominado pelo erro de heading
% acumulado ate t0, nao pela dinamica dentro da janela.
%
% Janelas definidas POR TEMPO (fix 2026-06-11), identico a rmse_pos_rebased
% — ver comentario la e results/grid_audit_20260611_2231.csv.
%
% Ancora com theta truth FILTRADO (fix 2026-06-11b): o heading da visao e
% ruidoso amostra-a-amostra e um outlier exatamente em t0 contamina a
% rotacao da janela inteira (ex.: shoot_to_goal_12_01, se2 0.955 >
% trans 0.566 no ideal_analytic). dth usa mediana movel de tht em janela
% de filt_s segundos (default 0.2 s, grade irregular via SamplePoints);
% o erro de posicao continua contra xt/yt crus.
if nargin < 10, filt_s = 0.2; end
tht_f = smoothdata(tht, 'movmedian', filt_s, 'SamplePoints', t);
t0s = t(1):win_s*(1 - overlap):(t(end) - win_s);
if isempty(t0s), t0s = t(1); end   % split mais curto que a janela: 1 janela
e2 = []; w = [];
for t0 = t0s
    idx = find(t >= t0 & t <= t0 + win_s);
    if numel(idx) < 2, continue; end
    i0 = idx(1);
    dth = tht_f(i0) - ths(i0);
    c = cos(dth);  sn = sin(dth);
    xa = c*(xs(idx) - xs(i0)) - sn*(ys(idx) - ys(i0)) + xt(i0);
    ya = sn*(xs(idx) - xs(i0)) + c*(ys(idx) - ys(i0)) + yt(i0);
    e2(end+1) = mean((xa - xt(idx)).^2 + (ya - yt(idx)).^2); %#ok<AGROW>
    w(end+1)  = numel(idx);                                  %#ok<AGROW>
end
r = sqrt(sum(w .* e2) / sum(w));
end
