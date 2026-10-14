# CLAUDE.md — dtssl: gêmeo digital do robô SSL (Doutorado CIn-UFPE / RobôCIn)

*Reescrito em 02/09/2026 na refatoração `refactor/dtssl`. Este arquivo é versionado. Contrato de
arquitetura: `docs/SPEC_DTSSL.md` (vence este arquivo em caso de conflito). Proveniência de todo
número: `results/CHANGELOG.md`. Índice de documentos: `docs/README.md`.*

## 1. O projeto em 10 linhas

- Tese: gêmeo digital de **fidelidade observacional comportamental** do robô SSL omnidirecional 4 rodas
  (RobôCIn v2025). Planta por DOF de corpo `G_i(s) = K_i e^(−Td_i s)/(τ_i s+1)`, i ∈ {vx, vy, ω}.
- **θ oficial (9 params, `config/twin_params.json`, ordem fixa `[K_vx,tau_vx,Td_vx,K_vy,tau_vy,Td_vy,K_w,tau_w,Td_w]`):**
  vx {1,1192; 0,0718; 0,0691}, vy {1,0524; 0,1273; 0,0565} — promovidos 14/06/2026
  (`models/sysid_vxvy_v2.mat`, logs de competição, hold-out ~87 %);
  **ω {1,0016; 0,0828; 0,0890} — promovido 24/07/2026** (`models/sysid_omega_rotate_v1.mat`, dataset
  dedicado de rotação pura em malha aberta, pré-registro `docs/PREREGISTRO_OMEGA_20260724.md`,
  fit hold-out 71,1 %, gate SE(2) p<0,05 em todos os horizontes). **Não há mais placeholder.**
- Achado central do artigo (SBR/LARS 2026, `latex/`): identificabilidade segue o **regime de excitação**,
  não o DOF — ω em malha fechada dava K≈1,3 e piorava o replay; em malha aberta K≈1,00.
- Headline: `e_pos` mediano em `h_ref=0,4 s` no hold-out (10/10 eventos): gêmeo **0,039 m** vs ideal
  0,101 m vs rSim 0,129 m. Ablação: τ 55 %, Td 43 %, K 2 % do ganho.
- Encerrado: bayesopt conjunto (v1/v2 não promovidos), ω por malha fechada, PSO/RL (arquivados).
- Fora de escopo agora: RL, Isaac Sim, multi-câmera/ruído realista, árbitro completo, robôs reais (SPEC §1).

## 2. Estrutura (= `docs/SPEC_DTSSL.md` §2)

| Caminho | Papel |
|---|---|
| `src/dtssl/` | pacote Python instalável (src-layout): `paths, config, units, geometry, kinematics, cli`; `data/` (schema, resample, loader, validate, splits, recordio, extract, rotate); `models/` (θ, `Plant`, `AnalyticFOPDTPlant` — porte bit-a-bit de `deadreckoning_p1d.m`, `IdealKinematicPlant`, `RSimReplay`); `sim/` (`TwinWorld`, bola, colisões, rollout, `backends`: `fopdt`/`ideal`/`mujoco-velocity`/`mujoco-rollers`; `world_plant`/`protocol_plant`: qualquer backend ou simulador externo via ssl-simulation-protocol como `Plant` do harness); `eval/` (métrica por janela multi-horizonte, stats, veredito, relatório); `analysis/` (1 módulo por número/figura do artigo); `bridge/` (servidor ssl-simulation-protocol, fake_strategy, recorder, protos versionados, `telemetry` = Feedback do rádio dos robôs reais); `gui/` (2D, 3D, aba Robot com o robô em 3D girável); `physics/` (MJCF + MuJoCoWorld) |
| CLI `dtssl` | `info · replay · gate · cache-convert · analysis · fig · etl · serve · fake-strategy · proto-build · mjcf · gui · release` |
| `config/` | `twin_params.json` (θ), `metrics.json`, `holdout_events.json`, `robot_geometry.json`, `robot_limits.json`, `field_divB.json` e `field_divA.json` (campos das Divisões B e A da SSL, `robots_per_team` 6 / 11; presets em `dtssl.config.load_field_preset`, seletor na GUI e `--field` nas CLIs), `bridge.json`, `external_sims.json` (endpoints grSim/ER-Force), `telemetry.json` (rádio dos robôs reais + modelo ilustrativo de bateria/capacitor da aba Robot), `ssl_robot.sldd` |
| `matlab/` | `bootstrap_paths.m` (sem `cd`); `dtssl/` VIVO (identificação, gate SE(2), `deadreckoning_p1d`, métricas, goldens, cadeia do oráculo Simulink); `sldd/`; `simulink_io/`; `legacy/` (arquivado, README por grupo) |
| `simulink/parameter_estimation_model_pid_v3.slx` | único oráculo Simulink mantido (~9,5 s/sim) |
| `tests/` | pytest; marcadores `requires_data / requires_mujoco / requires_gui / requires_net / requires_rsim`; goldens em `tests/fixtures/` (θ do golden em `plant_golden_theta.json`, **não** o θ oficial) |
| `data/` (DVC) · `models/` (.mat) · `results/` (artefatos + CHANGELOG) · `docs/` · `latex/` · `slr/` · `notebooks/` | dados, modelos, resultados, documentação, artigo |
| `tools/` | `make_release.py` (pacote anonimizado → `dist/`), `ssl_unification/` (build WSL2 + `config/local`), `external_sims/` (grSim/ER-Force no WSL2 + experimento C2b), `apply_refactor_manifest.json`, `inventor_export_cad.m` (chassi, roda, chute e dribbler tesselados com as cores do CAD a partir do `robot_v2025_v3.iam` pela API COM do Inventor, Windows) + `cad_lod.m` (LOD das vistas 3D da GUI: só as peças vistas de fora, faces por área visível) + `register_cad_meshes.py` (grava `src/dtssl/physics/assets/meshes.json`), `step_probe.m` (bbox por peça de um STEP) |
| `legacy/` | `archive/` (RL TD3 de maio, viewers, testes) e `apresentacao/` — fora do pacote |
| `phase0_replay/` | shim de compatibilidade (reexporta `dtssl`); remover em v2 |

Removidos na refatoração: `automation/` (→ `matlab/dtssl` e `matlab/legacy`), `scripts/*.py` (→ `dtssl.analysis`),
`python/` (→ `dtssl.data`), `open-source/` (→ `dtssl release`), `archive/` (→ `legacy/archive`).

## 3. Convenções (obrigatórias)

- Unidades **SI** internas (m, s, rad); mm/graus só na borda (visão SSL, logs). `Ts = 1/60 s`.
- Frames: mundo = ssl-vision (+x gol direito, θ CCW em (−π, π], `unwrap` para integrar); corpo = x para o
  dribbler, y para a esquerda; `v_world = R(θ)·v_body`. Comando = `BodyCmd(vx, vy, w)` = `move_x/y/w`.
- Geometria: `R = 0,079601 m`, `r = 0,029492 m`, φ = [60, 135, 225, 300]° (`config/robot_geometry.json`);
  zona morta por roda 1,567 rad/s (⇒ corpo 0,58–0,60 rad/s), **desligada por default**.
- Idioma: docs em PT-BR; código, identificadores, docstrings e commits em EN; artigo em EN.
- Python ≥ 3.10, `ruff` (linha 110), testes `pytest`; nada de `sys.path` hacks — instalar com `pip install -e .`.
- MATLAB: funções puras; caminhos resolvidos contra a raiz do repo (`matlab/dtssl/private/resolve_repo_path.m`),
  nunca contra `pwd`; `bootstrap_paths` **não** faz `cd`; scripts que chamam `apply_theta` escrevem o SLDD
  versionado → `git restore config/ssl_robot.sldd` depois.
- Resultados: arquivo novo com carimbo de tempo + cabeçalho (commit, θ, dataset, seed); **nunca sobrescrever**
  `results/` nem `models/`. Cada número do artigo = `dtssl analysis run <nome>` reproduzível.
- Git: branch `main` (a `refactor/dtssl` foi mesclada com `--no-ff` na tag `v1.0.0` em 14/10/2026), commits atômicos por etapa, sem push automático.

## 4. Guardrails (NUNCA)

- Alterar a **ordem** dos campos de θ, os valores de `config/twin_params.json`, `config/metrics.json`,
  `config/holdout_events.json` ou o SLDD sem uma promoção registrada (gate + CHANGELOG).
- Modificar `data/` (bruto ou extraído) ou apagar/sobrescrever `results/` e `models/`.
- Citar referências que não estejam em **`latex/refs/references.bib`** (único .bib; `slr/incluidos.bib`
  **não existe**). Nunca inventar referência ou número.
- Reportar números que não venham de execução real registrada em `results/` + CHANGELOG.
- Tocar no C++ do `ssl-unification` (só `config/local` + scripts de build, SPEC D6).
- Expandir escopo (RL, Isaac Sim, robôs reais) sem ordem explícita.
- Fazer `git push` ou reescrever histórico.

## 5. Definition of Done

Experimento/número: (1) script/módulo reproduzível commitado (`dtssl analysis`/`matlab/dtssl`), (2) seed
fixa, (3) artefato em `results/` com metadados (commit, θ, dataset, seed), (4) entrada em
`results/CHANGELOG.md`, (5) resumo de 3 linhas para o humano validar.
Código: testes passando (`pytest -m "not requires_data"` sem dataset; suíte completa com dataset),
`ruff` limpo nos arquivos tocados, SPEC atualizada se a interface mudou, nota em `docs/refactor_notes/`
quando for refatoração.
