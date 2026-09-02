function v = lag_filter(u, t, tau)
%LAG_FILTER 1/(tau*s+1) discretizado exato sob ZOH no comando, estado inicial nulo.
% Helper compartilhado por deadreckoning_p1d e ideal_deadreckoning (antes
% duplicado nos dois arquivos; implementacao bit-a-bit identica a original).
% Grade t possivelmente irregular: o polo discreto e recalculado por passo.
v = zeros(size(u));
for k = 2:numel(u)
    a = 1 - exp(-(t(k) - t(k-1)) / tau);
    v(k) = v(k-1) + a * (u(k-1) - v(k-1));
end
end
