function r = rmse_pos_rebased(t, xs, ys, xt, yt, win_s, overlap)
%RMSE_POS_REBASED RMSE de posicao (m) em janelas deslizantes RE-ANCORADAS,
% mesmo esquema do custo real (matlab/sysid/compute_rmse_position.m):
% rebase a zero no inicio de cada janela, media ponderada entre janelas.
% Isto e uma metrica de pos-processamento — a simulacao em si e free-run
% (integra do IC ate o fim sem reinjecao de pose medida).
Ts = median(diff(t));
win = max(2, round(win_s / Ts));
step = max(1, round(win * (1 - overlap)));
if numel(t) < win
    win = numel(t); step = win;   % split mais curto que a janela: 1 janela
end
e2 = []; w = [];
for s0 = 1:step:(numel(t) - win + 1)
    idx = s0:(s0 + win - 1);
    dx = (xs(idx) - xs(idx(1))) - (xt(idx) - xt(idx(1)));
    dy = (ys(idx) - ys(idx(1))) - (yt(idx) - yt(idx(1)));
    e2(end+1) = mean(dx.^2 + dy.^2); %#ok<AGROW>
    w(end+1)  = numel(idx);          %#ok<AGROW>
end
r = sqrt(sum(w .* e2) / sum(w));
end
