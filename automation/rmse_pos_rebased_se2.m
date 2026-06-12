function r = rmse_pos_rebased_se2(t, xs, ys, ths, xt, yt, tht, win_s, overlap)
%RMSE_POS_REBASED_SE2 RMSE de posicao (m) em janelas RE-ANCORADAS em POSE
% COMPLETA: no inicio de cada janela aplica-se a transformacao rigida SE(2)
% que leva a pose simulada (x,y,theta) em t0 na pose truth em t0; o erro de
% posicao e medido no resto da janela ja sob esse alinhamento. Mesma
% janela/passo/pesos de rmse_pos_rebased (que re-ancora so a translacao,
% i.e. e o caso particular dth=0). Teste H-a do diagnostico de deriva de
% heading: se a diferenca entre as duas metricas for grande, o erro de
% posicao re-ancorado em translacao e dominado pelo erro de heading
% acumulado ate t0, nao pela dinamica dentro da janela.
Ts = median(diff(t));
win = max(2, round(win_s / Ts));
step = max(1, round(win * (1 - overlap)));
if numel(t) < win
    win = numel(t); step = win;   % split mais curto que a janela: 1 janela
end
e2 = []; w = [];
for s0 = 1:step:(numel(t) - win + 1)
    idx = s0:(s0 + win - 1);
    i0 = idx(1);
    dth = tht(i0) - ths(i0);
    c = cos(dth);  sn = sin(dth);
    xa = c*(xs(idx) - xs(i0)) - sn*(ys(idx) - ys(i0)) + xt(i0);
    ya = sn*(xs(idx) - xs(i0)) + c*(ys(idx) - ys(i0)) + yt(i0);
    e2(end+1) = mean((xa - xt(idx)).^2 + (ya - yt(idx)).^2); %#ok<AGROW>
    w(end+1)  = numel(idx);                                  %#ok<AGROW>
end
r = sqrt(sum(w .* e2) / sum(w));
end
