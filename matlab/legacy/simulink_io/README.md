# `simulink_io/` (legado) — scripts de carga para o workspace base (mai/2026, ARQUIVADO)

Era `matlab/simulink_io/`. Scripts (não funções) que liam `all_*_labeled.parquet` ou um evento e
criavam `cmd_v{x,y,w}_ts` / `pos_{x,y,w}_ts` a 60 Hz no workspace base para o Simulink, além de
`t_delay` e `K_Matrix` hard-coded.

| Script | Estado |
|---|---|
| `load_commands_to_timeseries.m` | só comandos |
| `load_log_to_timeseries.m`, `load_log_to_timeseries_v2.m` | comandos + pose truth (v2 = variante com o mesmo cabeçalho) |

Substituídos por `matlab/dtssl/canonical_split.m` (mapa real→contrato, cache em `build/canonical_splits/`)
+ `matlab/simulink_io/load_split.m` (vivo) e, no Python, `dtssl.data.loader`. `matlab/simulink_io/kinematics.m`
(stub vazio gerado pelo editor) foi removido. Sem entradas no CHANGELOG.
