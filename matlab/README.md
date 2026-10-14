# `matlab/` — lado MATLAB/Simulink do gêmeo (identificação + oráculo)

```matlab
addpath('matlab'); bootstrap_paths();          % matlab/dtssl + sldd + simulink_io + config + simulink + results (sem cd)
bootstrap_paths('legacy');                     % idem + matlab/legacy (scripts arquivados)
```

| Pasta | Conteúdo |
|---|---|
| `bootstrap_paths.m` | único ponto de entrada de path; raiz derivada do próprio arquivo, **não** muda o pwd (`scripts/bootstrap_paths.m` é só um forwarder) |
| `dtssl/` | **VIVO** — identificação (`identify_trans_dof`, `identify_omega_rotate`, `check_excitation_trans`), gate SE(2) (`eval_omega_v3_se2`), planta analítica de referência (`deadreckoning_p1d`, `ideal_deadreckoning`; helpers em `private/`), métricas (`rmse_pos_rebased`, `rmse_pos_rebased_se2`, `rmse_heading_rebased`), goldens cross-linguagem (`export_plant_golden`, `export_resample_reference`), dados (`canonical_split`, `build_event_cache`), cadeia do oráculo Simulink (`ensure_model_ready`, `run_one_mat`, `sim_aligned`, `extract_sim_position`) |
| `sldd/` | `setup_sldd`, `link_sldd_to_model`, `apply_theta`, `load_theta_mat` — acesso ao `config/ssl_robot.sldd` (9 params na ordem fixa) |
| `simulink_io/` | `list_splits`, `load_split` (parquet canônico → struct para o Simulink) |
| `legacy/` | arquivado com README por grupo (`legacy/README.md`) |

Modelo Simulink mantido: `simulink/parameter_estimation_model_pid_v3.slx` (oráculo; ~9,5 s/sim).
Toolboxes: System Identification (`procest`), Simulink, Signal Processing (`sgolayfilt`),
Statistics (`signrank`, `lbqtest`), Parquet (base MATLAB ≥ R2022a).

Goldens para o porte Python (`tests/fixtures/`): `export_resample_reference(event_dir, out)` e
`export_plant_golden(event_dir, 'theta', 'promoted', 'tag', 'v2')` (gera também `plant_golden_v2_theta.json`).
Caminhos relativos nos scripts vivos são resolvidos contra a raiz do repo (`private/resolve_repo_path.m`).
