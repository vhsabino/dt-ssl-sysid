# legacy/archive/ (era `archive/` na raiz até 02/09/2026)

Conteúdo arquivado durante a reorganização de maio/2026 e movido para `legacy/` em 02/09/2026.
Nada aqui é deletado — fica disponível pra consulta histórica. Índice geral: `legacy/README.md`.

## Conteúdo

### `rl/` — Pipeline de Reinforcement Learning (pausado)
- `train_rl.m` — treino do agente TD3
- `play_rl.m` — execução do agente treinado
- `rl_model.slx`, `rl_model_with_ros.slx` — modelos Simulink

**Status**: pausado em maio/2026 (agente TD3 residual sobre os ganhos PI, modelo `rl_model_with_ros`). Foco do projeto migrou para identificação caixa-cinza por DOF (`matlab/dtssl/`). Inventário do experimento RL posterior (WSL2, repo `planning-rl-greybox`): `docs/INVENTARIO_RL_2026-07-24.md`. Os `.slx` são ponteiros Git LFS.

### `old_viewers/` — Visualizadores antigos
- `VisualizadorTempoReal.m`
- `VisualizadorTempoReal2.m`
- `VisualizadorTempoRealComErro.m`

**Status**: substituídos por `matlab/legacy/viewer/VisualizadorLogPlayer.m` (também arquivado); a interface atual é `dtssl gui`.

### `old_evaluators/` — Versões antigas do avaliador
- `avaliar_gemeo_digital_v0.m`
- `avaliar_gemeo_digital_stage_1.m`

**Status**: superados pela versão sem sufixo (hoje em `matlab/legacy/train/`).

### `tests/` — Scripts descartáveis / de teste
- `test.m`, `test2.m`, `temp.m`, `smoke_test_caminho2.m` (ainda referencia `scripts\local\train\robocin_tests_id5.mat`, cache fora do git), `test_env.py`
- `ssl_robot_stale_scripts_copy_2026-05-23.sldd` (na raiz de `archive/`): cópia stale do SLDD que vivia em `scripts/` — o SLDD canônico é `config/ssl_robot.sldd`

**Status**: scratch pads do desenvolvimento. Mantidos pra rastreabilidade caso algum teste isolado vire referência.

### `bus_conv_fcns_legacy/` — REMOVIDO em 02/09/2026
**Status**: era uma cópia byte-a-byte (verificada com `diff -r`) de `matlab/ros_bridge/+bus_conv_fcns`; a única cópia mantida está em `matlab/legacy/ros_bridge/`.

## Regras

1. **Não modifique arquivos aqui.** Se precisar editar, copie de volta para a estrutura ativa.
2. **Não delete sem revisão.** Pode haver código referenciado em commits antigos.
3. Se algo arquivado voltar a ser ativo, mova de volta e atualize este README.
