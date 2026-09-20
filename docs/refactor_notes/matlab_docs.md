# Notas de refatoração — MATLAB, legado, manifesto do PC, ssl-unification e docs (02/09/2026)

Agente: *matlab/legacy/docs*. Escopo: `matlab/**`, `automation/` (movida), `scripts/*.m`, `archive/` → `legacy/`,
`apresentacao/` → `legacy/`, `tools/ssl_unification/**`, `tools/apply_refactor_manifest.json`, `.gitignore`,
`.gitattributes`, `.dvcignore`, `README.md`, `CLAUDE.md`, `ROADMAP.md`, `DESIGN.md`, `docs/README.md`,
`latex/main.{aux,log}`. **Não tocado**: `src/`, `tests/`, `config/*.json`, `results/`, `data/`, `models/`,
`docs/ADR-*.md`, `simulink/` (só listado no manifesto). Nenhum `git commit` (o orquestrador commita).
MATLAB **não foi executado** (sem licença no sandbox): revisão estática + checagem de balanceamento de blocos.

## 1. MATLAB — `matlab/dtssl` (VIVO) × `matlab/legacy` (ARQUIVADO)

Todos os moves com `git mv` (histórico preservado). Layout final = `docs/SPEC_DTSSL.md` §2.

### 1.1 `automation/` → `matlab/dtssl/` (17 vivos)

`identify_trans_dof`, `identify_omega_rotate`, `eval_omega_v3_se2`, `check_excitation_trans`, `deadreckoning_p1d`,
`ideal_deadreckoning`, `rmse_pos_rebased`, `rmse_pos_rebased_se2`, `rmse_heading_rebased`, `export_plant_golden`,
`export_resample_reference`, `canonical_split`, `build_event_cache`, `run_one_mat`, `sim_aligned`,
`extract_sim_position`, `ensure_model_ready`. Mantidos no lugar: `matlab/sldd/{apply_theta,load_theta_mat,
setup_sldd,link_sldd_to_model}.m`, `matlab/simulink_io/{list_splits,load_split}.m`. `automation/` não existe mais.

### 1.2 `automation/` + `matlab/*` + `scripts/*.m` → `matlab/legacy/<grupo>/` (README por grupo, com as entradas do CHANGELOG que cada script gerou)

| Grupo | Arquivos (origem) |
|---|---|
| `omega_closedloop/` | `check_excitation`, `identify_omega_from_splits`, `identify_omega_v3_linear`, `diag_omega_gain_amplitude`, `diag_omega_gain_sign` (automation/) |
| `campaign_june/` | `run_all_experiments`, `eval_campaign`, `eval_horizons`, `eval_theta_full`, `eval_theta_full_se2`, `eval_theta_se2_vs_placeholder`, `audit_time_grids`, `debug_baseline`, `test_wheel_chain`, `fig_f1_dotplot`, `fig_f2_overlays`, `fig_f3_compare_omega`, `fig_f4_horizons` (automation/) |
| `bayesopt/` | `bo_cost`, `bo_cost_proxy`, `run_bayesopt_v1`, `run_bayesopt_v2_proxy`, `run_bayesopt_v2_fallback`, `phase0_proxy_ranking`, `eval_bayesopt_holdout`, `eval_bayesopt_v2_holdout`, `fig_bayesopt`, `fig_bayesopt_v2` (automation/) |
| `batch_20260724/` | `run_se2_gate_rotate`, `run_td_quantization_case`, `run_td_quantization_gate` (automation/) |
| `sysid/`, `optimization/`, `train/`, `viewer/`, `analytical/`, `ros_bridge/` | `matlab/<mesmo nome>/` inteiro |
| `simulink_io/` | `load_commands_to_timeseries`, `load_log_to_timeseries`, `load_log_to_timeseries_v2` (matlab/simulink_io/) |
| `scripts/` | `run_one.m`, `test.m` (scripts/) |

Removido: `matlab/simulink_io/kinematics.m` (stub vazio; SPEC §2) e `archive/bus_conv_fcns_legacy/` (duplicata
byte-a-byte de `matlab/ros_bridge`, verificada com `diff -r`; única cópia: `matlab/legacy/ros_bridge/`).
`eval_theta_se2_vs_placeholder.m` foi para `campaign_june/` (não estava na lista de vivos) embora tenha sido
usado em 24/07 (Parte C) — se o orquestrador preferir mantê-lo vivo, é só `git mv` de volta; ele só depende
de `run_one_mat`/`rmse_pos_rebased_se2` (vivos) e do `traj_eval_campaign_*.mat`.

### 1.3 `bootstrap_paths`

- `scripts/bootstrap_paths.m` → `matlab/bootstrap_paths.m` (git mv + reescrita): raiz = pasta acima do
  próprio arquivo (`fileparts(mfilename('fullpath'))`), **sem `cd()`**, sem caminho Windows; adiciona
  `matlab, matlab/dtssl, matlab/sldd, matlab/simulink_io, config, simulink, results`; `bootstrap_paths('legacy')`
  adiciona `genpath(matlab/legacy)`; `bootstrap_paths(root[,'legacy'])` aceita raiz explícita (compatibilidade).
- `scripts/bootstrap_paths.m` recriado como *forwarder* de 3 linhas (faz `cd` temporário em `matlab/` com
  `onCleanup` e resolve a implementação por `str2func`, para não recursar em si mesmo).
- Consequência: os scripts vivos deixaram de depender de `pwd`. Helpers novos em `matlab/dtssl/private/`:
  `dtssl_root.m` (raiz pela localização do arquivo) e `resolve_repo_path.m` (relativo → absoluto contra a raiz).
  Scripts legados continuam assumindo `pwd == raiz` (documentado em `matlab/legacy/README.md`).

### 1.4 Edições nos scripts vivos (sem mudar assinaturas, exceto `export_plant_golden`)

| Arquivo | Mudança |
|---|---|
| `deadreckoning_p1d.m`, `ideal_deadreckoning.m` | `series_on_grid` e `lag_filter` (duplicados nos dois) → `matlab/dtssl/private/{series_on_grid,lag_filter}.m`, implementação **bit-a-bit** idêntica (goldens Python não mudam). `p1d_response` continua local em `deadreckoning_p1d`. |
| `export_plant_golden.m` | **nova assinatura** `[out_path, theta_json] = export_plant_golden(event_dir, opts)` com name-value `'theta'` (caminho `.mat` \| caminho `.json` no formato de `twin_params.json` \| vetor 1×9 \| struct \| `'promoted'`/`'official'` = vx/vy de `models/sysid_vxvy_v2.mat` + ω de `models/sysid_omega_rotate_v1.mat`, mesma fusão de `run_td_quantization_case.m`), `'outdir'` (default `tests/fixtures`), `'tag'` (`plant_golden_<tag>_<evento>.parquet`), `'outpath'`, `'ts'`, `'thetajson'`. Com `tag` não vazio grava também `plant_golden_<tag>_theta.json` (mesmo layout de `tests/fixtures/plant_golden_theta.json`: `source`, `note`, `dof.{vx,vy,w}.{K,tau,Td,placeholder}`, `order`). Default de `'theta'` continua `models/sysid_vxvy_v2.mat` (reproduz os goldens v1). A forma posicional antiga `(event_dir, theta_mat, out_path, Ts)` **não** é mais aceita (não havia chamadores no repo). |
| `run_one_mat.m` | SLDD resolvido como `fullfile(dtssl_root(),'config','ssl_robot.sldd')` (era relativo a `pwd`); comentário atualizado (`scripts/run_one.m` → `matlab/legacy/scripts/`). |
| `canonical_split.m` | `commands_path` e `OutRoot` (`build/canonical_splits`) resolvidos contra a raiz; exemplo de uso com `run_one_mat`. |
| `eval_omega_v3_se2.m` | `CandMat`/`Campaign` relativos → raiz; CSV/`.mat` de saída em `<raiz>/results/`; `meta.script` = `matlab/dtssl/eval_omega_v3_se2.m`; nota do reuso de 24/07. |
| `check_excitation_trans.m` | CSV em `<raiz>/results/`. |
| `identify_trans_dof.m` | comparação "antigo" lê `models/sysid_initial.mat` (era `results/`), com `warning` e `NaN` se ausente (o `.mat` não está no git). |
| `export_resample_reference.m` | `event_dir`/`out_path` relativos → raiz. |
| `identify_omega_rotate.m` | só comentários (caminho de `identify_trans_dof`, registro da promoção). |

### 1.5 Edições nos scripts legados (mínimas, para não quebrarem no novo layout)

- `batch_20260724/*.m`, `train/control_parameters.m`: `C:\Users\victo\Documents\digitaltwin` → raiz derivada de
  `mfilename('fullpath')` (4 níveis acima); `addpath(REPO/scripts, REPO/automation); bootstrap_paths()` →
  `addpath(REPO/matlab); bootstrap_paths('legacy')`. O `cd(REPO)` dos wrappers batch foi mantido.
- `bayesopt/{phase0_proxy_ranking,run_bayesopt_v2_proxy,run_bayesopt_v2_fallback,eval_bayesopt_v2_holdout,
  fig_bayesopt_v2}.m`: `cd(here/../scripts); bootstrap_paths(); addpath(genpath(pwd/automation))` →
  `addpath(here/../..); repo_root = bootstrap_paths('legacy'); cd(repo_root)`.
- `results/sysid_initial.mat` / `results/sysid_bayesopt.mat` → `models/…` em `campaign_june/{debug_baseline,
  eval_campaign,eval_theta_full,eval_theta_full_se2,run_all_experiments}.m`, `omega_closedloop/{identify_omega_from_splits,
  identify_omega_v3_linear}.m`, `scripts/{run_one,test}.m` (os `.mat` são movidos no PC pelo manifesto).
- `legacy/apresentacao/orientacao_20260612.m`: bootstrap via `../../matlab`, `bootstrap_paths('legacy')` + `cd(repo)`.

## 2. `legacy/`

`archive/` → `legacy/archive/` (git mv; inclui `rl/*.slx` como ponteiros LFS e o `.sldd` stale), `archive/README.md`
atualizado; `apresentacao/{orientacao_20260612.m,guia_estudo_20260612.md}` → `legacy/apresentacao/` (a pasta era
gitignored — `mv` + `git add`); `legacy/README.md` novo (índice). Os binários `.mlx`/`.pdf` da apresentação e o
`.asv` ficam para o manifesto.

## 3. `tools/apply_refactor_manifest.json`

`{"moves": [...], "deletes": [...], "already_in_git": {...}, "keep": [...], "post_checks": [...]}`; cada entrada tem
`tracked` (usar `git mv`/`git rm`), `if_exists`, `glob` e `note`. 7 moves (`simulink/simulink_tests.slx` →
`legacy/simulink/` — decisão: manter como legado; `apresentacao/*.{mlx,pdf}` → `legacy/apresentacao/`;
`test_world.usd` → `usd/`; `results/sysid_{initial,bayesopt}.mat` → `models/` se existirem) e 35 deletes
(`simulink/{pid,pid_v2,with_ros,with_ros_v2}.slx`, `*.slxc` (raiz, `scripts/`, `scripts/local/` — **só** os .slxc),
`scripts/rl_model.slx.original`, `*.asv`/`*.autosave`, `results/_BROKEN_loo_translational_20260810_1742.md`
(após nota no CHANGELOG), `latex/main.{aux,log}`, `results/bo_run_v1.log`, `tree.txt`, `gitignore.txt`,
`reorganize.ps1`, `scripts/.vscode/`, `scripts/cluster/`, `scripts/analyticalModel/`, `src/__init__.py` + `src/{envs,utils}/`,
`config/{task,train}/`, `NVIDIA Corporation/`, `slprj/`, `build/`, `_claude_*.tar.gz`, `requirements.txt` da raiz,
`apresentacao/` vazia). "Deletar" = mover para `_to_delete/` (gitignored) e apagar depois da revisão.
Entradas `tracked: true` que ainda estão no git deste branch e o orquestrador pode preferir `git rm`/`git mv` **aqui**:
`simulink/*.slx` (4), `simulink/simulink_tests.slx`, `test_world.usd`, `scripts/rl_model.slx.original`,
`scripts/cluster/submit_job.sbatch`, `src/__init__.py`, `tree.txt`, `gitignore.txt`, `reorganize.ps1`,
`requirements.txt`, `results/_BROKEN_*` — não fiz por estarem fora da minha lista de arquivos tocáveis.

## 4. `.gitignore` / `.gitattributes` / `.dvcignore`

- `.gitignore` reescrito em UTF-8 (o anterior tinha lixo UTF-16 no fim): Python (`build/`, `dist/`, `*.egg-info`,
  `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.venv`), MATLAB (`*.asv`, `*.autosave`, `slprj/`, `*.slxc`, `*_grt_rtw/`,
  `*.mex*`), caches (`results/_cache_*`, `results/debug/`, `_to_delete/`, `_claude_*.tar.gz`, `NVIDIA Corporation/`,
  `scripts/local/`, `models/mjcf/*.tmp`), dados (`/data/extracted/`, `/data/recorded/`, `/data/bench/`, `.dvc/cache`,
  `*.log.gz`), LaTeX (`aux/log/out/bbl/blg/synctex.gz/fdb_latexmk/fls/toc`), IDE/SO. **`CLAUDE.md` e `apresentacao/`
  não são mais ignorados.** Padrões de `data/` ancorados na raiz para não esconder `src/dtssl/data/`.
  Atenção: `results/_cache_rsim_rollouts.pkl` já é rastreado (continua); um `.npz` novo em `results/_cache_*`
  precisará de `git add -f` se for para versionar.
- `.gitattributes`: `* text=auto eol=lf`; `*.parquet`, `*.mat`, `*.pkl`, `*.npz`, `*.sldd`, `*.mlx`, `*.pdf` marcados
  `binary`; regras LFS mantidas (`*.slx`, `*.stp`, `*.usd*`, `*.png`, …) + `*.step`.
- `.dvcignore`: caches Python/MATLAB, `build/`, `_to_delete/`.
- `latex/main.aux` (`git rm`) e `latex/main.log` (apagado) — únicos toques em `latex/`.

## 5. `tools/ssl_unification/`

- `build_wsl2.sh` (idempotente): checa Ubuntu 22.04/24.04 e WSL2, `git clone --recursive` ou checkout existente
  (`--update`), `sudo ./scripts/setup.py --install <essentials sem qt>` (o `qt.sh` do projeto usa `who` para o
  `chown` e falha em WSL sem login — por isso o Qt é tratado à parte: `--qt script` (default, `scripts/ubuntu/qt.sh
  6.4.0 /opt/qt`) \| `apt` \| `skip`), `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j`,
  imprime `<repo>/bin/ssl-unification` (o CMakeLists do projeto manda o binário para `bin/`), `--config-team`
  gera a config. **Não executado aqui** (só `bash -n`).
- `run_against_twin.sh`: `dtssl serve --backend … --config config/bridge.json [--unicast …] [--record …]` em
  background (log `/tmp/dtssl_serve.log`, encerrado por `trap`) + `bin/ssl-unification -running`; gera
  `config/local` se faltar; avisa se a cor do time da config não bate com `--team`. `--no-serve` para o gêmeo
  no Windows. **Não executado aqui.**
- `make_local_config.py` (stdlib): `--ssl-unification --team --vision-ip --vision-port --inet --n-robots
  --behavior --base --sim-ip --attacking-side --bridge-json --out --dry-run`. Chaves conferidas no C++
  (`CommunicationSim.cpp`, `DataWorld.cpp`, `GeneralEnvironment.cpp` — `INET` é `MappedComboBox` pelo nome da
  interface, `main.cpp` — `MAX_ROBOTS=16`, `-running`, `MainWindow.cpp::loadEvent`). Cria `Robot11..15`
  clonando `Robot00` quando o perfil base tem só 11 robôs. **Executado** com `--dry-run` e com saída em
  `/tmp` contra o `ronaldinho/config.json` real: 8 linhas alteradas, chaves validadas.
- `README.md` (PT-BR): build, tabela das chaves, rodar, **rede WSL2** (tudo no WSL; gêmeo no Windows com
  `dtssl serve --unicast <IP_WSL>:10006` + `--sim-ip <IP do host>`; `networkingMode=mirrored`), DualSense
  (joystick é do `dtssl gui`, robôs teleoperados devem ficar `TurnedOff` na estratégia).

## 6. Docs

`README.md` (novo: visão geral, θ oficial, headline 0,039/0,101/0,129 m em `h_ref=0,4 s`, 10/10 hold-out, ω só
identificável em malha aberta, instalação `pip install -e ".[gui,mujoco,dev]"`, uso rápido da CLI, ssl-unification,
layout, MATLAB), `CLAUDE.md` (reescrito: θ oficial com ω promovido, estrutura = SPEC, convenções, guardrails —
bibliografia **só** `latex/refs/references.bib`, `slr/incluidos.bib` não existe —, definition of done),
banners HISTÓRICO em `ROADMAP.md` e `DESIGN.md`, `docs/README.md` (índice por categoria), `matlab/README.md`,
`matlab/legacy/README.md` + 12 READMEs de grupo, `legacy/README.md`, `legacy/archive/README.md` atualizado.

## 7. Incertezas / pendências para o orquestrador

1. **MATLAB não executado.** Revisar em especial: o forwarder `scripts/bootstrap_paths.m` (resolução por
   `str2func` após `cd` temporário), `export_plant_golden` (`arguments` com `opts.thetajson logical = logical([])`,
   `jsonencode(...,'PrettyPrint',true)` ≥ R2021a) e as chamadas a funções `private/` a partir de subfunções.
2. Gerar os goldens v2 no PC: `export_plant_golden('data/extracted/2026-05-18_19-2-15/splits/shoot_to_goal/shoot_to_goal_12_01','theta','promoted','tag','v2')`
   e idem `side_to_side/side_to_side_01_05` → `tests/fixtures/plant_golden_v2_*.parquet` + `plant_golden_v2_theta.json`;
   depois o teste condicional previsto na SPEC §5.
3. `results/sysid_initial.mat` não está no git: os scripts apontam para `models/sysid_initial.mat` (manifesto move
   se existir). `identify_trans_dof` degrada com aviso se faltar.
4. `.claude/commands/experimento.md` ainda cita `automation/run_all_experiments.m` (fora do meu escopo).
5. `docs/RELATORIO_TECNICO_DESENVOLVIMENTO.md`, `docs/PLANO_PAPER_SBR2026.md` e o próprio CHANGELOG citam caminhos
   antigos (`automation/...`) — deixados intactos por rastreabilidade; `matlab/legacy/*/README.md` faz o mapa.
6. `simulink/simulink_tests.slx`: decidi **manter** (→ `legacy/simulink/`) em vez de apagar; reverter no manifesto se preferir.
7. Contagem de testes no README/CLAUDE não é citada numericamente (a suíte muda a cada agente).

## 8. Entrada proposta para `results/CHANGELOG.md`

```
- 2026-09-02 | REFATORACAO MATLAB/LEGADO/DOCS (branch refactor/dtssl) | commit <hash> | seed n/a | NENHUM experimento; nada em data/, models/, results/ historico ou config/*.json tocado; theta oficial inalterado (vx/vy v2 + omega rotate v1) | automation/ EXTINTA: 17 scripts vivos -> matlab/dtssl/ (identify_trans_dof, identify_omega_rotate, eval_omega_v3_se2, check_excitation_trans, deadreckoning_p1d, ideal_deadreckoning, rmse_pos_rebased{,_se2}, rmse_heading_rebased, export_plant_golden, export_resample_reference, canonical_split, build_event_cache, run_one_mat, sim_aligned, extract_sim_position, ensure_model_ready) e 31 arquivados -> matlab/legacy/{omega_closedloop,campaign_june,bayesopt,batch_20260724}/ (git mv, README por grupo com as entradas deste CHANGELOG que cada um gerou); matlab/{sysid,optimization,train,viewer,analytical,ros_bridge} e simulink_io/load_*_to_timeseries* + scripts/{run_one,test}.m -> matlab/legacy/; archive/ -> legacy/archive/ (rl TD3, viewers, testes; bus_conv_fcns_legacy REMOVIDO por ser duplicata byte-a-byte de ros_bridge); apresentacao/ -> legacy/apresentacao/ | bootstrap_paths: scripts/ -> matlab/bootstrap_paths.m, raiz derivada do proprio arquivo, SEM cd(), opcao 'legacy'; scripts/bootstrap_paths.m vira forwarder | helpers dedup matlab/dtssl/private/{series_on_grid,lag_filter}.m (bit-a-bit; goldens Python inalterados) + dtssl_root/resolve_repo_path (caminhos relativos -> raiz, fim da dependencia de pwd) | export_plant_golden ganha 'theta' (.mat|.json|vetor|struct|'promoted' = vxvy_v2 + omega_rotate_v1), 'outdir', 'tag' e grava plant_golden_<tag>_theta.json (goldens v2 a gerar no PC) | referencias results/sysid_*.mat -> models/ ; caminhos C:\Users\victo removidos dos wrappers de 24/07 | tools/apply_refactor_manifest.json (7 moves, 35 deletes p/ binarios/caches no PC: simulink pid/pid_v2/with_ros{,_v2}.slx apagados, simulink_tests.slx -> legacy/simulink, *.slxc, *.asv, tree.txt, gitignore.txt, reorganize.ps1, src/ antigo, config/{task,train}, build/, slprj/, NVIDIA Corporation/, _claude_*.tar.gz, results/_BROKEN_loo_translational_20260810_1742.md [saida quebrada de 2026-08-10, regravada como _1743; registrado aqui como incidente antes da remocao]) | .gitignore reescrito em UTF-8 (CLAUDE.md passa a ser versionado), .gitattributes (eol=lf, parquet/mat/pkl binary, LFS mantido), .dvcignore | tools/ssl_unification/{build_wsl2.sh,run_against_twin.sh,make_local_config.py,README.md} (SPEC secao 6; make_local_config validado em dry-run contra config/shared/ronaldinho real) | docs: README.md e CLAUDE.md reescritos (theta com omega promovido, headline 0.039/0.101/0.129 m @ h_ref=0.4 s, 10/10 hold-out), ROADMAP.md/DESIGN.md marcados HISTORICO, docs/README.md (indice), docs/refactor_notes/matlab_docs.md | latex/main.{aux,log} removidos | MATLAB nao executado nesta sessao (sem licenca no sandbox) -- validacao pendente no PC: bootstrap_paths, export_plant_golden 'promoted' + pytest tests/test_plant_golden.py
```
