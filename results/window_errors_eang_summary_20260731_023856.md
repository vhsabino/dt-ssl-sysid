# e_ang tabulado — twin (theta promovido) vs IdealKinematicPlant — 20260731_023856

Gerado por `scripts/window_errors_eang.py` (harness phase0_replay reusado; rSim indisponivel — bloqueio pre-existente).
theta twin = config/twin_params.json (vx/vy v2 + omega rotate_v1, K_w=1.0016, tau_w=0.0828, Td_w=0.0890; placeholder=False).
Hold-out: 10 segmentos (idle dropped=0); janelas=265; modo A (Lw=15, stride=15, H_max=90).
Bins: trans=264, misto=0, rot=1.

NOTA: NAO e o run da Figura twin-vs-rSim 20260617_0030 (la: omega placeholder, default=rSim). Aqui: omega promovido, default=cinematica ideal.

## Medianas (densas) — TODAS as janelas (N=265)

| h (s) | e_ang twin (rad) | e_ang ideal (rad) | e_pos twin (m) | e_pos ideal (m) |
|---:|---:|---:|---:|---:|
| 0.1 | 0.0129 | 0.0234 | 0.0079 | 0.0264 |
| 0.2 | 0.0314 | 0.0442 | 0.0178 | 0.0501 |
| 0.4 | 0.0446 | 0.0670 | 0.0388 | 0.1007 |
| 0.7 | 0.0630 | 0.0761 | 0.0610 | 0.1523 |
| 1.0 | 0.0745 | 0.0921 | 0.0918 | 0.2161 |
| 1.5 | 0.0901 | 0.0954 | 0.1192 | 0.2904 |

## Medianas (densas) — bin trans-dominado (N=264)

| h (s) | e_ang twin (rad) | e_ang ideal (rad) | e_pos twin (m) | e_pos ideal (m) |
|---:|---:|---:|---:|---:|
| 0.1 | 0.0128 | 0.0232 | 0.0079 | 0.0264 |
| 0.2 | 0.0311 | 0.0442 | 0.0178 | 0.0501 |
| 0.4 | 0.0440 | 0.0668 | 0.0388 | 0.1005 |
| 0.7 | 0.0627 | 0.0757 | 0.0617 | 0.1516 |
| 1.0 | 0.0733 | 0.0921 | 0.0920 | 0.2165 |
| 1.5 | 0.0895 | 0.0953 | 0.1193 | 0.2910 |

