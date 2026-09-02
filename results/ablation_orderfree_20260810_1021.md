# Ablacao ordem-robusta + condicao inicial - 20260810_1021

Mediana de e_pos (m) no bin translacional, h_ref = 0.4 s, mesmas janelas.

## 1. Fatorial completo 2^3 (todas as 8 combinacoes, IC medida)

| K | tau | Td | e_pos (m) |
|---|---|---|---|
| off | off | off | 0.1005 |
| off | off | on | 0.0569 |
| off | on | off | 0.0509 |
| off | on | on | 0.0467 |
| on | off | off | 0.1093 |
| on | off | on | 0.0544 |
| on | on | off | 0.0455 |
| on | on | on | 0.0388 |

## 2. Atribuicao de Shapley (ordem-INDEPENDENTE)

Reducao media de e_pos atribuivel a cada grupo, sobre todas as ordens:

| grupo | contribuicao (m) | fracao da melhoria |
|---|---|---|
| gain K | +0.0010 | +2% |
| time constant tau | +0.0341 | +55% |
| dead time Td | +0.0266 | +43% |

Soma = +0.0617 m = melhoria total (ideal 0.1005 -> completo 0.0388).

## 3. Quanto da vitoria e condicao inicial, e nao dinamica

| planta | IC | e_pos (m) |
|---|---|---|
| ideal kinematics (memoryless) | irrelevante | 0.1005 |
| **const-velocity extrapolation** | **usa SO a IC medida** | **0.1600** |
| FOPDT completo | parte do repouso (como o rSim) | 0.1137 |
| FOPDT completo | IC medida | 0.0388 |

- A extrapolacao de velocidade constante, que usa a IC e IGNORA os comandos, da 0.1600 m.
- O gemeo sem IC medida da 0.1137 m; com IC medida, 0.0388 m.
- Logo a IC sozinha explica +0.0749 m e a dinamica identificada o restante.