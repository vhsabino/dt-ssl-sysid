# Leave-one-event-out por DOF translacional - 20260810_1742

Refit completo a cada dobra, mantendo a estrutura P1D e a metrica Eq.(2).
NAO altera o modelo promovido em config/twin_params.json -- e analise de
dispersao, nao re-identificacao. Responde a objecao recorrente de que o fit
de vx repousa sobre UM unico evento de hold-out.

## vx (`front_to_back`, 4 eventos, 4 dobras)

| evento retido | fit (%) | K | tau (s) | Td (s) |
|---|---|---|---|---|
| front_to_back_01_01 | 74.2 | 1073.561 | -42.1536 | -27.7998 |
| front_to_back_01_02 | 74.4 | 1072.240 | -42.0925 | -27.7623 |
| front_to_back_01_03 | 71.2 | 1082.910 | -42.5203 | -28.0453 |
| front_to_back_01_04 | 69.6 | 1081.618 | -42.4696 | -28.0114 |

- fit medio **72.4 %**, desvio **2.4 p.p.**, faixa 69.6-74.4 %
- K medio 1077.582, desvio 5.458 (promovido: 1.119)

## vy (`side_to_side`, 13 eventos, 13 dobras)

| evento retido | fit (%) | K | tau (s) | Td (s) |
|---|---|---|---|---|
| side_to_side_01_01 | 66.5 | 1001.024 | -39.2742 | -25.9126 |
| side_to_side_01_02 | 67.7 | 1001.561 | -39.2960 | -25.9267 |
| side_to_side_01_03 | 66.0 | 1002.354 | -39.3284 | -25.9454 |
| side_to_side_01_04 | 66.7 | 1001.561 | -39.2960 | -25.9267 |
| side_to_side_01_05 | 67.3 | 1004.008 | -39.3928 | -25.9877 |
| side_to_side_01_06 | 67.1 | 996.133 | -39.0823 | -25.7848 |
| side_to_side_01_07 | 72.4 | 994.247 | -39.0076 | -25.7360 |
| side_to_side_01_08 | 74.2 | 995.048 | -39.0394 | -25.7566 |
| side_to_side_02_01 | 73.6 | 994.951 | -39.0356 | -25.7541 |
| side_to_side_02_02 | 77.9 | 994.526 | -39.0188 | -25.7431 |
| side_to_side_02_03 | 74.2 | 994.877 | -39.0326 | -25.7522 |
| side_to_side_02_04 | 74.6 | 995.127 | -39.0425 | -25.7587 |
| side_to_side_02_05 | 76.4 | 995.012 | -39.0379 | -25.7557 |

- fit medio **71.1 %**, desvio **4.3 p.p.**, faixa 66.0-77.9 %
- K medio 997.725, desvio 3.687 (promovido: 1.052)
