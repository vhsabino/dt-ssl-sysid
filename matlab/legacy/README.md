# `matlab/legacy/` — scripts MATLAB arquivados (02/09/2026)

Tudo aqui foi **substituído** ou **encerrou seu papel**; é mantido por rastreabilidade
(cada entrada de `results/CHANGELOG.md` cita o script que a gerou pelo caminho antigo,
`automation/<nome>.m` ou `matlab/<grupo>/<nome>.m`). Nada nesta pasta é chamado pelo
pacote Python `dtssl` nem pelos scripts vivos de `matlab/dtssl/`.

| Grupo | O que era | Substituído por / estado |
|---|---|---|
| [`omega_closedloop/`](omega_closedloop/README.md) | tentativas de identificar ω com dados de **malha fechada** de competição (jun/2026): `check_excitation`, `identify_omega_from_splits`, `identify_omega_v3_linear`, diagnósticos de ganho | `matlab/dtssl/identify_omega_rotate.m` (dataset dedicado de rotação pura, malha aberta, **PROMOVIDO** 24/07/2026) |
| [`campaign_june/`](campaign_june/README.md) | campanha de avaliação de junho (`run_all_experiments`, `eval_campaign`, `eval_horizons`, `eval_theta_*`, figuras F1–F4, auditoria de grade, `debug_baseline`, `test_wheel_chain`) | harness Python `dtssl.eval` / `dtssl.analysis` (métrica multi-horizonte por janela, gates estatísticos); os `.m` de métrica que sobreviveram (`rmse_pos_rebased*`, `rmse_heading_rebased`) estão em `matlab/dtssl/` |
| [`bayesopt/`](bayesopt/README.md) | calibração comportamental conjunta dos 9 parâmetros (bayesopt v1 no Simulink, Fase 0 proxy, v2 no proxy analítico) — **nenhum candidato promovido** | abandonado: θ oficial = identificação por DOF (`identify_trans_dof` + `identify_omega_rotate`) |
| [`batch_20260724/`](batch_20260724/README.md) | wrappers batch da sessão de 24/07/2026 (gate SE(2) do ω, sensibilidade de quantização de Td) | só reexecução; caminhos Windows removidos |
| [`sysid/`](sysid/README.md) | pipeline de identificação **antigo** (concatenado por label, `build_idData_per_dof` → `identify_per_dof` → `compute_rmse_position` → `run_bayesopt`) — gerou `sysid_initial.mat` | `matlab/dtssl/identify_trans_dof.m` (por evento, hold-out, velocidade derivada da visão) |
| [`optimization/`](optimization/README.md) | PSO sobre `K_Matrix` (4 ganhos cinemáticos + 8 ganhos PI de roda) no modelo `pid`/`pid_v2` (abr–mai/2026) | abandonado antes da criação do repo (11/06/2026); modelo `pid_v3` tem `K_Matrix = zeros(1,12)` |
| [`train/`](train/README.md) | função de custo do PSO (`avaliar_gemeo_digital`), `InitFcn` legado (`control_parameters`), pré-processamento de logs `.log.gz.txt` (`time_raw`, `time_sync`) | ETL: `dtssl etl extract/split/rotate`; custo: `dtssl.eval` |
| [`viewer/`](viewer/README.md) | visualizadores MATLAB (GUI Layout Toolbox): player de logs e overlay Simulink | GUI PySide6 `dtssl gui` (modos Debug/Bridge/Replay) |
| [`ros_bridge/`](ros_bridge/README.md) | conversores bus↔msg ROS 2 gerados pelo Simulink para `parameter_estimation_model_with_ros*.slx` | ROS removido do fluxo; modelos `with_ros*` descartados (ver `tools/apply_refactor_manifest.json`) |
| [`analytical/`](analytical/README.md) | cinemática de rodas (`kinematicSolver`, `inverse_kinematics_solver`, `local2global`) com as constantes do CAD | `dtssl.kinematics` (Python; verificado contra estes arquivos a 1e-6 / 2e-11) |
| [`simulink_io/`](simulink_io/README.md) | scripts de carga `load_*_to_timeseries*.m` (workspace base → Simulink) | `matlab/dtssl/canonical_split.m` + `matlab/simulink_io/load_split.m` |
| [`scripts/`](scripts/README.md) | `run_one.m` (θ por nome fixo) e `test.m` (setup + link do SLDD) | `matlab/dtssl/run_one_mat.m`; `matlab/sldd/{setup_sldd,link_sldd_to_model}.m` |

## Como executar algo daqui (se precisar)

```matlab
cd <raiz do repo>                 % os scripts legados usam caminhos relativos à raiz
addpath('matlab'); bootstrap_paths('legacy');   % matlab/dtssl + sldd + simulink_io + genpath(matlab/legacy)
```

Atenção:
- `bootstrap_paths` **não muda mais o diretório corrente** (antes fazia `cd` na raiz). Por isso o
  `cd <raiz>` acima é obrigatório para os scripts legados; os scripts vivos de `matlab/dtssl`
  resolvem caminhos contra a raiz do repo sozinhos.
- Referências a `results/sysid_initial.mat` e `results/sysid_bayesopt.mat` foram trocadas por
  `models/…` (os `.mat` de modelo vivem em `models/`; mover os arquivos no PC conforme
  `tools/apply_refactor_manifest.json`).
- Os wrappers de `batch_20260724/` e `train/control_parameters.m` tinham
  `C:\Users\victo\Documents\digitaltwin` hard-coded; agora derivam a raiz de `mfilename('fullpath')`.
- Vários scripts escrevem o SLDD versionado (`config/ssl_robot.sldd`) via `apply_theta` — restaurar
  com `git restore config/ssl_robot.sldd` depois.
- Muitos dependem de artefatos que **não** estão no git (`results/traj_eval_campaign_*.mat`,
  `build/*.mat`, `scripts/local/...`); estão listados no README de cada grupo.

## Regras

1. Não editar para "consertar": se um script legado voltar a ser necessário, portá-lo para
   `matlab/dtssl/` (ou para `dtssl.analysis` em Python) e registrar no `results/CHANGELOG.md`.
2. Não apagar sem revisão — as entradas históricas do CHANGELOG apontam para estes arquivos.
