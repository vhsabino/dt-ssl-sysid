# `viewer/` — visualizadores MATLAB (fev–mai/2026, ARQUIVADO)

Era `matlab/viewer/`. Requerem GUI Layout Toolbox (`uix.*`).

| Script | Papel |
|---|---|
| `VisualizadorLogPlayer.m` | player de logs SSL (truth) a partir de `ball.csv`/`processed_robots.csv`, slider, atalhos, overlay opcional do `out` do Simulink |
| `VisualizadorSimulink.m` | reprodução de `out.pos_*_out` vs `out.pos_*_truth_out` |
| `visualizadorOutputs.m` | plot XY estático gêmeo vs truth |

Substituídos por `dtssl gui` (PySide6 + pyqtgraph: campo, robôs, bola, rastros sim/verdade,
telemetria cmd×estado, editor de θ, modo Replay). As versões ROS 2 em tempo real
(`VisualizadorTempoReal*.m`) estão em `legacy/archive/old_viewers/`. Sem entradas no CHANGELOG.
