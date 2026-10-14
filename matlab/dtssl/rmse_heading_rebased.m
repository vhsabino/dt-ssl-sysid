function r = rmse_heading_rebased(t, ths, tht, win_s, overlap, filt_s)
%RMSE_HEADING_REBASED RMSE de HEADING (rad) em janelas re-ancoradas, analogo
% a rmse_pos_rebased_se2: em cada janela remove-se o offset de heading em t0
% (sim vs truth FILTRADO), e mede-se o desvio de heading no resto da janela.
% Mesma janela/passo de rmse_pos_rebased_se2. Erro envolto em (-pi,pi].
if nargin < 6, filt_s = 0.2; end
tht_f = smoothdata(tht, 'movmedian', filt_s, 'SamplePoints', t);
t0s = t(1):win_s*(1 - overlap):(t(end) - win_s);
if isempty(t0s), t0s = t(1); end
e2 = []; w = [];
for t0 = t0s
    idx = find(t >= t0 & t <= t0 + win_s);
    if numel(idx) < 2, continue; end
    i0 = idx(1);
    d = (ths(idx) - ths(i0)) - (tht_f(idx) - tht_f(i0));
    d = atan2(sin(d), cos(d));                 % wrap p/ (-pi,pi]
    e2(end+1) = mean(d.^2); %#ok<AGROW>
    w(end+1)  = numel(idx); %#ok<AGROW>
end
r = sqrt(sum(w .* e2) / sum(w));
end
