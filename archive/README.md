# archive/

Conteúdo arquivado durante reorganização do repositório.
Nada aqui é deletado — fica disponível pra consulta histórica.

## Conteúdo

### `rl/` — Pipeline de Reinforcement Learning (pausado)
- `train_rl.m` — treino do agente TD3
- `play_rl.m` — execução do agente treinado
- `rl_model.slx`, `rl_model_with_ros.slx` — modelos Simulink

**Status**: pausado em <data>. Foco do projeto migrou para identificação caixa-cinza (ver `matlab/sysid/`). Reativar futuramente se houver capacidade.

### `old_viewers/` — Visualizadores antigos
- `VisualizadorTempoReal.m`
- `VisualizadorTempoReal2.m`
- `VisualizadorTempoRealComErro.m`

**Status**: substituídos por `matlab/viewer/VisualizadorLogPlayer.m` (player com slider, navegação por splits, e atalhos de teclado).

### `old_evaluators/` — Versões antigas do avaliador
- `avaliar_gemeo_digital_v0.m`
- `avaliar_gemeo_digital_stage_1.m`

**Status**: superados pela versão sem sufixo (em `matlab/train/`).

### `tests/` — Scripts descartáveis / de teste
- `test.m`, `test2.m`, `temp.m`, `smoke_test_caminho2.m`, `test_env.py`

**Status**: scratch pads do desenvolvimento. Mantidos pra rastreabilidade caso algum teste isolado vire referência.

### `bus_conv_fcns_legacy/` — Cópia duplicada do ROS bridge
**Status**: estava em `local/train/+bus_conv_fcns`. A cópia ativa é em `matlab/ros_bridge/+bus_conv_fcns`.

## Regras

1. **Não modifique arquivos aqui.** Se precisar editar, copie de volta para a estrutura ativa.
2. **Não delete sem revisão.** Pode haver código referenciado em commits antigos.
3. Se algo arquivado voltar a ser ativo, mova de volta e atualize este README.
