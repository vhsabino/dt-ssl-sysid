# Checagem MIMO: termos cruzados de comando vs. estrutura por DOF - 20261014_1211

_Proveniencia: commit `8e31fa1-dirty` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed 42 | gerado por `dtssl.analysis.coupled_mimo_check` (dtssl 1.0.0a1) | atrasos primarios [5, 4, 6] amostras (ceil(Td/dt), alinhamento plant); pre-registro docs/PREREGISTRO_MIMO_CHECK_20260923.md_

Eventos: treino 36 / hold-out 10 (config/holdout_events.json); rotulos front_to_back, side_to_side, shoot_to_goal, square; grade 0.01667 s; referencia de yaw K_ref = 1.0016 (theta oficial (identificacao dedicada em malha aberta, config/twin_params.json)).

## 1. Fit de hold-out (Eq. 2)

| braco | vx pooled | vy pooled | w pooled | vx media ev. | vy media ev. | w media ev. |
|---|---|---|---|---|---|---|
| promoted | 75.3 % | 79.7 % | 40.1 % | 54.8 % | 70.3 % | 31.9 % |
| diagonal | 75.5 % | 79.9 % | 48.8 % | 55.0 % | 70.6 % | 38.4 % |
| coupled | 76.5 % | 80.1 % | 48.9 % | 59.4 % | 71.2 % | 38.6 % |

## 2. Ganhos estaticos G = B/(1-A) (linha = saida, coluna = comando)

Diagonal:

| saida \ comando | vx | vy | w | tau (s) | atrasos (amostras) |
|---|---|---|---|---|---|
| vx | 1.100 | 0.000 | 0.000 | 0.0679 | 5/5/5 |
| vy | 0.000 | 1.067 | 0.000 | 0.1302 | 4/4/4 |
| w | 0.000 | 0.000 | 1.419 | 0.0462 | 6/6/6 |

Acoplado:

| saida \ comando | vx | vy | w | tau (s) | atrasos (amostras) |
|---|---|---|---|---|---|
| vx | 1.105 | -0.045 | 0.028 | 0.0670 | 5/5/5 |
| vy | -0.009 | 1.067 | -0.065 | 0.1325 | 4/4/4 |
| w | -0.014 | -0.047 | 1.414 | 0.0458 | 6/6/6 |

## 3. Contribuicao cruzada no hold-out (RMS cruzado / RMS direto, braco acoplado)

| saida | total | de vx | de vy | de w |
|---|---|---|---|---|
| vx | 0.058 | - | 0.051 | 0.022 |
| vy | 0.039 | 0.006 | - | 0.040 |
| w | 0.048 | 0.011 | 0.046 | - |

## 4. Vereditos pre-registrados

**M1 (primario; ganho de fit pooled >= 3.0 p.p. E razao de contribuicao >= 0.1 no MESMO DOF):**

- vx: ganho +0.95 p.p., razao 0.058 -> nao importa
- vy: ganho +0.23 p.p., razao 0.039 -> nao importa
- w: ganho +0.13 p.p., razao 0.048 -> nao importa

- **M1: acoplamento nao importa neste envelope**

**M2 (mecanismo; premissa G_ww diagonal >= (1 + 0.10) x K_ref; o acoplado remove >= 50% do excesso):** G_ww diagonal 1.4190 (+41.7%), acoplado 1.4138 (+41.1%), fracao removida 0.01 -> **FALSIFICADA**

- sensibilidade (treino so `shoot_to_goal`, 13 eventos): G_ww diagonal 1.3719 (+37.0%), acoplado 1.4006 (+39.8%) -> FALSIFICADA

## 5. Secundario: atrasos por par (busca exaustiva 0..10 amostras)

| braco | vx pooled | vy pooled | w pooled |
|---|---|---|---|
| diagonal | 77.0 % | 80.2 % | 48.8 % |
| coupled | 78.1 % | 80.4 % | 49.0 % |

Acoplado (atrasos por par):

| saida \ comando | vx | vy | w | tau (s) | atrasos (amostras) |
|---|---|---|---|---|---|
| vx | 1.115 | -0.046 | 0.027 | 0.0964 | 3/0/5 |
| vy | -0.011 | 1.071 | -0.072 | 0.1470 | 0/3/9 |
| w | -0.016 | -0.063 | 1.413 | 0.0460 | 0/0/6 |

- M1 (atrasos por par): nao importa; M2: FALSIFICADA (G_ww 1.4190 -> 1.4127)

## 6. Bootstrap por eventos de treino (200 replicas, seed 42; IC 95 % percentil)

| quantidade | IC 95 % |
|---|---|
| G_diag_w | [1.360, 1.517] |
| G_coupled_w | [1.354, 1.528] |
| gain_vx | [0.616, 1.070] |
| gain_vy | [0.023, 0.305] |
| gain_w | [-0.052, 0.147] |
| ratio_vx | [0.046, 0.076] |
| ratio_vy | [0.019, 0.059] |
| ratio_w | [0.026, 0.074] |

## 7. Harness do artigo (free-run, janelas re-ancoradas, bin translacional; h_ref = 0.40 s)

265 janelas (264 translacionais) em 10 eventos.

| h (s) | e_pos promoted | e_pos diagonal | e_pos acoplado | e_ang promoted | e_ang diagonal | e_ang acoplado |
|---|---|---|---|---|---|---|
| 0.10 | 0.0079 | 0.0079 | 0.0076 | 0.0128 | 0.0136 | 0.0151 |
| 0.20 | 0.0178 | 0.0176 | 0.0163 | 0.0311 | 0.0274 | 0.0313 |
| 0.40 | 0.0388 | 0.0390 | 0.0381 | 0.0440 | 0.0456 | 0.0462 |
| 0.70 | 0.0617 | 0.0644 | 0.0631 | 0.0627 | 0.0737 | 0.0679 |
| 1.00 | 0.0920 | 0.0955 | 0.0905 | 0.0733 | 0.0883 | 0.0863 |
| 1.50 | 0.1193 | 0.1413 | 0.1289 | 0.0895 | 0.1056 | 0.0989 |

Sanidade: mediana por evento do promoted em h_ref = 0.0421 m (artigo: 0.0421).

**M3 (acoplado < diagonal por evento: >= 8/10, p < 0.05, rb >= 0.5):** 6/10, p = 0.461, rb = +0.05 -> **nao melhora**
- acoplado vs promoted: 5/10, p = 0.754; diagonal vs promoted: 4/10, p = 0.784

## Leitura

- M1 e o criterio do camera-ready (item B3): responde se, no envelope destes logs, termos cruzados de comando melhoram o que o modelo reproduz no hold-out.
- M2 testa em dado real o mecanismo do C1b: se o vies do ganho de yaw em malha fechada vem da guinada induzida pela translacao, dar ao modelo os comandos de translacao como entradas deve reduzir o ganho direto de yaw.
- M3 mede o efeito no uso do modelo (free-run no harness), com o mesmo gate por evento do C2b.
- Custo: ajuste e bootstrap 280 s; harness 1 s.