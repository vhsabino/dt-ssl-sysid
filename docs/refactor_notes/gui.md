# Notas de refatoração — GUI (`dtssl gui`), 02/09/2026

Agente: *gui* (`src/dtssl/gui/**`, `tests/test_gui_*.py`, esta nota). Escopo: `docs/SPEC_DTSSL.md` §3, §4.2, §4.5, §5.
Nada fora de `src/dtssl/gui/` foi tocado: o mundo (`dtssl.sim`), o servidor (`dtssl.bridge.server.SimServer`),
o loader/rollout/métricas e os backends foram usados **como estão**.

## O que existe

| Arquivo | Papel |
|---|---|
| `gui/app.py` | `MainWindow` (toolbar de modos, seletor de backend/time/robô, *publish vision*, *real-time thread*, velocidade 0,5×/1×/2×, reset, fit, pausa; toolbar de Replay com dataset/label/evento, Load, Play/Pause, *scrub*; `FieldView` central; docks *Velocities*, *Twin parameters* e *Log*; barra de status) e `run(args)` / `main(argv)`. Filtro de eventos da aplicação para o teclado (WASD/QE…) quando o foco não está num campo de texto. |
| `gui/controller.py` | `Controller(QObject)`: dono do mundo (`make_world(backend, n_blue, n_yellow, params=θ)`), do `SimServer` opcional, do `JoystickReader` e dos timers: **sim** (5 ms, `PreciseTimer`, acumulador de relógio de parede → passos de 1/60 s, máx. 4 por evento, sem espiral), **joystick** (8 ms ≈ 120 Hz), **render** (33 ms → `frame_ready(Frame)`), **stats** (500 ms). Sinais: `frame_ready`, `sample_ready` (60 Hz, cmd × velocidade de corpo do robô selecionado), `stats_ready`, `mode_changed`, `backend_changed`, `selection_changed`, `replay_loaded/changed`, `server_changed`, `message`, `joystick_event`. `shutdown()` para timers, `SimServer.stop()` + `join` da thread, `joystick.close()`, `world.close()`. |
| `gui/field_view.py` | `FieldView(QGraphicsView)`: cena em **mm** no frame ssl-vision (+y para cima via `scale(1,-1)` na view); campo Div B de `FieldGeometry` (boundary, linhas, círculo central, áreas de pênalti, gols; marca de pênalti só se cair dentro do campo); `RobotItem` (disco r = 90 mm com face plana a 75 mm, linha de heading, cor por time, id com `ItemIgnoresTransformations`, anel de seleção, marcador laranja de `has_ball`); `BallItem` (21,5 mm desenhada com 32 mm; cresce/esmaece com `z`); `TrailItem` (rastro dos últimos N s do robô selecionado — sim em ciano, verdade em rosa no Replay); robô-fantasma cinza da verdade. Itens criados uma vez e movidos (`update_state`). Clique esquerdo = teleporte do robô selecionado (`robot_teleport_requested`), direito = bola, Ctrl+clique = seleciona, roda = zoom sob o cursor, arrastar (esquerdo/meio) = pan, duplo clique/`F` = fit. Conversões `scene_from_m/mm`, `m_from_scene`, `px_from_m`, `m_from_px`. |
| `gui/plots.py` | `VelocityPlots` (pyqtgraph): linhas `vx`, `vy`, `w` (cmd tracejado × sim ciano × verdade rosa no Replay) com eixo x ligado; modo **sliding** (ring buffer, janela de 10 s, `append` a 60 Hz, redesenho a 30 Hz por timer próprio ou `redraw()`) e **fixed** (Replay: séries do evento inteiro, linha `e_pos(t)` com marcadores nos horizontes de `config/metrics.json` e *playhead*). |
| `gui/params_panel.py` | `ParamsPanel`: `K`, `tau`, `Td` por DOF (`QDoubleSpinBox`, 4 casas) com os limites do SLDD `K∈[0.5,2.0]`, `tau∈[0.01,0.5]`, `Td∈[0,0.2]` (valores fora são grampeados e reportados), checkbox `placeholder`; presets **oficial** (`config/twin_params.json`), **ω placeholder** (vx/vy oficiais + `w={1, 0.1, 0, placeholder}`) e **ideal** (`{1, 0.01, 0}`); Load/Save JSON no **mesmo esquema** de `twin_params.json` (`dof`, `order` fixa, `ts`, `robot_radius`, `wheel_radius`, `source`, `note`); `Apply` → `apply_requested(dict[str, DofParam])` → `Controller.apply_params` → `world.set_plant_params` (poses preservadas) e, no Replay, recomputa o free-run. |
| `gui/joystick.py` | Sem Qt. `JoyMap` (índices de eixos/botões + curva; presets `gamecontroller`, `dualsense-raw-linux`, `dualsense-raw-windows`; JSON parcial mesclado sobre um `base`), `JoystickState`, `InputProvider` (protocolo), `FakeProvider` (testes), `PygameProvider`/`PygameBackend` (pygame sem janela: `SDL_VIDEODRIVER=dummy`, `SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1`; usa `pygame._sdl2.controller` quando o SDL reconhece o pad — índices padrão — senão `pygame.joystick` cru), funções puras `read_state` e `map_state` (zona morta radial 0,08 + expo 0,3, turbo, chutes, dribbler, eventos de borda) e `JoystickReader` (`read() -> (RobotCmd, events)`, *rescan* a cada 2 s, preferência por nome `DualSense`/`PS5`/`Wireless Controller`, *fallback* para o provedor de teclado). |
| `gui/keyboard.py` | Sem Qt. `KeyboardProvider`: gamepad virtual com layout GameController alimentado por nomes de tecla (`press("w")`), rampa linear de 0,25 s nos sticks (teclas opostas se cancelam). |
| `gui/replay.py` | Sem Qt. `list_datasets/labels/events` (varre `data/extracted/<dataset>/splits/<label>/<event>/commands.parquet`), `ReplaySession.load(label, event, dataset, params)`: `load_segment` → `free_run` do evento inteiro a partir de `seg.pose0/velb0` (mesma receita de `dtssl replay`), velocidade de corpo simulada pelo mesmo estimador do loader (`body_velocity_series`), `e_pos/e_ang` por `pose_errors`, `epos_at_horizons()` (amostras de `metrics.json`), *playhead* (`seek`, `advance(dt_wall)` com velocidade, `play/pause/toggle`), `recompute(params)`. |
| `gui/cli.py` | `register(subparsers)` (descoberto por `dtssl.cli`, comando `gui`) e `build_parser()`/`main()`; só depende de `argparse`, então `dtssl gui --help` funciona sem PySide6 (o comando em si imprime a dica `pip install dtssl[gui]`). `gui/__main__.py` → `python -m dtssl.gui`. |
| `tests/test_gui_joystick.py` (13), `tests/test_gui_replay.py` (5), `tests/test_gui_window.py` (12, `requires_gui`) | 30 testes; janela com `TwinWorld`, um `tick` do controlador atualiza itens do campo e plots, round-trip JSON do painel, mapeamento com provedor falso, round-trip mm→cena→mm e m→px→m, sinais de clique, modos Bridge (`requires_net`, portas efêmeras) e Replay (`requires_data`), CLI registrada. Suíte completa: **295 passed, 1 skipped**. |

```
dtssl gui [--backend fopdt|ideal|mujoco-velocity|mujoco-rollers] [--mode debug|bridge|replay] [--team yellow]
          [--config config/bridge.json] [--joy-map arquivo.json|preset] [--field divB|divA|FILE]
          [--n-blue 11 --n-yellow 11] [--n-active N]
          [--publish] [--no-realtime] [--no-joystick] [--theta θ.json] [--saturate] [--deadzone]
          [--dataset ID --label L --event E] [-v]
python -m dtssl.gui ...
```

## Modos

- **Debug** (default): joystick/teclado comanda o robô selecionado (`--team`, combo *robot*, D-pad ←/→) num mundo local
  `make_world(backend)`. O comando é reamostrado na grade de 1/60 s (`set_command` a cada passo, ZOH como a estratégia).
  *publish vision* liga um `SimServer(step_mode=True)` que o timer da GUI "tica" (`tick()` = passo + pacote de visão):
  ferramentas externas (ssl-unification, ssl-vision-client) recebem visão/geometria e podem comandar os outros robôs.
- **Bridge**: `SimServer` no backend/config escolhidos. Com *real-time thread* (default `bridge.json: sim.realtime`) o
  loop `run()` roda numa thread e a GUI lê `server.last_state` (objeto imutável trocado sob o lock do servidor) a cada
  frame novo; com `--no-realtime` / caixa desmarcada, o timer da GUI chama `tick()` (modo passo). A GUI só observa;
  teleportes (clique) e `Apply` de θ continuam valendo; o joystick só troca o robô selecionado. Status mostra Hz real do
  servidor, pacotes/s por porta (visão, blue, yellow, simcontrol) e *watchdog hits*. Se a porta estiver ocupada (`dtssl
  serve` rodando), a mensagem aparece no Log e o modo fica sem servidor.
- **Replay**: escolha dataset/label/evento em `data/extracted` (DVC) → free-run da planta com o θ **atual do painel**
  (`ideal` se o backend for `ideal`; backends MuJoCo usam a `AnalyticFOPDTPlant`) a partir da primeira pose do evento vs
  verdade; `e_pos` nos horizontes de `config/metrics.json` no Log/toolbar; Play/Pause (Espaço), *scrub* pelo slider,
  0,5×/1×/2×. O campo mostra o robô simulado (cor do time), o fantasma da verdade e os dois rastros; os plots mostram
  cmd × sim × verdade e `e_pos(t)` com *playhead*. `Apply` recomputa o free-run sem perder a posição do *playhead*.

## Como rodar

Instalação: `pip install -e .[gui]` (PySide6 ≥ 6.6, pyqtgraph ≥ 0.13.4, pygame-ce ≥ 2.5 — `import pygame` continua igual; o pygame clássico 2.6 não tem wheel para Python 3.14 no Windows). Testado aqui com PySide6 6.11.2,
pyqtgraph 0.14.0, pygame 2.6.1 (Linux, `QT_QPA_PLATFORM=offscreen`).

### Windows nativo (recomendado para o DualSense)

1. Python 3.10+ (python.org ou `winget`), `pip install -e .[gui]` na raiz do repositório.
2. `dtssl gui` (ou `python -m dtssl.gui`). O gêmeo em modo Bridge no Windows + ssl-unification no WSL2: ver
   `docs/refactor_notes/bridge.md` ("Rede no WSL2") — multicast não atravessa o NAT do WSL2, use
   `--config` com `unicast_targets: ["<ip-do-wsl>:10006"]` ou `networkingMode=mirrored` no `.wslconfig`, e libere UDP
   10300–10302 no firewall para a interface `vEthernet (WSL)`.
3. DualSense por USB ou Bluetooth funciona sem driver extra (o SDL do pygame usa HIDAPI e reconhece o pad como
   GameController "PS5 Controller"). Se o Windows abrir o pad só como DirectInput ("Wireless Controller", sem
   mapeamento), use `--joy-map dualsense-raw-windows`. Feche Steam/DS4Windows enquanto testa: eles remapeiam o pad
   (Steam vira um Xbox virtual e o nome muda).

### WSLg (Ubuntu no WSL2 com GUI)

1. Windows 11 (ou 10 22H2+) com WSLg: `wsl --update`; dentro do Ubuntu `sudo apt install libgl1 libegl1 libxkbcommon0
   libxcb-cursor0 libfontconfig1 libdbus-1-3` (dependências das wheels do Qt); `pip install -e .[gui]`.
2. `dtssl gui` abre a janela pelo Wayland do WSLg; se aparecer erro de plugin de plataforma, force `QT_QPA_PLATFORM=xcb`
   (o WSLg também expõe X11 via XWayland). Sem GPU, `QT_OPENGL=software` evita artefatos.
3. **Joystick no WSL2**: o WSL2 não vê USB nem Bluetooth por padrão. Opções: (a) `usbipd-win` no Windows
   (`usbipd list` → `usbipd bind --busid X` → `usbipd attach --wsl --busid X`) + kernel do WSL com `hid-playstation`
   (o kernel padrão da Microsoft **não** o inclui; é preciso compilar o kernel com `CONFIG_HID_PLAYSTATION=y`,
   `CONFIG_INPUT_JOYDEV=y`, `CONFIG_INPUT_EVDEV=y`); (b) mais simples: rodar a GUI no Windows nativo e, se necessário,
   o ssl-unification no WSL2 (item acima). Sem pad, o teclado assume automaticamente.
4. Ao usar o WSLg com pad passado por USB/IP, o pygame abre `/dev/input/event*` — o usuário precisa estar no grupo `input`
   ou de uma regra udev (abaixo).

### Linux nativo e DualSense

- USB e Bluetooth são suportados pelo driver `hid-playstation` (kernel ≥ 5.12; substitui o `hid-sony` para o DualSense).
  `lsmod | grep hid_playstation` para conferir; por Bluetooth, parear com `bluetoothctl` (segurar *Create* + *PS* até o
  LED piscar rápido).
- Permissões: o SDL lê `/dev/input/event*` (evdev) e `/dev/hidraw*`. Regra udev típica em
  `/etc/udev/rules.d/70-dualsense.rules`:
  `KERNEL=="hidraw*", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="0ce6", MODE="0660", TAG+="uaccess"` (+ `0df2` para o
  DualSense Edge) e `sudo udevadm control --reload && sudo udevadm trigger`. Sem `uaccess`/grupo `input`, o pad aparece
  na lista mas os eixos ficam em zero.
- O SDL do pygame reconhece o DualSense como GameController tanto por HIDAPI (`SDL_JOYSTICK_HIDAPI_PS5`) quanto por evdev;
  se for aberto "cru" (sem mapeamento — nome sem "PS5"), o leitor troca sozinho para o preset `dualsense-raw-linux` quando
  o nome contém "DualSense"/"Wireless Controller"; force com `--joy-map dualsense-raw-linux` se necessário.
- Diagnóstico: `python -c "import pygame; pygame.init(); print([pygame.joystick.Joystick(i).get_name() for i in
  range(pygame.joystick.get_count())])"` ou `evtest`/`jstest-gtk`. O nome/estado atual aparece na barra de status
  (`keyboard` = nenhum pad; `✓` = conectado) e o Log registra `connected:<nome>` / `disconnected` (rescan a cada 2 s).

## Tabela de mapeamento (layout SDL GameController; `--joy-map` sobrescreve)

| Entrada | Índice GC | Índice cru DualSense Linux / Windows | Ação |
|---|---|---|---|
| Stick esquerdo Y (`ly`) | eixo 1 | 1 / 1 | `vx = −LY · v_max · escala` (frente = stick para cima) |
| Stick esquerdo X (`lx`) | eixo 0 | 0 / 0 | `vy = −LX · v_max · escala` (esquerda = stick para a esquerda) |
| Stick direito X (`rx`) | eixo 2 | 3 / 2 | `w = −RX · w_max · escala` (stick para a direita = horário) |
| R2 (`r2`) | eixo 5 (0..1) | 5 / 5 (−1..1, normalizado) | > 0,5 ⇒ **turbo**: escala 1,0 (senão 0,5) |
| ✕ cross | botão 0 | 0 / 1 | chute reto `kick_flat_max` (6,5 m/s) enquanto pressionado |
| ○ circle | botão 1 | 1 / 2 | chip `kick_chip_max` (6,0 m/s), `kick_angle = chip_angle_deg` (45°) |
| R1 | botão 10 | 5 / 5 | liga/desliga o dribbler (0,5·`dribbler_rpm_max` = 3000 rpm) |
| D-pad ← / → | botões 13 / 14 | hat 0 (x = −1 / +1) | robô anterior / seguinte (do time selecionado) |
| Options | botão 6 | 9 / 9 | teleporta o robô selecionado para (0, 0, 0) |
| PS | botão 5 | 10 / 12 | parar: comando zero + dribbler desligado |

Curva: zona morta **radial** 0,08 no stick esquerdo (reescalada para chegar a 1 no fim de curso) e 1-D no `rx`, depois
expo `y = 0,7·x + 0,3·x³`. `v_max = 3,0 m/s`, `w_max = 10 rad/s` vêm de `config/robot_limits.json` (`RobotSpec`), então
a escala normal (0,5) dá 1,5 m/s / 5 rad/s. O chute fica "armado" enquanto o botão está pressionado (o mundo consome uma
vez e aplica *cooldown* de 0,1 s), então pode-se segurar ✕ e esperar a bola chegar à face.

JSON de mapa (parcial, mesclado sobre `base`):
```json
{"base": "gamecontroller", "name": "meu pad", "axes": {"rx": 3}, "buttons": {"r1": 5, "options": 9},
 "invert": {"ly": false}, "hat_dpad": true, "deadzone": 0.08, "expo": 0.3, "turbo_threshold": 0.5,
 "turbo_scale": 1.0, "normal_scale": 0.5, "trigger_range": "auto"}
```
`trigger_range`: `auto` (GC ⇒ 0..1; cru ⇒ −1..1), `signed`, `unit`. `JoyMap.save()` grava o mapa completo (`base: null`).

### Teclado (fallback automático sem pad)

`W/S` frente/trás, `A/D` esquerda/direita, `Q/E` gira CCW/CW (setas também movem), `Shift` turbo, `Espaço` chute reto,
`C` chip, `R` dribbler, `,`/`.` (ou `[`/`]`) robô anterior/seguinte, `Home`/`T` teleporta ao centro, `Esc`/`X` para.
Os sticks virtuais sobem em rampa de 0,25 s. No Replay, `Espaço` = Play/Pause. As teclas são ignoradas quando um campo
numérico/combobox tem o foco (clique no campo para devolver o foco).

## Decisões

- **Relógio**: o Debug usa um acumulador de relógio de parede num `QTimer` de 5 ms (no Windows o `QTimer` padrão tem
  resolução de ~15,6 ms; com `PreciseTimer` + acumulador a média fica em 60,0 Hz mesmo com jitter; medido 59,9–60,2 Hz
  aqui). Backlog acima de 4 passos é descartado (janela minimizada, etc.).
- **Bridge com thread**: nenhuma chamada a `world.state()` por frame — a GUI usa o `WorldState` já produzido pelo tick do
  servidor (`server.last_state`); teleportes/θ entram pelo `RLock` do mundo. Hz mostrado = `server.hz_actual`.
- **Replay** reproduz exatamente `dtssl replay` (free-run inteiro, `prev_cmds=None`): `e_pos` em `h` amostras após a
  primeira pose = `epos_full[h]` da CLI. O robô do evento é o `robot_id` de `commands.parquet`, exibido com a cor de
  `--team` (os logs não têm cor). O painel de θ, em Replay, atua na planta do replay (o mundo local continua existindo,
  parado).
- **Backend MuJoCo** na GUI: `commanded()` lê `world.robots[key].cmd`; o restante é a interface `World`. Trocar backend
  recria o mundo (poses voltam ao `Scene.default`), preserva θ, e reinicia o servidor se estava ligado.
- **Sem `sys.path`**, sem estado global de Qt fora do `QApplication`; `pyqtgraph` configurado (`background="k"`) no import
  de `gui.plots`.

## Limitações conhecidas

- Não publica o comando do joystick por `RobotControl` UDP para um simulador externo (item opcional da SPEC §4.5): no
  Debug com *publish vision* o mundo local **é** o simulador; para teleoperar o grSim seria preciso um cliente UDP
  (a construção da mensagem já existe em `dtssl.bridge.fake_strategy.FakeStrategy.build_control`).
- Um único robô comandado pelo pad de cada vez; sem vibração (`rumble`) nem LED do DualSense.
- Replay só do robô do evento (um por segmento, como o loader) e só para plantas comportamentais (`fopdt`/`ideal`).
- Rastro apenas do robô selecionado (e da verdade); sem histórico da bola.
- Detecção de pad depende do SDL: em `pygame.joystick` cru os índices variam por SO (por isso os presets e o `--joy-map`).
  Hot-plug foi testado só com o provedor falso (sem pad físico neste contêiner); a lógica de rescan é a mesma.
- `QGraphicsView` sem OpenGL: com 12 robôs + rastros + 4 plots o custo medido fica bem abaixo de 1 core a 60 Hz de
  dados/30 Hz de desenho; em máquinas fracas reduza `--n-blue/--n-yellow`.
- Não há persistência de layout de janela/último dataset entre execuções.

## Verificação

- `QT_QPA_PLATFORM=offscreen python3 -m pytest -q`: **295 passed, 1 skipped** (skip pré-existente, dependente de dataset).
  Só a GUI: `pytest tests/test_gui_joystick.py tests/test_gui_replay.py tests/test_gui_window.py` → 30 passed em ~4 s.
- `ruff check src/dtssl/gui tests/test_gui_*.py` limpo (o repositório usa só o *lint*, não `ruff format`).
- `dtssl info` lista `dtssl.gui.cli ok`; `dtssl gui --help` e `python -m dtssl.gui --help` funcionam.
- Fumaça manual (offscreen): Debug com teclado (robô anda, plots cmd × corpo, 60 Hz), Bridge com thread e em modo passo
  (visão a 60 Hz em `224.5.23.2:10006`, teleportes), Debug + *publish vision*, Replay `side_to_side_01_05`
  (`e_pos@h`: 6=0,034, 12=0,051, 24=0,042, 42=0,034, 60=0,076, 90=0,079 m com o θ oficial; preset *ideal* piora),
  backend `mujoco-velocity` (60 Hz com 2×2 robôs).
- **Não verificado aqui**: pad físico (DualSense) — só provedores falsos e `PygameBackend` sem dispositivos; janela real
  no Windows/WSLg (só `offscreen`).

## Aba 3D com o CAD (C6, 08/09/2026)

`src/dtssl/gui/view3d.py` (`View3D`, `pyqtgraph.opengl.GLViewWidget`) + `src/dtssl/gui/scene3d.py` (geometria pura,
sem Qt): o centro da janela virou um `QTabWidget` com **Field (2D)** (a `FieldView` de sempre, interativa) e
**3D (CAD)**. A aba 3D desenha campo (chão em dois tons, linhas, gols), bola e robôs com as **malhas OBJ do C5**
(`dtssl.physics.assets`, por default o par LOD: chassi 10,8 k faces = só o exterior da malha completa, roda 1,2 k;
`RobotMeshes.build(cad=True, lod=True)`; o botão **HQ** troca pelas malhas completas de 37 k + 4×8 k faces), placa SSL na tampa
(cor do time + 4 pontos do padrão do rulebook, `ID_PATTERN` do `mjcf`), anel branco no robô selecionado. Tudo é
construído do `WorldState` → funciona com qualquer backend (`fopdt`, `ideal`, `mujoco-*`) e no Replay.

- **Rodas giram** em todos os backends: `WheelSpin` integra `omega_i = (-sin phi_i vx + cos phi_i vy + R w)/r` da
  velocidade de corpo do estado (cinemática inversa; o `WorldState` não expõe os ângulos das rodas da rota b) e
  `wheel_transform` aplica `rot_z(phi_i) · rot_x(-psi_i)` (eixo da malha em +x → direção radial; giro em torno de
  −u_r como a dobradiça do MJCF). Teste de rolamento sem escorregamento: a componente tangencial da velocidade do
  ponto de contato de cada roda é nula (`test_wheel_spin_rolls_without_slip`).
- Câmera: presets `iso`/`top`/`side`/`goal` (`CAMERA_PRESETS`, elevação/azimute/distância), **Follow** (centro da
  câmera segue o robô selecionado), **CAD** (malhas ↔ prisma em D + cilindros), **Wheels** (liga/desliga o giro),
  **Fit (F)**; mouse = órbita/pan/zoom do `GLViewWidget`. O preset `top` tem x para a direita e y para cima, como a
  aba 2D. Teleporte e seleção por clique continuam só na aba 2D.
- Custo: `GLMeshItem` do pyqtgraph 0.14 usa VBOs (upload uma vez; por quadro só `setTransform` de 12×6 itens e um
  `update()`), e a aba só é atualizada quando visível (`showEvent` reaplica o último estado). O custo é dominado
  pelo número de triângulos: 12 robôs com as malhas completas (830 k triângulos) = 27 ms/quadro na Intel Iris Xe
  do PC do Victor (medido em 08/09, 1440×924) e ~140 ms em software (llvmpipe); com o par LOD (185 k triângulos)
  cai para ~1/3 (47 ms em software). Por isso o LOD é o default e **HQ** é opcional. Sem GPU use `--no-cad`
  (primitivas) ou `--no-3d` (não cria a aba).
- Dependência nova: `PyOpenGL` (extra `dtssl[gui]`); sem ele (ou sem contexto GL, p.ex. `QT_QPA_PLATFORM=offscreen`)
  a aba mostra um rótulo com o motivo e o resto da GUI segue normal. `app.run` liga
  `AA_ShareOpenGLContexts` antes do `QApplication` porque o pyqtgraph guarda os *shaders* por processo.
- Testes `tests/test_gui_view3d.py` (15; 15 passam também no Windows com GL real, `QT_QPA_PLATFORM=windows`): geometria (OBJ, fechamento de malhas, placa, transformações, rolamento,
  campo), widget sem contexto (offscreen: constrói, aceita quadros, esconde/mostra, troca CAD/campo), presets/follow,
  renderização real (`grab_image` ≠ quadro vazio, `top` muda a imagem — roda sob `xvfb-run` ou num desktop; é
  *skip* no offscreen), `MainWindow` com/sem a aba. Captura: `docs/img/gui_3d_tab.png`.

## Aba Robot: telemetria por robô (19/09/2026)

Pedido da orientadora em 18/09: ver cada robô em destaque com os dados de hardware. A aba **Robot** (`gui/robot_tab.py`)
mostra o robô selecionado (o mesmo da toolbar, das teclas `,`/`.` e do clique no campo): um *spotlight* de cima
(chassi com a face do dribbler, as quatro rodas coloridas pela velocidade, setas de velocidade de corpo comandada
(tracejada) e resultante (cheia), arco de ω, a bola quando o sensor a vê), a tabela de estado (pose, v comando, v
resultante, idade do comando, watchdog, dribbler, sensor de bola, chutes do mundo), as quatro rodas em barras
(comando × resultante, rad/s) e nos últimos 10 s como curvas, e o bloco de hardware (bateria, capacitor, IR).

De onde vem cada valor (`dtssl/bridge/telemetry.py`, um `RobotTelemetry` por fonte):

- **gêmeo** (`twin_telemetry`): do `WorldState` e do último `RobotCmd`; as velocidades por roda pela cinemática inversa
  de `dtssl.kinematics` (a mesma que gira as rodas da aba 3D), com a zona morta por roda aplicada ao comando quando o
  mundo a tem ligada; idade do comando e watchdog pelo `t_recv` do comando e `watchdog_s` do mundo. **Bateria e capacitor
  não existem no modelo identificado**: `SyntheticHardware` é um modelo *ilustrativo* (capacitor esvazia no chute e
  recarrega com `capacitor_tau_s`; bateria cai com `battery_drain_per_rad · Σ|ω_roda| · dt`), parâmetros em
  `config/telemetry.json` (`synthetic`), e a aba escreve "modelo ILUSTRATIVO" por cima. Nada disso toca a simulação.
- **rádio** (`TelemetryReceiver`, `dtssl gui --telemetry` ou `real.enabled` no JSON): os datagramas
  `RCCommunication.Feedback` do `rc_communication.proto` (cópia verbatim do ssl-unification em `bridge/proto`, `_pb2`
  gerado com o mesmo protoc 25.1 dos demais), que os robôs reais mandam pelo `CommunicationWifi` (multicast
  224.0.1.99, porta 19903; comandos saem na 19901): vx, vy, w; velocidade comandada e medida por motor (`d_speed`/`c_speed`,
  mapeamento em `real.fields`), PWM, erro do PI e corrente por motor, `capacitorCharge`, `batteryCharge`, `hasBall`. As
  unidades são as que o firmware reporta; os rótulos vêm de `real.units` e nada é convertido. O `Feedback` não traz o
  time: `real.team` (default: o `--team` da GUI) diz de quem são os ids. Registro mais recente por id, descartado
  depois de `stale_s`; quando há registro fresco do robô selecionado, o bloco de hardware passa a mostrar os valores
  reais e a tabela por motor é preenchida, ao lado do gêmeo (barras: real em rosa).

Sem robôs reais a aba funciona só com a fonte gêmeo; com eles, é o uso de gêmeo digital como monitor (previsto ×
medido para o mesmo robô), sem mudar nada além de ligar o receptor. Flags: `--no-robot-tab`, `--telemetry`,
`--telemetry-config`. A aba só redesenha quando visível. Testes: `tests/test_telemetry.py` (7: IK, zona morta,
hardware ilustrativo, parser do Feedback cru/embrulhado/comando/lixo, receptor com socket em loopback, config) e
`tests/test_gui_robot_tab.py` (5: widgets pintam, registros gêmeo e real na aba, `MainWindow` com e sem a aba, flags).

### Vista 3D do robô selecionado e seletor na própria aba (24/09/2026)

Pedido do Victor em 24/09: ver o robô selecionado em 3D, girável em qualquer eixo como uma peça num CAD, com as rodas
se mexendo, e escolher o robô na própria aba. O lado esquerdo da aba passa a ser `RobotView3D` (`gui/robot_view3d.py`,
`pyqtgraph.opengl`), com o *spotlight* 2D uma troca ao lado (`3D`/`2D` no cabeçalho; a aba cai no 2D sozinha quando
não há GL ou com `--no-3d`):

- **Peça, não câmera**: a câmera fica parada e o robô gira. O arrasto esquerdo é um *arcball* (`scene3d.Arcball`,
  esfera de Shoemake): o par de pontos do arrasto vira dois vetores na esfera, expressos nos eixos da câmera
  (`right/up/toward`, lidos da `viewMatrix` do `GLViewWidget`), e a rotação entre eles pré-multiplica a matriz da
  peça, em torno do centro do robô (z = 0,07 m). Qualquer eixo, sem trava de gimbal, como no SolidWorks/Fusion. Roda
  do mouse aproxima, botão do meio arrasta, duplo clique ou `R` reinicia, `F` reajusta a distância, setas giram 5°,
  `Auto` liga a mesa giratória. Presets `iso`, `frente` (dribbler para o observador), `lado`, `topo`, `baixo` (rodas).
- **Rodas girando pelo registro**: `scene3d.WheelAngles` integra os ângulos com `wheel_meas` do `RobotTelemetry`
  (rad/s) e o `t` do registro; cada roda é colorida pela sua velocidade (vermelho para frente, azul para trás, cinza
  parada, saturando em 120 rad/s). `rodas: gêmeo` usa a cinemática inversa do gêmeo; `rodas: real` usa o `Feedback` do
  rádio quando há registro fresco (senão volta ao gêmeo). Bola no dribbler quando o sensor a vê; setas de velocidade de
  corpo comandada (laranja) e resultante (ciano) por cima da tampa; tríade do frame de corpo (x vermelho = dribbler).
- **Iluminação**: o `shaded` do pyqtgraph ilumina por trás da peça (uma peça sozinha fica quase preta): `RobotView3D`
  registra `dtssl_headlight`, o *vertex shader* do próprio `shaded` (segue a versão do pyqtgraph) com um *fragment*
  de luz frontal e 35 % de ambiente; se algo falhar, cai no `shaded` (desde 09/10/2026 o shader mora em
  `gui/glshading.py` e a vista 3D do campo usa o mesmo). Malhas CAD em resolução cheia por default (é
  um robô só; `HQ` desliga se pesar no WSLg), placa SSL com o id do robô.
- **Seletor na aba**: combo com todos os robôs presentes dos dois times mais `<`/`>`; emite `robot_requested` e o
  `MainWindow` chama `controller.select`, então vale para toda a GUI (campo 2D, aba 3D, plots), igual ao clique no
  campo e às teclas `,`/`.`. A troca de backend zera os ângulos das rodas (`RobotTab.reset_motion`).

Nada disso toca a simulação nem os dados; é só desenho a partir do `RobotTelemetry`. Testes: `tests/test_gui_view3d.py`
(+5 puros: mapa do arcball, rotações próprias, arrasto = rotação em torno do eixo da tela, integração das rodas,
transformadas da peça e setas) e `tests/test_gui_robot_tab.py` (+2: seletor e troca 3D/2D; `RobotView3D` com registros,
fonte real, arrasto, presets, teclado, auto-rotação, oculta = barata; e o `MainWindow` selecionando pelo combo da aba).
Verificado renderizando de verdade sob `xvfb` + Mesa (llvmpipe) no sandbox: `docs/img/gui_robot_tab_3d.png`.

## Chute e dribbler nas vistas 3D (06/10/2026) e cores do CAD (07/10/2026)

As duas vistas 3D (campo, `view3d._RobotItems`; aba Robot, `RobotView3D._build_items`) passaram a desenhar o chute e o
dribbler do CAD como itens estáticos presos ao chassi: `scene3d.mechanism_meshes(lod)` lê `ssl_kicker*.obj` e
`ssl_dribbler*.obj` de `physics/assets` (mesmo frame do OBJ do chassi, origem z no plano dos eixos das rodas) e
`RobotMeshes.mechanisms` os carrega junto (vazio no modo primitivo); os `GLMeshItem` recebem a transformada do
chassi a cada quadro. Campo com 12 robôs usa os LOD (1 490 + 3 486 faces por robô desde a LOD de 09/10); a aba Robot usa a resolução cheia
(4 990 + 14 862). Nada se move ainda nas vistas da GUI (o dribbler físico do MuJoCo, `dribbler="bar"`, gira a barra
só no modelo; a GUI continua desenhando o CAD estático). Origem e proveniência das malhas: `docs/refactor_notes/physics.md`,
seção "Malhas do CAD".

Cores (07/10): as quatro malhas (chassi, roda, chute, dribbler) agora saem do Inventor com as cores do CAD, agrupadas
por material no OBJ (`usemtl m_rrggbb` + `ssl_<tag>.mtl`). `scene3d.parse_obj(data, materials)` devolve `Mesh.colors`
(RGBA por face) e `_asset_mesh(key, lod)` lê o OBJ com o MTL de `meshes.json`, então `cad_meshes()` e
`mechanism_meshes()` vêm coloridas (preto da tampa e do chassi, cinza e branco do módulo do dribbler, cubos pretos e
roletes cinza nas rodas); `MECHANISM_RGBA` deixou de existir (`MECHANISM_KEYS`). `view3d._mesh_kwargs` e
`robot_view3d._mesh_kwargs` passavam `faceColors` ao `GLMeshItem` quando a malha tem cores (senão `color` liso, como
nas primitivas); desde 09/10 isso mora em `gui/glmesh.py` (`mesh_item`/`mesh_data`: cores por vértice nas malhas
suavizadas, por face nas demais). Na aba Robot as rodas continuam coloridas pela velocidade: `robot_view3d.wheel_face_colors(base,
omega)` tinge as cores do CAD para o vermelho (frente) ou azul (ré) em 32 níveis e a malha só é reenviada à GPU
(`setMeshData(meshdata=mesh_data(tinted))`) quando o nível muda. Placa de id: `RobotMeshes.build` usa
`wheel.r + mjcf.cad_plate_z()` (plano do decalque do padrão no CAD, 148,7 mm acima do piso) em vez do topo da bbox
(154,5 mm): as bolinhas deixaram de flutuar sobre a tampa. Testes: `tests/test_gui_view3d.py`
(`test_cad_meshes_match_the_physics_assets` confere as 13 cores do chassi, `test_mechanism_meshes_match_the_physics_assets`,
`test_robot_meshes_build_all_variants` confere cores por face nas três variantes e a altura da placa).

## Elenco de 11 robôs, reservas no banco e substituição por Shift+clique (07/10/2026)

Pedido do Victor em 07/10: 11 robôs por time, com os inativos fora das bordas para não atrapalhar, e colisão nas
traves e bordas no modo debug. O lado do mundo está em `docs/refactor_notes/bridge.md` (seção de 07/10: `park_spot`,
`Scene.default(n_active=...)`, gols sólidos no `TwinWorld`); aqui só o que a GUI faz com isso.

- **Defaults**: `Controller(n_blue=ROSTER_SIZE, n_yellow=ROSTER_SIZE)` e `MainWindow` idem; o número em campo
  segue a divisão do campo (6 na Div B, 11 na Div A; seção seguinte) e `--n-active N` fixa outro número. O padrão
  (`dtssl gui`) é a Divisão B com 6 em campo e 5 no banco de cada time; `--n-blue 6 --n-yellow 6` reproduz a
  configuração antiga sem ninguém no banco. Vale para todos os backends (`_make_world` passa `n_active`), e a
  troca de backend ou o `reset` recoloca cada um na vaga.
- **Campo 2D** (`field_view.py`): as reservas são desenhadas na vaga, além da parede de −y, com opacidade
  `PARKED_OPACITY = 0,45` (`RobotItem.set_present`), sem marcador de bola; `fit_field` reserva `PARK_MARGIN_MM = 500`
  abaixo da arena para o banco caber. `robot_at(pt, present_only=True)` ignora o banco, então Ctrl+clique e as
  setas de seleção só alcançam quem está em jogo. **Shift+clique** é a substituição: sobre um robô em jogo emite
  `robot_park_requested(team, id)` (vai para o banco); sobre o campo vazio emite `robot_enter_requested(x, y)` e o
  controlador traz o **menor id do banco** do time do joystick (`--team`) para aquele ponto, de frente para o gol
  adversário (θ = 0 azul, π amarelo), e o seleciona. Clique simples (teleporte), direito (bola), Ctrl (seleção), roda
  e arrasto continuam iguais. `Controller.park_robot(key)` e `enter_robot(x, y, team=None)` são os ganchos (falham
  em Replay e devolvem `False`/`None`); `robot_keys(team, present=True)` ganhou o filtro.
- **Aba 3D** (`scene3d.py`, `view3d.py`): um avental escuro de `APRON_WIDTH = 0,6 m` (`apron_quads`, `APRON_RGBA`)
  em volta da arena mostra onde o banco fica; as reservas são desenhadas com as rodas paradas (`compute_frame`
  só integra `WheelSpin` para robôs presentes; `show_absent=False` as esconde) e o anel de seleção não aparece em
  robô no banco. Custo: 22 robôs desenhados em vez de 12 (os LOD continuam o default); se pesar, `--n-blue 6
  --n-yellow 6` ou `--no-cad`.
- **Visão e bridge**: nada muda no que sai pela rede, `robots_of` só devolve os presentes; a aba Robot e o combo
  de robô listam só os presentes. No modo Bridge a substituição pelo clique também vale (é `set_present` no mundo,
  o mesmo caminho do `TeleportRobot{present}` do simcontrol).
- Testes: `tests/test_gui_window.py` (reserva visível esmaecida na vaga e ignorada por `robot_at`; sinais de
  Shift+clique; `test_controller_roster_substitutions`: 22 robôs, 12 presentes, 10 no banco no próprio lado,
  `enter_robot`/`park_robot`, banco amarelo esvazia depois de 5 entradas, `reset_scene` restaura) e
  `tests/test_gui_view3d.py` (reserva desenhada com rodas paradas, avental).

## Seletor de campo Div A / Div B (07/10/2026)

Pedido do Victor em 07/10: uma caixa de seleção para escolher entre os campos das Divisões A e B na execução de
debug, com 6 robôs de cada lado na B e 11 na A, e verificar em que modos faz sentido ter os dois campos.

- **Presets** (`dtssl.config`): `FieldPreset(name, label, path, field, robots_per_team)`, `FIELD_PRESETS`
  (`divB` = `config/field_divB.json`, default e divisão do RobôCIn; `divA` = `config/field_divA.json`, novo),
  `load_field_preset("divA" | "A" | "Division A" | caminho de um JSON em mm)` e `field_presets()`. A chave
  `robots_per_team` do JSON (6 e 11, os máximos do livro de regras por divisão) é lida só pela GUI e pelas CLIs; a
  `FieldGeometry` e o pacote de geometria a ignoram. Div A no JSON: 12 × 9 m, gol 1,8 × 0,18 m, área de defesa
  3,6 × 1,8 m, marca de pênalti a 8 m, círculo central r 0,5 m, linhas 10 mm, `boundary_width` 300 (as regras dão
  0,3 m nas laterais e 0,6 m atrás dos gols; o `SSL_GeometryFieldSize` só tem um valor, então 0,3 m em volta).
  Conferido no livro de regras da SSL em 07/10/2026 (seção Field Setup).
- **Controller**: `field: FieldPreset | str | Path` no construtor (`--field`), `field_preset`, `field_name`,
  `n_active` virou propriedade (`robots_per_team` do preset, ou o `--n-active` fixado em `n_active_pinned`),
  `set_field(preset)` reconstrói o mundo na nova geometria como `set_backend` faz (θ preservado, elenco
  reposicionado pelo `Scene.default` com o `n_active` da divisão, servidor reiniciado se estava ligado, mundo antigo
  mantido se a construção falhar) e emite `field_changed(name)`. Um preset inválido ou arquivo ausente vira
  mensagem no Log, sem trocar nada.
- **Toolbar**: combo `field` (`Div B`, `Div A`; um `--field` com JSON próprio aparece com o nome do arquivo) ao lado
  do backend. Ao trocar: campo 2D e 3D redesenhados (`FieldView.set_field`, `View3D.set_field`, que já escala a
  câmera pelo comprimento do campo), rastros e plots limpos, combos de robô refeitos (6 ou 11 por time), Log com
  `field: Div A (12 x 9 m): 22 robots on the field (11 per team), 0 parked`.
- **Em que modos vale**: **Debug** (o uso pedido: mundo local, colisões nas paredes e gols do campo escolhido) e
  **Bridge** (o campo vai no pacote de geometria da visão, então a estratégia externa recebe 12 × 9 m e 11 robôs
  por time; a troca reinicia o `SimServer` e o primeiro quadro já leva a nova geometria; o lado da estratégia
  precisa estar configurado para a mesma divisão, o ssl-unification tem o seu próprio número de robôs). **Replay**
  não: os eventos do dataset são logs do RobôCIn gravados em campos da Divisão B, e o campo é propriedade dos dados;
  o combo fica desabilitado e as vistas desenham a Divisão B (`app.REPLAY_FIELD`), voltando ao campo do mundo ao
  sair do Replay. O mesmo preset serve ao `dtssl serve --field divA` (geometria publicada e 11 × 11 sem
  `--n-blue/--n-yellow`) e ao `dtssl mjcf --field divA` (modelo e viewer na Divisão A, arquivos `ssl_route_<r>_divA.*`).
- CLI: `dtssl gui [--field divB|divA|FILE] [--n-active N]` (`--n-active` sem default: segue a divisão).
- Testes: `tests/test_paths.py` (presets e aliases, JSON próprio, arquivo ausente), `tests/test_gui_window.py`
  (`test_controller_field_switch_follows_the_division`: B → A → B, 22 em campo na A e 12 + 10 no banco na B, gols
  no lugar novo, `reset_scene`, preset quebrado, `--n-active` fixo; `test_window_field_box_switches_the_world_and_replay_draws_div_b`:
  combo, vistas, combos de robô, Replay desabilita e desenha a B, `--field divA` na abertura), `tests/test_world_twin.py`,
  `tests/test_physics_world.py`, `tests/test_physics_mjcf.py` e `tests/test_bridge_proto.py` (mundo, MJCF, pacote de
  geometria e CLIs na Divisão A).

## Manchas brancas na vista 3D do campo e verde das placas (09/10/2026)

Sintoma (captura do Victor, modo Debug, aba do campo em 3D): os robôs pretos apareciam salpicados de manchas brancas,
"um brilho", e as placas dos motores vistas pelos recortes das rodas tinham um verde muito claro.

- **Causa das manchas**: não era a luz, era a LOD. Renderizando de verdade no PC (`_to_delete\gl_probe.py`, GL do
  Windows, `grab_image()`), a malha cheia com o `shaded` sai limpa e a LOD com o mesmo shader mostra as manchas. A LOD
  antiga decimava cada peça pela mesma razão e `reducepatch` mantém os vértices na superfície, então as cordas da
  tampa e da placa quase branca sob ela (`Gehäuse_Unterplatte`) afundavam ~1 mm uma pela outra e a placa clara e as
  peças de alumínio furavam a tampa preta. Correção nos *assets*: `tools/cad_lod.m` (LOD só das peças vistas de fora,
  orçamento de faces por área visível; detalhes em `physics.md`, "LOD para as vistas 3D").
- **Luz da vista do campo**: `view3d.View3D` usava o `shaded` do pyqtgraph, que ilumina por trás (as faces voltadas
  para a câmera ficavam em 20 %, o que realçava qualquer face clara). O `dtssl_headlight` da aba Robot foi movido para
  `src/dtssl/gui/glshading.py` (`headlight_shader()`, mesma queda para `shaded` se falhar) e a vista do campo passa o
  shader à bola e aos `_RobotItems` (parâmetro `shader`, default `shaded`); `robot_view3d.py` importa dali.
- **Verde das placas**: as PCBs (`Motor_board_v3_0_BOARD` × 4, `MainBoard_SSL_2024_F7_BOARD`,
  `processor_board_v1_0_BOARD`) carregam no Inventor a aparência `BoardColor`, creme (247, 249, 209). Nos arquivos
  `ssl_chassis.obj`/`_lod.obj`/`.mtl` o material virou `m_1f4d2e` "BoardColor (override)", verde musgo (31, 77, 46),
  mais escuro que o piso (`FLOOR_RGBA` 0,13/0,47/0,20) e que a borda; o exportador ganhou `AppearanceOverrides` com
  esse default para a próxima exportação. Vale para a GUI (os dois modos) e para o `visual="cad"` do MuJoCo.
- Conferido em renders reais no PC (`_to_delete\gl_after_closeup_lod.png`, close dos robôs na LOD, e
  `gl_after_iso_divA.png`, campo da Divisão A com 22 robôs): sem manchas na LOD, placas verde-musgo. Testes: `tests/test_physics_cad.py`
  (`n_parts` da LOD ≤ da malha cheia), `test_physics_dribbler.py`, `test_gui_view3d.py`, `test_gui_robot_tab.py`.

## Polígonos das rodas no modo CAD e 60 Hz na vista do campo (09/10/2026, tarde)

Sintoma (captura do Victor, aba do campo em 3D, modo CAD sem HQ, close de uma roda): roletes como cristais pontiagudos
e cubo sextavado, "os polígonos da roda estão horríveis". Pedido: melhorar sem comprometer os 60 Hz.

- **Diagnóstico da roda**: a LOD da roda tinha 1 200 faces para 82 peças (75 visíveis), e cada um dos 20 roletes caía
  no piso de 24 faces do `cad_lod` (um rolete de 24 triângulos é um cristal); além disso tudo era desenhado com
  sombreamento chapado (normal por face), que marca cada faceta. Grade de candidatos renderizada no PC
  (`_to_delete\wheel_probe_grid.png`, orçamentos 1 200/3 000/5 000/9 000 × chapado/suave): a partir de 3 000 faces
  os roletes ficam redondos e o sombreamento suave apaga as facetas que sobram. Escolha: `wheel_lod` 5 000
  (`tools/cad_lod.m` e `inventor_export_cad.m`; `ssl_wheel_lod.obj` regenerado: 4 968 faces, 2 496 vértices, 5 cores,
  `meshes.json` atualizado).
- **Diagnóstico dos 60 Hz** (medido no PC, Intel Iris Xe, GL do Windows, `glFinish` por quadro): o custo do quadro na
  vista do campo é dominado pelo Python do pyqtgraph por item visível, cerca de 0,08 ms por `GLMeshItem` seja qual for
  o tamanho da malha (estado GL, matrizes, uniformes e atributos a cada `paint`); os triângulos custam poucos ms e a
  resolução quase nada. A Divisão A com 22 robôs tinha 8 itens por robô (chassi, 4 rodas, chute, dribbler, placa),
  183 itens visíveis e 22,3 ms por quadro (41 fps): já estava abaixo dos 60 Hz antes desta mudança. Então rodas mais
  ricas só cabem se o número de itens cair.
- **Sombreamento suave por grupos de suavização** (`scene3d.smooth_mesh`, aplicado por `RobotMeshes.build(smooth=True)`
  a todas as malhas, CAD e primitivas): `split_smoothing_groups` duplica os vértices nas arestas cujo ângulo diedro
  passa de `SMOOTH_ANGLE_DEG` (35°; componentes conexas do grafo de cantos de face com `scipy.sparse.csgraph`),
  `vertex_normals` faz a média ponderada por área das normais das faces e as cores por face passam a cores por vértice
  (`Mesh.normals`, `Mesh.vertex_colors`; `Mesh.colors` por face continua válido, a ordem das faces não muda). Cilindros,
  roletes e a tampa curva ficam redondos e as arestas de caixas continuam vivas; a normal por vértice do pyqtgraph
  (`MeshData.vertexNormals`, laço em Python por vértice) não é usada. O shader `dtssl_headlight` ilumina os dois lados,
  então o sentido das normais das primitivas (para dentro no `cylinder_mesh`) não aparece.
- **Dois itens GL por robô** (`gui/glmesh.py`): `scene3d.body_mesh(meshes, team, rid)` funde chassi, chute, dribbler e
  placa de id num só `Mesh` no frame do chassi (a placa entra em `z_top + PLATE_Z_OVER_TOP - z_chassis`) e
  `InstancedMeshItem` desenha a malha da roda nas quatro transformadas com um único `paint` (VBOs do `GLMeshItem` do
  pyqtgraph 0.14 ligados uma vez, só `u_mvp`/`u_normal` mudam entre os `glDrawElements`; `set_instances(QMatrix4x4...)`
  a cada quadro). `instancing_available()` confere a API (`upload_vertex_buffers`, `parseMeshData`, `currentModelView`,
  `currentProjection`); sem ela (pyqtgraph < 0.14) a vista volta a quatro itens de roda. `FastMeshData` substitui o
  cálculo de normais do pyqtgraph pelo de `scene3d`. `mesh_item(mesh, color, shader, cls=)` é o construtor comum das
  duas vistas (`view3d._RobotItems`, `robot_view3d._build_items`/`_ensure_plate`/`redraw`); a aba Robot continua com
  um item por parte (um robô só), com as rodas tingidas por vértice quando a malha é suave.
- **Medido no PC depois** (`_to_delete\gl_probe3.py`, mesmas condições): Divisão A, LOD, 51 itens visíveis, 11,5 ms por
  quadro (87 fps) contra 22,3 ms (41 fps) antes, com a roda de 4 968 faces; HQ (malhas cheias) 21,5 ms (46 fps) contra
  45 ms; `update_state` com 22 robôs 2,0 ms por chamada; primeira construção dos 22 robôs 92 ms. Renders olhados:
  `_to_delete\gl3_wheel_lod.png` (roda LOD: roletes redondos, cubo redondo, sombreamento suave),
  `_to_delete\gl3_closeup_lod.png` (dois robôs: placas, mecanismos e tampa corretos, sem artefatos de sombreamento),
  `_to_delete\gl3_wheel_hq.png`, `_to_delete\gl3_iso_divA.png`.
- Testes: `test_gui_view3d.py` ganha `test_smooth_mesh_keeps_box_edges_sharp_and_rounds_cylinders` (cubo: 24 vértices e
  normais iguais às das faces; cilindro: anel lateral compartilhado, tampas separadas, normais radiais),
  `test_vertex_normals_are_area_weighted_unit_vectors`, `test_merge_meshes_carries_normals_and_vertex_colours_only_when_all_parts_are_smooth`
  e `test_body_mesh_merges_chassis_mechanisms_and_plate_in_the_chassis_frame`; a razão de faces da LOD da roda passou
  a `< cheia` (`test_robot_meshes_build_all_variants`) e `< 70 %` (`test_physics_cad.py`); `test_gui_robot_tab.py` lê a
  cor da roda em `vertexColors()` quando a malha é suave. Suavizar as malhas custa uma vez por construção (scipy),
  não por quadro. Física, θ, `config/` e `data/` intocados; a mudança é só desenho.

## Correção 03/09/2026 — `ZeroDivisionError` do pyqtgraph ao trocar de robô

Sintoma (Windows, pyqtgraph 0.14.0, modo Debug): ao selecionar um robô, o console repete
`ZeroDivisionError ... AxisItem.tickValues` (e um `UnboundLocalError: painter` derivado) a cada repintura; a GUI
continua viva porque o pyqtgraph engole a exceção. Causa raiz, reproduzida no sandbox: um robô comandado e depois
deixado parado tem os estados da planta FOPDT decaindo como `v·exp(−Ts/τ)` sem nunca chegar a zero; após alguns
minutos os valores entram na faixa **subnormal** do IEEE-754 (~1e-308 … 5e-324). Ao selecionar esse robô, o
auto-range dos plots produz um intervalo de y com largura subnormal e o `tickSpacing()` do pyqtgraph 0.14
(`p10unit = 10**(floor((exp2−1)/3.32)−1)`) subfluxa para 0. Correção em `gui/plots.py`, em três camadas:
`ViewBox.setLimits(minXRange=0,25 s, minYRange=1e-3)`; valores `|v| < 1e-9` exibidos como 0 (`DISPLAY_FLUSH`,
só na exibição — a planta e o mundo não mudam, os goldens continuam bit-a-bit); janela deslizante sempre de
largura fixa (`[t_first, t_first+W]` → `[t_end−W, t_end]`) e `setYRange(−1, 1)` neutro no `clear()`;
`SafeAxisItem` que descarta espaçamentos nulos/não finitos. `gui/app.py`: `install_excepthook` (exceções
não tratadas, `warnings` e o `printExc` do pyqtgraph → `logging`) e um handler que espelha WARNING+ de
`dtssl`/`py.warnings` no dock *Log* (limitado a 1 linha/s por mensagem). Limite conhecido: erros dentro de
overrides virtuais do Qt (`paint`, `boundingRect`) são impressos pelo PySide no stderr de C e não podem ser
interceptados de Python. Testes: `test_safe_axis_item_survives_subnormal_ranges`,
`test_plots_paint_with_subnormal_and_zero_velocities`, `test_window_robot_switch_paints_after_long_idle_decay`
(os dois últimos falham com o `plots.py` anterior).
