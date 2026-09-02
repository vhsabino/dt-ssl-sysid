# `scripts/` (legado) — drivers antigos do oráculo Simulink (jun/2026, ARQUIVADO)

Era `scripts/`.

| Script | Papel | Substituído por |
|---|---|---|
| `run_one.m` | simula 1 split no `pid_v3` com θ por **nome fixo** (`'ideal'` \| `'procest'` \| `'bayesopt'`, caminhos hard-coded; agora `models/sysid_{initial,bayesopt}.mat`) | `matlab/dtssl/run_one_mat.m` (θ de qualquer `.mat`, + alinhamento SE(2) idempotente) — usado por `run_all_experiments` nas entradas 2026-06-10/11 do CHANGELOG |
| `test.m` | one-shot: `setup_sldd` + `link_sldd_to_model` (criação/vínculo do SLDD) | `matlab/sldd/{setup_sldd,link_sldd_to_model}.m` chamados diretamente; o SLDD versionado já está vinculado ao `pid_v3` |

`scripts/bootstrap_paths.m` continua existindo na pasta `scripts/` só como *forwarder* de 3 linhas para
`matlab/bootstrap_paths.m`.
