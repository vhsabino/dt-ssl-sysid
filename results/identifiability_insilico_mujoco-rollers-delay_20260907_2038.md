# Identificabilidade in-silico (C1b): gerador mujoco-rollers-delay - regime x ruido x zona morta - 20260907_2038

_Proveniencia: commit `cdef20c` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed 42 | gerado por `dtssl.analysis.identifiability_insilico` (dtssl 1.0.0a1) | gerador mujoco-rollers-delay (opts {}) | n_rep=12 | estimador profile-NM align=legacy | 384 ajustes em 2.9 min (geracao de trajetorias 1.4 min)_

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

Referencia por DOF (gerador `mujoco-rollers-delay`; celulas R3/none/off - pre-registrada C1b-v1) e sua distancia ao theta* do gemeo (contexto, nao criterio):

| DOF | celula de referencia | K ref | tau ref (s) | m_eff ref | K ref / K* - 1 | tau ref / tau* - 1 | m_eff ref - Td*/Ts |
|---|---|---|---|---|---|---|---|
| vx | R3/none/off | -0.4348 | 0.1136 | 9.0 | -138.8 % | +58.3 % | 4.86 |
| vy | R3/none/off | 0.8944 | 0.2258 | 4.0 | -15.0 % | +77.3 % | 0.61 |
| w | R3/none/off | 0.9835 | 0.0961 | 6.0 | -1.8 % | +16.1 % | 0.66 |

Checagem do estimador literal do artigo (NM 3-D em [K, tau, Td] a partir de X0, `r3`) contra o perfil em m, celula idealizada R3/none/off, split da replica 0:

| DOF | NM 3-D: K | tau | Td (s) | m_eff | custo | perfil: K | tau | m_eff | custo |
|---|---|---|---|---|---|---|---|---|---|
| vx | -0.4423 | 0.1881 | 0.0667 | 4 | 3710.489 | -0.4288 | 0.1264 | 9 | 3695.115 |
| vy | 0.8968 | 0.2104 | 0.0928 | 5 | 861.810 | 0.9125 | 0.2311 | 4 | 860.544 |
| w | 0.9777 | 0.0853 | 0.1219 | 7 | 90580.112 | 0.9777 | 0.0853 | 7 | 90580.112 |

## DOF vx (K* = 1.1192, tau* = 0.0718 s, Td*/Ts = 4.14 amostras, planta aplica 5)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6990 [0.6451, 0.7530] | -37.5 | 0.0233 [0.0191, 0.0291] | -67.5 | 5.0 [5.0, 5.0] | 0.86 | 9.6 | 63.9 | 69.7 | -260.8 | -79.5 | -4.0 | VIES | VIES |
| R1 | vision | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6992 [0.6453, 0.7531] | -37.5 | 0.0272 [0.0192, 0.0293] | -62.1 | 5.0 [5.0, 5.0] | 0.86 | 9.6 | 63.8 | 69.4 | -260.8 | -76.1 | -4.0 | VIES | VIES |
| R1 | none | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6949 [0.6405, 0.7493] | -37.9 | 0.0242 [0.0197, 0.0301] | -66.4 | 5.0 [5.0, 5.0] | 0.86 | 9.7 | 63.4 | 69.2 | -259.8 | -78.7 | -4.0 | VIES | VIES |
| R1 | vision | on | 4 (3/1) | 5.6 / 5.6 / 0.0 | 0.6950 [0.6406, 0.7494] | -37.9 | 0.0283 [0.0199, 0.0304] | -60.6 | 5.0 [5.0, 5.0] | 0.86 | 9.7 | 63.3 | 69.0 | -259.9 | -75.1 | -4.0 | VIES | VIES |
| R2-rotate | none | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | none | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | -0.4348 [-0.5104, -0.4153] | -138.8 | 0.1136 [0.0993, 0.1621] | +58.3 | 9.0 [6.8, 9.2] | 4.86 | 8.5 | 1.7 | 15.0 | -0.0 | +0.0 | 0.0 | ok | ok |
| R3 | vision | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | -0.4347 [-0.5105, -0.4150] | -138.8 | 0.1134 [0.0997, 0.1622] | +58.0 | 9.0 [6.8, 9.2] | 4.86 | 8.5 | 1.7 | 15.0 | -0.0 | -0.2 | 0.0 | ok | ok |
| R3 | none | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | -0.4203 [-0.4580, -0.3903] | -137.6 | 0.1266 [0.1147, 0.1918] | +76.3 | 8.0 [6.5, 9.0] | 3.86 | 6.0 | -1.3 | 10.0 | -3.3 | +11.4 | -1.0 | ok | ok |
| R3 | vision | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | -0.4219 [-0.4578, -0.3900] | -137.7 | 0.1321 [0.1153, 0.1919] | +84.1 | 8.0 [6.5, 9.0] | 3.86 | 6.1 | -1.3 | 10.0 | -3.0 | +16.3 | -1.0 | VIES | ok |

## DOF vy (K* = 1.0524, tau* = 0.1273 s, Td*/Ts = 3.39 amostras, planta aplica 4)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9251 [0.9178, 0.9361] | -12.1 | 0.0717 [0.0712, 0.0842] | -43.7 | 3.0 [2.0, 3.0] | -0.39 | 1.7 | 87.2 | 89.9 | +3.4 | -68.2 | -1.0 | VIES | ok |
| R1 | vision | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9251 [0.9187, 0.9345] | -12.1 | 0.0719 [0.0709, 0.0850] | -43.6 | 3.0 [2.0, 3.0] | -0.39 | 1.5 | 86.5 | 89.4 | +3.4 | -68.2 | -1.0 | VIES | ok |
| R1 | none | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9303 [0.9272, 0.9479] | -11.6 | 0.0771 [0.0761, 0.0777] | -39.4 | 3.0 [3.0, 3.0] | -0.39 | 2.0 | 89.2 | 90.4 | +4.0 | -65.8 | -1.0 | VIES | ok |
| R1 | vision | on | 13 (9/4) | 7.6 / 7.6 / 0.0 | 0.9303 [0.9272, 0.9477] | -11.6 | 0.0773 [0.0763, 0.0776] | -39.3 | 3.0 [3.0, 3.0] | -0.39 | 1.9 | 88.5 | 89.8 | +4.0 | -65.8 | -1.0 | VIES | ok |
| R2-rotate | none | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | off | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | none | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R2-rotate | vision | on | 10 (7/3) (12 degen.) | 40.0 / 0.0 / 40.0 | nan [nan, nan] | nan | nan [nan, nan] | nan | nan [nan, nan] | nan | nan | nan | nan | nan | nan | nan | indef. | indef. |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.8944 [0.8830, 0.9113] | -15.0 | 0.2258 [0.2194, 0.2297] | +77.3 | 4.0 [4.0, 4.0] | 0.61 | 2.7 | 55.5 | 50.0 | +0.0 | +0.0 | 0.0 | ok | ok |
| R3 | vision | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.8945 [0.8832, 0.9112] | -15.0 | 0.2256 [0.2196, 0.2298] | +77.2 | 4.0 [4.0, 4.0] | 0.61 | 2.7 | 55.2 | 49.8 | +0.0 | -0.0 | 0.0 | ok | ok |
| R3 | none | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.8942 [0.8864, 0.9128] | -15.0 | 0.2126 [0.2040, 0.2175] | +66.9 | 4.0 [4.0, 4.2] | 0.61 | 2.5 | 56.3 | 50.2 | -0.0 | -5.8 | 0.0 | ok | ok |
| R3 | vision | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.8941 [0.8863, 0.9127] | -15.0 | 0.2126 [0.2041, 0.2175] | +67.0 | 4.0 [4.0, 4.2] | 0.61 | 2.5 | 56.0 | 50.1 | -0.0 | -5.8 | 0.0 | ok | ok |

## DOF w (K* = 1.0016, tau* = 0.0828 s, Td*/Ts = 5.34 amostras, planta aplica 6)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1603 [1.0426, 1.2486] | +15.8 | 0.1010 [0.0841, 0.1227] | +22.1 | 6.0 [5.0, 7.2] | 0.66 | 20.6 | 29.2 | 26.6 | +18.0 | +5.1 | 0.0 | VIES | VIES |
| R1 | vision | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.1597 [1.0435, 1.2481] | +15.8 | 0.0983 [0.0837, 0.1226] | +18.8 | 6.0 [5.0, 7.2] | 0.66 | 20.4 | 26.8 | 25.1 | +17.9 | +2.3 | 0.0 | VIES | VIES |
| R1 | none | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.2735 [1.1962, 1.3627] | +27.1 | 0.1839 [0.1114, 0.2161] | +122.2 | 1.5 [1.0, 3.2] | -3.84 | 16.6 | 24.6 | 17.9 | +29.5 | +91.3 | -4.5 | VIES | VIES |
| R1 | vision | on | 18 (12/6) | 31.6 / 31.6 / 6.7 | 1.2697 [1.1785, 1.3908] | +26.8 | 0.1703 [0.1085, 0.2154] | +105.8 | 1.5 [1.0, 4.0] | -3.84 | 21.2 | 22.9 | 16.8 | +29.1 | +77.2 | -4.5 | VIES | VIES |
| R1-wonly | none | off | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9880 [0.9869, 0.9890] | -1.4 | 0.0333 [0.0327, 0.0391] | -59.8 | 5.0 [5.0, 5.0] | -0.34 | 0.2 | 80.9 | 91.2 | +0.5 | -65.4 | -1.0 | VIES | ok |
| R1-wonly | vision | off | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9882 [0.9867, 0.9893] | -1.3 | 0.0334 [0.0329, 0.0389] | -59.6 | 5.0 [5.0, 5.0] | -0.34 | 0.3 | 68.2 | 76.7 | +0.5 | -65.2 | -1.0 | VIES | ok |
| R1-wonly | none | on | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9353 [0.9223, 0.9375] | -6.6 | 0.0317 [0.0291, 0.0326] | -61.7 | 5.0 [5.0, 5.2] | -0.34 | 1.5 | 65.1 | 74.7 | -4.9 | -67.0 | -1.0 | VIES | ok |
| R1-wonly | vision | on | 18 (12/6) | 74.0 / 74.0 / 74.0 | 0.9295 [0.9100, 0.9370] | -7.2 | 0.0304 [0.0271, 0.0323] | -63.2 | 5.0 [5.0, 6.0] | -0.34 | 2.7 | 58.4 | 66.8 | -5.5 | -68.3 | -1.0 | VIES | ok |
| R2-rotate | none | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9963 [0.9960, 0.9965] | -0.5 | 0.0316 [0.0303, 0.0324] | -61.9 | 5.0 [5.0, 5.0] | -0.34 | 0.1 | 88.6 | 88.2 | +1.3 | -67.2 | -1.0 | VIES | ok |
| R2-rotate | vision | off | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9963 [0.9960, 0.9965] | -0.5 | 0.0307 [0.0283, 0.0321] | -62.9 | 5.0 [5.0, 5.0] | -0.34 | 0.0 | 26.8 | 12.2 | +1.3 | -68.0 | -1.0 | VIES | ok |
| R2-rotate | none | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9843 [0.9618, 0.9885] | -1.7 | 0.0331 [0.0310, 0.0337] | -60.1 | 5.0 [5.0, 5.0] | -0.34 | 2.7 | -108360.4 | 83.4 | +0.1 | -65.6 | -1.0 | VIES | ok |
| R2-rotate | vision | on | 10 (7/3) | 40.0 / 40.0 / 40.0 | 0.9843 [0.9619, 0.9884] | -1.7 | 0.0315 [0.0269, 0.0329] | -62.0 | 5.0 [5.0, 5.0] | -0.34 | 2.7 | -14.6 | 12.0 | +0.1 | -67.2 | -1.0 | VIES | ok |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.9835 [0.9662, 1.0071] | -1.8 | 0.0961 [0.0898, 0.1062] | +16.1 | 6.0 [6.0, 7.0] | 0.66 | 4.1 | 10.3 | 12.7 | +0.0 | +0.0 | 0.0 | ok | ok |
| R3 | vision | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.9735 [0.9511, 1.0071] | -2.8 | 0.0953 [0.0813, 0.1043] | +15.2 | 6.0 [6.0, 7.0] | 0.66 | 5.6 | 9.8 | 11.9 | -1.0 | -0.8 | 0.0 | ok | ok |
| R3 | none | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.9828 [0.9724, 0.9878] | -1.9 | 0.0884 [0.0754, 0.0969] | +6.8 | 5.0 [5.0, 6.0] | -0.34 | 1.5 | 11.0 | 10.6 | -0.1 | -8.0 | -1.0 | ok | ok |
| R3 | vision | on | 12 (8/4) | 14.3 / 14.3 / 0.0 | 0.9828 [0.9746, 0.9879] | -1.9 | 0.0884 [0.0759, 0.1067] | +6.8 | 5.0 [5.0, 6.0] | -0.34 | 1.3 | 11.0 | 10.6 | -0.1 | -8.1 | -1.0 | ok | ok |

## Resumo regime x DOF -> regime_bias? (dev K vs referencia R3/none/off) (celula realista: ruido `vision`, zona morta `on`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | VIES dev K -259.9 % | VIES dev K +4.0 % | VIES dev K +29.1 % |
| R1-wonly | - | - | VIES dev K -5.5 % |
| R2-rotate | indef. dev K nan % | indef. dev K nan % | VIES dev K +0.1 % |
| R3 | VIES dev K -3.0 % | ok dev K -0.0 % | ok dev K -0.1 % |

## Resumo regime x DOF -> regime_bias? (dev K vs referencia R3/none/off) (celula idealizada: ruido `none`, zona morta `off`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | VIES dev K -260.8 % | VIES dev K +3.4 % | VIES dev K +18.0 % |
| R1-wonly | - | - | VIES dev K +0.5 % |
| R2-rotate | indef. dev K nan % | indef. dev K nan % | VIES dev K +1.3 % |
| R3 | ok dev K -0.0 % | ok dev K +0.0 % | ok dev K +0.0 % |

## w: R1 (zona morta on/off) vs R1-wonly vs R2-rotate vs R2-square vs R3/R3-mild

| celula | K med | dev K % | tau med | dev tau % | m_eff med | fit ho % | regime_bias |
|---|---|---|---|---|---|---|---|
| R1 / none / on | 1.2735 | +29.5 | 0.1839 | +91.3 | 1.5 | 24.6 | VIES |
| R1 / vision / on | 1.2697 | +29.1 | 0.1703 | +77.2 | 1.5 | 22.9 | VIES |
| R1 / none / off | 1.1603 | +18.0 | 0.1010 | +5.1 | 6.0 | 29.2 | VIES |
| R1 / vision / off | 1.1597 | +17.9 | 0.0983 | +2.3 | 6.0 | 26.8 | VIES |
| R1-wonly / none / on | 0.9353 | -4.9 | 0.0317 | -67.0 | 5.0 | 65.1 | VIES |
| R1-wonly / vision / on | 0.9295 | -5.5 | 0.0304 | -68.3 | 5.0 | 58.4 | VIES |
| R1-wonly / none / off | 0.9880 | +0.5 | 0.0333 | -65.4 | 5.0 | 80.9 | VIES |
| R1-wonly / vision / off | 0.9882 | +0.5 | 0.0334 | -65.2 | 5.0 | 68.2 | VIES |
| R2-rotate / none / on | 0.9843 | +0.1 | 0.0331 | -65.6 | 5.0 | -108360.4 | VIES |
| R2-rotate / vision / on | 0.9843 | +0.1 | 0.0315 | -67.2 | 5.0 | -14.6 | VIES |
| R2-rotate / none / off | 0.9963 | +1.3 | 0.0316 | -67.2 | 5.0 | 88.6 | VIES |
| R2-rotate / vision / off | 0.9963 | +1.3 | 0.0307 | -68.0 | 5.0 | 26.8 | VIES |
| R3 / none / on | 0.9828 | -0.1 | 0.0884 | -8.0 | 5.0 | 11.0 | ok |
| R3 / vision / on | 0.9828 | -0.1 | 0.0884 | -8.1 | 5.0 | 11.0 | ok |
| R3 / none / off | 0.9835 | +0.0 | 0.0961 | +0.0 | 6.0 | 10.3 | ok |
| R3 / vision / off | 0.9735 | -1.0 | 0.0953 | -0.8 | 6.0 | 9.8 | ok |

## Leitura

- H5 (gerador fisico: K_w em R1 desvia >= +10 % da referencia R3 e R2-rotate/R3 nao), celula realista (vision/on): dev K_w(R1) = +29.1 %, regime_bias R2-rotate = SIM -> FALSIFICADA
- H5 (gerador fisico: K_w em R1 desvia >= +10 % da referencia R3 e R2-rotate/R3 nao), celula idealizada (none/off): dev K_w(R1) = +18.0 %, regime_bias R2-rotate = SIM -> FALSIFICADA
- H6 (controle R1-wonly: sem translacao o desvio de K_w some), celula realista: dev K_w(R1-wonly) = -5.5 % vs R1 = +29.1 %, regime_bias R1-wonly = SIM -> FALSIFICADA
- H6 (controle R1-wonly: sem translacao o desvio de K_w some), celula idealizada: dev K_w(R1-wonly) = +0.5 % vs R1 = +18.0 %, regime_bias R1-wonly = SIM -> FALSIFICADA
- H7 (vx/vy sem dependencia de regime comparavel em R1), celula realista: vx: dev K -259.9 %, dev tau -75.1 %, regime_bias SIM; vy: dev K +4.0 %, dev tau -65.8 %, regime_bias SIM -> FALSIFICADA
- H7 (vx/vy sem dependencia de regime comparavel em R1), celula idealizada: vx: dev K -260.8 %, dev tau -79.5 %, regime_bias SIM; vy: dev K +3.4 %, dev tau -68.2 %, regime_bias SIM -> FALSIFICADA

Leitura geral (C1b): para cada DOF fixo, compare regime_bias entre R1, R1-wonly, R2-rotate e R3.
Se o desvio de K_w aparece em R1 e some em R1-wonly (mesmos comandos de w, sem translacao), o
mecanismo e o acoplamento translacao -> guinada do modelo fisico, correlacionado com os comandos
de w da estrategia; se aparece tambem em R1-wonly, vem do conteudo dos comandos de w; se nao
aparece em lugar nenhum, o modelo fisico como entregue nao reproduz a inflacao de malha fechada
(K_w ~ 1.38 do artigo). O desvio da referencia R3 em relacao a theta* (tabela acima) e a distancia
entre o modelo fisico e o gemeo P1D no regime projetado, nao um erro do estimador.