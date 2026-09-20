# dtssl — Gêmeo digital comportamental do robô SSL (RobôCIn v2025)

Gêmeo digital do robô omnidirecional de 4 rodas da RobôCIn (Small Size League, Div. B), identificado
de **logs de competição** e de um **experimento dedicado de rotação pura**. Pesquisa de doutorado
(CIn-UFPE / RobôCIn) sobre *reality gap* e identificabilidade em gêmeos digitais de robôs móveis.

O que ele é, em uma frase: uma planta por grau de liberdade de corpo
`G_i(s) = K_i · e^(−Td_i·s) / (τ_i·s + 1)`, `i ∈ {vx, vy, ω}` (9 parâmetros, primeira ordem + atraso),
que recebe o **mesmo comando de velocidade de corpo** que o robô real recebe (`move_x, move_y, move_w`)
e devolve a pose no mundo — embrulhada num simulador que fala o *ssl-simulation-protocol* (drop-in do
grSim/ER-Force para o `ssl-unification`), numa GUI com modo teleoperado por DualSense e num harness
científico que reproduz cada número do artigo com um comando.

## Resultado científico (resumo)

| θ oficial (`config/twin_params.json`, ordem fixa) | K | τ (s) | Td (s) | Fonte |
|---|---|---|---|---|
| vx | 1,1192 | 0,0718 | 0,0691 | `front_to_back`, malha fechada, fit hold-out 86,7 % (`models/sysid_vxvy_v2.mat`, 14/06/2026) |
| vy | 1,0524 | 0,1273 | 0,0565 | `side_to_side`, malha fechada, fit hold-out 87,1 % (idem) |
| ω | 1,0016 | 0,0828 | 0,0890 | rotação pura em **malha aberta**, fit hold-out 71,1 % (`models/sysid_omega_rotate_v1.mat`, 24/07/2026) |

- **Gêmeo vs. cinemática ideal vs. rSim**, replay *free-run* em janelas re-ancoradas SE(2), horizonte de
  referência `h_ref = 0,4 s`, 10/10 eventos de hold-out nunca usados no ajuste: mediana de `e_pos`
  **0,039 m** (gêmeo) vs **0,101 m** (ideal) vs **0,129 m** (rSim não sintonizado); o gêmeo vence em todos
  os 10 eventos e em todos os horizontes (0,1–1,5 s), com evidência de 73,5 s de trajetória.
  Fontes: `results/gap_decomposition_20260809_2308.md`, `results/epos_eang_three_models_20260810_1022.md`,
  `results/clustered_stats_20260809_2309.md`.
- **ω só é identificável com dado dedicado de malha aberta**: nos logs de competição (malha fechada,
  |ω| mascarado pela zona morta em ~94 % das amostras) toda tentativa deu K≈1,3 e **piorou** o replay;
  com 6 degraus de rotação pura o mesmo estimador dá K≈1,00 (IC95 % contém 1) e o gate SE(2) passa em
  todos os horizontes (`results/identificacao_omega_20260724.md`, pré-registro em
  `docs/PREREGISTRO_OMEGA_20260724.md`). A tese do artigo: *a identificabilidade segue o regime de
  excitação, não o grau de liberdade*.
- Ablação: τ (55 %) e Td (43 %) explicam quase todo o ganho sobre a cinemática ideal; K contribui 2 %
  (`results/ablation_orderfree_20260810_1021.md`). Casar o atraso no rSim não fecha o gap
  (`results/eval_rsim_delay_ablation_20260809_2154.md`).

Artigo (SBR/LARS 2026): `latex/` (referências **somente** em `latex/refs/references.bib`).
Histórico completo de cada número: `results/CHANGELOG.md`.

## Instalação

```bash
git clone <este repo> digitaltwin && cd digitaltwin
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[gui,mujoco,dev]"                    # extras: gui (PySide6/pyqtgraph/pygame-ce), mujoco, rsim, etl, mat, dev
dtssl info                                            # versão, raiz, dataset, backends e extras disponíveis
pytest -q                                             # sem dataset: pytest -m "not requires_data"
```

Sem venv (`pip install --user -e .`), o executável `dtssl` fica fora do PATH no Windows
(`%APPDATA%\Python\Python3xx\Scripts`): use `py -3 -m dtssl.cli …` e `py -3 -m dtssl.gui …`, que são equivalentes.

Dados (`data/extracted/<dataset>/splits/<label>/<evento>/*.parquet`) são gerenciados por **DVC**
(`dvc pull`); sem eles os testes marcados `requires_data` são pulados. Python ≥ 3.10.

## Uso rápido

```bash
dtssl gui [--no-3d | --no-cad]              # interface: campo 2D + aba 3D com o CAD, bola, telemetria cmd×estado,
                                            #   editor de θ; modos Debug (DualSense/teclado), Bridge (ssl-unification), Replay
dtssl serve [--backend fopdt|ideal|mujoco-velocity|mujoco-rollers] [--n-blue 6 --n-yellow 6] [--record DIR]
                                            # servidor ssl-simulation-protocol: visão 224.5.23.2:10006, controle
                                            #   10301 (blue) / 10302 (yellow), SimulatorCommand 10300 (config/bridge.json)
dtssl fake-strategy --team yellow --target 1 0.5        # cliente de fumaça que emula a estratégia
dtssl replay shoot_to_goal shoot_to_goal_12_01 [--theta config/twin_params.json] [--plant fopdt|ideal|mujoco-velocity|mujoco-rollers[-delay]|proto:grsim[+delay]][+preroll]
dtssl gate twin-vs-ideal | twin-vs-rsim [--mode A|B]    # gate estatístico do hold-out (config/metrics.json)
dtssl analysis list | run <nome> | info <nome>          # cada número do artigo = um módulo de dtssl.analysis
dtssl fig <nome>                                        # figuras do artigo
dtssl etl extract|split|rotate|inspect                  # .log.gz (protobuf) -> parquet no contrato dos logs
dtssl mjcf --route a|b [--view --demo] [--visual cad]   # gera/visualiza os modelos MuJoCo (--visual cad: malhas do CAD)
dtssl cache-convert <pkl> <npz>  ·  dtssl proto-build   ·  dtssl release
```

### Rodar o `ssl-unification` contra o gêmeo

```bash
tools/ssl_unification/build_wsl2.sh --config-team yellow          # WSL2 Ubuntu: clone + deps + Qt + build + config/local
tools/ssl_unification/run_against_twin.sh --team yellow           # dtssl serve (background) + ssl-unification -running
```

Detalhes (chaves do `config/local/config.json`, rede Windows↔WSL2, DualSense):
`tools/ssl_unification/README.md`. Nenhuma alteração no C++ da estratégia é necessária.

### grSim e ER-Force no harness do artigo (replay via protocolo)

```bash
tools/external_sims/install_grsim_wsl.sh && tools/external_sims/install_erforce_wsl.sh   # WSL2; sudo só no apt
tools/external_sims/run_grsim.sh start && tools/external_sims/run_grsim.sh probe        # sonda: teleporte + 1 janela
tools/external_sims/run_protocol_holdout.sh          # hold-out via ssl-simulation-protocol (~35 min, tempo real)
dtssl analysis run protocol_holdout --kw sims=grsim delay=both   # o mesmo, com o simulador já de pé
```

`ProtocolPlant` (`dtssl.sim.protocol_plant`) replaya as janelas do hold-out em qualquer simulador da liga
(teleporte + comandos a 60 Hz + visão alinhada), com as mesmas janelas e métrica do gêmeo; endpoints em
`config/external_sims.json`, detalhes e limitações de cada simulador em `tools/external_sims/README.md`.

## Layout do repositório

```
pyproject.toml            pacote dtssl (src-layout); extras gui/mujoco/rsim/etl/mat/dev
config/                   twin_params.json (θ oficial), metrics.json, holdout_events.json, robot_geometry.json,
                          robot_limits.json, field_divB.json, bridge.json, external_sims.json, ssl_robot.sldd (SLDD do Simulink)
src/dtssl/                paths, config, units, geometry, kinematics, cli
  data/                   schema, resample, loader, validate, splits, recordio, extract, rotate (+ _proto/)
  models/                 params (θ), Plant, AnalyticFOPDTPlant, IdealKinematicPlant, ConstantVelocity, RSimReplay
  sim/                    entidades, TwinWorld (bola 2 fases, colisões, dribbler, watchdog), rollout, backends
  eval/                   métrica multi-horizonte por janela, estatística (Wilcoxon, bootstrap por blocos), veredito, relatório
  analysis/               21 análises/figuras do artigo (run(root, out) + main())
  bridge/                 servidor ssl-simulation-protocol (visão, controle, simcontrol), fake_strategy, recorder, protos
  gui/                    PySide6 + pyqtgraph (campo, plots, painel de θ, joystick)
  physics/                MuJoCo: builder MJCF (rota a: FOPDT dirige o ego; rota b: rodas + roletes), MuJoCoWorld
tests/                    pytest; marcadores requires_data / requires_mujoco / requires_gui / requires_net / requires_rsim
matlab/                   bootstrap_paths.m · dtssl/ (identificação, gate SE(2), planta analítica de referência,
                          goldens) · sldd/ · simulink_io/ · legacy/ (arquivado com README)
simulink/                 parameter_estimation_model_pid_v3.slx (único oráculo Simulink mantido)
models/                   .mat identificados (promovidos e candidatos)
results/                  artefatos com carimbo de tempo + CHANGELOG.md (proveniência de cada número)
docs/                     SPEC_DTSSL.md (contrato), ADRs, relatórios, revisões, refactor_notes/ (índice: docs/README.md)
latex/  slr/  paper/      artigo, revisão sistemática, outline
tools/                    make_release.py, ssl_unification/, external_sims/ (grSim/ER-Force no WSL2), apply_refactor_manifest.json
legacy/                   archive/ (RL TD3, viewers antigos, testes) e apresentacao/ — fora do pacote
phase0_replay/            shim de compatibilidade (reexporta dtssl; remover em v2)
assets/ cad/ usd/         STEP/USD do robô (fontes para meshes)
```

Convenções físicas (SI; mundo = ssl-vision com +x para o gol direito, θ CCW; corpo com x para o dribbler;
`Ts = 1/60 s`; ordem de θ `[K_vx, tau_vx, Td_vx, K_vy, tau_vy, Td_vy, K_w, tau_w, Td_w]`): `docs/SPEC_DTSSL.md` §3.

## Lado MATLAB

```matlab
addpath('matlab'); bootstrap_paths();                  % sem cd(); 'legacy' adiciona matlab/legacy
[theta_x, R] = identify_trans_dof('x');                % re-ID P1D de vx (hold-out por evento, seed 42)
[theta_w, R] = identify_omega_rotate();                % ω, dataset de rotação pura (pré-registrado)
[W, T] = eval_omega_v3_se2('CandMat', 'build/x.mat'); % gate SE(2) multi-horizonte vs placeholder (Simulink)
export_plant_golden(ev_dir, 'theta', 'promoted', 'tag', 'v2');   % golden bit-a-bit p/ a planta Python
```

`deadreckoning_p1d.m` é a referência da `AnalyticFOPDTPlant` (goldens em `tests/fixtures/`, atol 1e-6).
Requer System Identification, Simulink, Signal Processing e Statistics toolboxes.

## Licença

MIT (`LICENSE`). Autor: Victor H. S. Sabino (CIn-UFPE / RobôCIn).
