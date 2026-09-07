# Identificabilidade in-silico (C1b): gerador mujoco-rollers - regime x ruido x zona morta - 20260907_2041

_Proveniencia: commit `cdef20c` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed 42 | gerado por `dtssl.analysis.identifiability_insilico` (dtssl 1.0.0a1) | gerador mujoco-rollers (opts {}) | n_rep=12 | estimador profile-NM align=legacy | 384 ajustes em 3.1 min (geracao de trajetorias 1.5 min)_

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
- Regimes (eventos): `front_to_back` = 4 eventos; `side_to_side` = 13 eventos; `shoot_to_goal` = 18 eventos; `shoot_to_goal@wonly` = 18 eventos; `rotate` = 10 eventos; `R3` = 12 eventos
- R1 (pareamento do artigo): vx `front_to_back`, vy `side_to_side`, w `shoot_to_goal`; R1-wonly = as mesmas sequencias de R1 com vx = vy = 0 (controle, so DOF w); R2-rotate `rotate` (10 eventos, inclui +-0.25/+-0.5 rad/s); R2-square `square`; R3 sintetico: 12 eventos x 10 s, degraus de 0.3-1.2 s, amplitude +-[0.6, 1.5] m/s (vx, vy) e +-[1.5, 4.0] rad/s (w), 3 DOFs simultaneos, seed de desenho 42.
- Ruido (sigma_pos mm, sigma_theta rad): `none` = (0.0, 0.0); `vision` = (2.0, 0.01); i.i.d. por amostra, seed 42 + rep (numeros aleatorios comuns entre niveis).
- Zona morta do gerador: limiar de firmware 1.567 rad/s por roda aplicado pelo MuJoCoWorld (`deadzone=True`); as fracoes mascaradas abaixo usam a mesma regra por roda (`mask_deadzone`).
- Monte Carlo: n_rep = 12 por celula; split 2/3-1/3 por evento seeded (seed 42 + 1000 + rep); fit nos eventos de treino, fit % medio no hold-out.
- Estimador: `legacy_uy_series` (SG 7/2 + diferencas centrais, mm -> m) + Nelder-Mead em (K, tau) para cada atraso inteiro m = 0..12 (custo de erro de saida, `simulate_fopdt` align=legacy, clamps tau >= 1e-4), m de menor custo de treino; X0 (K, tau) = (1.0, 0.08) (vx, vy) / (1.3, 0.03) (w); NM {'maxiter': 400, 'xatol': 0.0001, 'fatol': 0.001}. m_eff = m - 1 (align legacy aplica uma amostra a menos de atraso que a planta; common.py).
- Regra (por celula, mediana/IQR sobre as replicas): |vies K| <= 10 %, |vies tau| <= 15 %, |mediana(m_eff) - Td*/Ts| <= 1 amostra, IQR(K)/K* <= 20 %; escore = criterios satisfeitos (0-4); recuperado = 4/4. Regra C1b: referencia = celula R3/none/off por DOF; regime_bias = |dev K| > 10 % ou |dev tau| > 15 %.

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
| `R3` | 12 | 7200 | 14.3 % | 14.3 % | 14.3 % | 14.3 % | 0.0 % |

Referencia por DOF (gerador `mujoco-rollers`; celulas R3/none/off - pre-registrada C1b-v1) e sua distancia ao theta* do gemeo (contexto, nao criterio):

| DOF | celula de referencia | K ref | tau ref (s) | m_eff ref | K ref / K* - 1 | tau ref / tau* - 1 | m_eff ref - Td*/Ts |
|---|---|---|---|---|---|---|---|
| vx | R3/none/off | -0.4550 | 0.1067 | 3.0 | -140.6 % | +48.7 % | -1.14 |
| vy | R3/none/off | 0.8729 | 0.2092 | 1.0 | -17.1 % | +64.3 % | -2.39 |
| w | R3/none/off | 1.0423 | 0.1091 | -1.0 | +4.1 % | +31.8 % | -6.34 |

Checagem do estimador literal do artigo (NM 3-D em [K, tau, Td] a partir de X0, `r3`) contra o perfil em m, celula idealizada R3/none/off, split da replica 0:

| DOF | NM 3-D: K | tau | Td (s) | m_eff | custo | perfil: K | tau | m_eff | custo |
|---|---|---|---|---|---|---|---|---|---|
| vx | -0.4467 | 0.1106 | 0.0727 | 4 | 3592.054 | -0.4507 | 0.1238 | 3 | 3591.411 |
| vy | 0.8985 | 0.2193 | 0.0293 | 1 | 900.446 | 0.8984 | 0.2193 | 1 | 900.446 |
| w | 1.0120 | 0.0632 | 0.0362 | 2 | 89905.397 | 1.0418 | 0.1002 | 0 | 89663.545 |

## DOF vx (K* = 1.1192, tau* = 0.0718 s, Td*/Ts = 4.14 amostras, planta aplica 5)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6896 [0.6347, 0.7447] | -38.4 | 0.0333 [0.0282, 0.0402] | -53.7 | -1.0 [-1.0, -1.0] | -5.14 | 9.8 | 62.8 | 68.6 | -251.6 | -68.8 | -4.0 | VIES | VIES |
| R1 | vision | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6897 [0.6347, 0.7447] | -38.4 | 0.0339 [0.0288, 0.0395] | -52.8 | -1.0 [-1.0, -1.0] | -5.14 | 9.8 | 62.7 | 68.4 | -251.6 | -68.3 | -4.0 | VIES | VIES |
| R1 | none | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6831 [0.6267, 0.7396] | -39.0 | 0.0353 [0.0299, 0.0425] | -50.9 | -1.0 [-1.0, -1.0] | -5.14 | 10.1 | 61.8 | 67.9 | -250.1 | -67.0 | -4.0 | VIES | VIES |
| R1 | vision | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6831 [0.6266, 0.7397] | -39.0 | 0.0358 [0.0305, 0.0420] | -50.1 | -1.0 [-1.0, -1.0] | -5.14 | 10.1 | 61.7 | 67.7 | -250.2 | -66.4 | -4.0 | VIES | VIES |
| R2-rotate | none | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | none | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | -0.4550 [-0.5288, -0.4369] | -140.6 | 0.1067 [0.0967, 0.1423] | +48.7 | 3.0 [1.8, 4.0] | -1.14 | 8.2 | 2.8 | 19.9 | -0.0 | +0.0 | 0.0 | ok | ok |
| R3 | vision | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | -0.4550 [-0.5286, -0.4369] | -140.7 | 0.1066 [0.0968, 0.1423] | +48.4 | 3.0 [1.8, 4.0] | -1.14 | 8.2 | 2.8 | 19.9 | +0.0 | -0.2 | 0.0 | ok | ok |
| R3 | none | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | -0.4626 [-0.5413, -0.4433] | -141.3 | 0.1150 [0.0983, 0.1501] | +60.2 | 3.0 [1.0, 4.0] | -1.14 | 8.8 | 2.5 | 19.4 | +1.7 | +7.7 | 0.0 | ok | ok |
| R3 | vision | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | -0.4626 [-0.5411, -0.4433] | -141.3 | 0.1147 [0.0982, 0.1500] | +59.7 | 3.0 [1.0, 4.0] | -1.14 | 8.7 | 2.5 | 19.4 | +1.7 | +7.4 | 0.0 | ok | ok |

## DOF vy (K* = 1.0524, tau* = 0.1273 s, Td*/Ts = 3.39 amostras, planta aplica 4)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9191 [0.9116, 0.9296] | -12.7 | 0.0671 [0.0662, 0.0678] | -47.3 | -1.0 [-1.0, -1.0] | -4.39 | 1.7 | 86.9 | 89.9 | +5.3 | -67.9 | -2.0 | VIES | ok |
| R1 | vision | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9192 [0.9115, 0.9294] | -12.7 | 0.0671 [0.0660, 0.0679] | -47.3 | -1.0 [-1.0, -1.0] | -4.39 | 1.7 | 86.1 | 89.3 | +5.3 | -67.9 | -2.0 | VIES | ok |
| R1 | none | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9549 [0.9525, 0.9727] | -9.3 | 0.0758 [0.0685, 0.0777] | -40.5 | -1.0 [-1.0, -0.8] | -4.39 | 1.9 | 91.1 | 92.0 | +9.4 | -63.8 | -2.0 | VIES | ok |
| R1 | vision | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9549 [0.9523, 0.9727] | -9.3 | 0.0758 [0.0686, 0.0776] | -40.4 | -1.0 [-1.0, -0.8] | -4.39 | 1.9 | 90.3 | 91.3 | +9.4 | -63.7 | -2.0 | VIES | ok |
| R2-rotate | none | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | none | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.8729 [0.8674, 0.8840] | -17.1 | 0.2092 [0.2011, 0.2120] | +64.3 | 1.0 [1.0, 1.0] | -2.39 | 1.6 | 55.1 | 53.3 | +0.0 | +0.0 | 0.0 | ok | ok |
| R3 | vision | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.8730 [0.8671, 0.8840] | -17.0 | 0.2091 [0.2011, 0.2121] | +64.2 | 1.0 [1.0, 1.0] | -2.39 | 1.6 | 54.9 | 53.2 | +0.0 | -0.0 | 0.0 | ok | ok |
| R3 | none | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.8945 [0.8904, 0.9089] | -15.0 | 0.2172 [0.2123, 0.2280] | +70.6 | 1.0 [0.8, 1.0] | -2.39 | 1.8 | 55.8 | 54.8 | +2.5 | +3.8 | 0.0 | ok | ok |
| R3 | vision | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.8944 [0.8905, 0.9088] | -15.0 | 0.2173 [0.2123, 0.2280] | +70.7 | 1.0 [0.8, 1.0] | -2.39 | 1.7 | 55.6 | 54.6 | +2.5 | +3.9 | 0.0 | ok | ok |

## DOF w (K* = 1.0016, tau* = 0.0828 s, Td*/Ts = 5.34 amostras, planta aplica 6)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1563 [1.0591, 1.2037] | +15.4 | 0.1385 [0.1134, 0.2038] | +67.3 | -1.0 [-1.0, -1.0] | -6.34 | 14.4 | 26.0 | 9.2 | +10.9 | +26.9 | 0.0 | VIES | VIES |
| R1 | vision | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1180 [1.0480, 1.1909] | +11.6 | 0.1374 [0.1115, 0.2045] | +66.0 | -1.0 [-1.0, -1.0] | -6.34 | 14.3 | 23.8 | 9.0 | +7.3 | +25.9 | 0.0 | VIES | ok |
| R1 | none | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1427 [1.1065, 1.2139] | +14.1 | 0.1123 [0.0964, 0.1486] | +35.6 | -1.0 [-1.0, -1.0] | -6.34 | 10.7 | 23.8 | 8.7 | +9.6 | +2.9 | 0.0 | ok | ok |
| R1 | vision | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1429 [1.0919, 1.2091] | +14.1 | 0.1117 [0.0955, 0.1483] | +35.0 | -1.0 [-1.0, -1.0] | -6.34 | 11.7 | 23.5 | 8.5 | +9.7 | +2.4 | 0.0 | ok | ok |
| R1-wonly | none | off | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9878 [0.9863, 0.9893] | -1.4 | 0.0336 [0.0328, 0.0391] | -59.4 | -1.0 [-1.0, -1.0] | -6.34 | 0.3 | 80.8 | 91.2 | -5.2 | -69.2 | 0.0 | VIES | ok |
| R1-wonly | vision | off | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9882 [0.9852, 0.9899] | -1.3 | 0.0338 [0.0328, 0.0389] | -59.2 | -1.0 [-1.0, -1.0] | -6.34 | 0.5 | 67.7 | 76.7 | -5.2 | -69.1 | 0.0 | VIES | ok |
| R1-wonly | none | on | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9336 [0.9292, 0.9364] | -6.8 | 0.0328 [0.0319, 0.0372] | -60.4 | -1.0 [-1.0, -1.0] | -6.34 | 0.7 | 68.2 | 74.9 | -10.4 | -70.0 | 0.0 | VIES | VIES |
| R1-wonly | vision | on | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9306 [0.9264, 0.9355] | -7.1 | 0.0319 [0.0311, 0.0362] | -61.5 | -1.0 [-1.0, -1.0] | -6.34 | 0.9 | 60.6 | 66.6 | -10.7 | -70.8 | 0.0 | VIES | VIES |
| R2-rotate | none | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9961 [0.9958, 0.9963] | -0.5 | 0.0288 [0.0286, 0.0289] | -65.2 | -1.0 [-1.0, -1.0] | -6.34 | 0.1 | 69.2 | 68.0 | -4.4 | -73.6 | 0.0 | VIES | ok |
| R2-rotate | vision | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9961 [0.9959, 0.9964] | -0.6 | 0.0279 [0.0262, 0.0297] | -66.3 | -1.0 [-1.0, -1.0] | -6.34 | 0.0 | 6.3 | 1.3 | -4.4 | -74.5 | 0.0 | VIES | ok |
| R2-rotate | none | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9842 [0.9617, 0.9883] | -1.7 | 0.0289 [0.0288, 0.0289] | -65.1 | -1.0 [-1.0, -1.0] | -6.34 | 2.7 | -151636.9 | 47.4 | -5.6 | -73.5 | 0.0 | VIES | ok |
| R2-rotate | vision | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9842 [0.9619, 0.9882] | -1.7 | 0.0279 [0.0263, 0.0300] | -66.3 | -1.0 [-1.0, -1.0] | -6.34 | 2.6 | -61.1 | 1.0 | -5.6 | -74.4 | 0.0 | VIES | ok |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0423 [1.0241, 1.0685] | +4.1 | 0.1091 [0.1031, 0.1246] | +31.8 | -1.0 [-1.0, 0.0] | -6.34 | 4.4 | 11.4 | 11.4 | +0.0 | +0.0 | 0.0 | ok | ok |
| R3 | vision | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0476 [1.0172, 1.0562] | +4.6 | 0.0868 [0.0744, 0.1053] | +4.9 | 0.0 [-1.0, 0.0] | -5.34 | 3.9 | 11.0 | 12.0 | +0.5 | -20.4 | 1.0 | VIES | ok |
| R3 | none | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.9887 [0.9743, 1.0268] | -1.3 | 0.0815 [0.0714, 0.0904] | -1.5 | -1.0 [-1.0, 0.0] | -6.34 | 5.2 | 11.2 | 13.9 | -5.1 | -25.3 | 0.0 | VIES | ok |
| R3 | vision | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.9852 [0.9743, 1.0196] | -1.6 | 0.0761 [0.0716, 0.0892] | -8.0 | -0.5 [-1.0, 0.0] | -5.84 | 4.5 | 11.2 | 13.8 | -5.5 | -30.2 | 0.5 | VIES | ok |

## Resumo regime x DOF -> regime_bias? (dev K vs referencia R3/none/off) (celula realista: ruido `vision`, zona morta `on`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | VIES dev K -250.2 % | VIES dev K +9.4 % | ok dev K +9.7 % |
| R1-wonly | - | - | VIES dev K -10.7 % |
| R2-rotate | indef. dev K nan % | indef. dev K nan % | VIES dev K -5.6 % |
| R3 | ok dev K +1.7 % | ok dev K +2.5 % | VIES dev K -5.5 % |

## Resumo regime x DOF -> regime_bias? (dev K vs referencia R3/none/off) (celula idealizada: ruido `none`, zona morta `off`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | VIES dev K -251.6 % | VIES dev K +5.3 % | VIES dev K +10.9 % |
| R1-wonly | - | - | VIES dev K -5.2 % |
| R2-rotate | indef. dev K nan % | indef. dev K nan % | VIES dev K -4.4 % |
| R3 | ok dev K -0.0 % | ok dev K +0.0 % | ok dev K +0.0 % |

## w: R1 (zona morta on/off) vs R1-wonly vs R2-rotate vs R2-square vs R3/R3-mild

| celula | K med | dev K % | tau med | dev tau % | m_eff med | fit ho % | regime_bias |
|---|---|---|---|---|---|---|---|
| R1 / none / on | 1.1427 | +9.6 | 0.1123 | +2.9 | -1.0 | 23.8 | ok |
| R1 / vision / on | 1.1429 | +9.7 | 0.1117 | +2.4 | -1.0 | 23.5 | ok |
| R1 / none / off | 1.1563 | +10.9 | 0.1385 | +26.9 | -1.0 | 26.0 | VIES |
| R1 / vision / off | 1.1180 | +7.3 | 0.1374 | +25.9 | -1.0 | 23.8 | VIES |
| R1-wonly / none / on | 0.9336 | -10.4 | 0.0328 | -70.0 | -1.0 | 68.2 | VIES |
| R1-wonly / vision / on | 0.9306 | -10.7 | 0.0319 | -70.8 | -1.0 | 60.6 | VIES |
| R1-wonly / none / off | 0.9878 | -5.2 | 0.0336 | -69.2 | -1.0 | 80.8 | VIES |
| R1-wonly / vision / off | 0.9882 | -5.2 | 0.0338 | -69.1 | -1.0 | 67.7 | VIES |
| R2-rotate / none / on | 0.9842 | -5.6 | 0.0289 | -73.5 | -1.0 | -151636.9 | VIES |
| R2-rotate / vision / on | 0.9842 | -5.6 | 0.0279 | -74.4 | -1.0 | -61.1 | VIES |
| R2-rotate / none / off | 0.9961 | -4.4 | 0.0288 | -73.6 | -1.0 | 69.2 | VIES |
| R2-rotate / vision / off | 0.9961 | -4.4 | 0.0279 | -74.5 | -1.0 | 6.3 | VIES |
| R3 / none / on | 0.9887 | -5.1 | 0.0815 | -25.3 | -1.0 | 11.2 | VIES |
| R3 / vision / on | 0.9852 | -5.5 | 0.0761 | -30.2 | -0.5 | 11.2 | VIES |
| R3 / none / off | 1.0423 | +0.0 | 0.1091 | +0.0 | -1.0 | 11.4 | ok |
| R3 / vision / off | 1.0476 | +0.5 | 0.0868 | -20.4 | 0.0 | 11.0 | VIES |

## Leitura

- H5 (gerador fisico: K_w em R1 desvia >= +10 % da referencia R3 e R2-rotate/R3 nao), celula realista (vision/on): dev K_w(R1) = +9.7 %, regime_bias R2-rotate = SIM -> FALSIFICADA (desvio negativo/abaixo de +10 %: o modelo fisico como entregue nao produz a inflacao de malha fechada)
- H5 (gerador fisico: K_w em R1 desvia >= +10 % da referencia R3 e R2-rotate/R3 nao), celula idealizada (none/off): dev K_w(R1) = +10.9 %, regime_bias R2-rotate = SIM -> FALSIFICADA
- H6 (controle R1-wonly: sem translacao o desvio de K_w some), celula realista: dev K_w(R1-wonly) = -10.7 % vs R1 = +9.7 %, regime_bias R1-wonly = SIM -> FALSIFICADA
- H6 (controle R1-wonly: sem translacao o desvio de K_w some), celula idealizada: dev K_w(R1-wonly) = -5.2 % vs R1 = +10.9 %, regime_bias R1-wonly = SIM -> FALSIFICADA
- H7 (vx/vy sem dependencia de regime comparavel em R1), celula realista: vx: dev K -250.2 %, dev tau -66.4 %, regime_bias SIM; vy: dev K +9.4 %, dev tau -63.7 %, regime_bias SIM -> FALSIFICADA
- H7 (vx/vy sem dependencia de regime comparavel em R1), celula idealizada: vx: dev K -251.6 %, dev tau -68.8 %, regime_bias SIM; vy: dev K +5.3 %, dev tau -67.9 %, regime_bias SIM -> FALSIFICADA

Leitura geral (C1b): para cada DOF fixo, compare regime_bias entre R1, R1-wonly, R2-rotate e R3.
Se o desvio de K_w aparece em R1 e some em R1-wonly (mesmos comandos de w, sem translacao), o
mecanismo e o acoplamento translacao -> guinada do modelo fisico, correlacionado com os comandos
de w da estrategia; se aparece tambem em R1-wonly, vem do conteudo dos comandos de w; se nao
aparece em lugar nenhum, o modelo fisico como entregue nao reproduz a inflacao de malha fechada
(K_w ~ 1.38 do artigo). O desvio da referencia R3 em relacao a theta* (tabela acima) e a distancia
entre o modelo fisico e o gemeo P1D no regime projetado, nao um erro do estimador.