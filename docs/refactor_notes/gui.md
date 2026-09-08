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
          [--config config/bridge.json] [--joy-map arquivo.json|preset] [--n-blue 6 --n-yellow 6]
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
