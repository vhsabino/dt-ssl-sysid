# Checagem MIMO: termos cruzados de comando vs. estrutura por DOF (CONTROLE in silico: gerador `mujoco-rollers-delay`) - 20261014_1216

_Proveniencia: commit `8e31fa1-dirty` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed 42 | gerado por `dtssl.analysis.coupled_mimo_check` (dtssl 1.0.0a1) | atrasos primarios [5, 4, 6] amostras (ceil(Td/dt), alinhamento plant); pre-registro docs/PREREGISTRO_MIMO_CHECK_20260923.md_

Eventos: treino 36 / hold-out 10 (config/holdout_events.json); rotulos front_to_back, side_to_side, shoot_to_goal, square; grade 0.01667 s; referencia de yaw K_ref = 0.9964 (estimador diagonal na resposta do gerador `mujoco-rollers-delay` aos eventos rotate_01_05..rotate_01_10).

**Controle in silico**: logs sinteticos gerados a partir dos comandos registrados; nenhum numero deste arquivo e do robo real.

## 1. Fit de hold-out (Eq. 2)

| braco | vx pooled | vy pooled | w pooled | vx media ev. | vy media ev. | w media ev. |
|---|---|---|---|---|---|---|
| promoted | -37.2 % | 69.4 % | 2.5 % | 19.9 % | 62.8 % | 25.3 % |
| diagonal | -24.0 % | 74.5 % | 2.5 % | 29.6 % | 70.5 % | 24.2 % |
| coupled | -24.0 % | 73.9 % | 2.8 % | 28.9 % | 69.9 % | -7.5 % |

## 2. Ganhos estaticos G = B/(1-A) (linha = saida, coluna = comando)

Diagonal:

| saida \ comando | vx | vy | w | tau (s) | atrasos (amostras) |
|---|---|---|---|---|---|
| vx | 0.917 | 0.000 | 0.000 | 0.0343 | 5/5/5 |
| vy | 0.000 | 0.938 | 0.000 | 0.0503 | 4/4/4 |
| w | 0.000 | 0.000 | 1.068 | 0.0960 | 6/6/6 |

Acoplado:

| saida \ comando | vx | vy | w | tau (s) | atrasos (amostras) |
|---|---|---|---|---|---|
| vx | 0.916 | 0.009 | -0.007 | 0.0344 | 5/5/5 |
| vy | 0.001 | 0.937 | -0.045 | 0.0520 | 4/4/4 |
| w | 0.038 | 0.160 | 1.075 | 0.0919 | 6/6/6 |

## 3. Contribuicao cruzada no hold-out (RMS cruzado / RMS direto, braco acoplado)

| saida | total | de vx | de vy | de w |
|---|---|---|---|---|
| vx | 0.015 | - | 0.012 | 0.007 |
| vy | 0.035 | 0.001 | - | 0.035 |
| w | 0.226 | 0.040 | 0.216 | - |

## 4. Vereditos pre-registrados

**M1 (primario; ganho de fit pooled >= 3.0 p.p. E razao de contribuicao >= 0.1 no MESMO DOF):**

- vx: ganho -0.02 p.p., razao 0.015 -> nao importa
- vy: ganho -0.55 p.p., razao 0.035 -> nao importa
- w: ganho +0.21 p.p., razao 0.226 -> nao importa

- **M1: acoplamento nao importa neste envelope**

**M2 (mecanismo; premissa G_ww diagonal >= (1 + 0.10) x K_ref; o acoplado remove >= 50% do excesso):** G_ww diagonal 1.0683 (+7.2%), acoplado 1.0749 (+7.9%), fracao removida -0.09 -> **nao testavel (premissa nao reproduzida)**

- sensibilidade (treino so `shoot_to_goal`, 13 eventos): G_ww diagonal 1.0793 (+8.3%), acoplado 1.0974 (+10.1%) -> nao testavel (premissa nao reproduzida)

## Leitura

- M1 e o criterio do camera-ready (item B3): responde se, no envelope destes logs, termos cruzados de comando melhoram o que o modelo reproduz no hold-out.
- M2 testa em dado real o mecanismo do C1b: se o vies do ganho de yaw em malha fechada vem da guinada induzida pela translacao, dar ao modelo os comandos de translacao como entradas deve reduzir o ganho direto de yaw.
- M3 mede o efeito no uso do modelo (free-run no harness), com o mesmo gate por evento do C2b.
- Custo: ajuste e bootstrap 2 s.