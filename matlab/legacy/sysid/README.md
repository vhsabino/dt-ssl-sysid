# `sysid/` — pipeline de identificação antigo (abr–jun/2026, ARQUIVADO)

Era `matlab/sysid/`. Pipeline herdado de antes do repositório (commit inicial `c283f47`,
11/06/2026): concatena todos os eventos de um label (`all_*_labeled.parquet`), monta `iddata`
por DOF com a velocidade `velocity_*` logada rotacionada ao corpo, ajusta `procest('P1D')`
sem hold-out e otimiza (`bayesopt`) um RMSE de posição em mm. Produziu `sysid_initial.mat`
(θ "procest": vx {0,9886; 0,1282; 0,1707}, vy {0,9493; 0,2416; 0,1045}, ω placeholder), usado
como baseline `procest_placeholder` em toda a campanha de junho.

Superado por `matlab/dtssl/identify_trans_dof.m` (2026-06-14 10:24/10:30 no CHANGELOG: re-ID
P1D por evento, velocidade derivada da posição da visão, hold-out seed 42, fit hold-out ≈87 %
→ `models/sysid_vxvy_v2.mat`, PROMOVIDO) e pelo harness Python.

| Script | Papel |
|---|---|
| `run_sysid.m` | orquestrador: `build_idData_per_dof` → `identify_per_dof` → salva `sysid_initial.mat` |
| `build_idData_per_dof.m` | monta `iddata (u,y)` por DOF; **rotaciona velocidade mundo→corpo** (linhas 97–100) — documento-fonte do frame de corpo |
| `identify_per_dof.m` | `procest(d,'P1D')` por DOF → K, τ, Td, fit |
| `compute_rmse_position.m` | RMSE de posição em janelas por amostra (esquema antigo; colapsava em grade irregular — CHANGELOG 2026-06-11 22:31) |
| `cross_log_validation.m` | degradação treino vs log out-of-distribution |
| `run_bayesopt.m` | BO dos 9 params sobre `compute_rmse_position` (Rota B antiga) |

Entradas do CHANGELOG: nenhuma direta (anterior ao CHANGELOG); referenciado em 2026-06-14 10:24
("ANTIGO vx/vy … rmse_val=NaN, nunca hold-out"). `results/sysid_initial.mat` → mover para
`models/sysid_initial.mat` no PC (`tools/apply_refactor_manifest.json`).
