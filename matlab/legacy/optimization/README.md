# `optimization/` — PSO da cinemática/PI de roda (abr–mai/2026, ARQUIVADO)

Era `matlab/optimization/`. Primeira abordagem do gêmeo (antes da identificação grey-box por DOF):
otimizar por enxame de partículas (`particleswarm`, workers paralelos com cache isolado) um
vetor `K_Matrix` de 12 deltas — 4 constantes cinemáticas de roda (K1..K4) + 8 ganhos PI dos
motores — no modelo Simulink `parameter_estimation_model_pid_v2`, com o custo em
`matlab/legacy/train/avaliar_gemeo_digital.m`.

| Script | Papel |
|---|---|
| `run_pso_optimization.m` | PSO 12 variáveis (K1..K4 cin + Kp/Ki × 4 motores) |
| `run_pso_optimization_stage_1.m` | estágio 1: só as 4 constantes cinemáticas |
| `train_parameter_estimation.m` | valores iniciais dos 8 ganhos PI (`ganhos_PID`) para o bloco Constant |

Estado: abandonado antes da criação do repo (11/06/2026). O `pid_v3` mantém `K_Matrix = zeros(1,12)`
no `InitFcn` (cadeia de rodas identidade). CHANGELOG 2026-07-24 19:35 (Parte D) rastreia a zona
morta `|ω|<0.3` do `kinematicSolver`/chart como herança "provavelmente da era PSO". Sem entradas
próprias no CHANGELOG. Requer Parallel Computing + Global Optimization Toolbox.
