# `campaign_june/` — campanha de avaliação de junho/2026 (ARQUIVADO)

Era `automation/`. Orquestradores, avaliadores e figuras da primeira campanha completa de
comparação de θ no oráculo Simulink (`parameter_estimation_model_pid_v3`), com a métrica de
janelas re-ancoradas (translação e SE(2)). Superados pelo harness Python (`dtssl.eval`,
`dtssl.analysis`, `dtssl replay`, `dtssl gate`) a partir de 16/06/2026, que usa a mesma
planta analítica (`deadreckoning_p1d` → `AnalyticFOPDTPlant`, golden bit-a-bit) e a métrica
por janela/horizonte de `config/metrics.json`.

| Script | Papel | Entradas do `results/CHANGELOG.md` |
|---|---|---|
| `run_all_experiments.m` | primeiro orquestrador (tabela mestra θ × splits, via `scripts/run_one.m`) | 2026-06-10 09:39 … 2026-06-11 08:52 (`results/tabela_mestra_*.csv`) |
| `test_wheel_chain.m` | teste unitário da cadeia de rodas do `pid_v3` (IK/FK dos charts; ganho DC por DOF) | 2026-06-11 17:25 (reconciliação analítico vs Simulink, `max|dx|=0.0046 m`); citado em 2026-07-24 16:00 (`chain_static`) |
| `eval_theta_full.m` | θ composto (vx/vy + ω candidato) vs placeholder vs ideal, 6 eventos, métrica translacional | 2026-06-11 17:30 |
| `eval_theta_full_se2.m` | mesmos 6 eventos × 3 θ com as DUAS métricas (translação / SE(2)); teste H-a da deriva de heading | 2026-06-11 22:02; 2026-06-11 22:36 (janelas POR TEMPO: inversão do veredito) |
| `audit_time_grids.m` | auditoria da grade temporal dos 46 splits (todas irregulares) | 2026-06-11 22:31 (`results/grid_audit_20260611_2231.csv`) |
| `eval_campaign.m` | campanha completa: 3 θ × 46 splits (4 labels), h=2,5 s; salva as trajetórias | 2026-06-11 22:38 (`results/eval_campaign_20260611_2238.csv`, `traj_eval_campaign_20260611_2238.mat`) |
| `fig_f1_dotplot.m`, `fig_f2_overlays.m`, `fig_f3_compare_omega.m` | figuras F1–F3 da campanha | 2026-06-11 22:57 |
| `eval_horizons.m` + `fig_f4_horizons.m` | RMSE multi-horizonte h={0,5;1;2;2,5;4} s das trajetórias salvas; figura F4 | 2026-06-11 23:25 |
| `eval_theta_se2_vs_placeholder.m` | gate SE(2) multi-horizonte genérico (candidato vs placeholder reusado da campanha, Wilcoxon) — generaliza `eval_omega_v3_se2` | 2026-06-14 10:28 (gate de vx/vy v2 → PROMOVIDOS); 2026-07-24 19:35 (Parte C, sensibilidade à quantização de Td, 6 casos) |
| `debug_baseline.m` | overlay truth vs simulado de 1 evento (debug visual, `results/debug/`) | — |

Dependem de: `results/traj_eval_campaign_20260611_2238.mat` (não versionado), `models/sysid_initial.mat`
(era `results/sysid_initial.mat`), `models/sysid_ideal_v3.mat`, dataset DVC, Simulink + SLDD.
Métricas usadas (vivas): `matlab/dtssl/rmse_pos_rebased.m`, `rmse_pos_rebased_se2.m`, `rmse_heading_rebased.m`.
