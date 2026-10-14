# Notas de refatoração — `dtssl.analysis` (scripts do artigo SBR/LARS 2026), 02/09/2026

Agente: *analysis*. Escopo: `src/dtssl/analysis/**`, `scripts/*.py` (migrados e apagados),
`open-source/` (apagado; substituído por `tools/make_release.py`), `tests/test_analysis*.py`,
esta nota. **Nada** em `src/dtssl/eval`, `src/dtssl/sim/rollout.py`, `src/dtssl/models`,
`config/`, `results/` ou `data/` foi alterado. Saídas de verificação em
`/home/claude/work/scratch_analysis/` (fora de `results/`).

## 1. O que existe agora

### `src/dtssl/analysis/common.py` (novo — o que era copiado em cada script)

| Item | Antes (scripts) | Agora |
|---|---|---|
| Raiz/saída | `R=Path('/sessions/happy-modest-euler/mnt/digitaltwin')`, `~/miniforge3/envs/rsim310`, `py -3` | `make_context(root, out) -> Ctx` (`dtssl.paths.repo_root()`; `out` default `<root>/results`; passar `root` exporta `DTSSL_ROOT` para que `dtssl.eval`/`dtssl.models` resolvam o mesmo `config/`) |
| `LW = 15`, `SUB_MS = 1` | duplicados em 20 arquivos | `common.LW`, `common.SUB_MS`, `MIN_DISPLACEMENT_M = 0.1` |
| `class DP` (duck-type de DofParam) | 4 cópias | `variant_params(base, use_K, use_tau, use_Td)` → `dict[str, DofParam]`; `theta_from_vector`, `load_theta_mat(path)` (h5py p/ v7.3, `scipy.io` p/ v5) |
| `def ros(f)` | 10 cópias | `ros(segs, factory, h_max, stride, lookback=LW, horizons)` |
| carimbo | `datetime.now().strftime(...)` | `stamp()`; `Ctx.stamp`, `Ctx.out_path(name, ext)`, `Ctx.write_text(...)` |
| cabeçalho de resultado | nenhum | `result_header(title, ctx, generator=..., seed=...)` → `# titulo - <stamp>` + linha `_Proveniencia: commit \`<hash[-dirty]>\` \| theta config/twin_params.json (vx: K=… tau=… Td=…; vy…; w…) \| dataset \| seed \| gerado por dtssl.analysis.<nome> (dtssl <versão>)_` |
| cache do rSim | `pickle.load(R/'results/_cache_rsim_rollouts.pkl')` | `load_rsim_cache(ctx)` lê `_cache_rsim_rollouts.npz` (em `out`, depois `results/`) e, se não houver, o `.pkl` legado (unpickler com mapa `phase0_replay.rollout → dtssl.sim.rollout` de `dtssl.sim.rollout._LegacyUnpickler`). `save_rsim_cache_npz`/`load_rsim_cache_npz` são wrappers finos de `dtssl.sim.rollout.save_rollouts/load_rollouts` (deduplicado conforme pedido em `core.md`) |
| leitura CSV | `pd.read_csv(ev/'commands.csv')` | `read_event_csv(label, event, dataset, data_root)` — CSV se existir, senão o parquet gêmeo (mesmas colunas, inclusive `timestamp` absoluto) |
| reamostragem legada | 5 cópias de `np.arange` + `np.interp` + SG | `legacy_uy_series(cmd, rob, dof, dt, min_len, pos_scale, sg_win, sg_order)` |
| FOPDT ad hoc | 4 implementações (`sim(u,K,tau,Td)`, `sim_p1d`) | `simulate_fopdt(u, dt, K, tau, Td, ic=0, align="legacy"\|"plant", upsample=1)` (+ `simulate_fopdt_plant` = referência que dirige `AnalyticFOPDTPlant`) |
| estatística por evento | 6 cópias | `per_event_medians(table, k, mask)`, `bootstrap_median_ci(d, n_boot=10000, seed=42)`, `trans_mask`, `paired_table(ctx, twin, def)` |
| figura p/ LaTeX | `shutil.copy(..., R/'latex/figures/…')` incondicional | `copy_figure(src, ctx, name, enabled)` — **só com `latex_copy=True`** (default False; `--kw latex_copy=true`) |
| CLI | `argparse` avulso ou nenhum | `cli_main(run, doc, argv, extra)`: `--root`, `--out`, `--kw k=v …` (valores JSON) |

### Contrato dos módulos

Cada `src/dtssl/analysis/<nome>.py` expõe `run(root=None, out=None, **kwargs) -> dict`
(`dict["path"]` = artefato principal) e `main(argv=None)`, além de `NAME`, `KIND`
(`analysis`/`fig`/`report`), `CLAIM` (afirmação do artigo) e `REQUIRES`
(`data`, `rsim_cache`, `rsim`, `mat`). Módulos que precisam de `robosim` importam
`dtssl.models.rsim.RSimReplay` **dentro** de `run` (o registro importa em qualquer máquina).
`quiet=True` suprime o `print` (usado nos testes).

### Registro e CLI

- `dtssl/analysis/__init__.py`: `REGISTRY` (nome → módulo, lazy), `ANALYSES`, `REPORTS`,
  `FIGURES`, `load(name)`, `names(kind)`, `info(name)`; docstring com a tabela
  análise → afirmação do artigo → script legado (fonte: `open-source/README.md` "One
  command per claim", `results/CHANGELOG.md`, `docs/PLANO_V2_EXECUTADO.md`, `PLANO_V3_EXECUTADO.md`).
  Entradas cujo arquivo não existe são descartadas (o release remove
  `meeting_overlay`/`fig_spec_main_result`).
- `dtssl/analysis/cli.py`: `register(subparsers)` (já descoberto por `dtssl.cli`):
  `dtssl analysis list [--kind]`, `dtssl analysis run <nome> [--root] [--out] [--kw k=v …]`,
  `dtssl analysis info <nome>`, `dtssl fig <nome|list>`. Antes de rodar checa `REQUIRES`
  (dataset, robosim, h5py, cache do rSim) e sai com código 3 se faltar algo.

### Módulos (28)

| módulo | origem | KIND | REQUIRES |
|---|---|---|---|
| ablation_orderfree, causal_ic_check, clustered_stats, gap_decomposition, gate_window_vs_event, window_errors_eang, regenerate_bin_distribution | `scripts/` | analysis | data |
| excitation_per_dof, loo_translational, r3_closedloop_omega_fit, analyze_omega_excitation | `scripts/` | analysis | data (CSV/parquet legado) |
| negcontrol_perevent | `scripts/` | analysis | data, mat (h5py) |
| epos_eang_three_models, eval_rsim_delay_ablation (`mode=finalize`) | `scripts/` | analysis | data, rsim_cache |
| eval_twin_vs_rsim, holdout_report | `phase0_replay/` (já em `analysis/`) | analysis/report | data, rsim |
| metrics_report, loader_report | `phase0_replay/` | report | data |
| fig_main_result, fig_trajectory_holdout | `scripts/` | fig | data, rsim_cache |
| fig_trajectory_by_label | `scripts/` | fig | data, rsim_cache (+ robosim só p/ o painel `square`; `allow_missing_rsim=true` desenha sem rSim) |
| fig_fit_holdout_vxvy, fig_omega_stepresponse_en | `scripts/` | fig | data |
| fig_twin_vs_rsim_epos_en, fig_spec_main_result | `scripts/` | fig | — (números transcritos / diagrama) |
| meeting_overlay, percurso_completo, percurso_square | `phase0_replay/` | fig | data, rsim |

`eval_twin_vs_rsim.run` tinha `from .rsim_plant import RSimReplay` (quebrado desde a
migração do esqueleto) — corrigido para import lazy de `dtssl.models.rsim`.
`regenerate_bin_distribution` deixou de duplicar `holdout_report._bin_distribution`
(reusa; a função ganhou `robot_radius`/`comparator_note` opcionais).

## 2. Decisões numéricas

### 2.1 FOPDT: `align="legacy"` (default) vs `align="plant"`

Os quatro scripts (`loo_translational`, `r3_closedloop_omega_fit`,
`fig_omega_stepresponse_en`, `fig_fit_holdout_vxvy`) foram trocados por
`common.simulate_fopdt`. As duas convenções **não** são numericamente iguais:

```
legacy (scripts de 2026-08):   m = ceil(Td/dt);         v[k] = v[k-1] + a·(u[k-m]   - v[k-1]);  y[k] = K·v[k]
plant  (AnalyticFOPDTPlant):   m = ceil(Td/dt - 1e-9);  v[0]=ic;  v[k] = v[k-1] + a·(u[k-1-m] - v[k-1])
```

No legado o comando atrasado do **mesmo índice k** alimenta `v[k]`; como a atualização
ZOH-exata integra a entrada mantida em `[(k-1)dt, k·dt)`, o atraso efetivo é `(m-1)·dt` —
**uma amostra a menos** que a planta (`m·dt`). Para `m ≥ 1`, `legacy(m) == plant(m-1)` bit a
bit; para `Td = 0` o legado é não-causal em uma amostra e não tem equivalente na planta.
Ex.: `Td_vx = 4.14·dt` → legado 4 amostras (67 ms), planta 5 (83 ms); `Td` verdadeiro 69 ms.

- Default `align="legacy"`: reproduz `loo_translational_20260810_1743.md` e
  `r3_closedloop_omega_fit_20260810_1036.md` **exatamente** (tabela abaixo) e a Fig. 1.
- `fig_fit_holdout_vxvy` usa `align="plant", upsample=20` (grade fina `Ts/20`, atraso
  fracionário por `floor(j − Td/dtf)`, lag ZOH-exato, IC por mínimos quadrados) — é a
  mesma recorrência da planta na grade fina, e reproduz o CSV de 2026-07-31 (fits
  86.66/86.85/86.32/87.27/88.09 %, `x0` iguais a 6 casas).
- A implementação é vetorizada (`scipy.signal.lfilter`); `simulate_fopdt_plant` dirige a
  planta passo a passo e serve de oráculo. `tests/test_analysis_fopdt.py` prova:
  legado == laço verbatim dos scripts (< 1e-12), planta == `AnalyticFOPDTPlant` (< 1e-12),
  `legacy(m) == plant(m-1)` (igualdade exata), `upsample=20` == referência de
  `fig_fit_holdout_vxvy` (< 1e-12).
- `loo_translational`/`r3` conservam os clamps legados (`tau ≥ 1e-3`/`1e-4`, `Td ≥ 0`) e as
  opções do Nelder-Mead; `align="plant"` está disponível como `--kw align=plant` (números
  mudam — p.ex. o diagnóstico NRMSE da Fig. 1 sobre o split *padded*, que não é o fit
  hold-out do artigo, vai de −95.8/24.0/−26.6 % para −107.6/25.2/−33.8 %).

### 2.2 CSV × parquet × `dtssl.data.loader`

Os scripts de identificação liam `commands.csv`/`processed_robots.csv` com `timestamp`
absoluto e reamostravam com `np.arange(0, T, dt)` + `np.interp` **linear** dos comandos +
Savitzky-Golay (7, 2). Neste checkout só existem os parquets; eles têm as mesmas colunas
(inclusive `timestamp` **e** `timestamp_event`, com o mesmo deslocamento nos dois streams).
Verificado: o parquet com `timestamp` (ou `timestamp_event`) reproduz **exatamente** os
números publicados (`excitation_per_dof`: n = 1964/7228/7484, corr 0.979/0.968/0.746,
R² 0.959/0.936/0.557, std meas 1281.055/1232.703/1.457 — em mm/s para vx/vy, como no
original; `loo`, `r3`, `analyze_omega_excitation` idem).

Passar pelo contrato do loader (`load_segment`: grade `matlab_colon`, comandos **ZOH**,
bloco contíguo da visão) **muda** os números (excitation: corr/R² vx 0.982/0.963,
vy 0.971/0.943, w 0.770/0.593; n 1960/7222/7468) — logo **NÃO** foi adotado. Fica
`common.read_event_csv` (CSV se existir, senão parquet) + `legacy_uy_series`, documentado
nos docstrings. `fig_fit_holdout_vxvy` já era parquet + `timestamp_event` + `matlab_colon`
+ ZOH (porte do `identify_trans_dof.m`) e continua assim.

### 2.3 Outros

- `excitation_per_dof` mantém as posições em **mm** (`std meas` em mm/s) para preservar a
  tabela publicada; `pos_scale=1e-3` está disponível.
- `results/_BROKEN_loo_translational_20260810_1742.md` (K ≈ 1000, τ/Td negativos) é a
  execução **sem** a conversão mm→m; o `loo_translational_20260810_1742.md` que estava em
  `open-source/results/` era essa mesma execução **sem** o marcador `_BROKEN_` — foi
  eliminado com a pasta e o manifesto do release lista explicitamente o `…_1743.md`.
- Figuras não são mais copiadas para `latex/figures/` por default (`latex_copy=True`).
- O cache do rSim continua sendo lido do `.pkl` legado; `dtssl cache-convert` gera o `.npz`
  (o release já embarca o `.npz`, sem pickle).

## 3. Verificação (saídas em `/home/claude/work/scratch_analysis/`, θ oficial, dataset `2026-05-18_19-2-15`)

Comparação automática dos `.md` gerados com os de `results/` ignorando carimbo e a linha de
proveniência (`idêntico` = diff vazio; diferenças de prosa listadas).

| análise | reproduzido? | número-chave (antigo → novo) | notas |
|---|---|---|---|
| clustered_stats | **sim** (idêntico) | gap por evento +0.0689 m, p = 0.0009766, rb +1.000, 10/10, 73.5 s, IC [+0.0375, +0.0969] | título com `-` em vez de `—` |
| gate_window_vs_event | **sim** (idêntico) | janela n=49 gap +0.0541 [+0.0251, +0.0830] rb +0.633 p 1.15e-08; evento n=10 gap +0.0689 [+0.0375, +0.0969] | mesmo gerador `default_rng(42)` compartilhado (ordem legada) |
| causal_ic_check | **sim** (idêntico) | central 0.0079/0.0388/0.1193, gap +0.0689; causal 0.0128/0.0468/0.1335, gap +0.0706; Δh_ref +0.0080 (+20.6 %) | monkeypatch escopado de `dtssl.data.loader.body_velocity_series` |
| epos_eang_three_models | **sim** (idêntico) | h_ref: twin 0.0388 / ideal 0.1005 / rSim 0.1293; e_ang 0.0440/0.0668/0.0635 | rSim do cache `.pkl`; checagem de vazamento impressa (ID ⊂ FID = True) |
| ablation_orderfree | **sim** (idêntico) | fatorial 0.1005 → 0.0388; Shapley K +0.0010 (2 %), τ +0.0341 (55 %), Td +0.0266 (43 %); const-vel 0.1600, cold 0.1137 | |
| gap_decomposition | **sim** (idêntico) | 0.0264/0.0298/0.0090/0.0079 @0.1 s … 0.2910/0.2769/0.1400/0.1193 @1.5 s | `evaluate` da nova `dtssl.eval.verdict` (medianas idênticas) |
| negcontrol_perevent | **sim** (idêntico) | per-DOF vs bayesopt gap +0.0038, 7/10, p 0.04199, rb +0.400; vs ideal +0.0689 | θ do `.mat` v7.3 via h5py (`pip install h5py` feito neste ambiente) |
| excitation_per_dof | **sim** (idêntico) | corr 0.979/0.968/0.746; R² 0.959/0.936/0.557; n 1964/7228/7484 | parquet + `timestamp` (CSV ausente) |
| loo_translational | **sim** (idêntico) | vx fit 84.3 ± 2.0 % (85.8/82.5/86.2/82.7), K 1.129; vy 82.8 ± 2.7 %, K 1.066; τ/Td por dobra iguais a 4 casas | `simulate_fopdt(align="legacy")`; ~1 min |
| r3_closedloop_omega_fit | **sim** (idêntico) | K 1.3775, τ 0.0430, Td 0.1117; fit hold-out 44.8 % (26.4, 46.8, 45.7, 60.3, 51.4, 38.0); treino 52.6 % | seed 42 |
| eval_rsim_delay_ablation (finalize) | **sim** (números idênticos) | m = 4 (66.7 ms), Td_trans 62.8 ms; gap@h_ref +0.0905 → rSim+Td +0.1434 (Δ −0.0529); N_indep 49 | prosa do cabeçalho reformatada; `mode=cache` requer robosim (não rodado) |
| window_errors_eang | **sim** (tabelas idênticas) | medianas trans: e_ang twin/ideal 0.0128/0.0232 (0.1 s) … 0.0895/0.0953 (1.5 s); e_pos 0.0079/0.0264 … 0.1193/0.2910 | CSV com 265 janelas × 6 horizontes |
| regenerate_bin_distribution | **sim** (tabela idêntica) | trans 264/49 (0.996), misto 0, rot 1/0 (0.004), total 265/49 | nota do comparador reescrita (sem "robosim indisponível") |
| analyze_omega_excitation | **sim** (números idênticos) | n 37437, 46 eventos; sub-limiar (0.581) 94.03 %; t_rms mediana 23.976 rad/s; SNR yaw/trans 0.00986; alguma roda ativa 97.32–97.79 % | o JSON de 2026-08-07 tem chaves de uma versão anterior do script (`razao_t_rms_sobre_clamp`); os valores comuns coincidem |
| fig_fit_holdout_vxvy | **sim** (CSV idêntico) | fits 86.66/86.85/86.32/87.27/88.09 %, deltas −0.04/+0.05/+0.02/−0.03/−0.01 pp; gate OK | `align="plant", upsample=20` |
| fig_main_result | **sim** | twin/ideal/rSim medianas = tabela de `epos_eang_three_models`; 10 pares por evento | PNG em `figs/main_result_en.png` |
| fig_trajectory_holdout | **sim** (mesma janela) | janela mediana seg 1 (`side_to_side_01_05`) win 9, e_pos(1.5 s) 0.1192 m | |
| fig_trajectory_by_label | **parcial** | painéis hold-out idênticos a `trajectory_by_label_20260811_0238.md` (ftb_01_01 win 19: 0.0039/0.2902/0.3262; stg_09_01 win 12: 0.1804/1.2008/1.0299; sts_01_06 win 13: 0.0564/0.6664/0.7218); square `square_01_02` win 15 twin 0.1544 / ideal 0.5619 iguais, rSim (0.6655) **não** recalculável | rodado com `allow_missing_rsim=true`; requer robosim p/ o painel square completo |
| fig_omega_stepresponse_en | **sim** (figura) | 3 painéis (rotate_01_09/06/07); sem número publicado | `align="legacy"` = script |
| fig_twin_vs_rsim_epos_en, fig_spec_main_result | **sim** | números transcritos / diagrama; sem dependência de dados | |
| metrics_report | **sim** (medianas/gap/p/effect/vereditos idênticos) | trans GO gap@h_ref +0.0617 p 1.15e-08 effect +0.832; N 264/49 | **ICs do bootstrap diferem na 3ª–4ª casa** (ex.: [+0.0458,+0.0797] → [+0.0460,+0.0792]) porque `dtssl.eval.verdict.evaluate` usa um gerador por (escopo, curva) — ver `core.md`, caveat 1 |
| loader_report | **sim** | 10 segmentos, dur 4.77–9.82 s, H_max sugerido 4.77 s | |
| eval_twin_vs_rsim, holdout_report, meeting_overlay, percurso_completo, percurso_square, eval_rsim_delay_ablation `mode=cache` | **requires_rsim** | — | importam sem robosim (lazy); não executados neste ambiente |

Testes: `tests/test_analysis_registry.py` (28 módulos importam, contrato run/main/metadata,
sem caminhos fixos, CLI `analysis`/`fig` registrado), `tests/test_analysis_fopdt.py`
(equivalências acima), `tests/test_analysis_smoke.py` (`requires_data`: `clustered_stats` e
`gate_window_vs_event` ponta a ponta em `tmp_path` com os números publicados, round-trip
do cache `.npz`, `read_event_csv`/`legacy_uy_series`). Suíte completa verde com e sem dataset
(`DTSSL_DATA=/nonexistent`).

## 4. `tools/make_release.py` (substitui `open-source/`)

`python3 tools/make_release.py [--out dist/dtssl-release] [--zip] [--strict] [--check-only]`
copia `src/dtssl` (sem `analysis/meeting_overlay.py` e `analysis/fig_spec_main_result.py`,
GUIA §2.3/2.4), `config/`, `tests/`, `matlab/dtssl/`, `docs/PREREGISTRO_OMEGA_20260724.md`,
`pyproject.toml`, `LICENSE`, os 16 artefatos de `results/` do manifesto (nunca `_BROKEN_*`),
o cache do rSim **convertido para `.npz`** (`dtssl.sim.rollout.convert_pickle_cache`) e as
figuras de `latex/figures/*.png`; gera `README.md` (tabela "um comando por afirmação" com
`dtssl analysis run …`) e `requirements.txt`. A etapa de *scrub* reescreve autor, equipe,
instituição, URL do repositório, firmware (`ssl-embedded`, hash `eb57531`), caminhos
privados e os hashes gravados pelos cabeçalhos (`commit \`…\`` → `withheld`); em seguida
varre **todos** os arquivos (bytes) e **falha (exit 1)** se restar qualquer um de
`happy-modest-euler`, `vhsabino`, `Sabino`, `RobôCIn`, `RoboCin`, `UFPE`, `ssl-embedded`,
`eb57531`, `C:\Users`. Verificado: pacote de teste em `scratch_analysis/dtssl-release`
limpo (26 análises registradas; `load_rsim_cache` lê o `.npz`). Neste checkout
`latex/figures/*.png` não existem (só `.tex`) → avisos; `--strict` transforma em erro.

A pasta `open-source/` (63 arquivos, congelada em 10/08) foi **apagada**: continha o
`phase0_replay/` antigo, cópias dos 18 scripts com o caminho absoluto embutido e
`results/loo_translational_20260810_1742.md` — a execução **quebrada** (bug mm/m) sem o
marcador `_BROKEN_` que o `results/` do repositório tem.

## 5. Arquivos criados / apagados

- Criados: `src/dtssl/analysis/{common,cli,ablation_orderfree,analyze_omega_excitation,causal_ic_check,clustered_stats,epos_eang_three_models,eval_rsim_delay_ablation,excitation_per_dof,fig_fit_holdout_vxvy,fig_main_result,fig_omega_stepresponse_en,fig_spec_main_result,fig_trajectory_by_label,fig_trajectory_holdout,fig_twin_vs_rsim_epos_en,gap_decomposition,gate_window_vs_event,loo_translational,negcontrol_perevent,r3_closedloop_omega_fit,regenerate_bin_distribution,window_errors_eang}.py`,
  `tools/make_release.py`, `tests/test_analysis_registry.py`, `tests/test_analysis_fopdt.py`,
  `tests/test_analysis_smoke.py`, `docs/refactor_notes/analysis.md`.
- Reescritos: `src/dtssl/analysis/{__init__,eval_twin_vs_rsim,holdout_report,loader_report,meeting_overlay,metrics_report,percurso_completo,percurso_square}.py`.
- Apagados (working tree, não commitado): 21 `scripts/*.py` migrados (ficam
  `scripts/build_rotate_splits.py` e `build_rotate_qc.py` — ETL, outro agente — e os `.m`/`.asv`/`local`), `open-source/` inteira.

## 6. Pendências / questões abertas

1. **Módulos com robosim não verificados** (`eval_twin_vs_rsim`, `holdout_report`,
   `meeting_overlay`, `percurso_completo`, `percurso_square`, `eval_rsim_delay_ablation
   mode=cache`, painel square de `fig_trajectory_by_label`): só importação e contrato
   testados. Rodar no PC com `robosim==1.0` (Linux) e comparar com
   `eval_twin_vs_rsim_modeA_20260617_0030.md` (esperado: mesma diferença de ~2 mm já vista em
   2026-08-09 por causa da versão do robosim).
2. **ICs do bootstrap** de `metrics_report`/`eval_twin_vs_rsim` mudam na 3ª–4ª casa (gerador
   por curva no novo `evaluate`); medianas, p, effect e vereditos idênticos. Registrar no
   `results/CHANGELOG.md` quando os relatórios forem regenerados oficialmente.
3. `results/_cache_rsim_rollouts.pkl` → converter com `dtssl cache-convert` e registrar no
   CHANGELOG (o `.pkl` segue lido pelo unpickler de compatibilidade).
4. `latex/figures/*.png` não estão no checkout (não versionadas?) — `make_release.py` avisa;
   com `--kw latex_copy=true` os geradores (`fig_main_result`, `fig_omega_stepresponse_en`,
   `fig_trajectory_holdout`, `fig_trajectory_by_label`, `fig_twin_vs_rsim_epos_en`,
   `fig_fit_holdout_vxvy`) recriam os candidatos.
5. `scripts/build_rotate_splits.py`/`build_rotate_qc.py` continuam com `REPO_ROOT =
   Path(__file__).parents[1]` e escrevem em `results/` — a migrar para `dtssl.data`
   (agente ETL) e registrar como `dtssl etl rotate`.
6. O README gerado pelo release aponta para um URL anônimo *placeholder*
   (`anonymous.4open.science/r/behavioral-twin-ssl`) — trocar pelo real antes de publicar
   (GUIA §6); `docs/PREREGISTRO_OMEGA_20260724.md` segue em PT-BR (GUIA §2.4 sugere traduzir).
7. Ruff: estilo herdado (`;` em linhas duplas, ordenação de imports) permanece nos módulos
   portados quase literalmente (`holdout_report`, `meeting_overlay`, `percurso_*`,
   `eval_twin_vs_rsim`); passar `ruff --fix` na varredura final.
8. `h5py` foi instalado no ambiente (`pip install h5py`) para `negcontrol_perevent`; está no
   extra `dtssl[mat]`.

## Checagem MIMO pré-registrada (WP2) executada e tabela `coupling` do periódico (14/10/2026)

- `dtssl analysis run coupled_mimo_check` rodou no PC nos três braços do §7 de
  `docs/PREREGISTRO_MIMO_CHECK_20260923.md` (C-, primária, C+), sem alteração do módulo nem do
  pré-registro; artefatos `results/coupled_mimo_check_20261014_1211.*`,
  `results/coupled_mimo_check_control-fopdt_20261014_1211.*` e
  `results/coupled_mimo_check_control-mujoco-rollers-delay_20261014_1216.*`, entrada 2026-10-14 12:11 do
  `results/CHANGELOG.md` com os vereditos (M1 não importa, M2 falsificada, M3 não melhora, C- OK, C+ com a
  premissa não reproduzida e leitura post hoc marcada).
- `journal_artifacts.py`: chaves `mimo`, `mimo_cminus`, `mimo_cplus` em `ARTEFACTS` e leitor `coupling()`
  (fits pooled e por evento, ganhos estáticos, razões cruzadas, vereditos, atrasos por par, bootstrap, harness
  e controles). `journal_tables.py`: `table_coupling` (`tables=coupling`, `tab:coupling`, `table*` com as
  linhas de M2, M3 e dos controles em `\multicolumn{4}{l}`), `TABLES` com seis nomes.
- Testes: `tests/test_journal_artifacts.py::test_mimo_numbers` fixa os números da entrada do CHANGELOG
  (pulado sem os artefatos); `test_journal_tables_write_latex` confere a tabela nova. 22 passados no PC
  (9 do arquivo + 13 do `test_coupled_mimo_check.py`); ruff limpo nos três arquivos.
- Fora do git: `latex_journal/tables/tab_journal_coupling.tex` gerado e o rascunho de
  `latex_journal/sections/07_results_coupling.tex` (texto em inglês a partir dos artefatos; a pasta
  `latex_journal/` continua não versionada, como o chat do artigo a deixou). Compilação verificada na nuvem
  com um invólucro `article` (sem `elsarticle` no sandbox): 0 erros, 0 referências indefinidas.
