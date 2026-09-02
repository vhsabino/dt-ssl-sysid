# `batch_20260724/` — wrappers batch da sessão de 24/07/2026 (ARQUIVADO)

Era `automation/`. Scripts de execução em lote (fora do MCP síncrono, com marcador `build/*_DONE.txt`
para polling) usados na promoção do ω e na verificação de determinismo/quantização. Os caminhos
absolutos `C:\Users\victo\Documents\digitaltwin` foram substituídos pela raiz derivada de
`mfilename('fullpath')`; o `cd(REPO)` interno permanece (são wrappers batch).

| Script | Papel | Entradas do `results/CHANGELOG.md` |
|---|---|---|
| `run_se2_gate_rotate.m` | gate (iii) SE(2) do candidato ω de malha aberta (`build/sysid_omega_rotate_v1_tmp.mat`) via `matlab/dtssl/eval_omega_v3_se2.m` | 2026-07-24 17:35 — candidato MELHOR em todos os horizontes (pool Δ=−0,1138 m, p=1,7e-16) → **PROMOVIDO**; `results/eval_omega_v3_se2_20260724_1723.csv` |
| `run_td_quantization_gate.m` | versão inicial da sensibilidade à quantização de Td (6 casos no mesmo processo) — registra o bug de contaminação de estado do SLDD entre casos | 2026-07-24 19:35 (Parte C) |
| `run_td_quantization_case.m` | versão corrigida: 1 processo MATLAB por caso (`run_td_quantization_case(k)`, k=1..6) via `eval_theta_se2_vs_placeholder` | 2026-07-24 19:35 — gate passa nos 6 vizinhos de quantização (±21 % em Td); `results/eval_tdquant_*_{se2,wilcoxon}_*.csv` |

O merge de θ feito aqui (vx/vy de `models/sysid_vxvy_v2.mat` + ω de `models/sysid_omega_rotate_v1.mat`)
é o mesmo que `matlab/dtssl/export_plant_golden.m('theta','promoted')` usa.
