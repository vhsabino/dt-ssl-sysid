# CLAUDE.md — Gêmeo Digital SSL (Doutorado UFPE / RobôCIn)

## Contexto (não mudar sem ordem explícita)
Tese: gêmeo digital de **fidelidade observacional comportamental** do robô SSL omnidirecional 4 rodas (versão 2025). Contribuição central: identificação grey-box por DOF — `G_i(s) = K_i/(τ_i·s+1)·e^(−Td_i·s)` para vx, vy, ω → **9 parâmetros** `[K_vx, tau_vx, Td_vx, K_vy, tau_vy, Td_vy, K_w, tau_w, Td_w]` (ordem fixa, SLDD `config/ssl_robot.sldd`), calibrados por `bayesopt` a partir de logs de competição SSL (malha fechada). Baselines: cinemática ideal, `procest('P1D')`. Custo: RMSE de posição multi-horizonte.

## Estrutura
- `src/` — pipeline MATLAB existente: `bootstrap_paths.m`, `list_splits.m`, `load_split.m`, `run_one.m`, `load_theta_mat.m`, `identify_omega_from_splits.m`
- `data/extracted/<log>/splits/<label>/<event>/` — parquet (DVC; nunca editar bruto)
- `models/` — `sysid_*.mat` versionados (`_v2`, `_v3`…)
- `results/` — tabelas, figuras, CHANGELOG (cada entrada: data, commit, script, θ, seed)
- `slr/`, `docs/`, `paper/`, `automation/` — overlay de refatoração

## Convenções
- MATLAB: funções puras quando possível; sem `clear all` em scripts de pipeline; caminhos sempre via `bootstrap_paths`.
- Python: 3.11+, `pandas`; scripts CLI com `argparse`.
- Versionamento: **nunca sobrescrever** `.mat` de modelos ou arquivos em `results/` — criar `_vN` e registrar no CHANGELOG.
- Idioma: documentos em PT-BR; artigo em EN; código/commits em EN.

## Critérios de aceite — identificação ω
`fit_val ≥ 60%`, `K_w ∈ [0.5, 2.0]`, `τ_w ∈ [0.02, 0.5] s`, `Td_w ≤ 0.15 s`. Fora disso: não promover para `sysid_initial_v2.mat`; reportar diagnóstico (excitação? `std(cmd_vw)`?).

## Definition of Done (experimento)
1. Script reproduzível commitado; 2. seed fixa; 3. resultado em `results/` com metadados (commit hash, θ, dataset); 4. entrada no CHANGELOG; 5. resumo de 3 linhas para o humano validar.

## Arquitetura verificada (2026-06-11)
- O gêmeo em `parameter_estimation_model_pid_v3.slx` é **free-run**: TransferFcn (θ do SLDD) → TransportDelay → rodas → rotação p/ global → integradores. Não há injeção de pose medida no estado; ICs dos integradores são paramétricas (`x0`, `y0`, `theta0`, via `SimulationInput`). A cadeia interna de rmse e os `From Workspace` do log antigo estão comentados no modelo.
- **`run_one` só simula — métrica no orquestrador** (`automation/rmse_pos_rebased.m`: RMSE de posição em janelas re-ancoradas, window 2.5 s / overlap 0.5, mesmo esquema de `compute_rmse_position`).
- Bounds do SLDD: **τ ≥ 0.01 s** (Min/Max não alteráveis). θ "ideal" com τ < 0.01 não simula; o baseline ideal oficial é **dead-reckoning analítico** (`automation/ideal_deadreckoning.m`); o ideal simulável mínimo é `models/sysid_ideal_v3.mat` (τ=0.01).

## Guardrails (NUNCA)
- Inventar referências bibliográficas — citar só de `slr/incluidos.bib`.
- Alterar a ordem dos campos do vetor θ ou o SLDD.
- Modificar dados em `data/` ou apagar resultados antigos.
- Reportar números não provenientes de execução real registrada.
- Expandir escopo (RL/sim-to-real) antes da qualificação sem ordem explícita.
