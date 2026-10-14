function u = series_on_grid(ts, t)
%SERIES_ON_GRID Amostra uma timeseries na grade t do split (ZOH, coluna).
% Helper compartilhado por deadreckoning_p1d e ideal_deadreckoning (antes
% duplicado nos dois arquivos; implementacao bit-a-bit identica a original).
% load_split constroi as timeseries na propria grade do split; o interp1
% 'previous' (ZOH) cobre o caso geral sem alterar o caso identico.
if numel(ts.Time) == numel(t) && all(ts.Time == t)
    u = ts.Data;
else
    u = interp1(ts.Time, ts.Data, t, 'previous', 0);
end
u = u(:);
end
