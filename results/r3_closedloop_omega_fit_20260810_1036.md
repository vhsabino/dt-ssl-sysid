# R3 - fit hold-out do ajuste de omega em MALHA FECHADA - 20260810_1036

Mesmo criterio da linha open-loop (Eq. 2 do artigo): split event-wise, media
sobre os eventos de hold-out. Fecha a lacuna que deixava a linha closed-loop
sem um numero comparavel (objecao C5 da 1a revisao independente).

- Eventos `shoot_to_goal` usados: 18 (12 treino / 6 hold-out)
- Parametros: K = 1.3775, tau = 0.0430 s, Td = 0.1117 s
- **fit hold-out = 44.8 %** (por evento: 26.4, 46.8, 45.7, 60.3, 51.4, 38.0)
- fit treino (mediana) = 52.6 %

Comparacao direta, agora sob o MESMO criterio:

| regime | K | tau (s) | Td (s) | fit hold-out |
|---|---|---|---|---|
| closed-loop (competicao) | 1.378 | 0.0430 | 0.1117 | **44.8 %** |
| open-loop (dedicado) | 1.002 | 0.0828 | 0.0890 | **71.1 %** |

Gate pre-registrado: fit hold-out >= 60 %.