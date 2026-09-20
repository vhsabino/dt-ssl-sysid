# `bayesopt/` — calibração comportamental conjunta (jun/2026, ARQUIVADO, nada promovido)

Era `automation/`. Cenário B da qualificação: otimizar os 9 parâmetros diretamente pela
fidelidade comportamental (custo `J = mediana_ev[wmean_h SE2(h)] + λ·RMSE_heading`, λ=1,171)
em vez de identificação por DOF. Dois caminhos: v1 no Simulink fiel (~9,5 s/sim) e v2 no proxy
analítico (`deadreckoning_p1d`, ~1,6 ms/sim) após o gate de ranking da Fase 0. **Ambos
falharam o gate de hold-out** contra vx/vy v2 + ω placeholder (overfit no v1; direção errada
no v2) — a linha de trabalho foi encerrada; o θ oficial é o identificado por DOF.

| Script | Papel | Entradas do `results/CHANGELOG.md` |
|---|---|---|
| `bo_cost.m` | custo comportamental no Simulink fiel (apply_theta uma vez, `sim_aligned` por evento) | 2026-06-14 16:22 (Fase 0: reproduz a campanha com dif 0,0000 m; Fase 1: λ) |
| `run_bayesopt_v1.m` | bayesopt 9 params, 100 avaliações, 5 eventos de treino, EI-plus | 2026-06-14 16:22 — `θ_opt` com `K_w=0.516` (piso); `models/sysid_bayesopt_v1_raw.mat` |
| `eval_bayesopt_holdout.m` | Fase 3 v1: gate hold-out (10 eventos) vs ideal e vs vx/vy v2 | 2026-06-14 18:37 — **GATE FALHA** (overfit); `models/sysid_bayesopt_v1_candidate.mat` |
| `fig_bayesopt.m` | figuras F5/F6/F7 do v1 | 2026-06-14 18:37 |
| `bo_cost_proxy.m` | mesma fórmula de custo no proxy analítico | 2026-06-14 21:05 |
| `phase0_proxy_ranking.m` | Fase 0 (Caminho 2): o proxy preserva o ranking do Simulink? 25 θ × 6 eventos | 2026-06-14 21:05 — Spearman ρ=0,9992 → Caminho 2; `build/phase0_ranking.mat` |
| `run_bayesopt_v2_proxy.m` | bayesopt no proxy, 18 eventos de treino, 400 avaliações | 2026-06-14 21:17 — `K_w=1.099`; `models/sysid_bayesopt_v2_raw.mat` |
| `run_bayesopt_v2_fallback.m` | fallback (bayesopt no Simulink com 9 eventos) caso ρ<0,85 — **não foi necessário** | — |
| `eval_bayesopt_v2_holdout.m` | Fase 3–4 v2: confirmação no Simulink fiel + gate hold-out | 2026-06-14 21:30 — bate a ideal, **não bate vx/vy v2** (pool +0,0041 m, p=0,040) → **GATE FALHA**; `models/sysid_bayesopt_v2_candidate.mat` |
| `fig_bayesopt_v2.m` | figuras F4/F6/F7 do v2 | 2026-06-14 21:30 |

Helpers vivos que estes scripts usam: `matlab/dtssl/{build_event_cache,sim_aligned,deadreckoning_p1d,
rmse_pos_rebased_se2,rmse_heading_rebased,ensure_model_ready}.m`. Dependem também de
`results/traj_eval_campaign_20260611_2238.mat`, `build/bo_fase01.mat`, `build/bo_proxy_train_v2.mat`
(não versionados) e da Statistics and Machine Learning Toolbox (`bayesopt`).
