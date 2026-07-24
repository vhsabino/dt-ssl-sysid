# DESIGN — Harness de replay para validação do gêmeo digital (FOPDT por DOF)

*Documento de exploração e contrato de dados. NÃO contém implementação. Para revisão antes de codar. Autor: sessão 2026-06-15.*

Robô SSL omnidirecional 4 rodas (RobôCIn v2025). Gêmeo = FOPDT por grau de liberdade:
`G_i(s) = K_i · e^(−Td_i·s) / (τ_i·s + 1)`, i ∈ {vx, vy, ω}, comandos de **corpo** integrados ao **mundo**.

---

## 1. Inventário do repositório

### 1.1 Identificação do gêmeo (FOPDT / P1D)
**Pipeline novo (vigente, por evento + hold-out, gera os modelos promovidos):**
- [automation/identify_trans_dof.m](automation/identify_trans_dof.m) — re-ID P1D de vx/vy (`procest 'P1D'`); velocidade medida derivada da posição da visão (Savitzky-Golay) e rotacionada ao corpo; hold-out por evento seed 42. **Fonte do modelo promovido.**
- [automation/identify_omega_v3_linear.m](automation/identify_omega_v3_linear.m) — ID P1D de ω no regime alto (|cmd_ω|>0,3); candidato, **não** promovido.
- [automation/identify_omega_from_splits.m](automation/identify_omega_from_splits.m) — ID P1D de ω (tentativa anterior, `procest`); candidato.
- [automation/check_excitation_trans.m](automation/check_excitation_trans.m) — diagnóstico de excitação translacional (std cmd, xcorr cmd→vel, Td₀) que escolhe as fontes (vx←front_to_back, vy←side_to_side).

**Pipeline antigo (concatenado por label; herdado, parcialmente estale):**
- [matlab/sysid/run_sysid.m](matlab/sysid/run_sysid.m) — orquestrador: monta iddata → `identify_per_dof` → salva.
- [matlab/sysid/build_idData_per_dof.m](matlab/sysid/build_idData_per_dof.m) — monta `iddata (u,y)` por DOF a partir dos `all_*_labeled.parquet` (colunas `label`/`event_id`); **rotaciona velocidade mundo→corpo** (linhas 97–100). Aqui é onde o frame fica explícito.
- [matlab/sysid/identify_per_dof.m](matlab/sysid/identify_per_dof.m) — `procest(d,'P1D')` por DOF → K, τ, Td, fit.
- [matlab/sysid/cross_log_validation.m](matlab/sysid/cross_log_validation.m) — validação cruzada entre logs.
- [matlab/sysid/compute_rmse_position.m](matlab/sysid/compute_rmse_position.m) — RMSE de posição (métrica antiga, janelas por amostra).

### 1.2 Parâmetros identificados (K, τ, Td por DOF)
Ordem fixa do vetor θ (9): `[K_vx, τ_vx, Td_vx, K_vy, τ_vy, Td_vy, K_ω, τ_ω, Td_ω]`.
- [config/ssl_robot.sldd](config/ssl_robot.sldd) — **store canônico** dos 9 params (Simulink Data Dictionary, binário); bounds τ ≥ 0,01 s embutidos. Lido/escrito por `apply_theta`/`load_theta_mat`.
- [models/sysid_vxvy_v2.mat](models/sysid_vxvy_v2.mat) — **θ PROMOVIDO (robusto atual)**: vx{K=1,1192; τ=0,0718; Td=0,0691}, vy{K=1,0524; τ=0,1273; Td=0,0565}, ω **placeholder** {K=1; τ=0,1; Td=0}.
- models/sysid_bayesopt_v2_candidate.mat — calibração comportamental conjunta (proxy + treino amplo); **não promovido**. v1_candidate, omega_v3_linear_candidate, initial_v2_candidate, ideal_v2/v3: outros candidatos/baselines.
- [matlab/sldd/load_theta_mat.m](matlab/sldd/load_theta_mat.m) — carrega θ (struct nomeado) de um `.mat` (`theta0`/`theta_opt`/`theta`).
- [matlab/sldd/apply_theta.m](matlab/sldd/apply_theta.m) — grava θ no SLDD (vetor ou struct).

### 1.3 Código que simula o modelo
- [automation/deadreckoning_p1d.m](automation/deadreckoning_p1d.m) — **referência analítica do replay**: aplica G_i(s) (atraso ZOH → lag 1ª ordem ZOH-exato → ganho K) a cada comando de corpo e integra ao mundo (`cumtrapz`). **É exatamente a planta a portar.**
- [automation/ideal_deadreckoning.m](automation/ideal_deadreckoning.m) — baseline cinemático ideal (caso K=1, τ=0, Td=0).
- [automation/sim_aligned.m](automation/sim_aligned.m) — wrapper do Simulink **fiel** (`parameter_estimation_model_pid_v3`): simula 1 evento e devolve a pose alinhada SE(2). Planta de alta fidelidade para cross-check.
- `scripts/parameter_estimation_model_pid_v3.slx` (+ `.slxc`) — modelo Simulink free-run (TransferFcn θ do SLDD → TransportDelay → rodas[identidade] → rotação → integradores). ~9,5 s/sim (medido).
- [scripts/run_one.m](scripts/run_one.m) / [automation/run_one_mat.m](automation/run_one_mat.m) — drivers de 1 evento no Simulink (só simulam; métrica fica no orquestrador).
- Reconciliação documentada: analítico vs Simulink fecha em < 6 mm no caso ideal (RELATÓRIO §4).

### 1.4 Métricas e avaliação (a portar/reusar)
- [automation/rmse_pos_rebased_se2.m](automation/rmse_pos_rebased_se2.m) — RMSE de posição em janelas por tempo re-ancoradas em **pose completa SE(2)** (θ truth filtrado por movmedian 0,2 s). **Métrica canônica.**
- [automation/rmse_pos_rebased.m](automation/rmse_pos_rebased.m) — variante re-ancorando só translação.
- [automation/rmse_heading_rebased.m](automation/rmse_heading_rebased.m) — RMSE de heading re-ancorado.
- [automation/eval_bayesopt_v2_holdout.m](automation/eval_bayesopt_v2_holdout.m) / [automation/eval_campaign.m](automation/eval_campaign.m) — orquestradores de avaliação multi-horizonte + Wilcoxon.
- [automation/build_event_cache.m](automation/build_event_cache.m) — pré-carrega eventos (canonical_split + load_split) p/ reuso.

### 1.5 Dados, carregamento e ETL
- [automation/canonical_split.m](automation/canonical_split.m) — **mapa real→contrato** (renomeia colunas, seleciona robô/team, alinha pose ao grid de comandos); cache em `build/canonical_splits/`. Documento-fonte do contrato.
- [matlab/simulink_io/load_split.m](matlab/simulink_io/load_split.m) — lê o parquet canônico → struct (timeseries cmd/truth, pos0, t, Tsim); converte mm→m.
- [matlab/simulink_io/list_splits.m](matlab/simulink_io/list_splits.m) — indexa todos os eventos.
- `python/` — leitura de protobuf SSL (`pyrecordio`, `proto/generated/RoboCupSSL.py`, `RCLog.py`) + `kinematics.py`; ETL de `.log.gz` → parquet.
- `data/extracted/<dataset>/...` (DVC) — derivado; `data/recorded/` — logs crus (`.log.gz`, `.csv`, `.mat`); `data/bench/`.

---

## 2. Contrato de dados (logs de competição) — verificado nos arquivos reais

Dataset único extraído hoje: `2026-05-18_19-2-15`. Origem: `scripts/local/logs/2026-05-18_19-2-15.log.gz` (protobuf) → parquet via `python/`.

### 2.1 Estrutura no disco
```
data/extracted/<dataset>/
  commands.parquet, processed_robots.parquet, ball.parquet, telemetry.parquet, referee.parquet, raw_*.parquet   (log inteiro)
  splits/
    all_commands_labeled.parquet, all_processed_robots_labeled.parquet, ...   (concatenado, colunas label/event_id)
    <label>/<event>/{commands,processed_robots,ball,telemetry,referee,raw_*}.parquet   (por evento — fonte do pipeline vigente)
```
Labels: `front_to_back` (4), `side_to_side` (13), `shoot_to_goal` (18), `square` (11) = 46 eventos.

### 2.2 `commands.parquet` (entrada do gêmeo) — colunas exatas
| coluna | tipo | unidade | nota |
|---|---|---|---|
| `timestamp` | double | s | relógio do log (absoluto, ex. 611,66) |
| `timestamp_event` | double | s | **relativo ao início do evento** (começa ~0); é o usado |
| `robot_id` | int64 | — | 1 robô por evento neste dataset |
| `move_x` | double | **m/s** | velocidade comandada — **frame de CORPO**, eixo longitudinal |
| `move_y` | double | **m/s** | velocidade comandada — **frame de CORPO**, eixo lateral |
| `move_w` | double | **rad/s** | velocidade angular comandada (independe de frame) |
| `actuation_kick_strength` | double | — | chute (não usado no gêmeo) |
| `actuation_front/chip/charge/dribbler` | logical | — | atuadores (não usados) |
| `actuation_dribbler_velocity` | double | — | (não usado) |

### 2.3 `processed_robots.parquet` (truth / pose) — colunas exatas
| coluna | tipo | unidade | nota |
|---|---|---|---|
| `timestamp` | double | s | relógio absoluto |
| `timestamp_event` | double | s | relativo ao evento |
| `team` | string | — | só `"allies"` neste dataset |
| `robot_id` | int64 | — | |
| `position_x` | double | **mm** | pose **mundo** (campo) — converter mm→m |
| `position_y` | double | **mm** | pose **mundo** |
| `position_w` | double | **rad** | heading θ no **mundo**; cru pode estar em (−π,π] → **aplicar `unwrap`** |
| `velocity_x` | double | **mm/s** | velocidade **mundo** (visão; ruidosa) |
| `velocity_y` | double | **mm/s** | velocidade **mundo** |
| `velocity_norm` | double | **mm/s** | ‖v‖ |

**Unidades confirmadas** (não confiar nas primeiras linhas — robô parte do repouso): `median |v|` por derivada da posição = 0,279 m/s (máx 3,08) vs `median(velocity_norm)` logado = 206 (máx 2019) ⇒ **velocity_* em mm/s** (consistente com position em mm). O `/1000` do pipeline antigo está correto.

### 2.4 Frame, pose e frequência — respostas diretas
- **Comando de velocidade: frame de CORPO.** `move_x`/`move_y` são velocidades no referencial do robô. Evidência: `build_idData_per_dof.m:97-100` rotaciona a velocidade medida **mundo→corpo** (`vx_r = cosθ·vx_w + sinθ·vy_w`) para casar com o comando; e `deadreckoning_p1d.m:29-31` integra **corpo→mundo** (`x += cosθ·vx − sinθ·vy`). `move_w` é angular (frame-independente).
- **Pose (x,y,θ): frame de MUNDO.** `position_x/y` em mm (campo), `position_w` em rad (heading absoluto), recomendado `unwrap`.
- **Frequência (grade IRREGULAR em ambos os streams):** comandos mediana ~108 Hz mas p10=0,2 ms / p90=29 ms (rajadas); visão mediana ~47 Hz. O pipeline reamostra para **Ts=1/60 s** quando identifica; a métrica de replay usa a grade nativa (janelas por tempo). **Há dois timestamps** — usar sempre `timestamp_event`.
- **Alinhamento atual:** `canonical_split` interpola a pose (linear) **no grid dos comandos** (a entrada dirige a simulação) e descarta amostras fora da sobreposição temporal.

### 2.5 Primeiras linhas (exemplo: `shoot_to_goal/shoot_to_goal_01_01`)
`commands.parquet` (subset relevante):
```
timestamp  robot_id   move_x    move_y     move_w     timestamp_event
 611.66        3      0.80036  0.031070  -0.012523     0.0052717
 611.68        3      0.76055  0.029548  -0.013862     0.0247070
 611.70        3      0.79190  0.031555  -0.010660     0.0412100
 611.70        3      0.74081  0.030060  -0.008103     0.0493000
 611.73        3      0.74842  0.030724  -0.010409     0.0740470
```
`processed_robots.parquet` (subset relevante):
```
timestamp  team     robot_id  position_x  position_y  position_w  velocity_x  velocity_y  velocity_norm  timestamp_event
 611.65   "allies"     3        392.89     -3.5335    0.0051747    0.17441    -0.50406      0.53338       0.00030758
 611.67   "allies"     3        392.85     -3.3962    0.0052647   -0.63090    -0.15263      0.64910       0.01934300
 611.69   "allies"     3        392.94     -3.0710    0.0047442   -0.88704     0.64633      1.09750       0.03622400
```
(`position_x` evolui 392,9 → 2885,5 mm ao longo de ~4,87 s.)

---

## 3. Marcação / recuperação dos segmentos de hold-out

**Não há marcação nos dados.** O hold-out é definido **em código**, de duas formas:
1. **Partição programática por DOF** (identificação): `randperm` com `rng(42)`, fração ~⅓, em `identify_trans_dof.m:48-50` e `identify_omega_v3_linear.m`. Reprodutível pela seed, **não persistida**.
2. **Lista congelada de 10 eventos** (avaliação/bayesopt), hard-coded e **duplicada** em `eval_bayesopt_holdout.m` e `eval_bayesopt_v2_holdout.m`:
   `front_to_back_01_01`; `side_to_side_{01_05,01_06,01_07,02_03}`; `shoot_to_goal_{05_02,08_01,09_01,12_01,14_02}`.
   O conjunto de treino amplo (18 ev) é construído deterministicamente em `run_bayesopt_v2_proxy.m` (`build_train_events`, seed 42) **excluindo** esses 10.

➡️ Para o harness: tratar a **lista de 10 como fonte única da verdade**, materializá-la em um artefato versionado (ex. `phase0_replay/splits.py` ou um `holdout.json`), e derivar treino = todos − hold-out. (Ver ambiguidade #6.)

---

## 4. Proposta: schema canônico em memória + interface `Plant` + layout

### 4.1 `Segment` (contrato em memória, **SI estrito**)
Um segmento = um (dataset, label, event, robot_id) já em SI, numa grade de tempo única.

```
Segment
  meta:     {dataset, label, event, robot_id, team, src_commands, src_robots, dvc_rev}
  t:        float[N]      # s, relativo ao evento, t[0]=0, monotônico, IRREGULAR
  dt:       float[N]      # s, diff(t) com dt[0] convencional (= dt[1])
  # comandos (entrada), frame de CORPO, na grade t (ZOH)
  cmd_vx:   float[N]      # m/s
  cmd_vy:   float[N]      # m/s
  cmd_w:    float[N]      # rad/s
  # truth (referência), frame de MUNDO, na grade t (pose interpolada linear; θ unwrapped)
  pos_x:    float[N]      # m
  pos_y:    float[N]      # m
  theta:    float[N]      # rad (unwrapped)
  # condições iniciais para o Plant.reset
  pose0:    (x0, y0, theta0)             # m, m, rad   = (pos_x[0], pos_y[0], theta[0])
  velb0:    (vx0, vy0, w0)               # m/s, m/s, rad/s, frame de CORPO  (ver ambiguidade #4)
```
Conversões na carga (raw→SI): `position_*` mm→m (÷1000); `velocity_*` mm/s→m/s (÷1000); `position_w` rad + `unwrap`; tempo = `timestamp_event` (s). Validação: t monotônico; sem NaN após interseção temporal; |cmd| e ‖pose‖ em faixas físicas.

### 4.2 Interface abstrata `Plant`
```
Plant (ABC)
  reset(pose0: (x,y,theta), velb0: (vx,vy,w)) -> None
      # zera estado: integradores de pose = pose0; estado do lag (velocidade de corpo)
      # = velb0; buffer de atraso Td preenchido (convenção: comando = 0 antes de t0).
  step(cmd: (vx_cmd, vy_cmd, w_cmd), dt: float) -> pose: (x, y, theta)
      # avança dt segundos: aplica atraso Td (ZOH), lag 1ª ordem ZOH-exato,
      # ganho K por DOF -> velocidade de corpo; integra corpo->mundo; devolve pose nova.
  # propriedades: state (debug), params (K,τ,Td por DOF)
```
Semântica de `step` que **reproduz** `deadreckoning_p1d.m` (a validar por teste-golden):
- atraso: `u_d = cmd(t − Td)`, 0 antes de t0 (ZOH, `interp1 'previous'`);
- lag ZOH-exato: `v[k] = v[k−1] + (1 − e^(−dt/τ))·(u_d − v[k−1])`; `v_corpo = K·v[k]`;
- integração corpo→mundo: `θ += w·dt`; `x += (cosθ·vx − sinθ·vy)·dt`; `y += (sinθ·vx + cosθ·vy)·dt` (esquema de integração: ver ambiguidade #3).

Implementações previstas: `AnalyticFOPDTPlant` (porta de `deadreckoning_p1d`, sem dependência externa) e — opcional — `SimulinkPlant` (adapta `sim_aligned`, alta fidelidade, lento) como oráculo de cross-check.

### 4.3 Layout de pacote
```
phase0_replay/
  __init__.py
  schema.py     # dataclass Segment + validação de unidades/grade
  io.py         # raw parquet (commands+processed_robots) -> Segment  (porta canonical_split+load_split)
  params.py     # carrega θ (K,τ,Td por DOF) de models/*.mat | JSON congelado; ordem do SLDD
  plant.py      # Plant (ABC) + AnalyticFOPDTPlant [+ SimulinkPlant opcional]
  replay.py     # dirige um Plant sobre Segment.cmd -> trajetória simulada
  metrics.py    # RMSE SE(2) re-ancorado multi-h + heading (porta rmse_pos_rebased_se2/heading)
  splits.py     # hold-out congelado (10) + partição treino (seed 42) — fonte única
  cli.py        # argparse: replay de 1 evento / partição -> CSV + figuras
tests/
  conftest.py            # fixtures: 1 segmento pequeno em cache + θ promovido
  test_io_units.py       # unidades/frame: mm→m, mm/s→m/s, corpo vs mundo
  test_schema.py         # validação (t monotônico, sem NaN, faixas)
  test_plant_fopdt.py    # GOLDEN: AnalyticFOPDTPlant ≈ deadreckoning_p1d (tol ~1e-6) e ≈ Simulink (tol ~mm)
  test_metrics.py        # reproduz números de rmse_pos_rebased_se2 num evento conhecido
  test_splits.py         # hold-out e partição determinísticos (seed 42)
```
Regras: read-only sobre `data/` (reusa o cache de eventos); reusa `models/*.mat` e a lista de hold-out; nada de re-simular baselines (cross-check pontual contra os artefatos MATLAB já gravados).

---

## 5. Ambiguidades — preciso da sua decisão

1. **Linguagem do harness.** O idioma "pacote/módulos/tests/" e a planta puramente analítica (`deadreckoning_p1d` é trivial em numpy) sugerem **Python** — recomendo Python (sem licença MATLAB no loop, fácil CI). Mas todo o gêmeo e as métricas vivem em MATLAB. **Python novo** ou **pacote MATLAB** espelhando `automation/`?
2. **θ alvo da validação.** Default = `sysid_vxvy_v2.mat` (promovido: vx/vy v2 + ω placeholder)? Incluir também o `bayesopt_v2_candidate` e o ideal como comparadores no mesmo harness?
3. **Esquema de integração / grade do `step`.** Reproduzir `deadreckoning_p1d` **na grade irregular** (lag ZOH-exato + integração trapezoidal `cumtrapz`) — recomendado, casa com a referência — ou `step` causal com **Euler** e/ou reamostragem a **Ts=1/60**? (Afeta o teste-golden e a fidelidade ~mm.)
4. **Velocidade de corpo inicial (`velb0`) no `reset`.** Derivar da posição (Savitzky-Golay, como o pipeline promovido) — recomendado — vs usar `velocity_x/y` logada (mm/s, mundo→corpo, ruidosa) vs assumir **0**? Impacta o transitório inicial do lag.
5. **Grade de avaliação da pose.** Manter a pose interpolada **no grid dos comandos** (como `canonical_split`) ou avaliar na **grade nativa da visão**? E confirmar a métrica canônica: SE(2) re-ancorado, janelas por tempo, overlap 0,5, h∈{0,5;1;2;2,5;4} s, peso ∝1/h, θ truth filtrado (movmedian 0,2 s).
6. **Hold-out como fonte única.** Posso **congelar** a lista dos 10 eventos num artefato versionado (`holdout.json`/`splits.py`) e desduplicá-la dos scripts MATLAB? Manter seed 42 para qualquer nova partição?
7. **Escopo de robô/dataset.** Confirmar replay **single-robot** (só `allies`, 1 `robot_id` por evento). Haverá **segundo log** (validação cross-log) ou o harness fica no dataset `2026-05-18_19-2-15` por ora?
8. **Localização e papel.** `DESIGN.md` na raiz e `phase0_replay/` como pacote novo ao lado do MATLAB (coexistência), ou dentro de `python/`? O harness **substitui** a avaliação MATLAB ou é um caminho independente de verificação?
9. **Não-linearidades.** Manter o gêmeo **linear puro** (zonas mortas = 0, como o promovido) no harness, ou já prever o gancho de zona morta por roda (firmware 1,567 rad/s) como parâmetro desligado por default?

---

*Próximo passo (após sua revisão): congelar decisões 1–9 e só então implementar `phase0_replay/` + `tests/`, começando pelo teste-golden `AnalyticFOPDTPlant ≈ deadreckoning_p1d`.*
