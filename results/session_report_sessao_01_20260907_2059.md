# Sessao gravada sessao_01: contrato, estatisticas de comando e round trip no harness - 20260907_2059

_Proveniencia: commit `a3786f7` | theta `config/twin_params.json` (vx: K=1.1192 tau=0.0718 Td=0.0691; vy: K=1.0524 tau=0.1273 Td=0.0565; w: K=1.0016 tau=0.0828 Td=0.0890) | dataset `2026-05-18_19-2-15` | seed n/a | gerado por `dtssl.analysis.session_report` (dtssl 1.0.0a1) | sessao `C:\Users\victo\Documents\digitaltwin\results\sessao_01`_

Contrato dos logs: OK (commands 12 colunas, processed_robots 10 colunas)
Robos [0, 1, 2, 3, 4, 5] (team ['allies']), 13207 ticks = 220.1 s, 79242 linhas de comando, 79248 linhas de pose; posicoes x -4.36..4.34 m, y -3.01..3.00 m.

## Comandos (RMS por robo, m/s e rad/s)

| robo | |v| med | |v| p90 | |w| med | |w| p90 | |w|<0.58 | parado |
|---|---|---|---|---|---|---|
| 0 | 0.070 | 0.725 | 0.111 | 0.312 | 99.3 % | 25.2 % |
| 1 | 0.579 | 1.483 | 0.560 | 3.122 | 50.8 % | 8.9 % |
| 2 | 0.577 | 1.445 | 0.236 | 1.613 | 70.9 % | 11.5 % |
| 3 | 0.576 | 1.602 | 0.155 | 0.635 | 88.4 % | 16.2 % |
| 4 | 0.561 | 1.604 | 0.205 | 1.260 | 78.6 % | 15.5 % |
| 5 | 0.582 | 1.644 | 0.268 | 1.873 | 70.3 % | 10.7 % |
| todos | 0.484 | 1.451 | 0.206 | 1.462 | 76.4 % | 14.7 % |
| competicao `shoot_to_goal` (18 ev) | 0.605 | 1.938 | 0.229 | 1.173 | 76.5 % | 4.0 % |

Flags: chute reto em 3603 ticks, chip em 14259 ticks, dribbler ligado em 0.0 % dos ticks; |v| max 3.14 m/s, |w| max 7.54 rad/s, |v| > 2.9 m/s em 0.3 %.

## Round trip no harness (janelas re-ancoradas, theta oficial; e_pos mediano em h_ref = 0.40 s)

| robo | N | janelas | twin med | twin p90 | ideal med |
|---|---|---|---|---|---|
| 0 | 13207 | 874 (parado 36) | 0.0000 | 0.0002 | 0.0118 |
| 1 | 13207 | 874 (parado 16) | 0.0002 | 0.0007 | 0.0975 |
| 2 | 13207 | 874 (parado 16) | 0.0001 | 0.0007 | 0.0844 |
| 3 | 13207 | 874 (parado 23) | 0.0001 | 0.0008 | 0.0836 |
| 4 | 13207 | 874 (parado 25) | 0.0001 | 0.0007 | 0.0756 |
| 5 | 13207 | 874 (parado 18) | 0.0002 | 0.0009 | 0.1018 |

Leitura: sessao gerada pelo backend fopdt -> o twin deve reproduzir as poses gravadas ao nivel do mm (residuo = reamostragem do loader + contatos com bola/robos/paredes); a cinematica ideal fica no gap usual (~0.1 m), como nos logs reais. A coluna |w|<0.58 compara a fracao de comandos de guinada abaixo do equivalente de corpo da zona morta com a dos logs de competicao.