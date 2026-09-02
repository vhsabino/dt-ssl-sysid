# `legacy/` — material arquivado fora do pacote (02/09/2026)

Nada aqui é importado por `dtssl`, por `matlab/dtssl/` nem pelos testes. Mantido por rastreabilidade;
o índice dos scripts MATLAB arquivados fica em `matlab/legacy/README.md`.

| Pasta | O que é | Origem |
|---|---|---|
| `archive/rl/` | vertente **RL** pausada (mai/2026): `train_rl.m`/`play_rl.m` (agente TD3 residual sobre os ganhos PI dos motores, observação = erros P/I/D de x,y,θ) e os modelos `rl_model.slx`, `rl_model_with_ros.slx` (ponteiros Git LFS) | `archive/rl/` |
| `archive/old_viewers/` | visualizadores ROS 2 em tempo real (`VisualizadorTempoReal{,2,ComErro}.m`, GUI Layout Toolbox) | `archive/old_viewers/` |
| `archive/old_evaluators/` | versões antigas do custo do PSO (`avaliar_gemeo_digital_{v0,stage_1}.m`) | `archive/old_evaluators/` |
| `archive/tests/` | scratch pads (`test.m`, `test2.m`, `temp.m`, `smoke_test_caminho2.m`, `test_env.py`) | `archive/tests/` |
| `archive/ssl_robot_stale_scripts_copy_2026-05-23.sldd` | cópia stale do SLDD que vivia em `scripts/` (o canônico é `config/ssl_robot.sldd`) | `archive/` |
| `archive/README.md` | índice original do `archive/` (atualizado) | `archive/` |
| `apresentacao/` | roteiro executável da reunião de orientação de 12/06/2026 (`orientacao_20260612.m`, 9 seções, `RERUN=false`) + `guia_estudo_20260612.md`; os binários `.mlx`/`.pdf` são movidos pelo `tools/apply_refactor_manifest.json` e o `.asv` é descartado | `apresentacao/` (era gitignored) |

Removido em vez de arquivado: `archive/bus_conv_fcns_legacy/` (duplicata byte-a-byte de
`matlab/ros_bridge/`, que vive agora em `matlab/legacy/ros_bridge/`).

Não confundir com `matlab/legacy/` (scripts MATLAB do pipeline substituídos pela refatoração) nem com
`_to_delete/` (lixo removido no PC, gitignored — ver `tools/apply_refactor_manifest.json`).
`open-source/` (pacote anonimizado do artigo SBR/LARS 2026) foi removido do repositório: é gerado por
`tools/make_release.py` (`dtssl release`).
