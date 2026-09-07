# Identificabilidade in-silico (C1b-v2, re-registro): gerador mujoco-rollers-delay - regime x ruido x zona morta - 20260907_2044

_Proveniencia: commit `cdef20c` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed 42 | gerado por `dtssl.analysis.identifiability_insilico` (dtssl 1.0.0a1) | gerador mujoco-rollers-delay (opts {}) | n_rep=12 | estimador profile-NM align=legacy | 528 ajustes em 3.2 min (geracao de trajetorias 1.5 min)_

Re-registro C1b-v2: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_V2_20260907.md (emenda documentada
apos a execucao v1; muda SO: regime R3-mild dentro do envelope da rota b, referencias por DOF =
regimes dedicados de malha aberta (w: R2-rotate/none/off; vx, vy: R2-square/none/off) e regra
K-only regime_bias_K = |dev K| > 10 %; dev tau e dm_eff sao descritivos). v1 e seus artefatos
ficam intocados.

Pre-registro: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_20260907.md (adendo C1b: hipoteses
H5-H8, referencia e bandeira regime_bias fixadas antes de rodar) sobre o desenho de C1
(docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md).
GERADOR: `mujoco-rollers-delay` via `dtssl.sim.world_plant.make_harness_plant` (MuJoCoWorld de um robo visto como
Plant do harness; `mujoco-velocity` = rota a, a AnalyticFOPDTPlant(theta*) dirigindo o chassi;
`mujoco-rollers` = rota b, rodas omni + roletes livres, sem sintonia e sem atraso;
`mujoco-rollers-delay` = rota b + tap de atraso ceil(Td*/Ts) por DOF no comando). Zona morta do
fator C aplicada DENTRO do mundo (`deadzone=True`: rota a = regra de corpo de apply_body_deadzone;
rota b = por roda, no setpoint de cada atuador); o estimador ve sempre o comando original.
Trajetoria por evento gerada UMA vez por (conjunto, zona morta) e partilhada pelas replicas.
Para este gerador theta* NAO e a verdade do modelo: a pergunta e se a estimativa P1D depende do
regime. Referencia por DOF = mediana das estimativas na celula R3 / none / off do proprio gerador;
cada celula reporta o desvio (dev) da referencia e a bandeira regime_bias = |dev K| > 10 % ou
|dev tau| > 15 % (substitui 'recuperado'). theta* fica na tabela so como contexto.

## Desenho

| DOF | K* | tau* (s) | Td* (s) | Td*/Ts (amostras) | atraso da planta (amostras) |
|---|---|---|---|---|---|
| vx | 1.1192 | 0.0718 | 0.06905 | 4.14 | 5 |
| vy | 1.0524 | 0.1273 | 0.05648 | 3.39 | 4 |
| w | 1.0016 | 0.0828 | 0.08895 | 5.34 | 6 |

- Ts = 0.016667 s; gerador `mujoco-rollers-delay` (`make_harness_plant`, opts {}), `reset(pose0, velb0=0)`, `pose[k] = step(cmd[k-1])` (driver de `free_run`, buffer de atraso vazio).
- Regimes (eventos): `front_to_back` = 4 eventos; `side_to_side` = 13 eventos; `shoot_to_goal` = 18 eventos; `shoot_to_goal@wonly` = 18 eventos; `rotate` = 10 eventos; `square` = 11 eventos; `R3-mild` = 12 eventos
- R1 (pareamento do artigo): vx `front_to_back`, vy `side_to_side`, w `shoot_to_goal`; R1-wonly = as mesmas sequencias de R1 com vx = vy = 0 (controle, so DOF w); R2-rotate `rotate` (10 eventos, inclui +-0.25/+-0.5 rad/s); R2-square `square`; R3 sintetico: 12 eventos x 10 s, degraus de 0.3-1.2 s, amplitude +-[0.6, 1.5] m/s (vx, vy) e +-[1.5, 4.0] rad/s (w), 3 DOFs simultaneos, seed de desenho 42. R3-mild (envelope da rota b): amplitude +-[0.3, 1.0] m/s (vx, vy) e +-[0.5, 2.0] rad/s (w), degraus de 0.5-1.5 s, mesma construcao e seed.
- Ruido (sigma_pos mm, sigma_theta rad): `none` = (0.0, 0.0); `vision` = (2.0, 0.01); i.i.d. por amostra, seed 42 + rep (numeros aleatorios comuns entre niveis).
- Zona morta do gerador: limiar de firmware 1.567 rad/s por roda aplicado pelo MuJoCoWorld (`deadzone=True`); as fracoes mascaradas abaixo usam a mesma regra por roda (`mask_deadzone`).
- Monte Carlo: n_rep = 12 por celula; split 2/3-1/3 por evento seeded (seed 42 + 1000 + rep); fit nos eventos de treino, fit % medio no hold-out.
- Estimador: `legacy_uy_series` (SG 7/2 + diferencas centrais, mm -> m) + Nelder-Mead em (K, tau) para cada atraso inteiro m = 0..12 (custo de erro de saida, `simulate_fopdt` align=legacy, clamps tau >= 1e-4), m de menor custo de treino; X0 (K, tau) = (1.0, 0.08) (vx, vy) / (1.3, 0.03) (w); NM {'maxiter': 400, 'xatol': 0.0001, 'fatol': 0.001}. m_eff = m - 1 (align legacy aplica uma amostra a menos de atraso que a planta; common.py).
- Regra (por celula, mediana/IQR sobre as replicas): |vies K| <= 10 %, |vies tau| <= 15 %, |mediana(m_eff) - Td*/Ts| <= 1 amostra, IQR(K)/K* <= 20 %; escore = criterios satisfeitos (0-4); recuperado = 4/4. Regra C1b: referencia = celula vx/vy/w por DOF; regime_bias = |dev K| > 10 % ou |dev tau| > 15 %.

Fracao de amostras em que a zona morta altera o comando (`qualquer roda`: ao menos uma roda abaixo
de 1.567 rad/s, comando de corpo alterado pela pseudo-inversa; colunas vx/vy/w: a componente do DOF
muda; `todas as rodas`: comando de corpo zerado = 'fully clamped' do artigo):

| conjunto | eventos | amostras | qualquer roda | vx | vy | w | todas as rodas |
|---|---|---|---|---|---|---|---|
| `front_to_back` | 4 | 1976 | 5.6 % | 5.6 % | 5.6 % | 5.6 % | 0.0 % |
| `side_to_side` | 13 | 7261 | 7.6 % | 7.6 % | 7.6 % | 7.6 % | 0.0 % |
| `shoot_to_goal` | 18 | 7558 | 31.6 % | 25.0 % | 25.0 % | 31.6 % | 6.7 % |
| `shoot_to_goal@wonly` | 18 | 7558 | 74.0 % | 0.0 % | 0.0 % | 74.0 % | 74.0 % |
| `rotate` | 10 | 5751 | 40.0 % | 0.0 % | 0.0 % | 40.0 % | 40.0 % |
| `square` | 11 | 5982 | 9.8 % | 8.5 % | 8.5 % | 9.8 % | 1.3 % |
| `R3-mild` | 12 | 7200 | 22.5 % | 22.5 % | 22.5 % | 22.5 % | 0.0 % |

Referencia por DOF (gerador `mujoco-rollers-delay`; celulas vx: R2-square/none/off; vy: R2-square/none/off; w: R2-rotate/none/off - pre-registrada C1b-v2) e sua distancia ao theta* do gemeo (contexto, nao criterio):

| DOF | celula de referencia | K ref | tau ref (s) | m_eff ref | K ref / K* - 1 | tau ref / tau* - 1 | m_eff ref - Td*/Ts |
|---|---|---|---|---|---|---|---|
| vx | R2-square/none/off | 0.9917 | 0.0461 | 4.0 | -11.4 % | -35.8 % | -0.14 |
| vy | R2-square/none/off | 0.9861 | 0.0660 | 3.0 | -6.3 % | -48.2 % | -0.39 |
| w | R2-rotate/none/off | 0.9963 | 0.0316 | 5.0 | -0.5 % | -61.9 % | -0.34 |

Checagem do estimador literal do artigo (NM 3-D em [K, tau, Td] a partir de X0, `r3`) contra o perfil em m, celula idealizada R3/none/off, split da replica 0:

| DOF | NM 3-D: K | tau | Td (s) | m_eff | custo | perfil: K | tau | m_eff | custo |
|---|---|---|---|---|---|---|---|---|---|
| vx | -0.2424 | 0.1777 | 0.0673 | 4 | 1938.829 | -0.2363 | 0.0988 | 10 | 1934.743 |
| vy | 0.9775 | 0.1729 | 0.0530 | 3 | 148.706 | 0.9622 | 0.1369 | 5 | 143.515 |
| w | 1.0795 | 0.0340 | 0.1113 | 6 | 83414.023 | 1.0877 | 0.0475 | 5 | 83412.047 |

## DOF vx (K* = 1.1192, tau* = 0.0718 s, Td*/Ts = 4.14 amostras, planta aplica 5)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6990 [0.6451, 0.7530] | -37.5 | 0.0233 [0.0191, 0.0291] | -67.5 | 5.0 [5.0, 5.0] | 0.86 | 9.6 | 63.9 | 69.7 | -29.5 | -49.4 | 1.0 | VIES | VIES |
| R1 | vision | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6992 [0.6453, 0.7531] | -37.5 | 0.0272 [0.0192, 0.0293] | -62.1 | 5.0 [5.0, 5.0] | 0.86 | 9.6 | 63.8 | 69.4 | -29.5 | -41.0 | 1.0 | VIES | VIES |
| R1 | none | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6949 [0.6405, 0.7493] | -37.9 | 0.0242 [0.0197, 0.0301] | -66.4 | 5.0 [5.0, 5.0] | 0.86 | 9.7 | 63.4 | 69.2 | -29.9 | -47.6 | 1.0 | VIES | VIES |
| R1 | vision | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6950 [0.6406, 0.7494] | -37.9 | 0.0283 [0.0199, 0.0304] | -60.6 | 5.0 [5.0, 5.0] | 0.86 | 9.7 | 63.3 | 69.0 | -29.9 | -38.7 | 1.0 | VIES | VIES |
| R2-rotate | none | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | none | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-square | none | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9917 [0.9912, 0.9923] | -11.4 | 0.0461 [0.0451, 0.0469] | -35.8 | 4.0 [4.0, 4.0] | -0.14 | 0.1 | 95.6 | 95.7 | +0.0 | +0.0 | 0.0 | ok | ok |
| R2-square | vision | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9916 [0.9912, 0.9922] | -11.4 | 0.0462 [0.0449, 0.0470] | -35.7 | 4.0 [4.0, 4.0] | -0.14 | 0.1 | 93.2 | 93.2 | -0.0 | +0.2 | 0.0 | ok | ok |
| R2-square | none | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9917 [0.9912, 0.9923] | -11.4 | 0.0462 [0.0452, 0.0470] | -35.6 | 4.0 [4.0, 4.0] | -0.14 | 0.1 | 95.4 | 95.7 | +0.0 | +0.2 | 0.0 | ok | ok |
| R2-square | vision | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9915 [0.9912, 0.9922] | -11.4 | 0.0461 [0.0450, 0.0472] | -35.7 | 4.0 [4.0, 4.0] | -0.14 | 0.1 | 93.0 | 93.3 | -0.0 | +0.1 | 0.0 | ok | ok |
| R3-mild | none | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | -0.2692 [-0.3422, -0.1771] | -124.1 | 0.0944 [0.0779, 0.1136] | +31.5 | 10.0 [8.8, 11.0] | 5.86 | 14.8 | -10.9 | -0.3 | -127.1 | +104.7 | 6.0 | VIES | VIES |
| R3-mild | vision | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | -0.2693 [-0.3420, -0.1775] | -124.1 | 0.0946 [0.0779, 0.1136] | +31.8 | 10.0 [8.8, 11.0] | 5.86 | 14.7 | -10.8 | -0.3 | -127.2 | +105.3 | 6.0 | VIES | VIES |
| R3-mild | none | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | -0.2684 [-0.3412, -0.1776] | -124.0 | 0.0930 [0.0763, 0.1113] | +29.6 | 10.0 [8.8, 11.0] | 5.86 | 14.6 | -10.9 | -0.3 | -127.1 | +101.8 | 6.0 | VIES | VIES |
| R3-mild | vision | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | -0.2684 [-0.3410, -0.1778] | -124.0 | 0.0933 [0.0760, 0.1110] | +30.0 | 10.0 [8.8, 11.0] | 5.86 | 14.6 | -10.9 | -0.2 | -127.1 | +102.4 | 6.0 | VIES | VIES |

## DOF vy (K* = 1.0524, tau* = 0.1273 s, Td*/Ts = 3.39 amostras, planta aplica 4)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9251 [0.9178, 0.9361] | -12.1 | 0.0717 [0.0712, 0.0842] | -43.7 | 3.0 [2.0, 3.0] | -0.39 | 1.7 | 87.2 | 89.9 | -6.2 | +8.6 | 0.0 | ok | ok |
| R1 | vision | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9251 [0.9187, 0.9345] | -12.1 | 0.0719 [0.0709, 0.0850] | -43.6 | 3.0 [2.0, 3.0] | -0.39 | 1.5 | 86.5 | 89.4 | -6.2 | +8.9 | 0.0 | ok | ok |
| R1 | none | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9303 [0.9272, 0.9479] | -11.6 | 0.0771 [0.0761, 0.0777] | -39.4 | 3.0 [3.0, 3.0] | -0.39 | 2.0 | 89.2 | 90.4 | -5.7 | +16.8 | 0.0 | VIES | ok |
| R1 | vision | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9303 [0.9272, 0.9477] | -11.6 | 0.0773 [0.0763, 0.0776] | -39.3 | 3.0 [3.0, 3.0] | -0.39 | 1.9 | 88.5 | 89.8 | -5.7 | +17.1 | 0.0 | VIES | ok |
| R2-rotate | none | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | none | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-square | none | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9861 [0.9855, 0.9938] | -6.3 | 0.0660 [0.0586, 0.0667] | -48.2 | 3.0 [3.0, 3.0] | -0.39 | 0.8 | 94.3 | 94.0 | +0.0 | +0.0 | 0.0 | ok | ok |
| R2-square | vision | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9862 [0.9855, 0.9918] | -6.3 | 0.0659 [0.0584, 0.0666] | -48.2 | 3.0 [3.0, 3.0] | -0.39 | 0.6 | 92.3 | 92.2 | +0.0 | -0.1 | 0.0 | ok | ok |
| R2-square | none | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9486 [0.9480, 0.9939] | -9.9 | 0.0713 [0.0583, 0.0721] | -44.0 | 3.0 [3.0, 3.0] | -0.39 | 4.4 | 92.3 | 92.2 | -3.8 | +8.0 | 0.0 | ok | ok |
| R2-square | vision | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9487 [0.9480, 0.9924] | -9.9 | 0.0712 [0.0580, 0.0718] | -44.1 | 3.0 [3.0, 3.0] | -0.39 | 4.2 | 90.8 | 90.7 | -3.8 | +7.9 | 0.0 | ok | ok |
| R3-mild | none | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9628 [0.9599, 0.9692] | -8.5 | 0.1383 [0.1325, 0.1420] | +8.6 | 5.0 [5.0, 5.0] | 1.61 | 0.9 | 68.8 | 68.8 | -2.4 | +109.5 | 2.0 | VIES | ok |
| R3-mild | vision | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9619 [0.9596, 0.9668] | -8.6 | 0.1362 [0.1313, 0.1419] | +7.0 | 5.0 [5.0, 5.2] | 1.61 | 0.7 | 68.1 | 68.1 | -2.4 | +106.4 | 2.0 | VIES | ok |
| R3-mild | none | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9636 [0.9608, 0.9702] | -8.4 | 0.1398 [0.1323, 0.1428] | +9.8 | 5.0 [5.0, 5.0] | 1.61 | 0.9 | 68.7 | 69.9 | -2.3 | +111.8 | 2.0 | VIES | ok |
| R3-mild | vision | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9634 [0.9604, 0.9695] | -8.5 | 0.1398 [0.1322, 0.1427] | +9.8 | 5.0 [5.0, 5.0] | 1.61 | 0.9 | 68.0 | 69.1 | -2.3 | +111.8 | 2.0 | VIES | ok |

## DOF w (K* = 1.0016, tau* = 0.0828 s, Td*/Ts = 5.34 amostras, planta aplica 6)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1603 [1.0426, 1.2486] | +15.8 | 0.1010 [0.0841, 0.1227] | +22.1 | 6.0 [5.0, 7.2] | 0.66 | 20.6 | 29.2 | 26.6 | +16.5 | +220.0 | 1.0 | VIES | VIES |
| R1 | vision | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1597 [1.0435, 1.2481] | +15.8 | 0.0983 [0.0837, 0.1226] | +18.8 | 6.0 [5.0, 7.2] | 0.66 | 20.4 | 26.8 | 25.1 | +16.4 | +211.5 | 1.0 | VIES | VIES |
| R1 | none | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.2735 [1.1962, 1.3627] | +27.1 | 0.1839 [0.1114, 0.2161] | +122.2 | 1.5 [1.0, 3.2] | -3.84 | 16.6 | 24.6 | 17.9 | +27.8 | +482.5 | -3.5 | VIES | VIES |
| R1 | vision | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.2697 [1.1785, 1.3908] | +26.8 | 0.1703 [0.1085, 0.2154] | +105.8 | 1.5 [1.0, 4.0] | -3.84 | 21.2 | 22.9 | 16.8 | +27.4 | +439.6 | -3.5 | VIES | VIES |
| R1-wonly | none | off | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9880 [0.9869, 0.9890] | -1.4 | 0.0333 [0.0327, 0.0391] | -59.8 | 5.0 [5.0, 5.0] | -0.34 | 0.2 | 80.9 | 91.2 | -0.8 | +5.4 | 0.0 | ok | ok |
| R1-wonly | vision | off | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9882 [0.9867, 0.9893] | -1.3 | 0.0334 [0.0329, 0.0389] | -59.6 | 5.0 [5.0, 5.0] | -0.34 | 0.3 | 68.2 | 76.7 | -0.8 | +5.9 | 0.0 | ok | ok |
| R1-wonly | none | on | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9353 [0.9223, 0.9375] | -6.6 | 0.0317 [0.0291, 0.0326] | -61.7 | 5.0 [5.0, 5.2] | -0.34 | 1.5 | 65.1 | 74.7 | -6.1 | +0.5 | 0.0 | ok | ok |
| R1-wonly | vision | on | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9295 [0.9100, 0.9370] | -7.2 | 0.0304 [0.0271, 0.0323] | -63.2 | 5.0 [5.0, 6.0] | -0.34 | 2.7 | 58.4 | 66.8 | -6.7 | -3.6 | 0.0 | ok | ok |
| R2-rotate | none | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9963 [0.9960, 0.9965] | -0.5 | 0.0316 [0.0303, 0.0324] | -61.9 | 5.0 [5.0, 5.0] | -0.34 | 0.1 | 88.6 | 88.2 | +0.0 | +0.0 | 0.0 | ok | ok |
| R2-rotate | vision | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9963 [0.9960, 0.9965] | -0.5 | 0.0307 [0.0283, 0.0321] | -62.9 | 5.0 [5.0, 5.0] | -0.34 | 0.0 | 26.8 | 12.2 | +0.0 | -2.7 | 0.0 | ok | ok |
| R2-rotate | none | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9843 [0.9618, 0.9885] | -1.7 | 0.0331 [0.0310, 0.0337] | -60.1 | 5.0 [5.0, 5.0] | -0.34 | 2.7 | -108360.4 | 83.4 | -1.2 | +4.7 | 0.0 | ok | ok |
| R2-rotate | vision | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9843 [0.9619, 0.9884] | -1.7 | 0.0315 [0.0269, 0.0329] | -62.0 | 5.0 [5.0, 5.0] | -0.34 | 2.7 | -14.6 | 12.0 | -1.2 | -0.3 | 0.0 | ok | ok |
| R2-square | none | off | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9708 [0.9628, 0.9866] | -3.1 | 0.0288 [0.0272, 0.0341] | -65.1 | 5.0 [4.8, 5.0] | -0.34 | 2.4 | 33.1 | 26.0 | -2.6 | -8.6 | 0.0 | ok | ok |
| R2-square | vision | off | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9736 [0.9661, 1.0026] | -2.8 | 0.0300 [0.0267, 0.0478] | -63.7 | 5.0 [4.0, 5.0] | -0.34 | 3.6 | 17.7 | 15.5 | -2.3 | -4.9 | 0.0 | ok | ok |
| R2-square | none | on | 11 (7/4) | 9.8 / 9.8 / 1.3 | 1.1329 [0.9853, 1.1357] | +13.1 | 0.0128 [0.0116, 0.0276] | -84.5 | 6.0 [5.0, 6.0] | 0.66 | 15.0 | 32.9 | 25.9 | +13.7 | -59.4 | 1.0 | VIES | VIES |
| R2-square | vision | on | 11 (7/4) | 9.8 / 9.8 / 1.3 | 1.1268 [1.0074, 1.1370] | +12.5 | 0.0125 [0.0110, 0.0282] | -84.9 | 6.0 [5.0, 6.0] | 0.66 | 12.9 | 17.0 | 15.1 | +13.1 | -60.5 | 1.0 | VIES | VIES |
| R3-mild | none | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 1.0311 [0.9815, 1.0604] | +2.9 | 0.0378 [0.0350, 0.0407] | -54.3 | 5.5 [5.0, 6.0] | 0.16 | 7.9 | 3.5 | 2.8 | +3.5 | +19.7 | 0.5 | VIES | ok |
| R3-mild | vision | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 1.0292 [0.9675, 1.0870] | +2.8 | 0.0382 [0.0352, 0.0418] | -53.8 | 5.0 [5.0, 6.0] | -0.34 | 11.9 | 3.6 | 2.6 | +3.3 | +21.1 | 0.0 | VIES | ok |
| R3-mild | none | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9451 [0.9241, 0.9861] | -5.6 | 0.0503 [0.0363, 0.0797] | -39.2 | 5.0 [4.8, 5.0] | -0.34 | 6.2 | 2.8 | 3.1 | -5.1 | +59.3 | 0.0 | VIES | ok |
| R3-mild | vision | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9860 [0.9503, 1.0214] | -1.6 | 0.0533 [0.0386, 0.0793] | -35.7 | 5.0 [4.8, 5.0] | -0.34 | 7.1 | 3.1 | 3.2 | -1.0 | +68.7 | 0.0 | VIES | ok |

## Resumo regime x DOF -> regime_bias_K? (|dev K| > 10 % vs referencia vx: R2-square/none/off; vy: R2-square/none/off; w: R2-rotate/none/off) (celula realista: ruido `vision`, zona morta `on`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | VIES dev K -29.9 % | ok dev K -5.7 % | VIES dev K +27.4 % |
| R1-wonly | - | - | ok dev K -6.7 % |
| R2-rotate | indef. dev K nan % | indef. dev K nan % | ok dev K -1.2 % |
| R2-square | ok dev K -0.0 % | ok dev K -3.8 % | VIES dev K +13.1 % |
| R3-mild | VIES dev K -127.1 % | ok dev K -2.3 % | ok dev K -1.0 % |

## Resumo regime x DOF -> regime_bias_K? (|dev K| > 10 % vs referencia vx: R2-square/none/off; vy: R2-square/none/off; w: R2-rotate/none/off) (celula idealizada: ruido `none`, zona morta `off`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | VIES dev K -29.5 % | ok dev K -6.2 % | VIES dev K +16.5 % |
| R1-wonly | - | - | ok dev K -0.8 % |
| R2-rotate | indef. dev K nan % | indef. dev K nan % | ok dev K +0.0 % |
| R2-square | ok dev K +0.0 % | ok dev K +0.0 % | ok dev K -2.6 % |
| R3-mild | VIES dev K -127.1 % | ok dev K -2.4 % | ok dev K +3.5 % |

## w: R1 (zona morta on/off) vs R1-wonly vs R2-rotate vs R2-square vs R3/R3-mild

| celula | K med | dev K % | tau med | dev tau % | m_eff med | fit ho % | regime_bias_K |
|---|---|---|---|---|---|---|---|
| R1 / none / on | 1.2735 | +27.8 | 0.1839 | +482.5 | 1.5 | 24.6 | VIES |
| R1 / vision / on | 1.2697 | +27.4 | 0.1703 | +439.6 | 1.5 | 22.9 | VIES |
| R1 / none / off | 1.1603 | +16.5 | 0.1010 | +220.0 | 6.0 | 29.2 | VIES |
| R1 / vision / off | 1.1597 | +16.4 | 0.0983 | +211.5 | 6.0 | 26.8 | VIES |
| R1-wonly / none / on | 0.9353 | -6.1 | 0.0317 | +0.5 | 5.0 | 65.1 | ok |
| R1-wonly / vision / on | 0.9295 | -6.7 | 0.0304 | -3.6 | 5.0 | 58.4 | ok |
| R1-wonly / none / off | 0.9880 | -0.8 | 0.0333 | +5.4 | 5.0 | 80.9 | ok |
| R1-wonly / vision / off | 0.9882 | -0.8 | 0.0334 | +5.9 | 5.0 | 68.2 | ok |
| R2-rotate / none / on | 0.9843 | -1.2 | 0.0331 | +4.7 | 5.0 | -108360.4 | ok |
| R2-rotate / vision / on | 0.9843 | -1.2 | 0.0315 | -0.3 | 5.0 | -14.6 | ok |
| R2-rotate / none / off | 0.9963 | +0.0 | 0.0316 | +0.0 | 5.0 | 88.6 | ok |
| R2-rotate / vision / off | 0.9963 | +0.0 | 0.0307 | -2.7 | 5.0 | 26.8 | ok |
| R2-square / none / on | 1.1329 | +13.7 | 0.0128 | -59.4 | 6.0 | 32.9 | VIES |
| R2-square / vision / on | 1.1268 | +13.1 | 0.0125 | -60.5 | 6.0 | 17.0 | VIES |
| R2-square / none / off | 0.9708 | -2.6 | 0.0288 | -8.6 | 5.0 | 33.1 | ok |
| R2-square / vision / off | 0.9736 | -2.3 | 0.0300 | -4.9 | 5.0 | 17.7 | ok |
| R3-mild / none / on | 0.9451 | -5.1 | 0.0503 | +59.3 | 5.0 | 2.8 | ok |
| R3-mild / vision / on | 0.9860 | -1.0 | 0.0533 | +68.7 | 5.0 | 3.1 | ok |
| R3-mild / none / off | 1.0311 | +3.5 | 0.0378 | +19.7 | 5.5 | 3.5 | ok |
| R3-mild / vision / off | 1.0292 | +3.3 | 0.0382 | +21.1 | 5.0 | 3.6 | ok |

## Leitura

- H5' (dev K_w(R1) >= +10 % vs referencia R2-rotate e regime_bias_K falsa em R3-mild), celula realista (vision/on): dev K_w(R1) = +27.4 %, regime_bias_K R3-mild = nao -> CORROBORADA
- H5' (dev K_w(R1) >= +10 % vs referencia R2-rotate e regime_bias_K falsa em R3-mild), celula idealizada (none/off): dev K_w(R1) = +16.5 %, regime_bias_K R3-mild = nao -> CORROBORADA
- H6' (controle R1-wonly: |dev K_w| <= 10 %), celula realista: dev K_w(R1-wonly) = -6.7 % vs R1 = +27.4 %, regime_bias_K R1-wonly = nao -> CORROBORADA
- H6' (controle R1-wonly: |dev K_w| <= 10 %), celula idealizada: dev K_w(R1-wonly) = -0.8 % vs R1 = +16.5 %, regime_bias_K R1-wonly = nao -> CORROBORADA
- H7' (vx/vy: regime_bias_K falsa em R1 vs referencia R2-square), celula realista: vx: dev K -29.9 %, regime_bias_K SIM [desvio negativo: assinatura de saturacao de velocidade]; vy: dev K -5.7 %, regime_bias_K nao -> FALSIFICADA
- H7' (vx/vy: regime_bias_K falsa em R1 vs referencia R2-square), celula idealizada: vx: dev K -29.5 %, regime_bias_K SIM [desvio negativo: assinatura de saturacao de velocidade]; vy: dev K -6.2 %, regime_bias_K nao -> FALSIFICADA

Descritivo (nao entra no veredito v2): dev tau e dm_eff por celula nas tabelas acima; a bandeira
composta regime_bias de v1 e mantida so para comparacao.