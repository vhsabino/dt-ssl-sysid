# Backends no hold-out: gemeo comportamental x MuJoCo (rotas a/b) x ideal - 20260907_1515

_Proveniencia: commit `fea0150` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed n/a | gerado por `dtssl.analysis.backends_holdout` (dtssl 1.0.0a1) | mesmas janelas (grade do theta oficial), stride 15, H_max 90_

Hold-out: 10 eventos (front_to_back_01_01, side_to_side_01_05, side_to_side_01_06, side_to_side_01_07, side_to_side_02_03, shoot_to_goal_05_02, shoot_to_goal_08_01, shoot_to_goal_09_01, shoot_to_goal_12_01, shoot_to_goal_14_02); 265 janelas; h_ref = 24 amostras = 0.40 s.

Modelos: `fopdt` = AnalyticFOPDTPlant (theta oficial); `mujoco-velocity` = rota (a), a mesma planta dirigindo o chassi no MuJoCo; `mujoco-rollers` = rota (b), rodas omni + roletes livres, **sem sintonia e sem atraso**; `mujoco-rollers-delay` = rota (b) + atraso de transporte Td por DOF do theta oficial; `ideal` = cinematica ideal.

## e_pos mediano por horizonte (bin translacional, janelas densas)

| h (s) | fopdt | mujoco-velocity | mujoco-rollers | mujoco-rollers-delay | ideal |
|---|---|---|---|---|---|
| 0.10 | 0.0079 | 0.0079 | 0.0124 | 0.0091 | 0.0264 |
| 0.20 | 0.0178 | 0.0178 | 0.0314 | 0.0223 | 0.0501 |
| 0.40 | 0.0388 | 0.0388 | 0.0729 | 0.0477 | 0.1005 |
| 0.70 | 0.0617 | 0.0617 | 0.1182 | 0.0920 | 0.1516 |
| 1.00 | 0.0920 | 0.0920 | 0.1706 | 0.1247 | 0.2165 |
| 1.50 | 0.1193 | 0.1192 | 0.2599 | 0.1766 | 0.2910 |

## e_ang mediano por horizonte (rad, bin translacional)

| h (s) | fopdt | mujoco-velocity | mujoco-rollers | mujoco-rollers-delay | ideal |
|---|---|---|---|---|---|
| 0.10 | 0.0128 | 0.0128 | 0.0202 | 0.0164 | 0.0232 |
| 0.20 | 0.0311 | 0.0311 | 0.0374 | 0.0316 | 0.0442 |
| 0.40 | 0.0440 | 0.0440 | 0.0641 | 0.0487 | 0.0668 |
| 0.70 | 0.0627 | 0.0627 | 0.0751 | 0.0632 | 0.0757 |
| 1.00 | 0.0733 | 0.0733 | 0.0809 | 0.0721 | 0.0921 |
| 1.50 | 0.0895 | 0.0895 | 0.0971 | 0.0878 | 0.0953 |

## Por evento em h_ref = 0.40 s (medianas por evento, n = 10)

| modelo | e_pos mediano (eventos) | gemeo vence | Wilcoxon p (gemeo < modelo) | rank-biserial | |delta e_pos| vs gemeo (mediana / max, todas as janelas) |
|---|---|---|---|---|---|
| mujoco-velocity | 0.0421 | 7/10 | 0.216 | +0.31 | 0.0000 / 0.0016 |
| mujoco-rollers | 0.0791 | 10/10 | 0.000977 | +1.00 | 0.0381 / 0.3494 |
| mujoco-rollers-delay | 0.0487 | 9/10 | 0.00977 | +0.82 | 0.0254 / 0.1671 |
| ideal | 0.1177 | 10/10 | 0.000977 | +1.00 | 0.0597 / 0.5328 |

Gemeo (`fopdt`) em h_ref: e_pos mediano dos eventos = 0.0421 m.

## Custo (segundos de parede para os rollouts do hold-out)

| modelo | s |
|---|---|
| fopdt | 0.2 |
| mujoco-velocity | 3.0 |
| mujoco-rollers | 15.5 |
| mujoco-rollers-delay | 16.1 |
| ideal | 0.1 |

## Leitura

- `mujoco-velocity` x `fopdt`: |delta e_pos| e a fidelidade do *embedding* - o quanto o chassi MuJoCo (servo dead-beat + limites de forca) reproduz a planta comportamental nas mesmas janelas.
- `mujoco-rollers` e a rota fisica **como sai da caixa** (geometria nominal, contato da receita de Wan et al. 2026): nao foi calibrada contra dados - e a baseline 'simulador fisico nao sintonizado', comparavel ao rSim do artigo; `-delay` isola o efeito do atraso identificado.
- Estatistica por evento (n pequeno): Wilcoxon unilateral pareado e rank-biserial, como em `clustered_stats`; nao ha bootstrap por blocos aqui.