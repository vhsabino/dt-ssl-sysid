# Excitacao por DOF nos logs de competicao - 20260810_1022

Comando alinhado pelo Td identificado; velocidade de corpo medida pelo mesmo
pre-processamento do artigo (Savitzky-Golay janela 7 ordem 2 + diferencas centrais).

| DOF | label | n | corr(cmd, meas) | R^2 (var. explicada) | std cmd | std meas |
|---|---|---|---|---|---|---|
| vx | `front_to_back` | 1964 | **0.979** | **0.959** | 1.141 | 1281.055 |
| vy | `side_to_side` | 7228 | **0.968** | **0.936** | 1.177 | 1232.703 |
| w | `shoot_to_goal` | 7484 | **0.746** | **0.557** | 1.001 | 1.457 |

Leitura: para vx/vy o comando explica a maior parte da variancia da velocidade
medida; para omega, nao. Esse e o diagnostico espectral/de correlacao que faltava
(objecoes C8/C9 e perguntas 7-8 do revisor).