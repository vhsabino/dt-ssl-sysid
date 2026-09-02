function [J, info] = bo_cost_proxy(theta, cache, opts)
%BO_COST_PROXY Custo de fidelidade COMPORTAMENTAL — PROXY ANALITICO barato.
% Identico em FORMULA a bo_cost (Cenario B), porem a trajetoria do gemeo vem do
% integrador analitico dead-reckoning P1D (deadreckoning_p1d), nao do Simulink:
%
%   J = mediana_eventos[ wmean_h( RMSE_pos_SE2(h) ) ]
%       + lambda * mediana_eventos[ wmean_h( RMSE_heading(h) ) ]
%
% h in {0.5,1,2,2.5,4} s, peso por horizonte w_h ∝ 1/h (normalizado), ancora
% SE(2) com theta truth filtrado (rmse_pos_rebased_se2 / rmse_heading_rebased)
% — exatamente os mesmos avaliadores de metrica de bo_cost.
%
% Custo ~1.6 ms/evento (vs ~9.5 s/sim no Simulink) -> habilita treino amplo no
% LOOP do bayesopt. NAO escreve o SLDD (theta entra direto na cadeia analitica).
% Determinístico. A validade do RANKING (nao do valor absoluto) e atestada na
% Fase 0 (phase0_proxy_ranking): o caveat documentado e que o proxy diverge
% ~0.2 m do Simulink em theta nao-ideal, mas preserva a ORDEM dos candidatos.

arguments
    theta (1,9) double
    cache (1,:) struct
    opts.Lambda   (1,1) double = 0
    opts.Horizons (1,:) double = [0.5 1 2 2.5 4]
    opts.Overlap  (1,1) double = 0.5
    opts.FiltS    (1,1) double = 0.2
end

th = vec2theta(theta);
H = opts.Horizons;  wts = (1./H) / sum(1./H);
ne = numel(cache);
pos_e = nan(ne,1);  head_e = nan(ne,1);
SE2 = nan(ne, numel(H));  HEAD = nan(ne, numel(H));
for i = 1:ne
    s = cache(i).s;
    [xs, ys, ths] = deadreckoning_p1d(s, th);
    for k = 1:numel(H)
        SE2(i,k)  = rmse_pos_rebased_se2(cache(i).t, xs, ys, ths, ...
            cache(i).xt, cache(i).yt, cache(i).tht, H(k), opts.Overlap, opts.FiltS);
        HEAD(i,k) = rmse_heading_rebased(cache(i).t, ths, cache(i).tht, ...
            H(k), opts.Overlap, opts.FiltS);
    end
    pos_e(i)  = wts * SE2(i,:).';
    head_e(i) = wts * HEAD(i,:).';
end
J_pos  = median(pos_e, 'omitnan');
J_head = median(head_e, 'omitnan');
J = J_pos + opts.Lambda * J_head;

info = struct('J',J,'J_pos',J_pos,'J_head',J_head,'lambda',opts.Lambda, ...
    'pos_e',pos_e,'head_e',head_e,'SE2',SE2,'HEAD',HEAD, ...
    'horizons',H,'weights',wts,'events',{ {cache.event} }, ...
    'se2_med_h', median(SE2,1,'omitnan'), 'head_med_h', median(HEAD,1,'omitnan'));
end

% =========================================================================
function th = vec2theta(v)
% Vetor de 9 (ordem fixa do SLDD) -> struct nomeado p/ deadreckoning_p1d.
NAMES = {'K_vx','tau_vx','Td_vx','K_vy','tau_vy','Td_vy','K_w','tau_w','Td_w'};
th = cell2struct(num2cell(v(:).'), NAMES, 2);
end
