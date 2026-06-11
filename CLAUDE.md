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
- O gêmeo em `parameter_estimation_model_pid_v3.slx` é **free-run**: TransferFcn (θ do SLDD) → TransportDelay → rodas → rotação p/ global → integradores. Não há injeção de pose medida no estado e **não existe bloco "Layer 3"** (inventário completo: 174 blocos; únicos Gains ativos `Multiply`/`Multiply1`=1). ICs dos integradores são paramétricas (`x0`, `y0`, `theta0`, via `SimulationInput`). A cadeia interna de rmse e os `From Workspace` do log antigo estão comentados no modelo.
- **`run_one` só simula — métrica no orquestrador** (`automation/rmse_pos_rebased.m`: RMSE de posição em janelas re-ancoradas, window 2.5 s / overlap 0.5, mesmo esquema de `compute_rmse_position`).
- Bounds do SLDD: **τ ≥ 0.01 s** (Min/Max não alteráveis). θ "ideal" com τ < 0.01 não simula; o baseline **ideal oficial é `ideal_analytic`** — dead-reckoning analítico (`automation/ideal_deadreckoning.m`), avaliado com a mesma métrica; o ideal simulável mínimo é `models/sysid_ideal_v3.mat` (τ=0.01).

## Estado atual (2026-06-11, commit eb97620+)
- **Zonas mortas da cadeia de rodas parametrizadas com default 0** (eram |vx|<0.1, |vy|<0.1, |ω|<0.3 e engoliam 84% do cmd_vw do square). Com isso o gêmeo ideal_v3 é totalmente explicável: reconciliação analítico (FOH exato + Euler 60 Hz) vs Simulink fecha em max|Δx|=0.0046 m, |Δy|=0.0057 m, |Δθ|=0.0009 rad no square_01_01.
- **RMSE re-ancorado (h=2.5 s), mediana em square_01_01 + 5 hold-outs shoot_to_goal**: ideal_analytic **0.490 m**; procest (ω placeholder K=1, τ=0.1) **0.548 m**; procest + ω candidato (K=1.353, τ=0.0354, Td=0.1058; fit_val 52.6%) **0.656 m** — o candidato ω **piora** posição (ganho 1.35 amplifica deriva de heading em malha aberta) e **não foi promovido**.
- Próximos passos: re-identificar ω (investigar viés de K_w; considerar coleta dedicada) e só então bayesopt sobre os 9 parâmetros.

## Guardrails (NUNCA)
- Inventar referências bibliográficas — citar só de `slr/incluidos.bib`.
- Alterar a ordem dos campos do vetor θ ou o SLDD.
- Modificar dados em `data/` ou apagar resultados antigos.
- Reportar números não provenientes de execução real registrada.
- Expandir escopo (RL/sim-to-real) antes da qualificação sem ordem explícita.
