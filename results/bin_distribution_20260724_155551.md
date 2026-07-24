# Distribuicao de bins — HOLD-OUT (10 eventos) — PREVIA, nao a operacao (D9: robot_radius=0.079601 m, CAD)

Populacao = janelas do **hold-out (10 eventos)**, NAO as 5 partidas. Resultado de previa; nao e a afirmacao final sobre operacao. **Pareamento twin vs IdealKinematicPlant** (nao vs RSimReplay/grSim como o `bin_distribution_20260619_000422.md` original -- modulo `robosim` indisponivel neste ambiente, bloqueio pre-existente; a classificacao de bin so depende de `win.cmd`, identico em qualquer pareamento, entao isso nao afeta a distribuicao reportada aqui).

Classificacao (metrics.py): razao = ativ_rot/(ativ_rot+ativ_trans); trans<0.2 / misto 0.2-0.5 / rot>0.5. H_max=90 (1.5 s), modo A (Lw=15).

| bin | janelas densas | janelas independentes | fracao (densas) |
|---|---:|---:|---:|
| trans-dominado | 264 | 49 | 0.996 |
| misto | 0 | 0 | 0.000 |
| rot-dominado | 1 | 0 | 0.004 |
| **TODOS** | 265 | 49 | 1.000 |
