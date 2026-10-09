# SPEC — `dtssl`: Gêmeo Digital do Robô SSL (RobôCIn v2025)

*Contrato de arquitetura da refatoração de 02/09/2026. Todo módulo novo segue este documento; conflitos entre código e SPEC resolvem-se atualizando o SPEC de forma explícita (registrar em `results/CHANGELOG.md`). Idioma: docs em PT-BR; código, identificadores, docstrings e commits em EN.*

## 0. Decisões fechadas (02/09/2026, Victor)

| # | Decisão | Consequência |
|---|---|---|
| D1 | Plataforma: **Python + MuJoCo** | núcleo `dtssl` puro-Python; MuJoCo como backend físico opcional (`pip install mujoco`); Isaac Sim adiado (MJCF/URDF importável depois) |
| D2 | ssl-unification roda no **WSL2 Ubuntu**; gêmeo/joystick no Windows ou no WSL | rede: unicast/multicast em `lo` dentro do WSL, ou unicast para o IP do WSL a partir do Windows; tudo configurável |
| D3 | Camada física: **rota (a)** (FOPDT dirige o ego; engine só contato/bola) entregue funcional + **rota (b)** (rodas+roletes+motores) como backend experimental no mesmo harness | dois MJCF; mesma interface `World` |
| D4 | Git: branch `refactor/dtssl`, commits atômicos por etapa, **sem push** | legado arquivado com tag; lixo removido |
| D5 | Interface: **PySide6 + pyqtgraph** | app desktop; joystick via `pygame` (SDL2) |
| D6 | `ssl-unification`: só `config/local` + script de build no WSL2; **nenhuma alteração em C++** | joystick PS5 vive no gêmeo (modo Debug) |
| D7 | Literatura: 20 PDFs da SLR + 3 novos (Schoenbach 2025, Han 2025, Wan 2026) | ADR-001 cita apenas esses |

## 1. Objetivo

Um gêmeo digital **comportamental** (publicado: FOPDT por DOF identificado de logs) do robô SSL omnidirecional de 4 rodas, que:
1. seja **drop-in do grSim/ER-Force** para o `ssl-unification` (fala o *ssl-simulation-protocol*), sem alterar o software de estratégia;
2. tenha uma **interface completa** (campo, robôs, bola, trajetórias, telemetria cmd×estado, editor de θ, seleção de backend) com **modo Debug** teleoperado por DualSense (PS5) em velocidade de corpo;
3. mantenha o **harness científico** (replay free-run vs verdade dos logs, métrica SE(2) multi-horizonte, gates estatísticos) reproduzível por um comando por afirmação do artigo;
4. permita trocar a planta comportamental por um backend **físico MuJoCo** (rota a agora, rota b experimental) sob a mesma API e as mesmas métricas.

Fora de escopo nesta rodada: RL, Isaac Sim, multi-câmera/ruído de visão realista (gancho previsto), árbitro completo (usar `CustomRef` no ssl-unification), robôs reais.

## 2. Layout final do repositório

```
digitaltwin/
├── pyproject.toml            # name="dtssl"; python>=3.10; extras: gui, mujoco, rsim, etl, dev
├── README.md                 # novo (visão geral, instalação, comandos)
├── CLAUDE.md                 # reescrito (estado real; ω promovido; guardrails)
├── config/
│   ├── twin_params.json      # θ oficial (INALTERADO; ordem fixa)
│   ├── metrics.json          # métrica canônica (INALTERADO)
│   ├── holdout_events.json   # hold-out congelado (INALTERADO)
│   ├── robot_geometry.json   # + wheel_angles_deg, proveniência corrigida
│   ├── robot_limits.json     # NOVO: v_max, w_max, a_max, kick, dribbler, watchdog
│   ├── field_divB.json       # NOVO: geometria do campo (mm) = defaults do ssl-unification (Divisão B, default; robots_per_team 6)
│   ├── field_divA.json       # geometria da Divisão A (12 x 9 m, gol 1,8 m, área 3,6 x 1,8 m; robots_per_team 11), mesmo esquema; presets em dtssl.config.load_field_preset
│   ├── bridge.json           # NOVO: portas/IPs/interface/rates do servidor
│   ├── external_sims.json    # NOVO (C2b): endpoints de simuladores externos via ssl-simulation-protocol (dtssl, grsim, erforce)
│   └── ssl_robot.sldd        # SLDD (MATLAB; mantido)
├── src/dtssl/                # pacote instalável (src-layout)
│   ├── __init__.py  paths.py  config.py  units.py  geometry.py  kinematics.py  cli.py
│   ├── data/      schema.py resample.py loader.py validate.py splits.py recordio.py extract.py rotate.py  _proto/ (RCLog betterproto)
│   ├── models/    params.py base.py fopdt.py ideal.py constvel.py rsim.py
│   ├── sim/       entities.py ball.py world.py rollout.py backends.py world_plant.py protocol_plant.py preroll.py
│   ├── eval/      metrics.py stats.py verdict.py report.py
│   ├── analysis/  common.py + um módulo por script do artigo (run(root, out) + main())
│   ├── bridge/    proto/ (pb2 gerados + .proto fonte + build_proto.py; inclui rc_communication.proto do rádio) vision.py control.py simcontrol.py server.py fake_strategy.py recorder.py telemetry.py
│   ├── gui/       app.py field_view.py view3d.py scene3d.py glmesh.py glshading.py robot_tab.py robot_view3d.py plots.py params_panel.py joystick.py controller.py
│   └── physics/   mjcf.py mujoco_world.py assets/ (meshes opcionais) 
├── phase0_replay/            # SHIM de compatibilidade (reexporta dtssl; permite unpickle do cache antigo); remover em v2
├── matlab/
│   ├── bootstrap_paths.m     # inclui matlab/dtssl e matlab/legacy quando pedido
│   ├── dtssl/                # VIVO: identify_trans_dof, identify_omega_rotate, eval_omega_v3_se2, check_excitation_trans, deadreckoning_p1d, ideal_deadreckoning, rmse_pos_rebased(_se2), rmse_heading_rebased, export_plant_golden, export_resample_reference, load_theta_mat, apply_theta, list_splits, load_split, canonical_split, run_one_mat, sim_aligned
│   └── legacy/               # ARQUIVADO com README: bayesopt/proxy/campanhas de junho, sysid antigo, optimization (PSO), train, viewer, ros_bridge, analytical (kinematicSolver etc.)
├── simulink/parameter_estimation_model_pid_v3.slx   # único modelo mantido (oráculo); demais → _to_delete/
├── tests/                    # pytest; marcadores requires_data / requires_mujoco / requires_gui / requires_net
├── tools/
│   ├── make_release.py       # gera pacote anonimizado (substitui open-source/)
│   ├── apply_refactor.sh     # (gerado) aplica moves/deletes no PC do Victor
│   ├── ssl_unification/      # build_wsl2.sh, make_local_config.py (config/local do ssl-unification apontando ao gêmeo)
│   └── external_sims/        # install_{grsim,erforce}_wsl.sh, simctl.sh, run_protocol_holdout.sh (grSim/ER-Force no harness, C2b)
├── assets/ cad/ (STEP) usd/ (Isaac, quebrado — mantido como fonte para meshes)
├── data/ (DVC)  models/ (.mat)  results/  docs/  latex/  slr/  notebooks/ (docs executáveis → dtssl.data.extract)
└── legacy/                   # archive/ antigo (rl TD3, viewers, tests) + open-source/ congelado (README explica) 
```

Removidos (movidos para `_to_delete/`, gitignored, no PC): `tree.txt`, `gitignore.txt`, `reorganize.ps1`, `scripts/.vscode/`, `*.asv`, `scripts/rl_model.slx.original`, `latex/main.aux`, `latex/main.log`, `results/bo_run_v1.log`, `src/` antigo (vazio), `config/task`, `config/train`, `scripts/cluster/`, `matlab/simulink_io/kinematics.m`, `scripts/test.m`, `python/utils/utils/auto_generate_proto.py`, `archive/bus_conv_fcns_legacy/`, `simulink/{pid,pid_v2,with_ros,with_ros_v2}.slx`, `requirements.txt` da raiz, `results/_BROKEN_*` (incidente registrado no CHANGELOG), `NVIDIA Corporation/`, `slprj/`, `build/`, `_claude_*.tar.gz`, `test_world.usd` (→ `usd/`).

## 3. Convenções físicas (obrigatórias em todo o código)

| Item | Convenção |
|---|---|
| Unidades internas | **SI**: m, s, rad, kg. Conversão para mm/graus só na borda (visão SSL, logs, Notion). |
| Frame de **mundo** (= ssl-vision) | origem no centro do campo; +x para o gol direito (do ponto de vista da TV); +y "para cima" (CCW); θ = heading CCW a partir de +x, em (−π, π]; usar `unwrap` para integrar. |
| Frame de **corpo** | x para a frente (dribbler), y para a esquerda, ω CCW. `v_world = R(θ)·v_body`, `R(θ)=[[c,−s],[s,c]]`. |
| Comando de velocidade | `BodyCmd(vx, vy, w)` = `RobotControl.local_velocity(forward, left, angular)` = colunas `move_x, move_y, move_w` dos logs. Nunca velocidades de roda na API pública. |
| Grade de tempo | `Ts = 1/60 s` (visão, comandos ZOH, planta); substeps internos ≤ 1/600 s para bola/contato. |
| θ (9) | ordem `[K_vx, tau_vx, Td_vx, K_vy, tau_vy, Td_vy, K_w, tau_w, Td_w]` (`config/twin_params.json:order`) — **nunca alterar**. |
| Geometria | `R = 0.079601 m` (centro→contato da roda), `r = 0.029492 m`, ângulos das rodas `φ = [60, 135, 225, 300]°` medidos do +x do corpo (CCW), sentido positivo da roda = tangente CCW. `ω_i·r = −sin φ_i·vx + cos φ_i·vy + R·ω`. Raio do corpo 0.090 m, dribbler a 0.075 m do centro (ssl-unification `Env.h`). |
| Zona morta | por roda `1.567 rad/s` (firmware) ⇒ corpo ≈ 0.58–0.60 rad/s; **desligada por default** na planta (modelo linear publicado); disponível como opção `deadzone_wheel_rad_s`. |
| Limites (`robot_limits.json`) | `v_max=3.0 m/s` (SLDD), `w_max=10.0 rad/s` (SLDD), `a_max=null` (sem limite; opcional 4.5 m/s²), `kick_flat_max=6.5`, `kick_chip_max=6.0 m/s`, `chip_angle_deg=45`, `dribbler_rpm_max=6000`, `watchdog_s=0.3`. |
| Bola | raio 0.0215 m (protocolo usa 22 mm), massa 0.046 kg; desaceleração 2 fases: deslizando −1.82135 m/s², rolando −0.3025 m/s² (ssl-unification `Env.h`), transição em `v < 0.6·v_kick` ou por tempo (documentar); chip: balística com g=9.81, quique e=0.5 (parametrizável). |
| Campo Div B (`field_divB.json`, mm) | length 9000, width 6000, goal_width 1000, goal_depth 180, boundary_width 300, penalty_area_depth 1000, penalty_area_width 2000, goal_center_to_penalty_mark 6000, center_circle_radius 500, line_thickness 10; `robots_per_team` 6 (lido pela GUI/CLI, não pela `FieldGeometry`). |
| Campo Div A (`field_divA.json`, mm) | length 12000, width 9000, goal_width 1800, goal_depth 180, boundary_width 300 (as regras dão 0,3 m nas laterais e 0,6 m atrás dos gols; o pacote de geometria só tem um `boundary_width`), penalty_area_depth 1800, penalty_area_width 3600, goal_center_to_penalty_mark 8000, center_circle_radius 500, line_thickness 10; `robots_per_team` 11. Presets: `dtssl.config.FIELD_PRESETS` (`divB` default, `divA`), `load_field_preset(nome | caminho JSON) -> FieldPreset(name, label, path, field, robots_per_team)`, `field_presets()`. |
| IDs/cores | `robot_id ∈ [0,15]`; `team ∈ {"blue","yellow"}`; porta de controle 10301 = blue, 10302 = yellow. |

## 4. Interfaces (assinaturas obrigatórias)

### 4.1 `dtssl.models`
```python
@dataclass(frozen=True)
class DofParam: K: float; tau: float; Td: float; placeholder: bool = False

def load_twin_params(path: Path | None = None) -> dict[str, DofParam]   # chaves "vx","vy","w"
def theta_to_vector(p: dict[str, DofParam]) -> np.ndarray               # ordem oficial
def theta_from_vector(v) -> dict[str, DofParam]

class Plant(ABC):                              # planta de UM robô (frame de corpo → pose no mundo)
    def reset(self, pose0: Pose, velb0: Vel = (0,0,0)) -> None
    def prime_delay(self, prev_cmds: Sequence[Vel]) -> None       # comandos ANTES de t0 (buffer de Td)
    def step(self, cmd: Vel, dt: float) -> Pose                   # avança dt; devolve pose nova (x, y, theta unwrapped)
    @property pose -> Pose;  body_velocity -> Vel;  params -> dict[str, DofParam] | None
    # opcional: state() -> dict (debug), copy()
class AnalyticFOPDTPlant(Plant)   # porta fiel de deadreckoning_p1d.m (atraso ZOH inteiro ⌈Td/dt⌉, lag ZOH-exato, ganho, trapézio)
class IdealKinematicPlant(Plant)  # K=1, τ=0, Td=0
class ConstantVelocityPlant(Plant)
class RSimReplay(Plant)           # import lazy de robosim
```
Semântica de `step` = `phase0_replay/plant.py` atual (**bit-a-bit**: goldens existentes devem continuar passando com o θ que os gerou).

### 4.2 `dtssl.sim` — mundo multi-entidade (usado por bridge, GUI e physics)
```python
@dataclass class RobotCmd: vx: float=0; vy: float=0; w: float=0; kick_speed: float=0; kick_angle_deg: float=0; dribbler_rpm: float=0; t_recv: float=0
@dataclass class RobotState: team: str; id: int; x: float; y: float; theta: float; vx_b: float; vy_b: float; w: float; has_ball: bool; present: bool=True
@dataclass class BallState: x: float; y: float; z: float; vx: float; vy: float; vz: float
@dataclass class WorldState: t: float; frame: int; robots: dict[tuple[str,int], RobotState]; ball: BallState

class World(ABC):
    def reset(self, scene: Scene) -> None                       # Scene: lista de robôs (team,id,pose0) + bola + campo
    def set_command(self, team: str, rid: int, cmd: RobotCmd) -> None
    def step(self, dt: float) -> WorldState                     # dt = Ts; substeps internos
    def state(self) -> WorldState
    def teleport_robot(self, team, rid, x, y, theta, present=True) -> None
    def teleport_ball(self, x, y, vx=0, vy=0, z=0, vz=0) -> None
    @property field -> FieldGeometry
    # ganchos opcionais do harness (TwinWorld e MuJoCoWorld os implementam; ver dtssl.sim.world_plant):
    def set_robot_state(self, team, rid, x, y, theta, vx_b=0, vy_b=0, w=0) -> None   # CI: pose + velocidade de CORPO
    def prime_robot_delay(self, team, rid, prev_cmds) -> None                       # buffer de atraso (rota a / fopdt)
    def robot_pose(self, team, rid) -> tuple[float, float, float]                    # pose direto do backend (θ contínuo quando possível)
class TwinWorld(World)            # backend "fopdt"/"ideal": um Plant por robô + ball.py + colisões círculo-círculo, paredes da arena (boundary) e gols (traves, laterais e fundo, goals; collisions.goal_segments) + kick/dribbler + watchdog;
                                  #   robôs não presentes ficam estacionados fora das paredes (entities.park_spot: além da parede em -y, cada time no seu lado, por id), sem física e sem visão;
                                  #   Scene.default(n_blue, n_yellow, field_length_m, field_width_m, n_active, boundary_width_m): elenco de 11 por time (ROSTER_SIZE); n_active em campo (GUI/CLI: robots_per_team do preset de campo, 6 na Div B e 11 na Div A, ou --n-active), o resto estacionado
class WorldPlant(Plant)           # dtssl.sim.world_plant: um World de 1 robô visto como Plant do harness (reset/prime_delay/step);
                                  #   make_harness_plant("fopdt"|"ideal"|"mujoco-velocity"|"mujoco-rollers"|"mujoco-rollers-delay"|"world:<backend>"|"proto:<sim>[+delay]"; qualquer um deles "+preroll")
class ProtocolPlant(Plant)        # dtssl.sim.protocol_plant: simulador EXTERNO via ssl-simulation-protocol (grSim, ER-Force, dtssl serve) como Plant; pre_roll=S (s) = prefixo real antes da janela + re-ancoragem em t0
class PreRollPlant                # dtssl.sim.preroll: o mesmo procedimento em processo para qualquer Plant (referência do auto-teste e coluna de controle fopdt+preroll)
                                  #   do harness; Endpoint de config/external_sims.json; free_run_window(win_cmds, pose0, velb0, dt, prev_cmds)
                                  #   (gancho em lote de free_run: teleporte + comandos a dt de parede + visão alinhada por âncora/tau0);
                                  #   delay=None | "theta" (Td do θ oficial aplicado no envio); stats (ProtocolStats) para o artefato
```
Backends registrados em `dtssl.sim.backends`: `"fopdt"` (default, θ oficial), `"ideal"`, `"mujoco-velocity"` (rota a), `"mujoco-rollers"` (rota b). `make_world(name, **opts) -> World`.
Qualquer backend pode ser avaliado no harness do artigo (mesmas janelas re-ancoradas, mesma métrica) via `WorldPlant`; `mujoco-rollers-delay` = rota b + atraso de transporte `Td` por DOF do θ oficial aplicado ao comando (análogo da ablação de atraso do rSim).
Simuladores externos entram pelo mesmo caminho via `ProtocolPlant` (`proto:grsim`, `proto:erforce+delay`; `dtssl analysis run protocol_holdout`): `free_run` usa `plant.free_run_window` quando a planta o oferece (janela inteira em lote, tempo real), senão o `reset/prime_delay/step` de sempre. Janelas que o simulador não reproduziu (teleporte não visto) voltam como NaN e são excluídas e contadas pela análise. O que cada simulador faz com a velocidade do teleporte (grSim: ignora, parte do repouso; ER-Force: só a linear) está em `config/external_sims.json` e em `tools/external_sims/README.md`. A pré-rolagem (`+preroll`, `dtssl.sim.preroll`, C2b2) remove essa desvantagem sem tocar no simulador: teleporte P amostras antes de t0, prefixo real de comandos transmitido, trajetória re-ancorada em SE(2) em t0; `pre_roll=0` é o comportamento anterior bit a bit.

### 4.3 `dtssl.sim.rollout` e `dtssl.eval` — mantêm as assinaturas atuais de `phase0_replay.rollout/metrics` (`free_run`, `rollout_segment`, `Window`, `WindowRollout`, `build_error_table`, `evaluate`, `make_figures`, `markdown_report`), com dois consertos: `rollout_segment` deriva `idx_min` da planta passada (não do JSON) e `build_error_table` recebe `robot_radius`/`params` explicitamente. Cache de rollouts serializado em `.npz` (não pickle).

### 4.4 `dtssl.bridge` — ssl-simulation-protocol (drop-in do grSim)
- **Visão**: `SSL_WrapperPacket` UDP para `bridge.json: vision.ip (224.5.23.2) : vision.port (10006 default do ssl-unification develop; 10020 no código)`; `multicast_if` (default `127.0.0.1`), `IP_MULTICAST_LOOP=1`, `TTL=1`; alternativa `unicast_targets=[...]`. `detection` a 60 Hz com `frame_number` contíguo, `t_capture=t_sent=time.time()`, `camera_id=0`, bolas/robôs em **mm** e `orientation` em rad wrap (−π,π], `confidence=1.0`, `pixel_x=pixel_y=0`. `geometry` **obrigatória**: enviada em todo N-ésimo frame (`geometry_every=60`) e no primeiro frame; campos do campo do mundo (`field_divB.json` por default; `--field divA` ou o seletor da GUI publicam a Divisão A) (+ `field_lines`/`field_arcs` opcionais).
- **Controle**: sockets UDP `0.0.0.0:10301` (blue) e `0.0.0.0:10302` (yellow) (configuráveis); parse `RobotControl`; para cada `robot_commands[i]`: `local_velocity` → `RobotCmd` (frame de corpo); `global_velocity` → converter com θ atual; `wheel_velocity` → `kinematics.wheels_to_body`; `kick_speed`, `kick_angle`, `dribbler_speed`; **responder a cada datagrama** com `RobotControlResponse{feedback[]{id, dribbler_ball_contact}}` para `(addr, port)` de origem. **Watchdog** 0.3 s → comando zero.
- **SimulatorCommand** em `0.0.0.0:10300`: `control.teleport_ball` / `teleport_robot` (m, m/s, rad; `present`), `simulation_speed` (aceita, aplica se ≤ 10×); responder `SimulatorResponse` vazio.
- **Loop**: `SimServer.run()` em tempo real (relógio monotônico, 60 Hz, compensando jitter) ou `step_mode=True` (avança sob demanda: testes/GUI). Thread-safe: comandos chegam em thread de rede e são consumidos no tick.
- **`fake_strategy.py`**: cliente Python que emula o ssl-unification (recebe visão, envia `RobotControl` de um GoToPoint simples, valida `RobotControlResponse`) — usado em testes `requires_net` (loopback) e como demo.
- **`recorder.py`**: grava a sessão em parquet no **mesmo contrato** dos logs (`commands.parquet`: `timestamp, timestamp_event, robot_id, move_x, move_y, move_w`; `processed_robots.parquet`: `timestamp, timestamp_event, team, robot_id, position_x/y (mm), position_w (rad), velocity_x/y (mm/s), velocity_norm`) para o harness avaliar sessões do próprio gêmeo.
- Protos: copiar de `ssl-unification/libs/protobufs/include/protobufs/pb/proto/` os `ssl_vision_*.proto`, `ssl_simulation_*.proto`, `ssl_gc_*.proto` (dependências), gerar `*_pb2.py` com `grpcio-tools`/`protoc` via `bridge/proto/build_proto.py`; **versionar os `_pb2.py` gerados** (usuário não precisa de protoc).

### 4.5 `dtssl.gui` (PySide6 + pyqtgraph)
- `dtssl gui` abre `MainWindow` com: **FieldSelector** (combo `Div B`/`Div A` na toolbar, `--field divB|divA|FILE` na linha de comando: reconstrói o mundo na geometria escolhida com os robôs por time da divisão em campo, 6 na B e 11 na A (`--n-active` fixa outro número) e o resto do elenco de 11 no banco; vale nos modos Debug e Bridge (o servidor é reiniciado e publica a nova geometria); no Replay fica desabilitado e o campo desenhado é sempre o da Divisão B, onde os eventos foram gravados), **FieldView** (campo em escala, robôs por cor/id com heading e dribbler, bola, rastro sim (e verdade, no Replay), clique = teleporte; reservas estacionadas fora das paredes em meio-tom; Shift+clique no campo = entra o próximo reserva do time selecionado ali, Shift+clique num robô = ele sai para fora do campo), **Plots** (por DOF: cmd vs velocidade de corpo; e_pos(t) no Replay), **ParamsPanel** (K, τ, Td por DOF editáveis com bounds do SLDD; presets `oficial`, `placeholder ω`, `ideal`; carregar/salvar JSON; aplica sem reiniciar), **BackendSelector** (`fopdt`, `ideal`, `mujoco-velocity`, `mujoco-rollers`), **Status** (Hz real, pacotes/s por porta, watchdog, joystick conectado); **View3D** (aba 3D, `pyqtgraph.opengl`: campo, bola e robôs com as malhas do CAD de `physics/assets`, rodas girando pela cinemática inversa, placa SSL, presets de câmera/follow e duas câmeras presas ao robô selecionado, terceira pessoa (`Chase`, tecla `3`: atrás e acima, seguindo o rumo com atraso de primeira ordem, mouse orbita e dá zoom) e primeira pessoa (`FPV`, tecla `1`: sobre a tampa acima do dribbler, olhando à frente, mouse vira a cabeça), `scene3d.RobotCamera`; construída do `WorldState`, logo válida para todo backend; malhas com sombreamento suave por grupos de suavização (`scene3d.smooth_mesh`) e cada robô em dois itens GL, corpo (`scene3d.body_mesh`: chassi + chute + dribbler + placa) e rodas instanciadas (`gui/glmesh.py`), para o campo da Divisão A ficar acima de 60 Hz; `--no-3d`/`--no-cad`); **RobotTab** (aba Robot: o robô selecionado em destaque com telemetria: em 3D (`RobotView3D`: CAD girável em qualquer eixo por arcball, rodas girando e coloridas pela velocidade do registro, bola, setas de velocidade; ou o spotlight 2D), seletor de robô na própria aba (os dois times), rodas pela cinemática inversa, comando × resultante, idade do comando/watchdog, sensor de bola, bateria e capacitor de um modelo *ilustrativo* rotulado; com `--telemetry` lê o `RCCommunication.Feedback` dos robôs reais pelo rádio (`bridge/telemetry.py`, `config/telemetry.json`) e mostra os valores reais ao lado; `--no-robot-tab`).
- **Modos**: `Debug` (joystick → `RobotCmd` do robô selecionado; servidor de protocolo pode ficar ligado ou não), `Bridge` (servidor ligado; ssl-unification manda; GUI só observa e permite teleporte/params), `Replay` (carrega evento do dataset, roda free-run com a planta atual vs verdade; mostra e_pos por horizonte).
- **Joystick** (`gui/joystick.py`, `pygame`): DualSense via SDL GameController (`pygame.joystick`; mapear por nome "DualSense"/"PS5"); eixos: `LY → vx = −LY·v_max`, `LX → vy = −LX·v_max`, `RX → w = −RX·w_max`; deadzone radial 0.08 + curva expo 0.3; `R2` turbo (escala 1.0 vs 0.5), `✕` chute reto (`kick_flat_max`), `○` chip, `R1` liga/desliga dribbler, D-pad ←/→ troca robô, `Options` teleporta ao centro, `PS`/`Share` para/zera. Loop de leitura a 120 Hz em `QTimer`; sem joystick, fallback WASD/QE no teclado. Publicar também (opcional) o comando por `RobotControl` UDP para permitir teleoperar um simulador externo (grSim) com a mesma mão.

### 4.6 `dtssl.physics` (MuJoCo)
- `mjcf.py`: gera XML programaticamente a partir de `geometry.py` + o preset de campo (`field_divB.json` por default, `field_divA.json` com `fld=`/`--field divA`) (+ opcional meshes de `assets/`): chão (plano, `condim=3`, μ=0.9), linhas (sites visuais), paredes (boundary), gols; bola (`sphere` r=0.0215, m=0.046, `condim=6`, μ_roll pequeno); robôs. Opção `visual="primitive"|"cad"` (builder, `MuJoCoWorld`, `dtssl mjcf --visual`): com `cad`, as quatro malhas do CAD RobôCIn v2025 (`assets/ssl_chassis.obj`, `ssl_wheel.obj`, `ssl_kicker.obj`, `ssl_dribbler.obj` + pares `_lod` e `.mtl`, tesseladas com as cores das aparências do Inventor a partir da montagem principal `robot_v2025_v3.iam` por `tools/inventor_export_cad.m` (API COM; os pares `_lod` das vistas 3D da GUI por `tools/cad_lod.m`, só as peças vistas de fora, orçamento de faces por área visível) e registradas em `meshes.json` por `tools/register_cad_meshes.py`) entram como geoms só visuais (`contype=conaffinity=0`, `mass=0`), um geom por cor (`cad_submeshes`: 45 geoms e 30 assets por robô), e as primitivas ficam ocultas (`group=3`); a placa de id fica no plano do decalque do padrão (`cad_plate_z`, 148,7 mm acima do piso); a física é idêntica nos dois modos (mesmos corpos, juntas, geoms de colisão, inércias e atuadores, testado bit a bit). Opção `dribbler="spring"|"bar"` (builder, `MuJoCoWorld`, `dtssl mjcf --dribbler`): `spring` (default) é a força de atração fraca de sempre; `bar` constrói o mecanismo do CAD (`DribblerOptions`, `mouth_fragment`, `dribbler_fragment`): barra como cápsula numa dobradiça com atuador `velocity` (rpm do comando, limite `dribbler_rpm_max`), montada num slide com mola e amortecedor (batente `engage` além do contato com a bola na placa), dentro de uma boca (fundo, bochechas até a borda das placas laterais, placa do chip) que é a única parte do robô que a bola toca (`BIT_MOUTH`); a bola é segurada só por atrito (retro-giro pela barra, atrito do piso `mu_slide` identificado) e a ação centralizadora da rosca da barra entra como força lateral `helix` no mundo. Parâmetros do módulo e da barra são placeholders (docstring); `MuJoCoWorld.dribbler_state(team, id)` devolve velocidade da barra, posição do slide e contato.
  - **Rota (a) `mujoco-velocity`**: chassi = cilindro r=0.09 h=0.15 m=2.4 kg em `slide x + slide y + hinge z` com atuadores `velocity` de ganho alto (`kv`), cujo alvo é `R(θ)·v_body` vindo da `AnalyticFOPDTPlant` (a planta comportamental **é** a dinâmica do ego; o engine impõe contato com bola/robôs/paredes). Kick = impulso na bola quando na região do dribbler; dribbler = força de atração fraca.
  - **Rota (b) `mujoco-rollers`**: chassi + 4 rodas (`hinge`, eixo tangencial em φ_i, r=0.029492) cada uma com `N` roletes (default 12; `hinge` livre, `cylinder`/`capsule` suave, μ≈1.0) — receita de Wan et al. 2026: `solver=Newton`, `cone=elliptic`, `impratio=10`, `noslip_iterations=1`, `timestep=0.002` (mínimo 1/600); atuadores `motor` por roda com PI de velocidade (Kp=0.3194, Ki=6.434 do firmware, opcional) ou `velocity` (`kv`), zona morta 1.567 rad/s opcional; cinemática inversa de `kinematics.py`.
- `mujoco_world.py`: `MuJoCoWorld(World)` para ambas as rotas; `step(dt)` faz `n_sub = round(dt/model.opt.timestep)` substeps; expõe `mj_model/mj_data` para viewer; `render_offscreen()` opcional. Testes: bola desacelera, robô rota-a segue FOPDT com erro < 1 mm/passo sem contato, rota-b anda em linha reta ±2 % com comando vx.

### 4.7 CLI (`dtssl` = `dtssl.cli:main`)
`dtssl serve [--backend fopdt] [--config config/bridge.json] [--field divB|divA|FILE] [--n-blue N --n-yellow N]` · `dtssl gui [--field divB|divA|FILE] [--n-active N]` · `dtssl replay <label> <event> [--theta config/twin_params.json] [--plant fopdt|ideal|mujoco-velocity|mujoco-rollers|mujoco-rollers-delay|world:<backend>|proto:<sim>[+delay]][+preroll] [--out results/]` · `dtssl gate twin-vs-ideal|twin-vs-rsim [--mode A|B]` · `dtssl analysis <name>` · `dtssl fig <name>` · `dtssl etl extract <log.gz> <out>` / `split` / `rotate` · `dtssl mjcf --route a|b [--field divB|divA|FILE] [--visual primitive|cad] [--view --demo] --out models/mjcf/` · `dtssl proto-build` · `dtssl release`.

## 5. Testes e reprodutibilidade
- `pytest -m "not requires_data and not requires_mujoco and not requires_gui"` deve passar em CI sem dataset. `conftest.py` registra marcadores e `skip` automático. `requires_net` = sockets UDP em loopback (servidor em processo), sem simulador externo; o replay via protocolo contra grSim/ER-Force não tem teste automático — é experimento (`protocol_holdout`, `REQUIRES = ("data", "net")`), validado pelo auto-teste `dtssl serve` ↔ `ProtocolPlant` ao nível do mm.
- Goldens: `tests/fixtures/plant_golden_*.parquet` (θ = `sysid_vxvy_v2` + ω placeholder) ficam **como estão** e o teste lê o θ de `tests/fixtures/plant_golden_theta.json` (novo). `matlab/dtssl/export_plant_golden.m` ganha argumento de θ para gerar `plant_golden_v2_*` com o θ promovido (rodar no PC; adicionar teste que só roda se o arquivo existir).
- Cada número do artigo = `dtssl analysis <name>` reproduzível; `results/` recebe arquivos com carimbo de tempo e cabeçalho (commit, θ, dataset, seed).
- `tools/make_release.py` gera `dist/dtssl-release/` anonimizado (substitui `open-source/`).

## 6. Fora do repositório
- `ssl-unification`: `tools/ssl_unification/build_wsl2.sh` (clone recursivo, `setup.py --essentials`, cmake/make) e `make_local_config.py` (gera `config/local/config.json` a partir de `config/shared/ronaldinho` com `CommunicationSim` porta 10301/10302 conforme `TeamColor`, `DataWorld.Raw.Port` = `bridge.json:vision.port`, `INET=lo`, `RefereeBase=CustomRef` + `FORCE_START`, robôs 0..N-1 = `Player`/`Debug`, demais `TurnedOff`).
