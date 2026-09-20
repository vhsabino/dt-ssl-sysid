# `tools/external_sims/` — grSim e ER-Force como baselines no harness do gêmeo (C2b)

O harness do artigo (janelas SE(2) re-ancoradas, stride 15, H_max 90, `config/metrics.json`) aceita qualquer
simulador que fale o **ssl-simulation-protocol** como uma `Plant` (`dtssl.sim.protocol_plant.ProtocolPlant`):
por janela, `TeleportRobot` para a pose/velocidade real, comandos de corpo a 60 Hz, poses lidas da visão do
simulador e alinhadas ao relógio da janela. Assim os simuladores da liga (grSim, ODE; ER-Force `simulator-cli`,
Bullet) entram no hold-out **com as mesmas janelas e a mesma métrica** do gêmeo, no papel de "física da liga sem
sintonia" que o rSim tinha no artigo. Os dois rodam no WSL2 (Ubuntu), e a análise roda **dentro do WSL** (multicast
no mesmo host); o resultado é escrito no repo do Windows via `/mnt/c`.

| Arquivo | Para quê | Precisa de sudo? |
|---|---|---|
| `install_grsim_wsl.sh` | clona `RoboCup-SSL/grSim`, instala dependências (Qt 5, ODE, protobuf, boost), compila em `~/grsim/build` (VarTypes e, com protobuf ≥ 3.21 do sistema, o protobuf 3.6.1 são baixados e compilados pelo CMake do grSim); binário em `~/grsim/bin/grSim` | **sim**, só o `apt-get install` (`--no-deps` pula) |
| `install_erforce_wsl.sh` | clona `robotics-erlangen/framework`, instala dependências (Qt 6, protobuf, OpenSSL), compila só o alvo `simulator-cli` (baixa Bullet/Eigen de `downloads.robotics-erlangen.de`) | **sim**, só o `apt-get install` |
| `simctl.sh <sim> start\|stop\|status\|log\|probe` (`run_grsim.sh`, `run_erforce.sh` = atalhos) | sobe o simulador em background (`~/external_sims/<sim>.{log,pid}`), espera as portas 10300/10301, derruba, sonda | não |
| `run_protocol_holdout.sh` | de ponta a ponta: para cada simulador sobe → sonda → `dtssl analysis run protocol_holdout` → derruba; ao final reanalisa os caches dos dois numa tabela só | não |

Config dos endpoints: `config/external_sims.json` (portas, grupo/porta de visão, interface do multicast, time/id do
robô replayado, `vision_rate`, `teleport_omega`, notas de cada simulador). Sonda de um endpoint:
`python -m dtssl.sim.protocol_plant --sim grsim`. Replay de um evento: `dtssl replay side_to_side side_to_side_01_05 --plant proto:grsim`.

## 1. Instalação (uma vez; as etapas com sudo são as únicas que precisam de você)

```bash
# no WSL2 (Ubuntu 26.04 no PC do Victor), dentro do repo: /mnt/c/Users/victo/Documents/digitaltwin
source ~/.venvs/dtssl/bin/activate          # venv com `pip install -e .[dev]` (já existe)
tools/external_sims/install_grsim_wsl.sh    # [sudo] apt + clone + build (~5 min)
tools/external_sims/install_erforce_wsl.sh  # [sudo] apt + clone + build simulator-cli (~10 min; baixa Bullet)
```

Ubuntu 26.04: `qtbase5-dev` 5.15.18 ainda existe (grSim é Qt 5); o CMake 4.x recusa `cmake_minimum_required < 3.5`
dos projetos externos (VarTypes, Bullet 2.83) — os scripts exportam `CMAKE_POLICY_VERSION_MINIMUM=3.5`, a válvula
oficial. Sem rede/sudo os scripts param na etapa 1 com a lista de pacotes para instalar à mão.

Alternativa sem compilar (Linux nativo; no Docker Desktop do Windows o `--net=host` não alcança a distro WSL, então
não serve aqui): `docker run --net=host robocupssl/grsim` (headless) e
`docker run --net=host -e GEOMETRY=2020B -e REALISM=None roboticserlangen/simulatorcli`.

## 2. Sanidade (sem sudo, 1–2 min por simulador)

```bash
tools/external_sims/run_grsim.sh start      # headless (-platform offscreen); portas 10020/10300-10302
tools/external_sims/run_grsim.sh probe      # teleporte + 1 janela de 1 s a 0,5 m/s: window_ok=true (grSim: moved ~0,43 m, parte do repouso)
tools/external_sims/run_grsim.sh stop
tools/external_sims/run_erforce.sh start    # simulator-cli -g 2020B --realism None
tools/external_sims/run_erforce.sh probe
tools/external_sims/run_erforce.sh stop
tools/external_sims/run_protocol_holdout.sh --sims grsim,erforce --smoke --out /tmp/c2b_smoke   # 1 evento por simulador (~2 min cada): valida o ambiente inteiro
```

A sonda imprime as estatísticas do replay (`stats`): período de visão medido, latência teleporte→visão, `tau0`,
jitter de envio, falhas de âncora. Os dois simuladores usam as mesmas portas: um de cada vez. O `--smoke`
(`max_events=1`) escreve um artefato marcado "TESTE DE FUMACA" que nunca vale como resultado; use `--out` fora de
`results/`.

Validado na nuvem (Ubuntu 24.04, 10/09/2026): `install_grsim_wsl.sh` compila e o grSim headless responde à sonda e
ao `run_protocol_holdout.sh --smoke` (27 janelas, 0 perdidas, jitter médio 0,01 ms); o `install_erforce_wsl.sh`
configura o alvo `simulator-cli` (apt + cmake OK) mas o build só termina onde `robotics-erlangen.de` é alcançável
(Bullet/Eigen/protobuf baixados pelo CMake) — no WSL do PC.

## 3. O experimento (C2b)

```bash
tools/external_sims/run_protocol_holdout.sh                  # grsim e erforce, delay=both, repeat=1 (~35 min)
tools/external_sims/run_protocol_holdout.sh --sims grsim --repeat 2     # repetibilidade (~32 min)
# equivalente manual, com o simulador de pé:
dtssl analysis run protocol_holdout --kw sims=grsim delay=both repeat=1
dtssl analysis run protocol_holdout --kw from_cache=results/_cache_protocol_grsim_*.npz,results/_cache_protocol_erforce_*.npz
```

### 3.1 C2b2: pré-rolagem (pré-registro `docs/PREREGISTRO_C2B2_PREROLAGEM_20260916.md`)

```bash
tools/external_sims/run_protocol_holdout.sh --delay none --preroll 0.5          # grsim, grsim+preroll, erforce, erforce+preroll (~40 min)
tools/external_sims/run_protocol_holdout.sh --sims grsim --smoke --preroll 0.5 --out /tmp/c2b2_smoke   # fumaça (~3 min), NAO e resultado
# equivalente manual, com o simulador de pé:
dtssl analysis run protocol_holdout --kw sims=grsim delay=none preroll=0.5
```

`+preroll`: teleporte P amostras antes de t0, prefixo real de comandos transmitido, trajetória re-ancorada em t0
(§4: a condição inicial deixa de ser imposta pelo teleporte). Caches `_cache_protocol_<sim>[_delay][_preroll]_<stamp>.npz`;
o `.stats.json` guarda `pre_roll_s`, e o `from_cache` mescla variantes cruas e com pré-rolagem numa tabela só.

Saída: `results/protocol_holdout_<stamp>.{md,json,csv}` (tabelas de `e_pos`/`e_ang` por horizonte, por evento em
`h_ref` com Wilcoxon/rank-biserial, diagnóstico do replay, repetibilidade, custo) e os rollouts de cada variante em
`results/_cache_protocol_<sim>[_delay]_<stamp>[_r<k>].npz` + `.stats.json` (ignorados pelo git; `from_cache`
reanalisa offline, sem simulador). Depois: entrada no `results/CHANGELOG.md` e commit dos `.md/.json/.csv` no Windows.

## 4. O que cada simulador faz com o teleporte (lido no código-fonte, 10/09/2026)

| | `dtssl serve` | grSim (`sslworld.cpp: processTeleportRobot`) | ER-Force (`simrobot.cpp`) |
|---|---|---|---|
| pose | aplicada | aplicada | aplicada |
| velocidade linear inicial | aplicada (estado FOPDT) | **ignorada**: `resetRobot()` zera o corpo e `setSpeed(vx,vy,vw)` vira setpoint dos motores (limitado pela aceleração) — toda janela parte do repouso | aplicada (`setLinearVelocity`) |
| velocidade de guinada inicial | aplicada | ignorada (idem) | aplicada **no eixo x** do Bullet (bug) → `teleport_omega=false` no endpoint: enviamos 0 |
| visão | 60 Hz, sem atraso | 60 Hz (ODE 60 Hz), sem ruído por default | 66,67 Hz, atraso 35 ms + 5 ms em todo perfil de realismo (`None` = sem ruído, `command_delay` 0); robô para 0,1 s sem comando |
| robô | FOPDT θ oficial | perfil `config/Parsian.ini` (default): R 0,09 m, r 0,027 m, a_max 4 m/s², v_max 5 m/s | especificação ER-Force default (`robotSetDefault`), 11 robôs por time |

Por isso o artefato traz a coluna `fopdt_v0=0` (o gêmeo com os estados zerados em t0, a mesma desvantagem do
grSim): separa "física da liga vs FOPDT" de "condição inicial". A pré-rolagem (§3.1) é o outro caminho: em vez de impor a
condição inicial, deixa o simulador chegar a t0 pela sua própria dinâmica sob o prefixo real de comandos. O alinhamento por âncora (primeiro quadro em que o
teleporte aparece + `tau0` pela projeção do deslocamento em v0) remove o atraso de visão, não o de comando.
