# C4 - Malha fechada da estrategia real sobre o gemeo vs logs de competicao (P1-P5) - 20260907_2137

_Proveniencia: commit `618a008` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed n/a | gerado por `dtssl.analysis.closed_loop_stats` (dtssl 1.0.0a1) | sessoes `sessao_01` | pool de competicao 46 eventos (front_to_back, side_to_side, shoot_to_goal, square)_

Pre-registro: docs/PREREGISTRO_C4_MALHA_FECHADA_20260908.md (criterios P1-P5 fixados a priori para as
distribuicoes completas; medianas do session_report ja tinham sido vistas). Todas as estatisticas de
comando na grade comum de 60 Hz (ZOH, regra do loader); a competicao e logada em rajadas de 2-10 ms.
Jogadores de campo = robos da sessao exceto o de maior fracao parada (goleiro, reportado a parte).
Pool de competicao = os 46 eventos de jogo do artigo (rotate = coleta dedicada, so descritivo).
RESSALVA DE SELECAO: os eventos de competicao sao segmentos rotulados por manobra (parado 4 %),
a sessao e jogo continuo; a massa perto de zero difere por construcao e nao e corrigida.

- Sessao `sessao_01`: robos [0, 1, 2, 3, 4, 5], 13207 ticks = 220.1 s; goleiro = robo 0 (parado 25.2 %).

## Tabela principal (grade de 60 Hz)

| conjunto | N (60 Hz) | \|v\| p50 / p90 / max (m/s) | \|w\| p50 / p90 / max (rad/s) | parado % | \|w\|<0.58 % | zona morta alterado / zerado % | \|v\|>2.9 % | med \|dv\| / \|dw\| por tick | chute / chip armado (ticks/min) | \|v_meas\| p50 / p90 |
|---|---|---|---|---|---|---|---|---|---|---|
| sessao: jogadores de campo | 66035 | 0.578 / 1.554 / 3.14 | 0.251 / 1.687 / 7.54 | 12.6 | 71.8 | 27.3 / 7.8 | 0.31 | 0.0181 / 0.0041 | 196.4 / 80.9 | 0.500 / 1.582 |
| sessao: goleiro | 13207 | 0.070 / 0.725 / 1.76 | 0.111 / 0.312 / 7.54 | 25.2 | 99.3 | 70.0 / 26.9 | 0.00 | 0.0006 / 0.0014 | 0.0 / 3482.8 | 0.073 / 0.592 |
| competicao: pool (46 ev.) | 22812 | 1.000 / 1.846 / 2.91 | 0.104 / 0.556 / 7.51 | 1.4 | 90.5 | 16.0 / 2.6 | 0.01 | 0.0132 / 0.0060 | 222.0 / 0.0 | 0.944 / 1.695 |
| competicao: `front_to_back` (4 ev.) | 1980 | 1.000 / 1.836 / 2.91 | 0.033 / 0.171 / 0.84 | 0.0 | 98.8 | 5.6 / 0.0 | 0.10 | 0.0030 / 0.0030 | 0.0 / 0.0 | 0.979 / 1.860 |
| competicao: `side_to_side` (13 ev.) | 7269 | 1.000 / 1.954 / 2.62 | 0.062 / 0.255 / 3.72 | 0.0 | 98.0 | 7.6 / 0.0 | 0.00 | 0.0049 / 0.0042 | 0.0 / 0.0 | 0.953 / 1.774 |
| competicao: `shoot_to_goal` (18 ev.) | 7576 | 0.614 / 1.962 / 2.91 | 0.254 / 1.269 / 7.51 | 3.6 | 74.5 | 31.7 / 6.7 | 0.01 | 0.0138 / 0.0118 | 668.7 / 0.0 | 0.594 / 1.791 |
| competicao: `square` (11 ev.) | 5987 | 1.044 / 1.743 / 2.14 | 0.107 / 0.313 / 0.78 | 0.7 | 98.9 | 9.8 / 1.3 | 0.00 | 0.0338 / 0.0083 | 0.0 / 0.0 | 1.065 / 1.538 |
| competicao: `rotate` (10 ev.) (fora do pool) | 5758 | 0.000 / 0.000 / 0.00 | 1.000 / 5.000 / 5.00 | 0.0 | 40.0 | 40.0 / 40.0 | 0.00 | 0.0000 / 0.0000 | 0.0 / 0.0 | 0.013 / 0.026 |

|v_meas| = velocidade logada (visao no robo real; gemeo na sessao), descritivo. Zona morta por roda (1.567 rad/s, `apply_body_deadzone`): 'alterado' = ao menos uma roda mascarada, 'zerado' = todas.

## Distancias e criterios pre-registrados (jogadores de campo vs pool de competicao)

| criterio | valor sessao | valor competicao | estatistica | limite | ok |
|---|---|---|---|---|---|
| P1 W1(\|v\|) | - | - | 0.3261 m/s | <= 0.2 | nao |
| P1 W1(\|w\|) | - | - | 0.3868 rad/s | <= 0.2 | nao |
| P2 \|w\| < 0.58 rad/s | 71.8 % | 90.5 % | diff -18.7 pp | +-10 pp | nao |
| P3 \|v\| > 2.9 m/s | 0.31 % | 0.01 % | diff +0.30 pp | +-2 pp | SIM |
| P4 medianas de \|v\| (janelas 110 vs eventos 46) | med 0.578 | med 1.000 | MW p = 0.0000, delta = -0.683 | p > 0.05 ou \|delta\| <= 0.33 | nao |
| P4 medianas de \|w\| | med 0.250 | med 0.117 | MW p = 0.0003, delta = 0.364 | idem | nao |
| P5 rugosidade (dv_med por tick) | 0.0181 m/s | 0.0132 m/s | razao 1.37 | [1/2, 2] | SIM |

**Veredito: 2/5 -> NAO PLAUSIVEL** (plausivel >= 4, parcial 3, nao plausivel <= 2).

KS bilateral (descritivo): \|v\| D = 0.305 (p = 0.00e+00), \|w\| D = 0.254 (p = 0.00e+00); n = 66035 vs 22812.
Sem as amostras paradas (descritivo): W1(\|v\|) = 0.2479 m/s, W1(\|w\|) = 0.4718 rad/s.
Razao de rastreamento mediana(\|v_meas\|)/mediana(\|v_cmd\|): sessao (gemeo) 0.865, competicao (robo real) 0.944 -- diferenca descritiva, nao criterio.

## Por rotulo (jogadores de campo da sessao vs cada rotulo; descritivo)

| rotulo | ev. | W1 \|v\| (m/s) | W1 \|w\| (rad/s) | KS \|v\| | KS \|w\| | P4 \|v\|: p / delta | P4 \|w\|: p / delta | rastreamento |
|---|---|---|---|---|---|---|---|---|
| `front_to_back` | 4 | 0.329 | 0.570 | 0.391 | 0.491 | 0.001 / -0.95 | 0.003 / 0.80 | 0.979 |
| `side_to_side` | 13 | 0.397 | 0.534 | 0.440 | 0.405 | 0.000 / -0.96 | 0.000 / 0.67 | 0.953 |
| `shoot_to_goal` | 18 | 0.179 | 0.127 | 0.176 | 0.097 | 0.076 / -0.26 | 0.905 / -0.02 | 0.968 |
| `square` | 11 | 0.463 | 0.504 | 0.427 | 0.338 | 0.000 / -0.95 | 0.010 / 0.47 | 1.021 |
| `rotate` (fora do pool) | 10 | 0.649 | 1.244 | 0.785 | 0.498 | 0.000 / 0.94 | 0.001 / -0.66 | nan |

## Por robo (sessao)

| conjunto | N (60 Hz) | \|v\| p50 / p90 / max (m/s) | \|w\| p50 / p90 / max (rad/s) | parado % | \|w\|<0.58 % | zona morta alterado / zerado % | \|v\|>2.9 % | med \|dv\| / \|dw\| por tick | chute / chip armado (ticks/min) | \|v_meas\| p50 / p90 |
|---|---|---|---|---|---|---|---|---|---|---|
| `sessao_01` robo 0 (goleiro) | 13207 | 0.070 / 0.725 / 1.76 | 0.111 / 0.312 / 7.54 | 25.2 | 99.3 | 70.0 / 26.9 | 0.00 | 0.0006 / 0.0014 | 0.0 / 3482.8 | 0.073 / 0.592 |
| `sessao_01` robo 1 | 13207 | 0.579 / 1.483 / 3.14 | 0.560 / 3.122 / 7.54 | 8.9 | 50.8 | 29.0 / 11.6 | 0.37 | 0.0187 / 0.0103 | 139.8 / 1.4 | 0.537 / 1.513 |
| `sessao_01` robo 2 | 13207 | 0.577 / 1.445 / 3.00 | 0.236 / 1.613 / 7.54 | 11.5 | 70.9 | 27.7 / 8.6 | 0.45 | 0.0170 / 0.0042 | 342.9 / 141.8 | 0.466 / 1.481 |
| `sessao_01` robo 3 | 13207 | 0.576 / 1.602 / 2.92 | 0.155 / 0.635 / 7.54 | 16.2 | 88.4 | 26.0 / 4.6 | 0.05 | 0.0169 / 0.0021 | 128.9 / 90.5 | 0.459 / 1.617 |
| `sessao_01` robo 4 | 13207 | 0.561 / 1.604 / 3.13 | 0.205 / 1.260 / 7.54 | 15.5 | 78.6 | 27.0 / 8.2 | 0.36 | 0.0135 / 0.0031 | 181.3 / 46.1 | 0.441 / 1.624 |
| `sessao_01` robo 5 | 13207 | 0.582 / 1.644 / 3.07 | 0.268 / 1.873 / 7.44 | 10.7 | 70.3 | 27.0 / 6.2 | 0.33 | 0.0249 / 0.0050 | 189.2 / 124.6 | 0.574 / 1.671 |
| `sessao_01` todos | 79242 | 0.484 / 1.451 / 3.14 | 0.206 / 1.462 / 7.54 | 14.7 | 76.4 | 34.4 / 11.0 | 0.26 | 0.0109 / 0.0031 | 163.7 / 647.8 | - |

Continuidade com session_report (linhas brutas, sem grade): sessao todos os robos |v| med 0.484 (p90 1.451), |w| med 0.206 (p90 1.462), |w|<0.58 em 76.4 %, parado 14.7 %; pool de competicao bruto |v| med 1.000, |w| med 0.089, |w|<0.58 em 94.0 %, parado 1.0 %.

![ECDF |v_cmd| e |w_cmd|](figs/closed_loop_stats_20260907_2137.png)

## Leitura

- Veredito pre-registrado: 2/5 (nao plausivel). Criterios: P1 FALHA, P2 FALHA, P3 ok, P4 FALHA, P5 ok.
- Amplitude: |v_cmd| mediano 0.578 vs 1.000 m/s (p90 1.554 vs 1.846); |w_cmd| mediano 0.251 vs 0.104 rad/s (p90 1.687 vs 0.556); parado 12.6 % vs 1.4 % (ressalva de selecao).
- Zona morta: |w| < 0.58 rad/s em 71.8 % (sessao) vs 90.5 % (competicao); comando alterado por roda 27.3 % vs 16.0 %, zerado 7.8 % vs 2.6 % -- o regime de guinada diluida do artigo reaparece quando a estrategia joga contra o gemeo.
- Rastreamento (descritivo): mediana(|v_meas|)/mediana(|v_cmd|) = 0.865 no gemeo vs 0.944 no robo real; o gemeo P1D nao contem escorregamento nem saturacao, o robo real sim.
- Leitura de 'nao plausivel': a estrategia, fechando a malha sobre o gemeo, emite comandos com amplitude/guinada/saturacao/rugosidade fora do que emite contra o robo real.