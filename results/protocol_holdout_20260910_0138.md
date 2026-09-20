# Simuladores da liga no hold-out via ssl-simulation-protocol: gemeo x grSim / ER-Force - 20260910_0138

_Proveniencia: commit `7c7bcad-dirty` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed n/a | gerado por `dtssl.analysis.protocol_holdout` (dtssl 1.0.0a1) | mesmas janelas do theta oficial, stride 15, H_max 90; replay em tempo real via protocolo_

Hold-out: 10 eventos (front_to_back_01_01, side_to_side_01_05, side_to_side_01_06, side_to_side_01_07, side_to_side_02_03, shoot_to_goal_05_02, shoot_to_goal_08_01, shoot_to_goal_09_01, shoot_to_goal_12_01, shoot_to_goal_14_02); 265 janelas; h_ref = 24 amostras = 0.40 s. Variantes: grsim, grsim+delay (`+delay` = Td identificado aplicado nos comandos enviados). `fopdt_v0=0` = o gemeo com os estados FOPDT zerados em t0 (a mesma desvantagem do grSim, que ignora a velocidade inicial no teleporte).

## e_pos mediano por horizonte (bin translacional, janelas densas; NaN = janelas perdidas excluidas)

| h (s) | fopdt | fopdt_v0=0 | grsim | grsim+delay |
|---|---|---|---|---|
| 0.10 | 0.0079 | 0.0683 | 0.1040 | 0.1043 |
| 0.20 | 0.0178 | 0.0964 | 0.1765 | 0.1761 |
| 0.40 | 0.0388 | 0.1137 | 0.2389 | 0.2335 |
| 0.70 | 0.0617 | 0.1220 | 0.2818 | 0.2700 |
| 1.00 | 0.0920 | 0.1419 | 0.3233 | 0.3040 |
| 1.50 | 0.1193 | 0.1783 | 0.4061 | 0.3633 |

## e_ang mediano por horizonte (rad, bin translacional)

| h (s) | fopdt | fopdt_v0=0 | grsim | grsim+delay |
|---|---|---|---|---|
| 0.10 | 0.0128 | 0.0270 | 0.0293 | 0.0282 |
| 0.20 | 0.0311 | 0.0366 | 0.0457 | 0.0439 |
| 0.40 | 0.0440 | 0.0455 | 0.0738 | 0.0627 |
| 0.70 | 0.0627 | 0.0663 | 0.0955 | 0.0901 |
| 1.00 | 0.0733 | 0.0757 | 0.1026 | 0.0905 |
| 1.50 | 0.0895 | 0.0776 | 0.1151 | 0.1119 |

## Por evento em h_ref = 0.40 s (medianas por evento)

| variante | e_pos mediano (eventos) | gemeo vence | Wilcoxon p (gemeo < sim) | rank-biserial | janelas perdidas | |delta e_pos| vs gemeo (mediana / max) |
|---|---|---|---|---|---|---|
| grsim | 0.2341 | 10/10 | 0.000977 | +1.00 | 0/265 | 0.2172 / 0.8332 |
| grsim+delay | 0.2345 | 10/10 | 0.000977 | +1.00 | 0/265 | 0.2106 / 0.8159 |

Gemeo (`fopdt`) em h_ref: e_pos mediano dos eventos = 0.0421 m.

## Diagnostico do replay via protocolo

| variante | endpoint | visao (Hz sim) | latencia teleporte (ms) | tau0 mediano (ms) | tau0 estimado | fase de envio | jitter envio max/med (ms) | envios atrasados | teleporte nao visto | ancora tardia | janelas curtas | gaps de visao |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grsim | grsim 127.0.0.1 vis 224.5.23.2:10020 ctrl 10301 (blue 0) | 60.00 | 16.12 | 0.00 | 248/265 | 0.50 | 1.66 / 0.00 | 0/28090 | 0 | 0 | 0 | 0 |
| grsim+delay | grsim 127.0.0.1 vis 224.5.23.2:10020 ctrl 10301 (blue 0) | 60.00 | 17.10 | 0.00 | 248/265 | 0.50 | 5.45 / 0.00 | 0/28090 | 0 | 0 | 0 | 0 |

Validade do instrumento (pre-registro C2b, criterio V: janelas perdidas <= 5 %, jitter medio de envio < 2 ms com <= 1 % dos envios atrasados > 10 ms, espalhamento da latencia < 1 quadro, tau0 estimado em >= 50 % das janelas):

- grsim: VALIDO (janelas perdidas ok: 0/265 = 0.0 %; jitter de envio ok: medio 0.00 ms, atrasados > 10 ms: 0/28090 (max 1.7 ms); latencia do teleporte ok: espalhamento 4.9 ms vs quadro 17.2 ms; tau0 estimado ok: 248/265)
- grsim+delay: VALIDO (janelas perdidas ok: 0/265 = 0.0 %; jitter de envio ok: medio 0.00 ms, atrasados > 10 ms: 0/28090 (max 5.5 ms); latencia do teleporte ok: espalhamento 2.6 ms vs quadro 17.2 ms; tau0 estimado ok: 248/265)

## Custo (segundos de parede)

| variante | s |
|---|---|
| fopdt | 0.4 |
| grsim | 495.7 |
| grsim+delay | 495.6 |

Rollouts salvos (reanalise offline): `_cache_protocol_grsim_20260910_0138.npz`, `_cache_protocol_grsim_delay_20260910_0138.npz`

## Leitura

- Os simuladores da liga entram **como saem da caixa** (modelo de robo, atuacao e visao proprios; sem calibracao ao robo RoboCIn): sao as baselines 'fisica da liga nao sintonizada', o papel que o rSim tinha no artigo, agora com o mesmo harness e as mesmas janelas.
- O alinhamento por teleporte remove o atraso de visao do simulador (ER-Force: 35 ms) mas nao o atraso de comando nem a logica de standby; `+delay` mostra quanto do gap e explicado pelo atraso de transporte identificado.
- Condicao inicial: o grSim reinicia o robo no teleporte e converte a velocidade em setpoint dos motores (toda janela parte do repouso); o ER-Force aplica a velocidade linear mas nao a de guinada (v_angular cai no eixo x do Bullet no simrobot.cpp; enviamos 0). A coluna `fopdt_v0=0` da o custo dessa desvantagem no proprio gemeo: o que sobra alem dela e fisica.
- Replay em tempo real: as janelas perdidas (teleporte nao visto / visao insuficiente) sao excluidas e contadas; use `repeat=2` para reportar a repetibilidade.