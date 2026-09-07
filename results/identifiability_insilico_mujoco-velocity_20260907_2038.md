# Identificabilidade in-silico (C1b): gerador mujoco-velocity - regime x ruido x zona morta - 20260907_2038

_Proveniencia: commit `cdef20c` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed 42 | gerado por `dtssl.analysis.identifiability_insilico` (dtssl 1.0.0a1) | gerador mujoco-velocity (opts {}) | n_rep=6 | estimador profile-NM align=legacy | 36 ajustes em 0.6 min (geracao de trajetorias 0.5 min)_

Pre-registro: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_20260907.md (adendo C1b: hipoteses
H5-H8, referencia e bandeira regime_bias fixadas antes de rodar) sobre o desenho de C1
(docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md).
GERADOR: `mujoco-velocity` via `dtssl.sim.world_plant.make_harness_plant` (MuJoCoWorld de um robo visto como
Plant do harness; `mujoco-velocity` = rota a, a AnalyticFOPDTPlant(theta*) dirigindo o chassi;
`mujoco-rollers` = rota b, rodas omni + roletes livres, sem sintonia e sem atraso;
`mujoco-rollers-delay` = rota b + tap de atraso ceil(Td*/Ts) por DOF no comando). Zona morta do
fator C aplicada DENTRO do mundo (`deadzone=True`: rota a = regra de corpo de apply_body_deadzone;
rota b = por roda, no setpoint de cada atuador); o estimador ve sempre o comando original.
Trajetoria por evento gerada UMA vez por (conjunto, zona morta) e partilhada pelas replicas.
Este gerador embute a propria AnalyticFOPDTPlant(theta*): a verdade e conhecida e as bandeiras
'recuperado' de C1 continuam validas; o desvio da referencia R3 e reportado em paralelo.

**Desvio declarado:** n_rep = 6 (pre-registrado: 12)

## Desenho

| DOF | K* | tau* (s) | Td* (s) | Td*/Ts (amostras) | atraso da planta (amostras) |
|---|---|---|---|---|---|
| vx | 1.1192 | 0.0718 | 0.06905 | 4.14 | 5 |
| vy | 1.0524 | 0.1273 | 0.05648 | 3.39 | 4 |
| w | 1.0016 | 0.0828 | 0.08895 | 5.34 | 6 |

- Ts = 0.016667 s; gerador `mujoco-velocity` (`make_harness_plant`, opts {}), `reset(pose0, velb0=0)`, `pose[k] = step(cmd[k-1])` (driver de `free_run`, buffer de atraso vazio).
- Regimes (eventos): `front_to_back` = 4 eventos; `side_to_side` = 13 eventos; `shoot_to_goal` = 18 eventos; `R3` = 12 eventos
- R1 (pareamento do artigo): vx `front_to_back`, vy `side_to_side`, w `shoot_to_goal`; R2-rotate `rotate` (10 eventos, inclui +-0.25/+-0.5 rad/s); R2-square `square`; R3 sintetico: 12 eventos x 10 s, degraus de 0.3-1.2 s, amplitude +-[0.6, 1.5] m/s (vx, vy) e +-[1.5, 4.0] rad/s (w), 3 DOFs simultaneos, seed de desenho 42.
- Ruido (sigma_pos mm, sigma_theta rad): `none` = (0.0, 0.0); i.i.d. por amostra, seed 42 + rep (numeros aleatorios comuns entre niveis).
- Zona morta do gerador: limiar de firmware 1.567 rad/s por roda aplicado pelo MuJoCoWorld (`deadzone=True`); as fracoes mascaradas abaixo usam a mesma regra por roda (`mask_deadzone`).
- Monte Carlo: n_rep = 6 por celula; split 2/3-1/3 por evento seeded (seed 42 + 1000 + rep); fit nos eventos de treino, fit % medio no hold-out.
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
| `R3` | 12 | 7200 | 14.3 % | 14.3 % | 14.3 % | 14.3 % | 0.0 % |

Referencia por DOF (gerador `mujoco-velocity`; celulas R3/none/off - pre-registrada C1b-v1) e sua distancia ao theta* do gemeo (contexto, nao criterio):

| DOF | celula de referencia | K ref | tau ref (s) | m_eff ref | K ref / K* - 1 | tau ref / tau* - 1 | m_eff ref - Td*/Ts |
|---|---|---|---|---|---|---|---|
| vx | R3/none/off | 1.1191 | 0.0742 | 5.0 | -0.0 % | +3.3 % | 0.86 |
| vy | R3/none/off | 1.0520 | 0.1285 | 4.0 | -0.0 % | +0.9 % | 0.61 |
| w | R3/none/off | 1.0012 | 0.0840 | 6.0 | -0.0 % | +1.5 % | 0.66 |

Checagem do estimador literal do artigo (NM 3-D em [K, tau, Td] a partir de X0, `r3`) contra o perfil em m, celula idealizada R3/none/off, split da replica 0:

| DOF | NM 3-D: K | tau | Td (s) | m_eff | custo | perfil: K | tau | m_eff | custo |
|---|---|---|---|---|---|---|---|---|---|
| vx | 1.1425 | 0.1108 | 0.0536 | 3 | 37.954 | 1.1190 | 0.0742 | 5 | 2.096 |
| vy | 1.0693 | 0.1479 | 0.0522 | 3 | 8.215 | 1.0521 | 0.1285 | 4 | 0.926 |
| w | 0.9888 | 0.0671 | 0.1277 | 7 | 78.134 | 1.0012 | 0.0841 | 6 | 8.689 |

## DOF vx (K* = 1.1192, tau* = 0.0718 s, Td*/Ts = 4.14 amostras, planta aplica 5)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K | escore | recuperado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 4 (3/1) | 5.6 / 5.6 / 0.0 | 1.1191 [1.1190, 1.1191] | -0.0 | 0.0724 [0.0724, 0.0724] | +0.9 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 99.4 | 99.5 | -0.0 | -2.3 | 0.0 | ok | ok | 4 | SIM (4/4) |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.1191 [1.1191, 1.1191] | -0.0 | 0.0742 [0.0742, 0.0742] | +3.3 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 98.1 | 98.1 | +0.0 | +0.0 | 0.0 | ok | ok | 4 | SIM (4/4) |

## DOF vy (K* = 1.0524, tau* = 0.1273 s, Td*/Ts = 3.39 amostras, planta aplica 4)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K | escore | recuperado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 13 (9/4) | 7.6 / 7.6 / 0.0 | 1.0523 [1.0523, 1.0523] | -0.0 | 0.1276 [0.1276, 0.1277] | +0.2 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 99.6 | 99.6 | +0.0 | -0.6 | 0.0 | ok | ok | 4 | SIM (4/4) |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0520 [1.0520, 1.0521] | -0.0 | 0.1285 [0.1284, 0.1285] | +0.9 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 98.6 | 98.7 | +0.0 | +0.0 | 0.0 | ok | ok | 4 | SIM (4/4) |

## DOF w (K* = 1.0016, tau* = 0.0828 s, Td*/Ts = 5.34 amostras, planta aplica 6)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K | escore | recuperado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | none | off | 18 (12/6) | 31.6 / 31.6 / 6.7 | 0.9999 [0.9998, 1.0000] | -0.2 | 0.0840 [0.0839, 0.0846] | +1.5 | 6.0 [6.0, 6.0] | 0.66 | 0.0 | 95.8 | 98.0 | -0.1 | -0.0 | 0.0 | ok | ok | 4 | SIM (4/4) |
| R3 | none | off | 12 (8/4) | 14.3 / 14.3 / 0.0 | 1.0012 [1.0012, 1.0012] | -0.0 | 0.0840 [0.0840, 0.0841] | +1.5 | 6.0 [6.0, 6.0] | 0.66 | 0.0 | 98.3 | 98.2 | +0.0 | +0.0 | 0.0 | ok | ok | 4 | SIM (4/4) |

## Resumo regime x DOF -> recuperado? (celula idealizada: ruido `none`, zona morta `off`)

| regime | vx | vy | w |
|---|---|---|---|
| R1 | SIM (4/4) K -0.0 % | SIM (4/4) K -0.0 % | SIM (4/4) K -0.2 % |
| R3 | SIM (4/4) K -0.0 % | SIM (4/4) K -0.0 % | SIM (4/4) K -0.0 % |

## w: R1 (zona morta on/off) vs R1-wonly vs R2-rotate vs R2-square vs R3/R3-mild

| celula | K med | dev K % | tau med | dev tau % | m_eff med | fit ho % | regime_bias |
|---|---|---|---|---|---|---|---|
| R1 / none / off | 0.9999 | -0.1 | 0.0840 | -0.0 | 6.0 | 95.8 | ok |
| R3 / none / off | 1.0012 | +0.0 | 0.0840 | +0.0 | 6.0 | 98.3 | ok |

## Leitura

- H5 (gerador fisico: K_w em R1 desvia >= +10 % da referencia R3 e R2-rotate/R3 nao), celula idealizada (none/off): dev K_w(R1) = -0.1 %, regime_bias R2-rotate = indef. -> FALSIFICADA (desvio negativo/abaixo de +10 %: o modelo fisico como entregue nao produz a inflacao de malha fechada)
- H7 (vx/vy sem dependencia de regime comparavel em R1), celula idealizada: vx: dev K -0.0 %, dev tau -2.3 %, regime_bias nao; vy: dev K +0.0 %, dev tau -0.6 %, regime_bias nao -> CORROBORADA
- H8 (gerador = gemeo embutido, verdade conhecida): 6 de 6 celulas nao degeneradas recuperam theta* (4/4); comparacao numerica com o artefato de C1 (fopdt, `_1552`) feita fora do modulo (mesmas seeds; criterio 1 % em K e tau, mesmo m_eff).

Leitura geral (C1b): para cada DOF fixo, compare regime_bias entre R1, R1-wonly, R2-rotate e R3.
Se o desvio de K_w aparece em R1 e some em R1-wonly (mesmos comandos de w, sem translacao), o
mecanismo e o acoplamento translacao -> guinada do modelo fisico, correlacionado com os comandos
de w da estrategia; se aparece tambem em R1-wonly, vem do conteudo dos comandos de w; se nao
aparece em lugar nenhum, o modelo fisico como entregue nao reproduz a inflacao de malha fechada
(K_w ~ 1.38 do artigo). O desvio da referencia R3 em relacao a theta* (tabela acima) e a distancia
entre o modelo fisico e o gemeo P1D no regime projetado, nao um erro do estimador.