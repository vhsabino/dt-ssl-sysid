# Identificabilidade in-silico (C1): regime de excitacao x ruido x zona morta - 20260907_1552

_Proveniencia: commit `df833af` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed 42 | gerado por `dtssl.analysis.identifiability_insilico` (dtssl 1.0.0a1) | n_rep=20 | estimador profile-NM align=legacy | 1200 ajustes em 3.9 min_

Pre-registro: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md (hipoteses H1-H4, regra
de decisao e seeds fixadas antes de rodar). Verdade conhecida: theta* = theta oficial; o gemeo
(AnalyticFOPDTPlant) gera as trajetorias a partir dos comandos de cada regime, a cadeia de medicao
tipo visao adiciona ruido, e a cadeia de estimacao Python do artigo (legacy_uy_series + custo de
erro de saida de r3_closedloop_omega_fit) re-identifica (K, tau, Td) por DOF.

## Desenho

| DOF | K* | tau* (s) | Td* (s) | Td*/Ts (amostras) | atraso da planta (amostras) |
|---|---|---|---|---|---|
| vx | 1.1192 | 0.0718 | 0.06905 | 4.14 | 5 |
| vy | 1.0524 | 0.1273 | 0.05648 | 3.39 | 4 |
| w | 1.0016 | 0.0828 | 0.08895 | 5.34 | 6 |

- Ts = 0.016667 s; gerador `AnalyticFOPDTPlant(theta*)`, `reset(pose0, velb0=0)`, `pose[k] = step(cmd[k-1])` (driver de `free_run`, buffer de atraso vazio).
- Regimes (eventos): `front_to_back` = 4 eventos; `side_to_side` = 13 eventos; `shoot_to_goal` = 18 eventos; `rotate` = 10 eventos; `square` = 11 eventos; `R3` = 12 eventos
- R1 (pareamento do artigo): vx `front_to_back`, vy `side_to_side`, w `shoot_to_goal`; R2-rotate `rotate` (10 eventos, inclui +-0.25/+-0.5 rad/s); R2-square `square`; R3 sintetico: 12 eventos x 10 s, degraus de 0.3-1.2 s, amplitude +-[0.6, 1.5] m/s (vx, vy) e +-[1.5, 4.0] rad/s (w), 3 DOFs simultaneos, seed de desenho 42.
- Ruido (sigma_pos mm, sigma_theta rad): `none` = (0.0, 0.0); `vision` = (2.0, 0.01); `heavy` = (5.0, 0.03); i.i.d. por amostra, seed 42 + rep (numeros aleatorios comuns entre niveis).
- Zona morta do gerador: `apply_body_deadzone` por roda, limiar 1.567 rad/s (corpo ~0.58-0.60 rad/s em rotacao pura), aplicada ao comando ANTES da planta; o estimador ve o comando original.
- Monte Carlo: n_rep = 20 por celula; split 2/3-1/3 por evento seeded (seed 42 + 1000 + rep); fit nos eventos de treino, fit % medio no hold-out.
- Estimador: `legacy_uy_series` (SG 7/2 + diferencas centrais, mm -> m) + Nelder-Mead em (K, tau) para cada atraso inteiro m = 0..12 (custo de erro de saida, `simulate_fopdt` align=legacy, clamps tau >= 1e-4), m de menor custo de treino; X0 (K, tau) = (1.0, 0.08) (vx, vy) / (1.3, 0.03) (w); NM {'maxiter': 400, 'xatol': 0.0001, 'fatol': 0.001}. m_eff = m - 1 (align legacy aplica uma amostra a menos de atraso que a planta; common.py).
- Regra (por celula, mediana/IQR sobre as replicas): |vies K| <= 10 %, |vies tau| <= 15 %, |mediana(m_eff) - Td*/Ts| <= 1 amostra, IQR(K)/K* <= 20 %; escore = criterios satisfeitos (0-4); recuperado = 4/4.

Fracao de amostras em que a zona morta altera o comando (`qualquer roda`: ao menos uma roda abaixo
de 1.567 rad/s, comando de corpo alterado pela pseudo-inversa; colunas vx/vy/w: a componente do DOF
muda; `todas as rodas`: comando de corpo zerado = 'fully clamped' do artigo):

| conjunto | eventos | amostras | qualquer roda | vx | vy | w | todas as rodas |
|---|---|---|---|---|---|---|---|
| `front_to_back` | 4 | 1976 | 5.6 % | 5.6 % | 5.6 % | 5.6 % | 0.0 % |
| `side_to_side` | 13 | 7261 | 7.6 % | 7.6 % | 7.6 % | 7.6 % | 0.0 % |
| `shoot_to_goal` | 18 | 7558 | 31.6 % | 25.0 % | 25.0 % | 31.6 % | 6.7 % |
| `rotate` | 10 | 5751 | 40.0 % | 0.0 % | 0.0 % | 40.0 % | 40.0 % |
| `square` | 11 | 5982 | 9.8 % | 8.5 % | 8.5 % | 9.8 % | 1.3 % |
| `R3` | 12 | 7200 | 14.3 % | 14.3 % | 14.3 % | 14.3 % | 0.0 % |

Checagem do estimador literal do artigo (NM 3-D em [K, tau, Td] a partir de X0, `r3`) contra o perfil em m, celula idealizada R3/none/off, split da replica 0:

| DOF | NM 3-D: K | tau | Td (s) | m_eff | custo | perfil: K | tau | m_eff | custo |
|---|---|---|---|---|---|---|---|---|---|
| vx | 1.1416 | 0.1096 | 0.0532 | 3 | 34.775 | 1.1180 | 0.0731 | 5 | 2.001 |
| vy | 1.0686 | 0.1474 | 0.0524 | 3 | 7.495 | 1.0514 | 0.1281 | 4 | 0.885 |
| w | 0.9886 | 0.0669 | 0.1176 | 7 | 81.188 | 1.0010 | 0.0839 | 6 | 8.692 |

## DOF vx (K* = 1.1192, tau* = 0.0718 s, Td*/Ts = 4.14 amostras, planta aplica 5)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | escore | recuperado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 1.1191 [1.1190, 1.1191] | -0.0 | 0.0724 [0.0724, 0.0724] | +0.9 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 99.4 | 99.4 | 4 | SIM (4/4) |
| R1 | vision | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 1.1190 [1.1189, 1.1192] | -0.0 | 0.0724 [0.0722, 0.0726] | +0.8 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 97.1 | 96.1 | 4 | SIM (4/4) |
| R1 | heavy | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 1.1185 [1.1182, 1.1189] | -0.1 | 0.0722 [0.0720, 0.0727] | +0.6 | 5.0 [5.0, 5.0] | 0.86 | 0.1 | 92.9 | 90.5 | 4 | SIM (4/4) |
| R1 | none | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 1.1190 [1.1190, 1.1191] | -0.0 | 0.0723 [0.0722, 0.0723] | +0.8 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 99.4 | 99.4 | 4 | SIM (4/4) |
| R1 | vision | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 1.1190 [1.1188, 1.1191] | -0.0 | 0.0722 [0.0721, 0.0724] | +0.6 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 97.1 | 96.1 | 4 | SIM (4/4) |
| R1 | heavy | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 1.1185 [1.1182, 1.1189] | -0.1 | 0.0721 [0.0719, 0.0726] | +0.5 | 5.0 [5.0, 5.0] | 0.86 | 0.1 | 92.9 | 90.5 | 4 | SIM (4/4) |
| R2-rotate | none | off | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | vision | off | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | heavy | off | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | none | on | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | vision | on | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | heavy | on | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-square | none | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.1190 [1.1190, 1.1190] | -0.0 | 0.0724 [0.0724, 0.0724] | +0.8 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 99.2 | 99.2 | 4 | SIM (4/4) |
| R2-square | vision | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.1189 [1.1188, 1.1190] | -0.0 | 0.0724 [0.0723, 0.0725] | +0.8 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 95.5 | 95.5 | 4 | SIM (4/4) |
| R2-square | heavy | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.1184 [1.1181, 1.1187] | -0.1 | 0.0724 [0.0722, 0.0728] | +0.9 | 5.0 [5.0, 5.0] | 0.86 | 0.1 | 88.7 | 88.8 | 4 | SIM (4/4) |
| R2-square | none | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.1190 [1.1189, 1.1190] | -0.0 | 0.0725 [0.0724, 0.0725] | +0.9 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 99.2 | 99.1 | 4 | SIM (4/4) |
| R2-square | vision | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.1189 [1.1188, 1.1190] | -0.0 | 0.0724 [0.0723, 0.0726] | +0.9 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 95.5 | 95.5 | 4 | SIM (4/4) |
| R2-square | heavy | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.1184 [1.1182, 1.1187] | -0.1 | 0.0724 [0.0722, 0.0728] | +0.9 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 88.7 | 88.8 | 4 | SIM (4/4) |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.1179 [1.1179, 1.1180] | -0.1 | 0.0731 [0.0731, 0.0731] | +1.8 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 98.1 | 98.2 | 4 | SIM (4/4) |
| R3 | vision | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.1180 [1.1178, 1.1180] | -0.1 | 0.0731 [0.0730, 0.0731] | +1.8 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 95.9 | 96.0 | 4 | SIM (4/4) |
| R3 | heavy | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.1176 [1.1173, 1.1178] | -0.1 | 0.0730 [0.0729, 0.0732] | +1.7 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 90.6 | 90.8 | 4 | SIM (4/4) |
| R3 | none | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.1179 [1.1179, 1.1180] | -0.1 | 0.0731 [0.0731, 0.0731] | +1.8 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 98.1 | 98.2 | 4 | SIM (4/4) |
| R3 | vision | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.1179 [1.1178, 1.1180] | -0.1 | 0.0730 [0.0730, 0.0731] | +1.7 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 95.9 | 96.0 | 4 | SIM (4/4) |
| R3 | heavy | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.1176 [1.1172, 1.1178] | -0.1 | 0.0729 [0.0728, 0.0731] | +1.6 | 5.0 [5.0, 5.0] | 0.86 | 0.1 | 90.6 | 90.8 | 4 | SIM (4/4) |

## DOF vy (K* = 1.0524, tau* = 0.1273 s, Td*/Ts = 3.39 amostras, planta aplica 4)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | escore | recuperado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 1.0523 [1.0523, 1.0523] | -0.0 | 0.1276 [0.1276, 0.1276] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 99.6 | 99.6 | 4 | SIM (4/4) |
| R1 | vision | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 1.0522 [1.0522, 1.0523] | -0.0 | 0.1276 [0.1276, 0.1277] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 96.3 | 96.0 | 4 | SIM (4/4) |
| R1 | heavy | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 1.0518 [1.0517, 1.0519] | -0.1 | 0.1276 [0.1274, 0.1279] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 91.0 | 90.0 | 4 | SIM (4/4) |
| R1 | none | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 1.0522 [1.0521, 1.0522] | -0.0 | 0.1275 [0.1275, 0.1276] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 99.6 | 99.6 | 4 | SIM (4/4) |
| R1 | vision | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 1.0521 [1.0521, 1.0521] | -0.0 | 0.1275 [0.1275, 0.1276] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 96.3 | 96.0 | 4 | SIM (4/4) |
| R1 | heavy | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 1.0517 [1.0516, 1.0517] | -0.1 | 0.1275 [0.1274, 0.1278] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 91.0 | 90.0 | 4 | SIM (4/4) |
| R2-rotate | none | off | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | vision | off | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | heavy | off | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | none | on | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | vision | on | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-rotate | heavy | on | 10 (7/3) (20 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | 0 | nao (0/4) |
| R2-square | none | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.0523 [1.0522, 1.0523] | -0.0 | 0.1276 [0.1276, 0.1276] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 99.6 | 99.6 | 4 | SIM (4/4) |
| R2-square | vision | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.0522 [1.0521, 1.0523] | -0.0 | 0.1276 [0.1275, 0.1277] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 95.2 | 95.2 | 4 | SIM (4/4) |
| R2-square | heavy | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.0517 [1.0515, 1.0520] | -0.1 | 0.1276 [0.1274, 0.1279] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 87.9 | 88.0 | 4 | SIM (4/4) |
| R2-square | none | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.0521 [1.0521, 1.0522] | -0.0 | 0.1275 [0.1275, 0.1275] | +0.1 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 99.5 | 99.5 | 4 | SIM (4/4) |
| R2-square | vision | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.0521 [1.0520, 1.0522] | -0.0 | 0.1275 [0.1275, 0.1276] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 95.2 | 95.2 | 4 | SIM (4/4) |
| R2-square | heavy | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 1.0516 [1.0515, 1.0519] | -0.1 | 0.1276 [0.1274, 0.1278] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 87.9 | 88.0 | 4 | SIM (4/4) |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0514 [1.0514, 1.0514] | -0.1 | 0.1280 [0.1280, 0.1281] | +0.5 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 98.7 | 98.7 | 4 | SIM (4/4) |
| R3 | vision | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0513 [1.0512, 1.0514] | -0.1 | 0.1280 [0.1279, 0.1282] | +0.5 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 95.5 | 95.6 | 4 | SIM (4/4) |
| R3 | heavy | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0508 [1.0504, 1.0511] | -0.1 | 0.1280 [0.1278, 0.1283] | +0.5 | 4.0 [4.0, 4.0] | 0.61 | 0.1 | 89.1 | 89.3 | 4 | SIM (4/4) |
| R3 | none | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0515 [1.0514, 1.0516] | -0.1 | 0.1281 [0.1280, 0.1281] | +0.6 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 98.6 | 98.7 | 4 | SIM (4/4) |
| R3 | vision | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0515 [1.0513, 1.0516] | -0.1 | 0.1280 [0.1280, 0.1282] | +0.6 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 95.5 | 95.6 | 4 | SIM (4/4) |
| R3 | heavy | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0510 [1.0506, 1.0514] | -0.1 | 0.1281 [0.1279, 0.1284] | +0.6 | 4.0 [4.0, 4.0] | 0.61 | 0.1 | 89.1 | 89.3 | 4 | SIM (4/4) |

## DOF w (K* = 1.0016, tau* = 0.0828 s, Td*/Ts = 5.34 amostras, planta aplica 6)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | escore | recuperado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 0.9998 [0.9997, 0.9999] | -0.2 | 0.0844 [0.0839, 0.0846] | +2.0 | 6.0 [6.0, 6.0] | 0.66 | 0.0 | 97.1 | 98.0 | 4 | SIM (4/4) |
| R1 | vision | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 0.9999 [0.9992, 1.0005] | -0.2 | 0.0841 [0.0839, 0.0847] | +1.6 | 6.0 [6.0, 6.0] | 0.66 | 0.1 | 75.3 | 76.1 | 4 | SIM (4/4) |
| R1 | heavy | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.0000 [0.9977, 1.0018] | -0.2 | 0.0840 [0.0830, 0.0852] | +1.5 | 6.0 [6.0, 6.0] | 0.66 | 0.4 | 41.3 | 40.7 | 4 | SIM (4/4) |
| R1 | none | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 0.9964 [0.9958, 0.9968] | -0.5 | 0.0840 [0.0837, 0.0843] | +1.5 | 6.0 [6.0, 6.0] | 0.66 | 0.1 | 93.2 | 94.1 | 4 | SIM (4/4) |
| R1 | vision | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 0.9964 [0.9957, 0.9970] | -0.5 | 0.0838 [0.0835, 0.0841] | +1.3 | 6.0 [6.0, 6.0] | 0.66 | 0.1 | 74.6 | 75.5 | 4 | SIM (4/4) |
| R1 | heavy | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 0.9964 [0.9944, 0.9983] | -0.5 | 0.0836 [0.0825, 0.0847] | +1.0 | 6.0 [6.0, 6.0] | 0.66 | 0.4 | 41.1 | 40.6 | 4 | SIM (4/4) |
| R2-rotate | none | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 1.0017 [1.0017, 1.0017] | +0.0 | 0.0840 [0.0840, 0.0840] | +1.4 | 6.0 [6.0, 6.0] | 0.66 | 0.0 | 97.5 | 97.5 | 4 | SIM (4/4) |
| R2-rotate | vision | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 1.0018 [1.0016, 1.0019] | +0.0 | 0.0842 [0.0831, 0.0855] | +1.8 | 6.0 [6.0, 6.0] | 0.66 | 0.0 | 25.1 | 16.5 | 4 | SIM (4/4) |
| R2-rotate | heavy | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 1.0019 [1.0013, 1.0022] | +0.0 | 0.0826 [0.0807, 0.0876] | -0.2 | 6.0 [6.0, 6.0] | 0.66 | 0.1 | 10.3 | 2.7 | 4 | SIM (4/4) |
| R2-rotate | none | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9938 [0.9844, 0.9953] | -0.8 | 0.0839 [0.0839, 0.0839] | +1.4 | 6.0 [6.0, 6.0] | 0.66 | 1.1 | 92.6 | 93.2 | 4 | SIM (4/4) |
| R2-rotate | vision | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9939 [0.9847, 0.9953] | -0.8 | 0.0843 [0.0831, 0.0856] | +1.8 | 6.0 [6.0, 6.0] | 0.66 | 1.1 | -36.5 | 16.5 | 4 | SIM (4/4) |
| R2-rotate | heavy | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9938 [0.9849, 0.9951] | -0.8 | 0.0825 [0.0807, 0.0877] | -0.3 | 6.0 [6.0, 6.0] | 0.66 | 1.0 | -2.2 | 2.7 | 4 | SIM (4/4) |
| R2-square | none | off | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9994 [0.9994, 0.9995] | -0.2 | 0.0831 [0.0831, 0.0832] | +0.5 | 6.0 [6.0, 6.0] | 0.66 | 0.0 | 99.1 | 99.1 | 4 | SIM (4/4) |
| R2-square | vision | off | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9994 [0.9965, 1.0032] | -0.2 | 0.0830 [0.0817, 0.0849] | +0.3 | 6.0 [6.0, 6.0] | 0.66 | 0.7 | 22.0 | 21.9 | 4 | SIM (4/4) |
| R2-square | heavy | off | 11 (7/4) | 9.8 / 9.8 / 1.3 | 1.0026 [0.9894, 1.0131] | +0.1 | 0.0830 [0.0750, 0.0919] | +0.3 | 6.0 [6.0, 6.0] | 0.66 | 2.4 | 3.5 | 3.3 | 4 | SIM (4/4) |
| R2-square | none | on | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9923 [0.9913, 0.9930] | -0.9 | 0.0814 [0.0810, 0.0819] | -1.7 | 6.0 [6.0, 6.0] | 0.66 | 0.2 | 91.1 | 91.4 | 4 | SIM (4/4) |
| R2-square | vision | on | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9922 [0.9882, 0.9950] | -0.9 | 0.0813 [0.0787, 0.0825] | -1.7 | 6.0 [6.0, 6.0] | 0.66 | 0.7 | 21.8 | 21.6 | 4 | SIM (4/4) |
| R2-square | heavy | on | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9949 [0.9666, 1.0061] | -0.7 | 0.0812 [0.0694, 0.0894] | -1.9 | 6.0 [6.0, 7.0] | 0.66 | 4.0 | 3.5 | 3.2 | 4 | SIM (4/4) |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0010 [1.0010, 1.0010] | -0.1 | 0.0839 [0.0839, 0.0839] | +1.3 | 6.0 [6.0, 6.0] | 0.66 | 0.0 | 98.2 | 98.2 | 4 | SIM (4/4) |
| R3 | vision | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0010 [1.0009, 1.0013] | -0.1 | 0.0840 [0.0839, 0.0841] | +1.4 | 6.0 [6.0, 6.0] | 0.66 | 0.0 | 91.4 | 91.9 | 4 | SIM (4/4) |
| R3 | heavy | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0009 [1.0007, 1.0017] | -0.1 | 0.0841 [0.0838, 0.0846] | +1.6 | 6.0 [6.0, 6.0] | 0.66 | 0.1 | 75.6 | 76.8 | 4 | SIM (4/4) |
| R3 | none | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.9996 [0.9993, 1.0000] | -0.2 | 0.0839 [0.0838, 0.0839] | +1.3 | 6.0 [6.0, 6.0] | 0.66 | 0.1 | 97.9 | 97.8 | 4 | SIM (4/4) |
| R3 | vision | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.9998 [0.9991, 1.0000] | -0.2 | 0.0840 [0.0838, 0.0841] | +1.4 | 6.0 [6.0, 6.0] | 0.66 | 0.1 | 91.4 | 91.8 | 4 | SIM (4/4) |
| R3 | heavy | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.9996 [0.9991, 1.0004] | -0.2 | 0.0841 [0.0838, 0.0846] | +1.6 | 6.0 [6.0, 6.0] | 0.66 | 0.1 | 75.5 | 76.7 | 4 | SIM (4/4) |

## Resumo regime x DOF -> recuperado? (celula realista: ruido `vision`, zona morta `on`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | SIM (4/4) K -0.0 % | SIM (4/4) K -0.0 % | SIM (4/4) K -0.5 % |
| R2-rotate | nao (0/4) K nan % | nao (0/4) K nan % | SIM (4/4) K -0.8 % |
| R2-square | SIM (4/4) K -0.0 % | SIM (4/4) K -0.0 % | SIM (4/4) K -0.9 % |
| R3 | SIM (4/4) K -0.1 % | SIM (4/4) K -0.1 % | SIM (4/4) K -0.2 % |

## Resumo regime x DOF -> recuperado? (celula idealizada: ruido `none`, zona morta `off`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | SIM (4/4) K -0.0 % | SIM (4/4) K -0.0 % | SIM (4/4) K -0.2 % |
| R2-rotate | nao (0/4) K nan % | nao (0/4) K nan % | SIM (4/4) K +0.0 % |
| R2-square | SIM (4/4) K -0.0 % | SIM (4/4) K -0.0 % | SIM (4/4) K -0.2 % |
| R3 | SIM (4/4) K -0.1 % | SIM (4/4) K -0.1 % | SIM (4/4) K -0.1 % |

## w: R1 (zona morta on) vs R2-rotate

| celula | K med | vies K % | tau med | vies tau % | m_eff med | fit ho % | escore |
|---|---|---|---|---|---|---|---|
| R1 / none / on | 0.9964 | -0.5 | 0.0840 | +1.5 | 6.0 | 93.2 | 4 |
| R1 / vision / on | 0.9964 | -0.5 | 0.0838 | +1.3 | 6.0 | 74.6 | 4 |
| R1 / heavy / on | 0.9964 | -0.5 | 0.0836 | +1.0 | 6.0 | 41.1 | 4 |
| R1 / none / off | 0.9998 | -0.2 | 0.0844 | +2.0 | 6.0 | 97.1 | 4 |
| R1 / vision / off | 0.9999 | -0.2 | 0.0841 | +1.6 | 6.0 | 75.3 | 4 |
| R1 / heavy / off | 1.0000 | -0.2 | 0.0840 | +1.5 | 6.0 | 41.3 | 4 |
| R2-rotate / none / on | 0.9938 | -0.8 | 0.0839 | +1.4 | 6.0 | 92.6 | 4 |
| R2-rotate / vision / on | 0.9939 | -0.8 | 0.0843 | +1.8 | 6.0 | -36.5 | 4 |
| R2-rotate / heavy / on | 0.9938 | -0.8 | 0.0825 | -0.3 | 6.0 | -2.2 | 4 |
| R2-rotate / none / off | 1.0017 | +0.0 | 0.0840 | +1.4 | 6.0 | 97.5 | 4 |
| R2-rotate / vision / off | 1.0018 | +0.0 | 0.0842 | +1.8 | 6.0 | 25.1 | 4 |
| R2-rotate / heavy / off | 1.0019 | +0.0 | 0.0826 | -0.2 | 6.0 | 10.3 | 4 |

## Leitura

- H1 (w recuperado em R2-rotate/R3 e NAO em R1 com zona morta on, celula realista): R2-rotate=SIM, R3=SIM, R1=SIM -> FALSIFICADA (w E recuperado em R1: o conteudo de comando de competicao basta para o gerador linear; o mecanismo do K~1.38 real esta fora do gerador - diluicao/realimentacao)
- H2 (vx/vy recuperados em R1 e R3, degradados em R2-rotate): R1=SIM, R3=SIM, R2-rotate degradado=SIM -> CORROBORADA
- H3 (ruido alarga o IQR de K mas nao enviesa K): celulas recuperadas em `none` que perdem o criterio de K em `heavy`: 0; IQR(K) nao decrescente none->vision->heavy em 95 % das combinacoes regime x DOF x zona morta -> CORROBORADA
- H4 (zona morta e o mecanismo principal do vies de K em R1/w): vies K on=-0.5 %, off=-0.2 % -> FALSIFICADA (a zona morta nao explica o K~1.38 de malha fechada: reforca a leitura de diluicao/realimentacao do artigo, ausente do gerador)
- Fit % vs recuperacao: 10 de 60 celulas recuperadas (4/4) tem fit hold-out mediano < 60 % (gate do artigo): R2-rotate/w/vision/on = -36.5 %; R2-rotate/w/heavy/on = -2.2 %; R2-square/w/heavy/on = 3.5 %; R2-square/w/heavy/off = 3.5 %; R2-rotate/w/heavy/off = 10.3 %; R2-square/w/vision/on = 21.8 % -> o fit % (NRMSE) mede a relacao sinal-ruido da excitacao do regime (variancia de y explicada pelo comando), nao a recuperacao dos parametros: parametros exatos podem coexistir com fit baixo em regimes de pouca excitacao ou muito ruido

Leitura geral: para cada DOF fixo, compare o escore entre regimes (o que muda e a excitacao, nao o
DOF); em R3 (excitacao projetada dos tres DOFs) os tres DOFs devem ser recuperados. Celulas
'degeneradas' (comando de treino com variancia nula, ex. vx/vy em `rotate`) nao tem ajuste: sem
excitacao nao ha identificabilidade, qualquer que seja o DOF. O gerador e o gemeo linear sem
escorregamento nem realimentacao: R1 in-silico mede apenas o conteudo informacional dos comandos
de competicao (mais ruido e zona morta), nao o mecanismo de diluicao/realimentacao do artigo.
Td: a planta aplica ceil(Td*/Ts) amostras; o estimador legacy devolve m_eff = m - 1, comparavel
com Td*/Ts; o Td* continuo nao e recuperavel abaixo dessa quantizacao (criterio de 1 amostra).