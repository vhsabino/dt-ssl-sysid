# Estatistica agrupada por EVENTO — 20260809_2309

Unidade de analise = evento de hold-out. n = **10 eventos** (contra n=49 janelas na analise por janela).

Janelas translacionais densas: 264; nao-sobrepostas: 49; movimento pontuado = 49 x 1.5 s = **73.5 s**.

| evento (idx) | twin e_pos (m) | ideal e_pos (m) | gap (m) | janelas |
|---|---|---|---|---|
| 0 | 0.0172 | 0.0547 | +0.0375 | 27 |
| 1 | 0.0581 | 0.1618 | +0.1037 | 33 |
| 2 | 0.0449 | 0.1140 | +0.0692 | 33 |
| 3 | 0.0224 | 0.0530 | +0.0306 | 33 |
| 4 | 0.0213 | 0.0530 | +0.0317 | 28 |
| 5 | 0.0552 | 0.1214 | +0.0662 | 17 |
| 6 | 0.0393 | 0.1079 | +0.0686 | 13 |
| 7 | 0.0436 | 0.1290 | +0.0854 | 27 |
| 8 | 0.0540 | 0.1619 | +0.1079 | 31 |
| 9 | 0.0406 | 0.1376 | +0.0969 | 22 |

- Wilcoxon pareado **por evento** (one-sided twin<ideal): **p = 0.0009766**
- Gap mediano por evento: **+0.0689 m**; IC95% bootstrap por evento [+0.0375, +0.0969]
- Rank-biserial pareado por evento: **+1.000** (10 a favor / 0 contra)

Todos em h_ref = 0.4 s, bin translacional, twin vs cinematica ideal.