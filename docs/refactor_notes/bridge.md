# Notas de refatoração — mundo multi-robô e bridge ssl-simulation-protocol, 02/09/2026

Agente: *bridge/world* (`sim/ball.py`, `sim/collisions.py`, `sim/twin_world.py`, `bridge/**`, testes, esta nota).
Escopo: `docs/SPEC_DTSSL.md` §3, §4.2, §4.4, §5. Nada em `models/`, `eval/`, `data/`, `analysis/`, `physics/`, `gui/`
foi tocado; `sim/entities.py`, `sim/world.py` e `sim/backends.py` foram usados **como estão** (nenhum campo renomeado).

## O que mudou

| Item | Arquivo(s) | Resumo |
|---|---|---|
| Bola analítica | `src/dtssl/sim/ball.py` (novo) | `BallParams` (lido de `robot_limits.json:ball`), `Ball` com modelo **duas fases** (desliza a −1,82135 m/s² até `v < 0,6·v0`, depois rola a −0,3025 m/s²) integrado **exatamente** por substep (eventos de troca de fase/parada resolvidos analiticamente); chute reto (`kick`), chip (balística, g=9,81, quique com `restitution_floor`, assentamento abaixo de `settle_vz`), quique nas paredes (`Walls.from_field`, `restitution_wall`), `reflect` para contatos. Distância de parada = fórmula fechada `(v0²−vs²)/(2a_s)+vs²/(2a_r)` a 1e-9 m (teste). |
| Contatos | `src/dtssl/sim/collisions.py` (novo) | `resolve_robot_robot` (push-out posicional simétrico, disco r=0,09), `clamp_to_walls` (centro do robô dentro de campo+boundary−raio), `robot_ball_contact` (disco + **face plana do dribbler** a 0,075 m: bola encostada fica a 0,0965 m do centro, dentro de `ball_contact_dist`=0,11), `ball_in_front` (cone do dribbler: distância ≤ 0,11 e |ângulo| ≤ 0,31 rad), `dribbler_hold_pose`. |
| Mundo | `src/dtssl/sim/twin_world.py` (novo) | `TwinWorld(World)`: um `Plant` por robô (`plant="fopdt"` → `AnalyticFOPDTPlant` com θ de `twin_params.json` ou `params=`; `"ideal"` → `IdealKinematicPlant`; ou fábrica), `set_command` com `RLock` e carimbo `t_recv` (relógio `watchdog_clock="wall"|"sim"|callable`), **watchdog** (`watchdog_s` → comando zero, contado em `watchdog_hits`, rearmado por novo comando), saturação `v_max/w_max` e zona morta por roda (`saturate=False`, `deadzone=False` por default — o modelo publicado não tem nenhuma), `step(dt)` = plantas → push-out robô-robô → clamp paredes → chute/dribbler → substeps da bola (≤1/600 s) com pose do robô **interpolada** ao longo do frame; `state()` com θ em (−π, π]; `teleport_robot` (reset + `prime_delay([])`, velocidade global opcional, cria robô novo), `teleport_ball`, `set_present`, `set_plant_params` (θ trocado *in place* nas `AnalyticFOPDTPlant`: pose, velocidade e buffer de atraso preservados), `reset(Scene)`; expõe `plants`, `commands`, `ball_obj`, contadores (`kicks`, `contacts`, `watchdog_hits`). Cinemática de rodas: usa `dtssl.kinematics` (import preguiçoso, validado por `w=1 → R/r` em todas as rodas), senão implementação local de `ω_i·r = −sin φ_i·vx + cos φ_i·vy + R·ω` (φ=60,135,225,300°, R=0,079601, r=0,029492). Registrado via `dtssl.sim.backends` (`"fopdt"`, `"ideal"`), sem alteração no registro. |
| Protos | `src/dtssl/bridge/proto/` (novo) | Cópias **verbatim** de `ssl-unification/libs/protobufs/.../proto/`: `ssl_vision_{wrapper,detection,geometry}`, `ssl_simulation_{robot_control,robot_feedback,control,config,error,synchronous}`, `ssl_gc_common`. `*_pb2.py` **versionados** (gerados com protoc 25.1 / grpcio-tools 1.62.3: gencode sem *runtime version check*, carrega em protobuf ≥4.21 — testado em 4.25.9 e 7.36.1). `build_proto.py` regenera (`dtssl proto-build`, `--check` verifica se estão atuais) e reescreve `import x_pb2` → `from . import x_pb2` (sub-pacote sem `sys.path`). `__init__.py` reexporta as mensagens e `TEAM_NAME`/`TEAM_ENUM`. |
| Config | `src/dtssl/bridge/config.py` (novo) | `BridgeConfig` (`VisionConfig`, `ControlConfig`, `SimConfig`) de `config/bridge.json`; `with_overrides(...)` para as flags da CLI; `as_bridge_config` aceita `BridgeConfig`/dict/caminho/`None`. |
| Visão | `src/dtssl/bridge/vision.py` | `VisionPublisher(config, field)`: `build_packet(ws)` (puro) → `SSL_WrapperPacket` com detection (mm, rad wrap, `confidence=1`, `pixel=0`, `height=150`, `frame_number` contíguo próprio, `t_capture=t_sent=time.time()`, `camera_id` da config) + geometry no frame 0 e a cada `geometry_every` (campo de `field_divB.json`, 12 `field_lines` + arco `CenterCircle` com `SSL_FieldShapeType`, `ball_radius`, `max_robot_radius`, `goal_height`, `models.straight_two_phase`/`chip_fixed_loss` = parâmetros da nossa bola); socket multicast (`IP_MULTICAST_IF/TTL/LOOP` da config; falha de opção → aviso e interface default) + `unicast_targets`; ruído gaussiano opcional (`position_noise_std_mm`, `orientation_noise_std_rad`, `seed`) e latência por `latency_frames` (ring buffer). `z` da bola publicado = altura da base da bola (0 no chão). |
| Controle | `src/dtssl/bridge/control.py` | `ControlServer(world, config)`: sockets `bind_ip:10301` (blue) e `:10302` (yellow), uma thread de recepção por socket (ou `poll()` sem threads); `RobotControl` → `RobotCmd` por robô (`local_velocity` direto; `global_velocity` girado com θ atual; `wheel_velocity` via `proto_wheels_to_body`), `kick_speed`/`kick_angle`/`dribbler_speed`, `t_recv`; **resposta a todo datagrama** `RobotControlResponse{feedback[]{id, dribbler_ball_contact}}` ao endereço de origem; ids fora de [0,15] → `errors[]` (`INVALID_ROBOT_ID`); datagrama malformado → contado, logado (rate-limited) e ignorado. Estatísticas por porta (`packets`, `bytes`, `commands`, `responses`, `parse_errors`, `last_addr`). |
| SimControl | `src/dtssl/bridge/simcontrol.py` | `SimControlServer(world, config)` em `:10300`: `teleport_ball` (m, m/s; campos ausentes mantêm o atual; `roll` → fase rolando), `teleport_robot[]` (`id.team/id.id`, x/y/orientation opcionais, `v_x/v_y/v_angular` globais, `present`: True adiciona, False remove, ausente mantém), `simulation_speed` (aplicado se 0 < s ≤ 10, senão erro), `config.vision_port` (aplicado), `config.geometry/robot_specs/realism_config` → erro `UNSUPPORTED`; responde `SimulatorResponse` (vazio em sucesso). |
| Servidor | `src/dtssl/bridge/server.py` | `SimServer(world, config, step_mode=False, recorder=None)`: compõe visão + controle + simcontrol; `run(duration)` em tempo real (relógio monotônico, período `1/(rate_hz·speed)`, dorme até o próximo tick, `late_ticks`, reancora se atrasar > `max_lag_s`), `run_in_thread`, `tick()` (modo passo: testes/GUI), `stop()`, *context manager*; `stats` (`hz_actual` em janela móvel, `packets` por porta, `watchdog_hits`, `kicks`, `sim_time`, stats dos três módulos) legível de outra thread; `set_speed`, `set_vision_port`. Aplica `control.watchdog_s` da config ao mundo. Com `recorder`, grava a pose inicial em `start()` e uma linha por tick. |
| Cliente falso | `src/dtssl/bridge/fake_strategy.py` | `FakeStrategy(team, target=...)`: entra no multicast (ou porta unicast, `vision_port=0` = efêmera), parseia `SSL_WrapperPacket`, GoToPoint proporcional (mundo → corpo, `kp`, `v_max`, `target_theta` opcional), envia `RobotControl` (`local_velocity`, como `Simulation::toRobotControl`) a cada frame e lê `RobotControlResponse`; stats (`frames`, `frame_gaps`, `geometry_packets`, `responses`, `last_feedback`, `reached`). |
| Gravador | `src/dtssl/bridge/recorder.py` | `SessionRecorder(teams, robot_ids)`: `record_initial(ws)` + `record(ws, commands)` → `commands.parquet` / `processed_robots.parquet` **exatamente** no contrato dos logs (colunas de DESIGN.md §2.2/§2.3: `team="allies"`, posição mm, `position_w` rad wrap, velocidade mm/s mundo). Linha de comando carimbada no **início** do passo (ZOH-forward como nos logs) e a pose no fim; carimbos ancorados em `k·Ts` exatos. `dtssl.data.loader.load_event` carrega e `validate_segment` passa; o free-run da `AnalyticFOPDTPlant` sobre os comandos gravados reproduz a pose gravada a <1e-6 m (teste). |
| CLI | `src/dtssl/bridge/cli.py` | `register(subparsers)` (descoberto por `dtssl.cli`): `dtssl serve [--backend fopdt] [--config config/bridge.json] [--vision-port N] [--vision-ip IP] [--multicast-if IP] [--unicast host:port]* [--blue-port N] [--yellow-port N] [--simcontrol-port N] [--bind-ip IP] [--field divB|divA|FILE] [--n-blue N --n-yellow N] [--duration S] [--no-realtime] [--speed X] [--rate-hz F] [--theta JSON] [--saturate] [--deadzone] [--record DIR --record-team blue|yellow|both] [--stats-every S]`; `dtssl fake-strategy --team yellow --target x y [--robot N] [--target-theta] [--vision-ip/--vision-port/--multicast-if/--unicast] [--control-host/--control-port] [--duration S] [--stop-when-reached]`; `dtssl proto-build [--check]`. Também `python -m dtssl.bridge.cli ...`. |
| Testes | `tests/test_world_ball.py` (14), `tests/test_world_twin.py` (16), `tests/test_bridge_proto.py` (11), `tests/test_bridge_net.py` (8, `requires_net`), `tests/test_bridge_recorder.py` (4) | 53 testes; suíte inteira: 217 passed, 1 skipped. Rede: só loopback, portas efêmeras (`port=0`); multicast testado apenas se a sonda `_multicast_loopback_works()` passar (passa neste host). |

## Como rodar contra o ssl-unification (WSL2)

1. **Gêmeo**: `dtssl serve` (defaults de `config/bridge.json`: visão `224.5.23.2:10006` via `lo`, controle `0.0.0.0:10301/10302`, simcontrol `10300`, 6×6 robôs, backend `fopdt`, tempo real 60 Hz). Ex.: `dtssl serve --n-blue 6 --n-yellow 6 --record results/sessao_01`.
2. **ssl-unification** (`config/local/config.json`, gerado por `tools/ssl_unification/make_local_config.py` quando existir; até lá, na GUI):
   - `VisionBase = DataWorld`; `DataWorld/Raw/IP = 224.5.23.2`, `DataWorld/Raw/Port = vision.port` (**10006** no `bridge.json`; o default do código C++ é 10020 — o que importa é os dois lados baterem); `PacketType = Raw`; `TeamColor = Blue|Yellow`; `AttackingSide` a gosto.
   - `Environment/General/INET = lo` (índice da interface usada no `joinMulticastGroup`); no `develop` está `eno2/wlp3s0` — **trocar para `lo`** quando o gêmeo roda no mesmo WSL.
   - `CommunicationBase = CommunicationSim`; `CommunicationSim/Communication/IP = 127.0.0.1`, `Port = 10301` se `TeamColor=Blue`, `10302` se `Yellow` (o `develop` traz 10301 e o `ronaldinho` 10302 — conferir com a cor!); `Replacement/IP = 127.0.0.1`, `Port = 10300` (teclas P/M/Y/B+dígito teleportam via `SimulatorCommand`).
   - `RefereeBase = CustomRef` com `Command = FORCE_START` (o gêmeo não fala com o game-controller).
   - Robôs 0..N−1 com comportamento `Player`/`Debug`, demais `TurnedOff` (`DataWorld` remove `TurnedOff` da lista de aliados).
3. **Conferir**: o log do gêmeo mostra `pkts yellow=...` crescendo e `watchdog=0`; na GUI do ssl-unification o campo desenha a partir do pacote de geometria (obrigatório — enviado no frame 0 e a cada 60 frames, logo até 1 s para aparecer). `dtssl fake-strategy --team yellow --target 1 0.5` serve de "estratégia" de fumaça sem o C++.

### Rede no WSL2

- **Tudo dentro do WSL2** (gêmeo e estratégia): loopback funciona, inclusive multicast em `lo` (é o caso testado aqui: `IP_MULTICAST_IF=127.0.0.1`, `IP_MULTICAST_LOOP=1`, `INET=lo` no ssl-unification).
- **Gêmeo no Windows + estratégia no WSL2** (NAT, default do WSL): multicast **não** atravessa o NAT. Usar unicast: `dtssl serve --unicast <ip-do-wsl>:10006` (o IP do WSL: `hostname -I` dentro do WSL; muda a cada boot) — o `DataWorld` faz `bind(AnyIPv4, port)` e o `joinMulticastGroup` falhando não impede a recepção unicast na mesma porta. No ssl-unification, `CommunicationSim/Communication/IP = <ip-do-host-windows>` (o gateway visto do WSL: `ip route | grep default`) e `Replacement/IP` idem; o Windows precisa liberar UDP 10300–10302 no firewall para o `vEthernet (WSL)`. Alternativa: `networkingMode=mirrored` em `%USERPROFILE%\.wslconfig` (Windows 11 22H2+), aí `127.0.0.1` e multicast em `lo` voltam a funcionar como no caso 1.
- **Gêmeo no WSL2 + GUI/joystick no Windows**: mesma lógica invertida (`--unicast <ip-windows>:porta`).
- `--multicast-if` deve ser o IP da interface que o *outro* lado escuta; `--bind-ip 0.0.0.0` (default) aceita comandos de qualquer interface.

## Decisões de modelo (documentadas para o artigo/GUI)

- **Ordem do passo**: comandos (pós-watchdog/saturação/zona morta) → `plant.step` de cada robô presente na grade 1/60 → push-out robô-robô (simétrico, 4 passadas) → clamp nas paredes (pose da planta corrigida *in place*, estado interno intocado) → chute/dribbler → bola em `ceil(dt/dt_sub)` substeps com contato robô-bola (pose do robô interpolada entre a anterior e a nova; velocidade de contato = diferença finita do frame). Um robô **sem contato** reproduz `AnalyticFOPDTPlant` bit a bit (`test_fopdt_world_reproduces_plant_bit_for_bit`).
- **Chute**: aplicado quando `kick_speed>0` e a bola está no cone do dribbler (não exige dribbler ligado); velocidade **absoluta** ao longo do heading (não soma a velocidade do robô — "Absolute kick speed" do proto), saturada em `kick_flat_max` (6,5) / `kick_chip_max` (6,0); `kick_angle>0` ⇒ chip com o ângulo **da config** (`chip_angle_deg=45`; o ssl-unification manda 45 mesmo); consumido uma vez (`cmd.kick_speed=0`) + *cooldown* de 0,1 s por robô.
- **Dribbler**: `dribbler_rpm>0` e bola no cone e no chão ⇒ bola presa, centrada na face (0,0965 m do centro), move com o robô (velocidade publicada = do robô); `dribbler_rpm=0` solta com a velocidade do robô. `has_ball`/`dribbler_ball_contact` = bola no cone (presa ou encostada).
- **Chip**: sem colisão com robôs enquanto `z > height` (0,15 m); paredes quicam em qualquer altura (mantém a bola na arena); sem perda xy por quique (o `chip_fixed_loss` publicado reflete isso: damping xy = 1, z = 0,5).
- **Transição deslizar→rolar** por velocidade (`k=0,6·v0`), não por tempo; o ssl-unification usa limiar fixo 1133,85 mm/s em `Env.h` para *predição* — não afeta o gêmeo.
- **Mapeamento de rodas do proto** (`MoveWheelVelocity`, m/s de superfície, positivo = tangente CCW como em SPEC §3): `(front_right, back_right, back_left, front_left)` = φ `(300°, 225°, 135°, 60°)` = ordem **invertida** da dtssl (`PROTO_WHEEL_ORDER=(3,2,1,0)`); corpo = pseudo-inversa. O proto não fixa o sinal — se um cliente usar "positivo = frente", inverter o sinal em `proto_wheels_to_body`.
- **Watchdog** com relógio de parede (`time.monotonic`) por default; `watchdog_clock="sim"` nos testes/modo passo determinístico.
- **Robô ausente do mundo**: comandos para ids não instanciados são ignorados (`--n-blue/--n-yellow` ou `TeleportRobot{present=true}` para adicionar).

## Correção 10/09/2026: `recvfrom` com `ConnectionResetError` no Windows

No Windows, um socket UDP que **enviou** um datagrama a uma porta que deixou de existir (cliente fechou) recebe
um ICMP "port unreachable" e o próximo `recvfrom` levanta `ConnectionResetError` (WSAECONNRESET). Os loops de
recepção do controle e do simcontrol faziam `except OSError: break` — a thread morria em silêncio e o `dtssl
serve` ficava **surdo** para todos os comandos seguintes daquele time (o robô só respondia a teleportes).
Encontrado pelo replay via protocolo em processo no PC (a partir da 3.ª instância de `ProtocolPlant`, os
comandos deixavam de chegar). Agora `ConnectionResetError` é contado (`ControlStats.resets`,
`SimControlServer.resets`) e ignorado; outro `OSError` só encerra o loop quando o servidor está parando.
Mesmo tratamento em `VisionReceiver` e `FakeStrategy`. Teste: `tests/test_bridge_net.py::
test_control_and_simcontrol_survive_windows_connection_resets` (socket embrulhado que levanta o erro n vezes).

## Limitações conhecidas

- Sem `by_force` (tratado como teleporte direto), sem `teleport_safely`, sem `SimulatorConfig.geometry/robot_specs/realism` (respondidos como `UNSUPPORTED`), sem modo síncrono (`SimulationSyncRequest` — mensagens geradas, servidor não).
- Uma câmera (`camera_id` único); ruído/latência simples (gaussiano i.i.d., atraso inteiro em frames); sem oclusão nem perda de pacotes simulada.
- Robô não tem inércia de contato: push-out puramente posicional (a planta segue comandando; dois robôs se empurrando "deslizam"); bola presa no dribbler pode penetrar ~3 cm na parede (clamp usa o raio do robô).
- `a_max` de `robot_limits.json` não é aplicado (a SPEC o deixa `null`).
- `Ball.z` = altura da **base** da bola (0 no chão), publicado assim em `SSL_DetectionBall.z` (grSim publica o centro; o ssl-unification ignora `z`).
- O relógio do mundo acumula `t += dt` (deriva de ulps); o gravador reancora os carimbos em `k·Ts` — quem consumir `WorldState.t` diretamente deve tolerar 1e-12 s.

## Replay via protocolo: simuladores externos no harness (C2b, 10/09/2026)

O caminho inverso do servidor: `dtssl.sim.protocol_plant.ProtocolPlant` é um **cliente** do
ssl-simulation-protocol que se apresenta ao harness do artigo como uma `Plant`. Serve para avaliar os
simuladores da liga (grSim, ER-Force `simulator-cli`) — e o próprio `dtssl serve`, como auto-teste — nas mesmas
janelas re-ancoradas e com a mesma métrica do gêmeo (`dtssl analysis run protocol_holdout`,
`dtssl replay ... --plant proto:grsim`, `make_harness_plant("proto:<sim>[+delay]")`).

- **Por janela** (`free_run_window`, gancho em lote que `free_run` usa quando existe): `TeleportRobot` (pose real +
  velocidade de mundo de `velb0`) seguido do primeiro `RobotControl`; os demais comandos saem a `dt` exato de
  relógio de parede (não amarrados aos pacotes de visão: o atraso de visão do ER-Force atrasaria cada comando);
  a visão é colhida até `H·dt + cauda`; **alinhamento**: âncora = primeiro quadro após o teleporte consistente com
  `pose0` (tolerância cresce com |v0|), `tau0` (fração de período entre teleporte e captura) pela projeção do
  deslocamento em `v0` (ou mediana corrente quando parado), pose em `h·dt` por interpolação linear nos
  `t_capture` (θ desembrulhado). Envios em fase (meio período após a chegada de um quadro), para nunca cavalgar
  a fronteira de um tick; base de tempo por contagem de quadros nos simuladores com carimbo de parede
  (`dtssl serve`), por `t_capture` nos que carimbam tempo simulado (grSim, ER-Force).
- **Atraso**: `delay=None` (comandos como gravados) ou `"theta"` (Td por DOF do θ oficial aplicado no envio,
  `ud[j] = u[j − ⌈Td/dt⌉]`, primado com os comandos anteriores à janela — análogo de `mujoco-rollers-delay`).
- **Endpoints** em `config/external_sims.json` (`dtssl`, `grsim`, `erforce`): portas, grupo de visão, interface do
  join (`127.0.0.1` para o `dtssl serve`, que envia em `lo`; `0.0.0.0` = interface da rota default, onde grSim e
  ER-Force enviam — um join na interface errada recebe nada), `vision_rate`, `teleport_omega`.
- **Diagnóstico** (`ProtocolStats`, no artefato): período/taxa de visão, escala de `t_capture`, latência
  teleporte→visão (3 teleportes na abertura), `tau0` por janela, fase e jitter de envio, teleportes não vistos,
  janelas curtas, gaps de `frame_number`.
- **Verificação**: `tests/test_protocol_plant.py` (7) e `tests/test_protocol_holdout.py` (8): `dtssl serve`
  (fopdt, Td = 0) em processo + `ProtocolPlant(delay="theta")` reproduz a `AnalyticFOPDTPlant` nas mesmas
  janelas com erro máximo ≤ 0,5 mm (H = 90; float32 do protocolo + alinhamento sub-quadro), 0 falhas de âncora,
  jitter de envio < 10 ms; `compute` de ponta a ponta com `repeat=2`, caches `.npz` + `.stats.json` e
  reanálise offline (`from_cache`) idêntica.
- **O que os simuladores fazem com o teleporte** (fonte lida): grSim `resetRobot()` + `setSpeed()` → a
  velocidade vira setpoint dos motores, toda janela parte do repouso; ER-Force aplica a velocidade linear no
  corpo Bullet e a de guinada no eixo **x** (bug; enviamos 0). A análise reporta o gêmeo com a mesma
  desvantagem (`fopdt_v0=0`) ao lado do gêmeo do artigo. Scripts WSL2 (instalação com sudo só no `apt`,
  `simctl.sh`, experimento de ponta a ponta): `tools/external_sims/README.md`.

### Pré-rolagem (C2b2, 16/09/2026; código pronto, experimento pré-registrado e ainda não rodado)

`ProtocolPlant(pre_roll=S)` (tag `+preroll` em `make_harness_plant`, opção `preroll=S` do `protocol_holdout`,
`run_protocol_holdout.sh --preroll S`) remove a desvantagem da condição inicial sem tocar no simulador: o robô é
teleportado `P = min(round(S/dt), prefixo)` amostras antes de `t0`, o prefixo real de comandos (`prev_cmds`, o
mesmo que o tap de atraso já recebe) é transmitido antes da janela, e a trajetória é **re-ancorada em SE(2)** na
pose real de `t0` (`dtssl.sim.preroll.reanchor_se2`). Em `t0` o simulador está no estado que a sua própria
dinâmica produziu. `dtssl.sim.preroll.PreRollPlant` faz o mesmo em processo para qualquer `Plant` passo a passo:
é a referência do auto-teste do caminho de protocolo (`tests/test_protocol_plant.py`, erro máximo < 3 mm por
janela contra `dtssl serve`) e a coluna de controle `fopdt+preroll` do artefato. `pre_roll=0` (default) é o
comportamento do C2b, bit a bit; a interpolação da janela passa por `interpolate_at` (mesma série de quadros de
`interpolate_poses`, tempos arbitrários desde o teleporte). Diagnóstico novo em `ProtocolStats`:
`preroll_windows`, `preroll_samples_median`, `preroll_short`, `reanchor_failures`. Critérios e hipóteses:
`docs/PREREGISTRO_C2B2_PREROLAGEM_20260916.md`.

## Verificação

- `python3 -m pytest -q`: **217 passed, 1 skipped** (o skip é de outro módulo, dependente de dataset); só os arquivos deste agente: 53 passed em ~2,5 s.
- Demo real: `dtssl serve --duration 5 --vision-port 10999 --blue-port 20301 --yellow-port 20302 --simcontrol-port 20300` + `dtssl fake-strategy --team yellow --target 1.0 0.5 --duration 3 --vision-port 10999 --control-port 20302 --stop-when-reached` → 60,0 Hz reais, 128 comandos/128 respostas, alvo atingido (dist 0,049 m) e `watchdog=1` após o cliente parar.
- `_pb2` carregam em protobuf 4.25.9 (runtime da geração) e 7.36.1 (runtime deste container).
- **Não verificado aqui**: o binário do ssl-unification (não compilado neste container — só o código C++ foi lido para fixar campos obrigatórios, unidades e `camera_id<8`/`robot_id<16`); Windows↔WSL2 real (instruções acima derivadas da configuração de rede do WSL, não executadas); multicast em interfaces físicas (só `lo`).

## TODOs para o orquestrador

- `tools/ssl_unification/make_local_config.py` e `build_wsl2.sh` (SPEC §6) não existem ainda — a tabela "Como rodar" acima é a fonte para o gerador (`Raw.Port = bridge.json:vision.port`, `CommunicationSim.Port` por `TeamColor`, `INET=lo`, `CustomRef FORCE_START`).
- GUI: `SimServer.stats`, `world.plants`, `world.commands`, `world.set_plant_params`, `world.teleport_*`, `world.set_present` são os ganchos previstos; `SimServer(step_mode=True).tick()` para dirigir pelo `QTimer`.
- Backend MuJoCo: `SimServer` só exige a interface `World` (+ `ball()`/`spec`/`field`); `teleport_robot(..., vx, vy, w)` e `teleport_ball(..., rolling)` são extensões opcionais (o simcontrol faz fallback por `TypeError`).
- Se `protobuf` do usuário for < 4.21, `pip install -U protobuf`; se regenerar os protos com protoc ≥ 26, subir o mínimo em `pyproject.toml` (ver docstring de `build_proto.py`).

## Elenco de 11 robôs, reservas fora da arena e gols sólidos no mundo analítico (07/10/2026)

Pedido do Victor em 07/10: confirmar a divisão do campo, pôr 11 robôs por time para funcionar com os inativos fora das
bordas, e dar colisão às traves e às bordas no modo debug, para robôs e bola. O campo é o da **Divisão B**
(`config/field_divB.json`: 9 × 6 m, gol de 1,0 × 0,18 m, *boundary* de 0,3 m; `FieldGeometry` já tinha esses
defaults e nada mudou nele). Divisão B joga com 6 em campo, então o elenco de 11 entra com 6 ativos e 5 reservas.

- **Elenco** (`sim/entities.py`): `ROSTER_SIZE = 11`, `ACTIVE_ROBOTS = 6`, `PARK_GAP = 0,25 m` e
  `park_spot(team, rid, field_length_m, field_width_m, boundary_width_m, gap)`: a vaga de banco fica **além da
  parede de −y** (centro em y = −(W/2 + bw + gap) = −3,55 m), cada time no seu lado (azul em x < 0, amarelo em
  x > 0), enfileirada por id a partir do meio (x = ±gap·(1 + id)), de frente para o campo (θ = π/2).
  `Scene.default(n_blue, n_yellow, field_length_m, field_width_m, n_active=None, boundary_width_m=0,3)`: os ids
  menores que `n_active` recebem a formação de sempre, calculada com `n_active` robôs (a formação de 6 é idêntica à
  anterior), e os demais nascem `RobotSpawn(present=False)` na vaga. `n_active=None` mantém todos em campo.
- **`TwinWorld(..., boundary=True, goals=True, n_active=None)`**. Robô ausente: a planta é criada na vaga, não é
  passada em `step`, não participa de contato nenhum e não sai em `robots_of` (logo a visão não o publica), mas
  continua no `WorldState` para a GUI desenhá-lo esmaecido. `set_present(False)` leva o robô à vaga (e solta a
  bola se a segurava); `set_present(True)` traz de volta pela parede mais próxima, grampeado dentro da arena;
  `teleport_robot(..., present=False)` ignora as coordenadas e estaciona; `reset` respeita o `present` do spawn.
  Novo `park_spot(team, rid)` no mundo para quem precisar da vaga com a geometria carregada.
- **Gols sólidos** (`sim/collisions.py`): `goal_segments(field)` devolve os 6 segmentos de linha de centro dos gols
  (por gol, duas laterais com a trave na frente, da linha de gol até o fundo, e o fundo), coincidindo com as caixas
  do MJCF (`GOAL_WALL_THICKNESS = 0,02 m`); `clamp_to_goals(x, y, radius, field)` empurra o robô para fora das
  cápsulas (ponto mais próximo do segmento, 2 passadas para os cantos); `goal_ball_contact(ball, field)` empurra
  a bola e reflete a velocidade com `restitution_wall` (a mesma das paredes), a não ser que a bola esteja acima de
  `GOAL_WALL_HEIGHT = 0,16 m` (chip passa por cima). Ordem do passo: plantas → push-out robô-robô → paredes
  (`clamp_to_walls`, se `boundary`) → gols (`clamp_to_goals`, se `goals`) → chute/dribbler → bola em substeps com
  paredes e gols a cada substep. `boundary=False` desliga paredes para robô e bola (a bola segue em frente).
- **Harness intacto**: `WorldPlant` passa `goals=False` aos backends analíticos (o harness nunca teve gols; paredes
  como antes), então os rollouts e as métricas do artigo não mudam; os backends MuJoCo já tinham gols e paredes no
  MJCF e não recebem nada novo.
- **`MuJoCoWorld`** usa a mesma `park_spot` (antes estacionava numa fileira no canto +x/−y), guarda `park_theta` e
  grampeia a reentrada em `set_present(True)` com `clamp_to_walls` quando há *boundary*; `n_active` também existe.
- Testes: `tests/test_world_twin.py` (+4: reserva estacionada, não simulada nem publicada, reentrada pela parede;
  elenco padrão com 12 presentes e 10 no banco; robôs param no fundo e na lateral do gol e a bola chutada no gol
  volta sem atravessar o fundo; `boundary=False` deixa robô e bola saírem), `tests/test_physics_world.py`
  (vaga e reentrada no MuJoCo), `tests/test_bridge_proto.py` segue igual (spawn `present=False` agora nasce na
  vaga). SPEC §4.2 e §5 atualizadas.

### Campo por divisão no servidor (07/10/2026)

`dtssl serve --field divB|divA|FILE` (`bridge/cli.py`, `build_world_from_args`): o preset de campo de
`dtssl.config.load_field_preset` entra no mundo (`make_world(..., field=preset.field)`) e, por consequência, no
pacote de geometria da visão (`VisionPublisher(config, world.field)`: `field_length` 12000, `goal_width` 1800,
`penalty_area_width` 3600 na Divisão A); sem `--n-blue/--n-yellow` o servidor nasce com os robôs por time da
divisão (6 na B, 11 na A, `robots_per_team` do JSON), todos em campo. Sem `--field` nada muda (`bridge.json`,
`field_divB.json`). A estratégia do outro lado precisa estar configurada para a mesma divisão (o ssl-unification
lê a geometria da visão, mas o número de robôs que comanda é config dele). Teste:
`test_serve_field_option_builds_the_division_world_and_geometry_packet`. O seletor equivalente da GUI está em
`docs/refactor_notes/gui.md` (Debug e Bridge; Replay fixo na Divisão B).
