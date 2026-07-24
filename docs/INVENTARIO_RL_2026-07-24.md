# Inventário — repositório `planning-rl-greybox`

**Data do inventário:** 2026-07-24
**Local:** `\\wsl.localhost\Ubuntu\home\victo\planning-rl-greybox` (WSL2 Ubuntu: `/home/victo/planning-rl-greybox`)
**Propósito:** experimento de gap de dinâmica do gêmeo digital comportamental (RobôCIn SSL v2025) — reprodução do pipeline SAC+FSCAPS de Machado et al. (*Planning the path with RL*) com a dinâmica trocada por planta grey-box FOPTD identificada, mais validação cruzada em grSim (terceira dinâmica).

---

## 1. Onde o trabalho parou

- **Último commit:** `de3953c` — *"Move grSim raw eval CSV + trajectories from git to DVC (no LFS)"* — **2026-07-10 15:14 (BRT)**.
- **Último artefato modificado:** `RELATORIO_GRSIM.md` e `results/grsim.dvc` (2026-07-10 15:11–15:14).
- Working tree limpo (exceto `.claude/` untracked). Branch única `master`. **Sem remote git configurado** (repo apenas local).
- Todo o trabalho foi concentrado em **2 dias**: 2026-07-09 (pipeline grey-box + treino) e 2026-07-10 (resultados 150k, grSim, análises). 8 commits no total.

Cronologia dos 8 commits:

| Data | Commit | Conteúdo |
|---|---|---|
| 07-09 21:29 | `78a8cb3` | Pipeline grey-box FOPTD: módulo+testes, integração no env, treino/eval/análise, proveniência |
| 07-09 21:39 | `8a24688` | Scaffold do relatório, launcher de eval, CSV consolidado |
| 07-10 06:47 | `cea8da3` | Resultados: treino 2×5, eval 1000 ep + cross-eval, estatística, figuras |
| 07-10 12:30 | `a8cd5cb` | **Resultados finais 150k com FOPTD calibrado**: eval, stats, figuras, relatório |
| 07-10 13:28 | `dcdf173` | Validação cruzada grSim: cliente, GrSimEvalEnv, sanity checks, driver |
| 07-10 13:31 | `cf7e22f` | Análise grSim (teste H1) + scaffold do relatório |
| 07-10 15:14 | `5961aef` | Resultados H1 grSim: análise, tabelas, figuras, veredicto |
| 07-10 15:14 | `de3953c` | CSVs/trajetórias grSim movidos de git para DVC |

## 2. Estrutura do repositório

### 2.1 Código próprio (raiz)

| Arquivo | Papel |
|---|---|
| `greybox_dynamics.py` | `FOPTDChannel` (ZOH exato + FIFO de atraso) + `GreyBoxFOPTD` (3 canais, deadzone de ω, integração SE(2)). Parâmetros **carregados de JSON** (`GreyBoxFOPTD.from_json`), não hard-coded |
| `params_greybox.json` | Parâmetros FOPTD por DOF usados no experimento (ver §4) |
| `integration/greybox_rsim.py` | `GreyBoxRSimSSL` — drop-in do `RSimSSL` (mesma interface, sem robosim) |
| `integration/greybox_env.py` | Registro dos envs `ProposedOrig-v1` / `ProposedGB-v1` (idênticos exceto dinâmica) |
| `integration/grsim_rsim.py` | `GrSimRSim` — drop-in falando UDP com grSim |
| `integration/grsim_env.py` | `GrSimEvalEnv` (reutiliza obs/ação/recompensa do treino; só a física muda) |
| `grsim_client/` | Bindings protobuf + `client.py` (comando, replacement, visão com fusão de 4 câmeras) |
| `train_greybox.py` / `run_training.sh` | Treino SAC+FSCAPS (150k steps, 16 envs, 5 seeds × 2 dinâmicas) |
| `eval_greybox.py` / `run_eval.sh` | Eval determinística 1000 ep/condição + cross-eval (episódios pareados por seed) |
| `grsim_eval.py` | Driver da eval em grSim (100 ep/seed, episódios pareados) |
| `sanity_grsim.py` | Sanity checks do grSim (frames, degrau, jitter de visão) |
| `analyze_results.py` / `analyze_grsim.py` | Tabelas, Mann-Whitney U, Cliff's δ, Wilcoxon, figuras |
| `tests/test_greybox_dynamics.py` | 10 testes unitários da dinâmica (10/10 passed) |
| `provenance.json`, `requirements_lock.txt`, `clone_repos.sh`, `install_env.sh`, `build_grsim_env.sh` | Reprodutibilidade |
| `RELATORIO_RL_GREYBOX.md` | Relatório completo do experimento principal (gap de dinâmica) |
| `RELATORIO_GRSIM.md` | Relatório da validação cruzada em grSim (H1) |

### 2.2 Repositórios de terceiros vendorizados (clonados, não submódulos)

| Diretório | Origem | Pin |
|---|---|---|
| `Planning-the-path-with-rl/` | `goncamateus/Planning-the-path-with-rl` | commit `2287531e87b31dacbc60f482321d3fc3640d4246` |
| `rSoccer/` | fork `goncamateus/rSoccer`, branch **`dev`** | commit `3a2f0b23b5e87e4699734d25008d0fadf212904c` |
| `grSim/` | `RoboCup-SSL/grSim` (compilado do zero, headless, sem root) | commit `fe2bd2915a46f9f11ea6cb48dc426b8047952073` |

`Planning-the-path-with-rl/trained_models/` contém os modelos originais do artigo (Baseline/Enhanced/Obstacle × v0/v1 × ±caps) — não usados no experimento (políticas foram re-treinadas).

### 2.3 Ambientes RL

| Env id | Dinâmica | Definição |
|---|---|---|
| `ProposedOrig-v1` | rSoccer/robosim (ODE) | `integration/greybox_env.py` — equivale ao `Enhanced-v1` do artigo (`repeat_action=16`, `max_episode_steps=75`) |
| `ProposedGB-v1` | grey-box FOPTD | idem, com `GreyBoxRSimSSL` |
| `GrSimEvalEnv` | grSim (ODE, roda omni própria) | `integration/grsim_env.py` — só avaliação, skip=24 frames de visão (período de ação 0.4 s preservado) |

Infraestrutura para cenário Obstacle (`ObstacleOrig/GB-v1`) pronta, **nunca executada**.

### 2.4 Políticas treinadas e checkpoints (`runs/`, via DVC)

10 runs = {original, greybox} × seeds {0, 10, 20, 30, 40}, 150 000 steps cada (orçamento completo do artigo). Por run:

- `runs/Proposed_{dyn}_seed{s}/final/{actor.pt,critic.pt}` — checkpoint final (usado nas evals);
- `ckpt_{25000,50000,75000,100000,125000}/` — checkpoints intermediários;
- `learning_curve.csv`, `meta.json` (gym_id, seed, steps, num_envs, wall_time).

Total 140 arquivos, ~189 MB (`runs.dvc`, md5 `0115aaee…`). Formato: `state_dict` PyTorch (torch 2.0.0+cpu) — **não** TorchScript.

### 2.5 Resultados (`results/`)

- `results/raw_episodes.csv` — 20 000 episódios consolidados (4 condições × 5 seeds × 1000), em git.
- `results/eval/` (DVC) — 20 CSVs `Proposed_train-{dyn}_exec-{dyn}_seed{s}.csv`.
- `results/grsim/` (DVC) — `grsim_eval.csv` (1000 ep pareados) + `trajectories/*.npy` (20 trajetórias).
- `results/tables/` — tabelas finais em git (ver §3).
- `results/figures/` — `learning_curves.png`, `action_scatter.png`, `grsim_boxplots.png`, `grsim_trajectories.png`, `grsim_step_response.png`, `three_dynamics_step.png`.

## 3. Resultados-chave — arquivos-fonte exatos

### 3.1 Gap de transferência assimétrico (rSoccer vs grey-box, Cliff's δ = −1.0)

Resultado central: política treinada no simulador original executada no grey-box degrada catastroficamente (Episode Length mediano 109 → **947** passos, **δ = −1.000**, separação perfeita); na direção inversa a política grey-box fica mais rápida no original (307 → 192, δ = +0.75) porém oscilatória (CPAD 0.596 → 2.106, δ = −0.85).

Fontes:

| Arquivo | Conteúdo |
|---|---|
| `results/tables/table_stats.csv` / `.md` | Mann-Whitney U + Cliff's δ dos 6 contrastes (inclui as linhas δ=−1.000: CPAD matched e Episode Length orig→gb) |
| `results/tables/table_metrics.csv` / `.md` | Medianas/IQR/min/max das 4 condições (n=5000 cada) |
| `results/tables/summary.json` | Agregado em JSON |
| `results/raw_episodes.csv` | Dados brutos por episódio (20k linhas) |
| `results/eval/*.csv` (DVC) | Dados brutos por seed/condição |
| `results/figures/action_scatter.png`, `learning_curves.png` | Figuras |
| `RELATORIO_RL_GREYBOX.md` §6.1–6.3 | Tabelas transcritas + leitura |
| Geradores: `eval_greybox.py` → `analyze_results.py` | |

### 3.2 Caracterização das três dinâmicas (degrau vx = 0.5 m/s)

| dinâmica | K | τ (ms) | Td (ms) |
|---|---|---|---|
| rSoccer/robosim (original) | 1.00 | 75 | 25 |
| grey-box FOPTD (vx) | 0.989 | 128 | 171 |
| grSim (medido) | 1.00 | 67 | 50 |

Conclusão associada: grSim ≈ rSoccer original (árbitro **não equidistante**), grey-box é a dinâmica discrepante — condiciona toda a leitura de H1.

Fontes:

| Arquivo | Conteúdo |
|---|---|
| `results/tables/three_dynamics_params.csv` / `.md` | A tabela acima |
| `results/figures/three_dynamics_step.png` | Sobreposição das respostas ao degrau |
| `results/tables/grsim_sanity.json` | Medições do grSim (K, τ, Td, frames, jitter) |
| `results/figures/grsim_step_response.png` | Degrau do grSim |
| `RELATORIO_GRSIM.md` §1.3 | Discussão |
| Geradores: `sanity_grsim.py` → `analyze_grsim.py` | |

Resultados do teste H1 em grSim: `results/tables/grsim_stats_primary.csv` (Wilcoxon pareado por seed, n=5, W=0, p=0.0625), `grsim_stats_secondary.csv` (Mann-Whitney n=500×500: length δ=−0.596, CPAD δ=−1.000), `grsim_degradation.csv` (Δlen −21.8% gb vs +46.8% orig), `grsim_h1_verdict.json`, `grsim_summary.csv`; relatório em `RELATORIO_GRSIM.md` §4.

## 4. Dependências cruzadas com o repo `digitaltwin`

1. **Parâmetros FOPTD — DIVERGÊNCIA entre os repos (ponto de atenção).**
   Os valores usados neste experimento (`params_greybox.json`) **não coincidem** com os atualmente promovidos em `digitaltwin/config/twin_params.json`:

   | DOF | `params_greybox.json` (usado no RL) | `twin_params.json` (digitaltwin, promovido) |
   |---|---|---|
   | vx | K=0.989, τ=0.128, Td=0.171 | K=1.119, τ=0.0718, Td=0.0691 |
   | vy | K=0.949, τ=0.242, Td=0.105 | K=1.052, τ=0.1273, Td=0.0565 |
   | ω/w | K=1.35, τ=0.035, Td=0.106 + deadzone corpo 0.472 rad/s | **placeholder** K=1, τ=0.1, Td=0 |

   Ou seja: o experimento RL usou uma **calibração anterior/distinta** da identificação hoje promovida (`models/sysid_vxvy_v2.mat`). Antes de retomar, decidir se os resultados devem ser re-executados com os parâmetros promovidos ou se a versão usada aqui vira a de registro. Não há hard-coding no código: `GreyBoxFOPTD.from_json` lê o JSON — re-treinar com novos parâmetros é trocar o arquivo.
   Diferenças estruturais adicionais: `twin_params.json` não tem deadzone de ω; `params_greybox.json` não tem `robot_radius`/`wheel_radius`; nomes de chave diferem (`omega` vs `w`).

2. **Nenhuma referência direta.** Grep no repo não encontra `twin_params`, `digitaltwin`, caminho ou import cruzado — o acoplamento é apenas por valores copiados manualmente para `params_greybox.json`.

3. **rSoccer.** Este repo usa o **fork `goncamateus/rSoccer` branch `dev`** (`3a2f0b2`) + `rc-robosim 1.2` — não o rSoccer upstream. Qualquer integração com o digitaltwin que assuma rSoccer upstream precisa conferir compatibilidade de interface (`RSimSSL.send_commands`/`get_frame`).

4. **dt.** Identificação a 1/60 s (ts do `twin_params.json`), simulador rSoccer a 0.025 s (40 Hz), grSim a 1/60 s. Tratado analiticamente (K, τ, Td contínuos; discretização no dt do executor) — convenção que o digitaltwin deve manter.

5. **Convenção de frames** compartilhada com a identificação: comandos em frame LOCAL do robô, velocidades observadas em frame MUNDO (`RELATORIO_RL_GREYBOX.md` §2).

## 5. Pendências

| # | Pendência | Status neste repo |
|---|---|---|
| P1 | **Exportação TorchScript** das políticas (deploy fora de Python/pickle) | **Não iniciada.** Checkpoints são `state_dict` PyTorch 2.0.0+cpu em `runs/*/final/actor.pt`; nenhum script de exportação existe |
| P2 | **Bridge SSL-Unification** (executar políticas no software do time / robô real) | **Não iniciada.** Nenhuma referência no repo; o mais próximo é o cliente grSim (`grsim_client/`), que pode servir de base |
| P3 | **Protocolo de episódios pareados** (formalização) | **Parcial.** Pareamento por seed já implementado em `eval_greybox.py` (mesmas 1000 tarefas nas duas dinâmicas) e `grsim_eval.py` (mesmos episode-seeds nas duas condições); falta formalizar como protocolo reutilizável, incl. para testes no robô real |
| P4 | **DVC sem remote** | `.dvc/config` vazio — `runs/` (189 MB), `results/eval/`, `results/grsim/` existem **somente no cache local** do WSL. Risco de perda; configurar remote (ou backup) antes de qualquer limpeza |
| P5 | **Sem remote git** | Repo apenas local, branch `master` |
| P6 | **Canal ω preliminar** | Fit ~30%, deadzone mascarou ~84% dos comandos; ganhos de ω são placeholders — conclusões dependentes de rotação/heading provisórias (limitação nº 1 dos dois relatórios). Ligado à divergência do §4.1 (ω reprovado na ID física do digitaltwin) |
| P7 | **Cenário Obstacle não executado** | Envs `ObstacleOrig/GB-v1` prontos; `GreyBoxRSimSSL` não simula robôs amarelos/bola (obstáculos estáticos) — precisaria de extensão |
| P8 | **Re-execução com parâmetros promovidos** | Decidir sobre a divergência `params_greybox.json` × `twin_params.json` (§4.1) antes de citar os números em publicação |

---

*Inventário gerado em 2026-07-24 para o relatório de retomada do doutorado (resolve a pendência D7 do repositório digitaltwin). Cópia em `digitaltwin/docs/INVENTARIO_RL_2026-07-24.md`.*
