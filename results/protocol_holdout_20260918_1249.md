# Simuladores da liga no hold-out via ssl-simulation-protocol: gemeo x grSim / ER-Force - 20260918_1249

_Proveniencia: commit `a04e2b6-dirty` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed n/a | gerado por `dtssl.analysis.protocol_holdout` (dtssl 1.0.0a1) | mesmas janelas do theta oficial, stride 15, H_max 90; replay em tempo real via protocolo_

Hold-out: 10 eventos (front_to_back_01_01, side_to_side_01_05, side_to_side_01_06, side_to_side_01_07, side_to_side_02_03, shoot_to_goal_05_02, shoot_to_goal_08_01, shoot_to_goal_09_01, shoot_to_goal_12_01, shoot_to_goal_14_02); 265 janelas; h_ref = 24 amostras = 0.40 s. Variantes: grsim, grsim+preroll (`+delay` = Td identificado aplicado nos comandos enviados). `fopdt_v0=0` = o gemeo com os estados FOPDT zerados em t0 (a mesma desvantagem do grSim, que ignora a velocidade inicial no teleporte). `+preroll` = pre-rolagem de 0.50 s: teleporte P amostras antes de t0, prefixo real de comandos transmitido, trajetoria re-ancorada em SE(2) em t0 (dtssl.sim.preroll; pre-registro C2b2). `fopdt+preroll` = o gemeo submetido a mesma pre-rolagem (controle: o efeito do procedimento numa planta cuja condicao inicial exata o harness impoe).

## e_pos mediano por horizonte (bin translacional, janelas densas; NaN = janelas perdidas excluidas)

| h (s) | fopdt | fopdt_v0=0 | fopdt+preroll | grsim | grsim+preroll |
|---|---|---|---|---|---|
| 0.10 | 0.0079 | 0.0683 | 0.0137 | 0.1040 | 0.0267 |
| 0.20 | 0.0178 | 0.0964 | 0.0246 | 0.1779 | 0.0489 |
| 0.40 | 0.0388 | 0.1137 | 0.0406 | 0.2421 | 0.0996 |
| 0.70 | 0.0617 | 0.1220 | 0.0642 | 0.2818 | 0.1493 |
| 1.00 | 0.0920 | 0.1419 | 0.0883 | 0.3288 | 0.1977 |
| 1.50 | 0.1193 | 0.1783 | 0.1219 | 0.4075 | 0.2778 |

## e_ang mediano por horizonte (rad, bin translacional)

| h (s) | fopdt | fopdt_v0=0 | fopdt+preroll | grsim | grsim+preroll |
|---|---|---|---|---|---|
| 0.10 | 0.0128 | 0.0270 | 0.0215 | 0.0293 | 0.0260 |
| 0.20 | 0.0311 | 0.0366 | 0.0335 | 0.0457 | 0.0489 |
| 0.40 | 0.0440 | 0.0455 | 0.0455 | 0.0730 | 0.0691 |
| 0.70 | 0.0627 | 0.0663 | 0.0637 | 0.0967 | 0.0987 |
| 1.00 | 0.0733 | 0.0757 | 0.0742 | 0.1052 | 0.0980 |
| 1.50 | 0.0895 | 0.0776 | 0.0873 | 0.1131 | 0.1234 |

## Por evento em h_ref = 0.40 s (medianas por evento)

| variante | e_pos mediano (eventos) | gemeo vence | Wilcoxon p (gemeo < sim) | rank-biserial | janelas perdidas | |delta e_pos| vs gemeo (mediana / max) |
|---|---|---|---|---|---|---|
| grsim | 0.2398 | 10/10 | 0.000977 | +1.00 | 0/265 | 0.2209 / 0.8368 |
| grsim+preroll | 0.1106 | 10/10 | 0.000977 | +1.00 | 0/265 | 0.0539 / 0.5031 |

Gemeo (`fopdt`) em h_ref: e_pos mediano dos eventos = 0.0421 m.

## Diagnostico do replay via protocolo

| variante | endpoint | visao (Hz sim) | latencia teleporte (ms) | tau0 mediano (ms) | tau0 estimado | fase de envio | jitter envio max/med (ms) | envios atrasados | teleporte nao visto | ancora tardia | janelas curtas | gaps de visao | pre-rolagem P mediano (amostras) / curtas / re-ancoragem falhou |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grsim | grsim 127.0.0.1 vis 224.5.23.2:10020 ctrl 10301 (blue 0) | 60.00 | 16.52 | 0.00 | 248/265 | 0.50 | 1.82 / 0.00 | 0/28090 | 0 | 0 | 0 | 0 | - |
| grsim+preroll | grsim 127.0.0.1 vis 224.5.23.2:10020 ctrl 10301 (blue 0) | 60.00 | 16.66 | 0.00 | 236/265 | 0.50 | 1.53 / 0.00 | 0/35730 | 0 | 1 | 0 | 0 | 30.00 / 20 / 0 |

Validade do instrumento (pre-registro C2b, criterio V: janelas perdidas <= 5 %, jitter medio de envio < 2 ms com <= 1 % dos envios atrasados > 10 ms, espalhamento da latencia < 1 quadro, tau0 estimado em >= 50 % das janelas):

- grsim: VALIDO (janelas perdidas ok: 0/265 = 0.0 %; jitter de envio ok: medio 0.00 ms, atrasados > 10 ms: 0/28090 (max 1.8 ms); latencia do teleporte ok: espalhamento 9.1 ms vs quadro 17.2 ms; tau0 estimado ok: 248/265)
- grsim+preroll: VALIDO (janelas perdidas ok: 0/265 = 0.0 %; jitter de envio ok: medio 0.00 ms, atrasados > 10 ms: 0/35730 (max 1.5 ms); latencia do teleporte ok: espalhamento 5.4 ms vs quadro 17.0 ms; tau0 estimado ok: 236/265)

## Custo (segundos de parede)

| variante | s |
|---|---|
| fopdt | 0.7 |
| grsim | 495.7 |
| grsim+preroll | 607.5 |

Rollouts salvos (reanalise offline): `_cache_protocol_grsim_20260918_1249.npz`, `_cache_protocol_grsim_preroll_20260918_1249.npz`

## Leitura

- Os simuladores da liga entram **como saem da caixa** (modelo de robo, atuacao e visao proprios; sem calibracao ao robo RoboCIn): sao as baselines 'fisica da liga nao sintonizada', o papel que o rSim tinha no artigo, agora com o mesmo harness e as mesmas janelas.
- O alinhamento por teleporte remove o atraso de visao do simulador (ER-Force: 35 ms) mas nao o atraso de comando nem a logica de standby; `+delay` mostra quanto do gap e explicado pelo atraso de transporte identificado.
- Condicao inicial: o grSim reinicia o robo no teleporte e converte a velocidade em setpoint dos motores (toda janela parte do repouso); o ER-Force aplica a velocidade linear mas nao a de guinada (v_angular cai no eixo x do Bullet no simrobot.cpp; enviamos 0). A coluna `fopdt_v0=0` da o custo dessa desvantagem no proprio gemeo: o que sobra alem dela e fisica.
- Replay em tempo real: as janelas perdidas (teleporte nao visto / visao insuficiente) sao excluidas e contadas; use `repeat=2` para reportar a repetibilidade.
- Pre-rolagem (`+preroll`): o simulador chega a t0 com o estado que a SUA dinamica produziu sob o prefixo real de comandos, e a trajetoria e re-ancorada em t0; a condicao inicial deixa de ser imposta pelo teleporte. O que sobra de gap e fisica e atuacao. O tau0 do teleporte continua nao identificavel no grSim (robo em repouso no teleporte: estimativa saturada em 0); com a re-ancoragem em t0 o erro de tau0 vira um deslocamento de tempo comum a toda a janela (efeito de segunda ordem), nao um erro de pose.