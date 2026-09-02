# Leave-one-event-out por DOF translacional - 20260810_1743

Refit completo a cada dobra, mantendo a estrutura P1D e a metrica Eq.(2).
NAO altera o modelo promovido em config/twin_params.json -- e analise de
dispersao, nao re-identificacao. Responde a objecao recorrente de que o fit
de vx repousa sobre UM unico evento de hold-out.

## vx (`front_to_back`, 4 eventos, 4 dobras)

| evento retido | fit (%) | K | tau (s) | Td (s) |
|---|---|---|---|---|
| front_to_back_01_01 | 85.8 | 1.126 | 0.0933 | 0.0563 |
| front_to_back_01_02 | 82.5 | 1.128 | 0.0948 | 0.0569 |
| front_to_back_01_03 | 86.2 | 1.130 | 0.0881 | 0.0556 |
| front_to_back_01_04 | 82.7 | 1.134 | 0.0885 | 0.0574 |

- fit medio **84.3 %**, desvio **2.0 p.p.**, faixa 82.5-86.2 %
- K medio 1.129, desvio 0.003 (promovido: 1.119)

## vy (`side_to_side`, 13 eventos, 13 dobras)

| evento retido | fit (%) | K | tau (s) | Td (s) |
|---|---|---|---|---|
| side_to_side_01_01 | 79.1 | 1.069 | 0.1435 | 0.0419 |
| side_to_side_01_02 | 82.6 | 1.069 | 0.1416 | 0.0450 |
| side_to_side_01_03 | 82.7 | 1.069 | 0.1421 | 0.0468 |
| side_to_side_01_04 | 81.6 | 1.068 | 0.1408 | 0.0471 |
| side_to_side_01_05 | 83.3 | 1.070 | 0.1409 | 0.0461 |
| side_to_side_01_06 | 77.2 | 1.064 | 0.1456 | 0.0470 |
| side_to_side_01_07 | 83.1 | 1.064 | 0.1450 | 0.0483 |
| side_to_side_01_08 | 88.5 | 1.065 | 0.1450 | 0.0481 |
| side_to_side_02_01 | 82.0 | 1.065 | 0.1462 | 0.0476 |
| side_to_side_02_02 | 84.3 | 1.065 | 0.1455 | 0.0473 |
| side_to_side_02_03 | 83.1 | 1.064 | 0.1456 | 0.0469 |
| side_to_side_02_04 | 82.9 | 1.065 | 0.1460 | 0.0468 |
| side_to_side_02_05 | 85.4 | 1.065 | 0.1451 | 0.0482 |

- fit medio **82.8 %**, desvio **2.7 p.p.**, faixa 77.2-88.5 %
- K medio 1.066, desvio 0.002 (promovido: 1.052)
