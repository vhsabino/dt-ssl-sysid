# Identificabilidade in-silico (C1b-v2, re-registro): gerador mujoco-rollers - regime x ruido x zona morta - 20260907_2048

_Proveniencia: commit `cdef20c` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed 42 | gerado por `dtssl.analysis.identifiability_insilico` (dtssl 1.0.0a1) | gerador mujoco-rollers (opts {}) | n_rep=12 | estimador profile-NM align=legacy | 528 ajustes em 3.5 min (geracao de trajetorias 1.5 min)_

Re-registro C1b-v2: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_V2_20260907.md (emenda documentada
apos a execucao v1; muda SO: regime R3-mild dentro do envelope da rota b, referencias por DOF =
regimes dedicados de malha aberta (w: R2-rotate/none/off; vx, vy: R2-square/none/off) e regra
K-only regime_bias_K = |dev K| > 10 %; dev tau e dm_eff sao descritivos). v1 e seus artefatos
ficam intocados.

Pre-registro: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_20260907.md (adendo C1b: hipoteses
H5-H8, referencia e bandeira regime_bias fixadas antes de rodar) sobre o desenho de C1
(docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md).
GERADOR: `mujoco-rollers` via `dtssl.sim.world_plant.make_harness_plant` (MuJoCoWorld de um robo visto como
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

- Ts = 0.016667 s; gerador `mujoco-rollers` (`make_harness_plant`, opts {}), `reset(pose0, velb0=0)`, `pose[k] = step(cmd[k-1])` (driver de `free_run`, buffer de atraso vazio).
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

Referencia por DOF (gerador `mujoco-rollers`; celulas vx: R2-square/none/off; vy: R2-square/none/off; w: R2-rotate/none/off - pre-registrada C1b-v2) e sua distancia ao theta* do gemeo (contexto, nao criterio):

| DOF | celula de referencia | K ref | tau ref (s) | m_eff ref | K ref / K* - 1 | tau ref / tau* - 1 | m_eff ref - Td*/Ts |
|---|---|---|---|---|---|---|---|
| vx | R2-square/none/off | 0.9914 | 0.0461 | -1.0 | -11.4 % | -35.7 % | -5.14 |
| vy | R2-square/none/off | 0.9865 | 0.0655 | -1.0 | -6.3 % | -48.5 % | -4.39 |
| w | R2-rotate/none/off | 0.9961 | 0.0288 | -1.0 | -0.5 % | -65.2 % | -6.34 |

Checagem do estimador literal do artigo (NM 3-D em [K, tau, Td] a partir de X0, `r3`) contra o perfil em m, celula idealizada R3/none/off, split da replica 0:

| DOF | NM 3-D: K | tau | Td (s) | m_eff | custo | perfil: K | tau | m_eff | custo |
|---|---|---|---|---|---|---|---|---|---|
| vx | -0.2385 | 0.1133 | 0.0787 | 4 | 1933.649 | -0.2369 | 0.1000 | 5 | 1933.512 |
| vy | 0.9692 | 0.1351 | 0.0325 | 1 | 125.214 | 0.9692 | 0.1351 | 1 | 125.213 |
| w | 1.0712 | 0.0870 | 0.0000 | -1 | 90277.303 | 1.0713 | 0.0870 | -1 | 90277.303 |

## DOF vx (K* = 1.1192, tau* = 0.0718 s, Td*/Ts = 4.14 amostras, planta aplica 5)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6896 [0.6347, 0.7447] | -38.4 | 0.0333 [0.0282, 0.0402] | -53.7 | -1.0 [-1.0, -1.0] | -5.14 | 9.8 | 62.8 | 68.6 | -30.4 | -27.9 | 0.0 | VIES | VIES |
| R1 | vision | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6897 [0.6347, 0.7447] | -38.4 | 0.0339 [0.0288, 0.0395] | -52.8 | -1.0 [-1.0, -1.0] | -5.14 | 9.8 | 62.7 | 68.4 | -30.4 | -26.6 | 0.0 | VIES | VIES |
| R1 | none | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6831 [0.6267, 0.7396] | -39.0 | 0.0353 [0.0299, 0.0425] | -50.9 | -1.0 [-1.0, -1.0] | -5.14 | 10.1 | 61.8 | 67.9 | -31.1 | -23.6 | 0.0 | VIES | VIES |
| R1 | vision | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6831 [0.6266, 0.7397] | -39.0 | 0.0358 [0.0305, 0.0420] | -50.1 | -1.0 [-1.0, -1.0] | -5.14 | 10.1 | 61.7 | 67.7 | -31.1 | -22.4 | 0.0 | VIES | VIES |
| R2-rotate | none | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | none | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-square | none | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9914 [0.9908, 0.9920] | -11.4 | 0.0461 [0.0451, 0.0471] | -35.7 | -1.0 [-1.0, -1.0] | -5.14 | 0.1 | 95.4 | 95.7 | +0.0 | +0.0 | 0.0 | ok | ok |
| R2-square | vision | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9913 [0.9909, 0.9919] | -11.4 | 0.0460 [0.0451, 0.0470] | -35.9 | -1.0 [-1.0, -1.0] | -5.14 | 0.1 | 93.1 | 93.2 | -0.0 | -0.3 | 0.0 | ok | ok |
| R2-square | none | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9917 [0.9911, 0.9922] | -11.4 | 0.0461 [0.0450, 0.0470] | -35.8 | -1.0 [-1.0, -1.0] | -5.14 | 0.1 | 95.5 | 95.6 | +0.0 | -0.1 | 0.0 | ok | ok |
| R2-square | vision | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9916 [0.9913, 0.9921] | -11.4 | 0.0460 [0.0450, 0.0471] | -35.9 | -1.0 [-1.0, -1.0] | -5.14 | 0.1 | 93.2 | 93.2 | +0.0 | -0.3 | 0.0 | ok | ok |
| R3-mild | none | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | -0.2692 [-0.3428, -0.1806] | -124.0 | 0.0936 [0.0775, 0.1137] | +30.4 | 5.0 [3.8, 6.0] | 0.86 | 14.5 | -10.7 | -0.0 | -127.1 | +102.9 | 6.0 | VIES | VIES |
| R3-mild | vision | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | -0.2691 [-0.3423, -0.1807] | -124.0 | 0.0934 [0.0781, 0.1137] | +30.1 | 5.0 [3.8, 6.0] | 0.86 | 14.4 | -10.7 | 0.0 | -127.1 | +102.3 | 6.0 | VIES | VIES |
| R3-mild | none | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | -0.2724 [-0.3431, -0.1810] | -124.3 | 0.0900 [0.0761, 0.1137] | +25.3 | 5.0 [3.8, 7.0] | 0.86 | 14.5 | -10.5 | -0.1 | -127.5 | +94.9 | 6.0 | VIES | VIES |
| R3-mild | vision | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | -0.2723 [-0.3429, -0.1813] | -124.3 | 0.0901 [0.0768, 0.1137] | +25.5 | 5.0 [3.8, 7.0] | 0.86 | 14.4 | -10.4 | -0.0 | -127.5 | +95.2 | 6.0 | VIES | VIES |

## DOF vy (K* = 1.0524, tau* = 0.1273 s, Td*/Ts = 3.39 amostras, planta aplica 4)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9191 [0.9116, 0.9296] | -12.7 | 0.0671 [0.0662, 0.0678] | -47.3 | -1.0 [-1.0, -1.0] | -4.39 | 1.7 | 86.9 | 89.9 | -6.8 | +2.3 | 0.0 | ok | ok |
| R1 | vision | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9192 [0.9115, 0.9294] | -12.7 | 0.0671 [0.0660, 0.0679] | -47.3 | -1.0 [-1.0, -1.0] | -4.39 | 1.7 | 86.1 | 89.3 | -6.8 | +2.4 | 0.0 | ok | ok |
| R1 | none | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9549 [0.9525, 0.9727] | -9.3 | 0.0758 [0.0685, 0.0777] | -40.5 | -1.0 [-1.0, -0.8] | -4.39 | 1.9 | 91.1 | 92.0 | -3.2 | +15.6 | 0.0 | VIES | ok |
| R1 | vision | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9549 [0.9523, 0.9727] | -9.3 | 0.0758 [0.0686, 0.0776] | -40.4 | -1.0 [-1.0, -0.8] | -4.39 | 1.9 | 90.3 | 91.3 | -3.2 | +15.7 | 0.0 | VIES | ok |
| R2-rotate | none | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | none | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-square | none | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9865 [0.9863, 0.9909] | -6.3 | 0.0655 [0.0444, 0.0668] | -48.5 | -1.0 [-1.0, 0.0] | -4.39 | 0.4 | 94.1 | 94.1 | +0.0 | +0.0 | 0.0 | ok | ok |
| R2-square | vision | off | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9866 [0.9863, 0.9908] | -6.3 | 0.0652 [0.0498, 0.0663] | -48.8 | -1.0 [-1.0, 0.0] | -4.39 | 0.4 | 92.2 | 92.0 | +0.0 | -0.5 | 0.0 | ok | ok |
| R2-square | none | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9857 [0.9853, 0.9909] | -6.3 | 0.0657 [0.0444, 0.0669] | -48.4 | -1.0 [-1.0, 0.0] | -4.39 | 0.5 | 94.1 | 94.0 | -0.1 | +0.2 | 0.0 | ok | ok |
| R2-square | vision | on | 11 (7/4) | 9.8 / 8.5 / 1.3 | 0.9860 [0.9853, 0.9908] | -6.3 | 0.0655 [0.0553, 0.0670] | -48.6 | -1.0 [-1.0, -0.8] | -4.39 | 0.5 | 92.2 | 92.1 | -0.1 | -0.1 | 0.0 | ok | ok |
| R3-mild | none | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9679 [0.9603, 0.9716] | -8.0 | 0.1373 [0.1336, 0.1403] | +7.8 | 1.0 [1.0, 1.0] | -2.39 | 1.1 | 70.6 | 71.0 | -1.9 | +109.5 | 2.0 | VIES | ok |
| R3-mild | vision | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9677 [0.9605, 0.9713] | -8.1 | 0.1373 [0.1334, 0.1405] | +7.8 | 1.0 [1.0, 1.0] | -2.39 | 1.0 | 69.8 | 70.2 | -1.9 | +109.5 | 2.0 | VIES | ok |
| R3-mild | none | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9580 [0.9529, 0.9668] | -9.0 | 0.1369 [0.1294, 0.1421] | +7.5 | 1.0 [1.0, 1.0] | -2.39 | 1.3 | 66.8 | 69.5 | -2.9 | +108.9 | 2.0 | VIES | ok |
| R3-mild | vision | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | 0.9591 [0.9528, 0.9669] | -8.9 | 0.1372 [0.1330, 0.1420] | +7.7 | 1.0 [1.0, 1.0] | -2.39 | 1.3 | 66.1 | 68.7 | -2.8 | +109.2 | 2.0 | VIES | ok |

## DOF w (K* = 1.0016, tau* = 0.0828 s, Td*/Ts = 5.34 amostras, planta aplica 6)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1563 [1.0591, 1.2037] | +15.4 | 0.1385 [0.1134, 0.2038] | +67.3 | -1.0 [-1.0, -1.0] | -6.34 | 14.4 | 26.0 | 9.2 | +16.1 | +380.6 | 0.0 | VIES | VIES |
| R1 | vision | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1180 [1.0480, 1.1909] | +11.6 | 0.1374 [0.1115, 0.2045] | +66.0 | -1.0 [-1.0, -1.0] | -6.34 | 14.3 | 23.8 | 9.0 | +12.2 | +376.7 | 0.0 | VIES | VIES |
| R1 | none | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1427 [1.1065, 1.2139] | +14.1 | 0.1123 [0.0964, 0.1486] | +35.6 | -1.0 [-1.0, -1.0] | -6.34 | 10.7 | 23.8 | 8.7 | +14.7 | +289.6 | 0.0 | VIES | VIES |
| R1 | vision | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1429 [1.0919, 1.2091] | +14.1 | 0.1117 [0.0955, 0.1483] | +35.0 | -1.0 [-1.0, -1.0] | -6.34 | 11.7 | 23.5 | 8.5 | +14.7 | +287.8 | 0.0 | VIES | VIES |
| R1-wonly | none | off | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9878 [0.9863, 0.9893] | -1.4 | 0.0336 [0.0328, 0.0391] | -59.4 | -1.0 [-1.0, -1.0] | -6.34 | 0.3 | 80.8 | 91.2 | -0.8 | +16.7 | 0.0 | VIES | ok |
| R1-wonly | vision | off | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9882 [0.9852, 0.9899] | -1.3 | 0.0338 [0.0328, 0.0389] | -59.2 | -1.0 [-1.0, -1.0] | -6.34 | 0.5 | 67.7 | 76.7 | -0.8 | +17.2 | 0.0 | VIES | ok |
| R1-wonly | none | on | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9336 [0.9292, 0.9364] | -6.8 | 0.0328 [0.0319, 0.0372] | -60.4 | -1.0 [-1.0, -1.0] | -6.34 | 0.7 | 68.2 | 74.9 | -6.3 | +13.7 | 0.0 | ok | ok |
| R1-wonly | vision | on | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9306 [0.9264, 0.9355] | -7.1 | 0.0319 [0.0311, 0.0362] | -61.5 | -1.0 [-1.0, -1.0] | -6.34 | 0.9 | 60.6 | 66.6 | -6.6 | +10.7 | 0.0 | ok | ok |
| R2-rotate | none | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9961 [0.9958, 0.9963] | -0.5 | 0.0288 [0.0286, 0.0289] | -65.2 | -1.0 [-1.0, -1.0] | -6.34 | 0.1 | 69.2 | 68.0 | +0.0 | +0.0 | 0.0 | ok | ok |
| R2-rotate | vision | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9961 [0.9959, 0.9964] | -0.6 | 0.0279 [0.0262, 0.0297] | -66.3 | -1.0 [-1.0, -1.0] | -6.34 | 0.0 | 6.3 | 1.3 | -0.0 | -3.3 | 0.0 | ok | ok |
| R2-rotate | none | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9842 [0.9617, 0.9883] | -1.7 | 0.0289 [0.0288, 0.0289] | -65.1 | -1.0 [-1.0, -1.0] | -6.34 | 2.7 | -151636.9 | 47.4 | -1.2 | +0.3 | 0.0 | ok | ok |
| R2-rotate | vision | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9842 [0.9619, 0.9882] | -1.7 | 0.0279 [0.0263, 0.0300] | -66.3 | -1.0 [-1.0, -1.0] | -6.34 | 2.6 | -61.1 | 1.0 | -1.2 | -3.1 | 0.0 | ok | ok |
| R2-square | none | off | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9666 [0.9595, 0.9727] | -3.5 | 0.0264 [0.0258, 0.0287] | -68.1 | -1.0 [-1.0, -1.0] | -6.34 | 1.3 | 33.5 | 23.9 | -3.0 | -8.3 | 0.0 | ok | ok |
| R2-square | vision | off | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9670 [0.9590, 0.9739] | -3.5 | 0.0275 [0.0257, 0.0297] | -66.8 | -1.0 [-1.0, -1.0] | -6.34 | 1.5 | 17.9 | 13.3 | -2.9 | -4.5 | 0.0 | ok | ok |
| R2-square | none | on | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9800 [0.9722, 0.9859] | -2.2 | 0.0247 [0.0227, 0.0262] | -70.2 | -1.0 [-1.0, -1.0] | -6.34 | 1.4 | 32.3 | 26.0 | -1.6 | -14.4 | 0.0 | ok | ok |
| R2-square | vision | on | 11 (7/4) | 9.8 / 9.8 / 1.3 | 0.9775 [0.9658, 0.9859] | -2.4 | 0.0255 [0.0229, 0.0276] | -69.2 | -1.0 [-1.0, -1.0] | -6.34 | 2.0 | 17.4 | 15.2 | -1.9 | -11.4 | 0.0 | ok | ok |
| R3-mild | none | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 1.0153 [0.9649, 1.0569] | +1.4 | 0.0531 [0.0460, 0.0750] | -35.8 | -1.0 [-1.0, -1.0] | -6.34 | 9.2 | 2.9 | 3.3 | +1.9 | +84.4 | 0.0 | VIES | ok |
| R3-mild | vision | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 1.0462 [0.9975, 1.1005] | +4.5 | 0.0460 [0.0452, 0.0550] | -44.4 | -1.0 [-1.0, -1.0] | -6.34 | 10.3 | 3.1 | 4.1 | +5.0 | +59.8 | 0.0 | VIES | ok |
| R3-mild | none | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | 1.0784 [1.0482, 1.1311] | +7.7 | 0.0710 [0.0461, 0.1360] | -14.2 | -1.0 [-1.0, -1.0] | -6.34 | 8.3 | 2.4 | 3.8 | +8.3 | +146.4 | 0.0 | VIES | ok |
| R3-mild | vision | on | 12 (8/4) | 22.5 / 22.5 / 0.0 | 1.0648 [1.0150, 1.1133] | +6.3 | 0.0670 [0.0457, 0.1216] | -19.0 | -1.0 [-1.0, -1.0] | -6.34 | 9.8 | 2.7 | 3.4 | +6.9 | +132.6 | 0.0 | VIES | ok |

## Resumo regime x DOF -> regime_bias_K? (|dev K| > 10 % vs referencia vx: R2-square/none/off; vy: R2-square/none/off; w: R2-rotate/none/off) (celula realista: ruido `vision`, zona morta `on`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | VIES dev K -31.1 % | ok dev K -3.2 % | VIES dev K +14.7 % |
| R1-wonly | - | - | ok dev K -6.6 % |
| R2-rotate | indef. dev K nan % | indef. dev K nan % | ok dev K -1.2 % |
| R2-square | ok dev K +0.0 % | ok dev K -0.1 % | ok dev K -1.9 % |
| R3-mild | VIES dev K -127.5 % | ok dev K -2.8 % | ok dev K +6.9 % |

## Resumo regime x DOF -> regime_bias_K? (|dev K| > 10 % vs referencia vx: R2-square/none/off; vy: R2-square/none/off; w: R2-rotate/none/off) (celula idealizada: ruido `none`, zona morta `off`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | VIES dev K -30.4 % | ok dev K -6.8 % | VIES dev K +16.1 % |
| R1-wonly | - | - | ok dev K -0.8 % |
| R2-rotate | indef. dev K nan % | indef. dev K nan % | ok dev K +0.0 % |
| R2-square | ok dev K +0.0 % | ok dev K +0.0 % | ok dev K -3.0 % |
| R3-mild | VIES dev K -127.1 % | ok dev K -1.9 % | ok dev K +1.9 % |

## w: R1 (zona morta on/off) vs R1-wonly vs R2-rotate vs R2-square vs R3/R3-mild

| celula | K med | dev K % | tau med | dev tau % | m_eff med | fit ho % | regime_bias_K |
|---|---|---|---|---|---|---|---|
| R1 / none / on | 1.1427 | +14.7 | 0.1123 | +289.6 | -1.0 | 23.8 | VIES |
| R1 / vision / on | 1.1429 | +14.7 | 0.1117 | +287.8 | -1.0 | 23.5 | VIES |
| R1 / none / off | 1.1563 | +16.1 | 0.1385 | +380.6 | -1.0 | 26.0 | VIES |
| R1 / vision / off | 1.1180 | +12.2 | 0.1374 | +376.7 | -1.0 | 23.8 | VIES |
| R1-wonly / none / on | 0.9336 | -6.3 | 0.0328 | +13.7 | -1.0 | 68.2 | ok |
| R1-wonly / vision / on | 0.9306 | -6.6 | 0.0319 | +10.7 | -1.0 | 60.6 | ok |
| R1-wonly / none / off | 0.9878 | -0.8 | 0.0336 | +16.7 | -1.0 | 80.8 | ok |
| R1-wonly / vision / off | 0.9882 | -0.8 | 0.0338 | +17.2 | -1.0 | 67.7 | ok |
| R2-rotate / none / on | 0.9842 | -1.2 | 0.0289 | +0.3 | -1.0 | -151636.9 | ok |
| R2-rotate / vision / on | 0.9842 | -1.2 | 0.0279 | -3.1 | -1.0 | -61.1 | ok |
| R2-rotate / none / off | 0.9961 | +0.0 | 0.0288 | +0.0 | -1.0 | 69.2 | ok |
| R2-rotate / vision / off | 0.9961 | -0.0 | 0.0279 | -3.3 | -1.0 | 6.3 | ok |
| R2-square / none / on | 0.9800 | -1.6 | 0.0247 | -14.4 | -1.0 | 32.3 | ok |
| R2-square / vision / on | 0.9775 | -1.9 | 0.0255 | -11.4 | -1.0 | 17.4 | ok |
| R2-square / none / off | 0.9666 | -3.0 | 0.0264 | -8.3 | -1.0 | 33.5 | ok |
| R2-square / vision / off | 0.9670 | -2.9 | 0.0275 | -4.5 | -1.0 | 17.9 | ok |
| R3-mild / none / on | 1.0784 | +8.3 | 0.0710 | +146.4 | -1.0 | 2.4 | ok |
| R3-mild / vision / on | 1.0648 | +6.9 | 0.0670 | +132.6 | -1.0 | 2.7 | ok |
| R3-mild / none / off | 1.0153 | +1.9 | 0.0531 | +84.4 | -1.0 | 2.9 | ok |
| R3-mild / vision / off | 1.0462 | +5.0 | 0.0460 | +59.8 | -1.0 | 3.1 | ok |

## Leitura

- H5' (dev K_w(R1) >= +10 % vs referencia R2-rotate e regime_bias_K falsa em R3-mild), celula realista (vision/on): dev K_w(R1) = +14.7 %, regime_bias_K R3-mild = nao -> CORROBORADA
- H5' (dev K_w(R1) >= +10 % vs referencia R2-rotate e regime_bias_K falsa em R3-mild), celula idealizada (none/off): dev K_w(R1) = +16.1 %, regime_bias_K R3-mild = nao -> CORROBORADA
- H6' (controle R1-wonly: |dev K_w| <= 10 %), celula realista: dev K_w(R1-wonly) = -6.6 % vs R1 = +14.7 %, regime_bias_K R1-wonly = nao -> CORROBORADA
- H6' (controle R1-wonly: |dev K_w| <= 10 %), celula idealizada: dev K_w(R1-wonly) = -0.8 % vs R1 = +16.1 %, regime_bias_K R1-wonly = nao -> CORROBORADA
- H7' (vx/vy: regime_bias_K falsa em R1 vs referencia R2-square), celula realista: vx: dev K -31.1 %, regime_bias_K SIM [desvio negativo: assinatura de saturacao de velocidade]; vy: dev K -3.2 %, regime_bias_K nao -> FALSIFICADA
- H7' (vx/vy: regime_bias_K falsa em R1 vs referencia R2-square), celula idealizada: vx: dev K -30.4 %, regime_bias_K SIM [desvio negativo: assinatura de saturacao de velocidade]; vy: dev K -6.8 %, regime_bias_K nao -> FALSIFICADA

Descritivo (nao entra no veredito v2): dev tau e dm_eff por celula nas tabelas acima; a bandeira
composta regime_bias de v1 e mantida so para comparacao.