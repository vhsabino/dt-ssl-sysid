# Identificabilidade in-silico (C1b-v2, re-registro): gerador fopdt - regime x ruido x zona morta - 20260907_2051

_Proveniencia: commit `cdef20c` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed 42 | gerado por `dtssl.analysis.identifiability_insilico` (dtssl 1.0.0a1) | n_rep=6 | estimador profile-NM align=legacy | 18 ajustes em 0.2 min_

Re-registro C1b-v2: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_V2_20260907.md (emenda documentada
apos a execucao v1; muda SO: regime R3-mild dentro do envelope da rota b, referencias por DOF =
regimes dedicados de malha aberta (w: R2-rotate/none/off; vx, vy: R2-square/none/off) e regra
K-only regime_bias_K = |dev K| > 10 %; dev tau e dm_eff sao descritivos). v1 e seus artefatos
ficam intocados.

Pre-registro: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md (hipoteses H1-H4, regra
de decisao e seeds fixadas antes de rodar). Verdade conhecida: theta* = theta oficial; o gemeo
(AnalyticFOPDTPlant) gera as trajetorias a partir dos comandos de cada regime, a cadeia de medicao
tipo visao adiciona ruido, e a cadeia de estimacao Python do artigo (legacy_uy_series + custo de
erro de saida de r3_closedloop_omega_fit) re-identifica (K, tau, Td) por DOF.

**Desvio declarado:** n_rep = 6 (pre-registrado: 20)

## Desenho

| DOF | K* | tau* (s) | Td* (s) | Td*/Ts (amostras) | atraso da planta (amostras) |
|---|---|---|---|---|---|
| vx | 1.1192 | 0.0718 | 0.06905 | 4.14 | 5 |
| vy | 1.0524 | 0.1273 | 0.05648 | 3.39 | 4 |
| w | 1.0016 | 0.0828 | 0.08895 | 5.34 | 6 |

- Ts = 0.016667 s; gerador `AnalyticFOPDTPlant(theta*)`, `reset(pose0, velb0=0)`, `pose[k] = step(cmd[k-1])` (driver de `free_run`, buffer de atraso vazio).
- Regimes (eventos): `R3-mild` = 12 eventos
- R1 (pareamento do artigo): vx `front_to_back`, vy `side_to_side`, w `shoot_to_goal`; R2-rotate `rotate` (10 eventos, inclui +-0.25/+-0.5 rad/s); R2-square `square`; R3 sintetico: 12 eventos x 10 s, degraus de 0.3-1.2 s, amplitude +-[0.6, 1.5] m/s (vx, vy) e +-[1.5, 4.0] rad/s (w), 3 DOFs simultaneos, seed de desenho 42. R3-mild (envelope da rota b): amplitude +-[0.3, 1.0] m/s (vx, vy) e +-[0.5, 2.0] rad/s (w), degraus de 0.5-1.5 s, mesma construcao e seed.
- Ruido (sigma_pos mm, sigma_theta rad): `none` = (0.0, 0.0); i.i.d. por amostra, seed 42 + rep (numeros aleatorios comuns entre niveis).
- Zona morta do gerador: `apply_body_deadzone` por roda, limiar 1.567 rad/s (corpo ~0.58-0.60 rad/s em rotacao pura), aplicada ao comando ANTES da planta; o estimador ve o comando original.
- Monte Carlo: n_rep = 6 por celula; split 2/3-1/3 por evento seeded (seed 42 + 1000 + rep); fit nos eventos de treino, fit % medio no hold-out.
- Estimador: `legacy_uy_series` (SG 7/2 + diferencas centrais, mm -> m) + Nelder-Mead em (K, tau) para cada atraso inteiro m = 0..12 (custo de erro de saida, `simulate_fopdt` align=legacy, clamps tau >= 1e-4), m de menor custo de treino; X0 (K, tau) = (1.0, 0.08) (vx, vy) / (1.3, 0.03) (w); NM {'maxiter': 400, 'xatol': 0.0001, 'fatol': 0.001}. m_eff = m - 1 (align legacy aplica uma amostra a menos de atraso que a planta; common.py).
- Regra (por celula, mediana/IQR sobre as replicas): |vies K| <= 10 %, |vies tau| <= 15 %, |mediana(m_eff) - Td*/Ts| <= 1 amostra, IQR(K)/K* <= 20 %; escore = criterios satisfeitos (0-4); recuperado = 4/4.

Fracao de amostras em que a zona morta altera o comando (`qualquer roda`: ao menos uma roda abaixo
de 1.567 rad/s, comando de corpo alterado pela pseudo-inversa; colunas vx/vy/w: a componente do DOF
muda; `todas as rodas`: comando de corpo zerado = 'fully clamped' do artigo):

| conjunto | eventos | amostras | qualquer roda | vx | vy | w | todas as rodas |
|---|---|---|---|---|---|---|---|
| `R3-mild` | 12 | 7200 | 22.5 % | 22.5 % | 22.5 % | 22.5 % | 0.0 % |

Checagem do estimador literal do artigo (NM 3-D em [K, tau, Td] a partir de X0, `r3`) contra o perfil em m, celula idealizada R3/none/off, split da replica 0:

| DOF | NM 3-D: K | tau | Td (s) | m_eff | custo | perfil: K | tau | m_eff | custo |
|---|---|---|---|---|---|---|---|---|---|
| vx | 1.1387 | 0.1089 | 0.0555 | 3 | 11.757 | 1.1185 | 0.0731 | 5 | 0.653 |
| vy | 1.0610 | 0.1464 | 0.0525 | 3 | 1.713 | 1.0521 | 0.1281 | 4 | 0.219 |
| w | 0.9908 | 0.0673 | 0.1187 | 7 | 14.077 | 1.0012 | 0.0839 | 6 | 1.501 |

## DOF vx (K* = 1.1192, tau* = 0.0718 s, Td*/Ts = 4.14 amostras, planta aplica 5)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | escore | recuperado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R3-mild | none | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 1.1185 [1.1185, 1.1185] | -0.1 | 0.0731 [0.0731, 0.0731] | +1.8 | 5.0 [5.0, 5.0] | 0.86 | 0.0 | 98.3 | 98.4 | 4 | SIM (4/4) |

## DOF vy (K* = 1.0524, tau* = 0.1273 s, Td*/Ts = 3.39 amostras, planta aplica 4)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | escore | recuperado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R3-mild | none | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 1.0521 [1.0521, 1.0521] | -0.0 | 0.1281 [0.1280, 0.1281] | +0.6 | 4.0 [4.0, 4.0] | 0.61 | 0.0 | 98.8 | 98.9 | 4 | SIM (4/4) |

## DOF w (K* = 1.0016, tau* = 0.0828 s, Td*/Ts = 5.34 amostras, planta aplica 6)

| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % | tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % | escore | recuperado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R3-mild | none | off | 12 (8/4) | 22.5 / 22.5 / 0.0 | 1.0012 [1.0012, 1.0012] | -0.0 | 0.0839 [0.0839, 0.0839] | +1.4 | 6.0 [6.0, 6.0] | 0.66 | 0.0 | 98.5 | 98.6 | 4 | SIM (4/4) |

## Resumo regime x DOF -> recuperado? (celula idealizada: ruido `none`, zona morta `off`)

| regime | vx | vy | w |
|---|---|---|---|
| R3-mild | SIM (4/4) K -0.1 % | SIM (4/4) K -0.0 % | SIM (4/4) K -0.0 % |

## w: R1 (zona morta on) vs R2-rotate

| celula | K med | vies K % | tau med | vies tau % | m_eff med | fit ho % | escore |
|---|---|---|---|---|---|---|---|

## Leitura

- Fit % vs recuperacao: 0 de 3 celulas recuperadas (4/4) tem fit hold-out mediano < 60 % (gate do artigo)

Leitura geral: para cada DOF fixo, compare o escore entre regimes (o que muda e a excitacao, nao o
DOF); em R3 (excitacao projetada dos tres DOFs) os tres DOFs devem ser recuperados. Celulas
'degeneradas' (comando de treino com variancia nula, ex. vx/vy em `rotate`) nao tem ajuste: sem
excitacao nao ha identificabilidade, qualquer que seja o DOF. O gerador e o gemeo linear sem
escorregamento nem realimentacao: R1 in-silico mede apenas o conteudo informacional dos comandos
de competicao (mais ruido e zona morta), nao o mecanismo de diluicao/realimentacao do artigo.
Td: a planta aplica ceil(Td*/Ts) amostras; o estimador legacy devolve m_eff = m - 1, comparavel
com Td*/Ts; o Td* continuo nao e recuperavel abaixo dessa quantizacao (criterio de 1 amostra).