# twin (FOPDT) vs rSim (ODE replay) — metrica SE(2) multi-horizonte

Modo de justica de IC: **B (sem warm-up; descarta amostras < 15 p/ AMBOS)**. Lw(warm-up)=15 amostras, sub_ms=1, stride=15, h_max=90.
Config metrica: horizontes(amostras)=[np.int64(24), np.int64(42), np.int64(60), np.int64(90)] (s=[0.4, 0.7, 1.0, 1.5]), h_ref=24, N_min=10, alpha=0.05, effect_min=0.2, bloco_MBB=6 janelas.

## Distribuicao de bins

| bin | total (densas) | independentes |
|---|---:|---:|
| trans-dominado | 264 | 49 |
| misto | 0 | 0 |
| rot-dominado | 1 | 0 |
| **TODOS** | 265 | 49 |

## TODOS (agregado)
N total=265, independentes=49

| h (s) | twin e_pos | rSim (ODE replay) e_pos | gap (m) | gap CI95 | p (nao-sobr.) | effect |
|---:|---:|---:|---:|---:|---:|---:|
| 0.40 | 0.0383 | 0.3199 | +0.2816 | [+0.2637,+0.2921] | 4.44e-14 | +0.987 |
| 0.70 | 0.0637 | 0.3705 | +0.3069 | [+0.2785,+0.3268] | 1.35e-12 | +0.961 |
| 1.00 | 0.0908 | 0.4042 | +0.3134 | [+0.2772,+0.3426] | 8.84e-12 | +0.941 |
| 1.50 | 0.1228 | 0.4696 | +0.3467 | [+0.2965,+0.4032] | 1.93e-09 | +0.864 |

## trans-dominado
N total=264, independentes=49

| h (s) | twin e_pos | rSim (ODE replay) e_pos | gap (m) | gap CI95 | p (nao-sobr.) | effect |
|---:|---:|---:|---:|---:|---:|---:|
| 0.40 | 0.0382 | 0.3202 | +0.2820 | [+0.2587,+0.2917] | 4.44e-14 | +0.987 |
| 0.70 | 0.0644 | 0.3708 | +0.3065 | [+0.2799,+0.3280] | 1.35e-12 | +0.961 |
| 1.00 | 0.0919 | 0.4045 | +0.3126 | [+0.2790,+0.3422] | 8.84e-12 | +0.941 |
| 1.50 | 0.1229 | 0.4697 | +0.3469 | [+0.2990,+0.4037] | 1.93e-09 | +0.864 |

## misto
_(sem janelas)_

## rot-dominado
N total=1, independentes=0

| h (s) | twin e_pos | rSim (ODE replay) e_pos | gap (m) | gap CI95 | p (nao-sobr.) | effect |
|---:|---:|---:|---:|---:|---:|---:|
| 0.40 | 0.0384 | 0.2123 | +0.1739 | [+0.1739,+0.1739] | 1 | +0.000 |
| 0.70 | 0.0250 | 0.1764 | +0.1514 | [+0.1514,+0.1514] | 1 | +0.000 |
| 1.00 | 0.0241 | 0.1787 | +0.1546 | [+0.1546,+0.1546] | 1 | +0.000 |
| 1.50 | 0.0217 | 0.1801 | +0.1584 | [+0.1584,+0.1584] | 1 | +0.000 |

## Vereditos por bin (gates: omega placeholder + populacao N_min)

| bin | veredito | N indep | gap@h_ref | p@h_ref | effect@h_ref |
|---|---|---:|---:|---:|---:|
| trans-dominado | GO | 49 | +0.2820 | 4.44e-14 | +0.987 |
| misto | INDETERMINADO (omega placeholder) | 0 | - | - | - |
| rot-dominado | INDETERMINADO (omega placeholder) | 0 | +0.1739 | 1 | +0.000 |

## Figuras
- `rsim_twin_all_20260617_0031.png`
- `rsim_twin_trans_20260617_0031.png`
- `rsim_twin_rot_20260617_0031.png`
