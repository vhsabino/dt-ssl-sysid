# Distribuicao de bins — HOLD-OUT (10 eventos) — PREVIA, nao a operacao

Populacao = janelas do **hold-out (10 eventos)**, NAO as 5 partidas. Resultado de previa; nao e a afirmacao final sobre operacao.

Classificacao (metrics.py): razao = ativ_rot/(ativ_rot+ativ_trans); trans<0.2 / misto 0.2-0.5 / rot>0.5. H_max=90 (1.5 s), modo A (Lw=15).

| bin | janelas densas | janelas independentes | fracao (densas) |
|---|---:|---:|---:|
| trans-dominado | 264 | 49 | 0.996 |
| misto | 0 | 0 | 0.000 |
| rot-dominado | 1 | 0 | 0.004 |
| **TODOS** | 265 | 49 | 1.000 |
