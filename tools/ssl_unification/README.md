# `tools/ssl_unification/` — rodar a estratégia do RobôCIn contra o gêmeo

O `ssl-unification` (software de estratégia do RobôCIn, C++/Qt 6) fala o **ssl-simulation-protocol**
com o grSim/ER-Force. O gêmeo (`dtssl serve`) implementa o mesmo protocolo, então a estratégia
roda contra ele **sem nenhuma alteração em C++** (decisão D6 da `docs/SPEC_DTSSL.md`): só é preciso
compilar o ssl-unification no WSL2 e gerar um `config/local/config.json` apontando para o gêmeo.

| Arquivo | Para quê |
|---|---|
| `build_wsl2.sh` | clona (`--recursive`), instala dependências (`scripts/setup.py` do próprio projeto), instala o Qt 6 pelo script do projeto, compila em Release e imprime onde está `bin/ssl-unification`. Idempotente. |
| `make_local_config.py` | gera `config/local/config.json` (+ copia `config.ini`) a partir de um perfil de `config/shared/` com os parâmetros de rede/time/árbitro/comportamento do gêmeo. Só biblioteca padrão do Python. `--dry-run` mostra o diff. |
| `run_against_twin.sh` | sobe `dtssl serve` em background e o `ssl-unification -running` em primeiro plano; encerra o gêmeo ao fechar a estratégia. |

## 1. Build (WSL2 Ubuntu 22.04/24.04/26.04)

```bash
# no WSL2 (Ubuntu), dentro do repo digitaltwin
tools/ssl_unification/build_wsl2.sh                       # ~/ssl-unification, deps via sudo apt, Qt 6.4 em /opt/qt
tools/ssl_unification/build_wsl2.sh --dir ~/src/ssl-unification --jobs 8 --config-team yellow
tools/ssl_unification/build_wsl2.sh --no-deps --qt skip   # rebuild rápido
```

O que o script faz (cada etapa é pulada se já estiver feita):

1. checa Ubuntu 22.04/24.04/26.04 (`--force-os` para outros) e se está no WSL2;
2. `git clone --recursive https://github.com/robocin/ssl-unification.git` (submódulos `cmake/`,
   `libs/soccer-common`, `scripts/ubuntu`) ou usa o checkout existente (`--update` faz `pull --ff-only`);
3. `sudo ./scripts/setup.py --install boost cmake clang-format doxygen g++ open-gl protobuf zlib`
   (= `--essentials` menos o `qt`, que é tratado à parte porque `scripts/ubuntu/qt.sh` faz `chown`
   com `who`, vazio em sessões WSL sem login, e derrubaria o `--essentials` inteiro);
4. Qt 6: `sudo bash scripts/ubuntu/qt.sh 6.4.0 /opt/qt` (aqtinstall; o `cmake/utils.cmake` procura
   `$HOME/qt`, `$HOME/Qt`, `/opt/qt`, `/opt/Qt/<versão>/gcc_64`). Alternativa: `--qt apt`
   (`qt6-base-dev` + svg + opengl — Qt 6.2 no 22.04 é ≥ 6.1, suficiente);
5. `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j` — o `CMakeLists.txt`
   do projeto manda o executável para `<repo>/bin/ssl-unification` (não para `build/`).

Requisitos que o script não instala: `git`, `sudo`, ~3 GB livres (Qt + build), X11/WSLg para a GUI Qt
(Windows 11 já traz WSLg; no Windows 10 use um X server e `export DISPLAY=...`).

## 2. `config/local` apontando para o gêmeo

```bash
python3 tools/ssl_unification/make_local_config.py --ssl-unification ~/ssl-unification --team yellow
python3 tools/ssl_unification/make_local_config.py --ssl-unification ~/ssl-unification --team blue \
    --vision-port 10006 --inet lo --n-robots 6 --behavior Player \
    --base ~/ssl-unification/config/shared/ronaldinho/config.json --dry-run
python3 tools/ssl_unification/make_local_config.py --ssl-unification ~/ssl-unification --team blue \
    --bridge-json config/bridge.json        # portas/IP de visão lidos do config do gêmeo
```

O ssl-unification lê **`<projeto>/config/local/config.json` + `config.ini`** na inicialização
(`MainWindow::setup` → `loadEvent()`; a pasta é `ROBOCIN_PROJECT_PATH/config/local/`, gravada em
compile-time, e é recriada/salva ao fechar a GUI — `Ctrl+S` salva, `Ctrl+Shift+S` "salva como").
`config/local` está no `.gitignore` do ssl-unification. O gerador parte do perfil `ronaldinho`
(11 robôs, `CommunicationSim`, `CustomRef`) e reescreve exatamente estas chaves:

| Chave (`MainWindow.…`) | Valor |
|---|---|
| `CommunicationBase.comboBox` | `CommunicationSim` |
| `CommunicationBase.ParametersDialog.CommunicationSim.Communication.Port.Value` | `10301` (blue) / `10302` (yellow) — `config/bridge.json:control.port_*` |
| `…CommunicationSim.Communication."Using Hostname".{Value, Conditional.false.IP.Value}` | `false`, `--sim-ip` (default `127.0.0.1`) |
| `…CommunicationSim.Replacement.{IP,Port,Enable}.Value` | `--sim-ip`, `10300`, `true` (teclas P/M e Y/B+dígito teleportam via `SimulatorCommand`) |
| `VisionBase.comboBox` / `…DataWorld.PacketType.Value` | `DataWorld` / `Raw` |
| `…DataWorld.Raw.{IP,Port}.Value` | `224.5.23.2` / `10006` (`bridge.json:vision`; o default do C++ seria 10020 — o que importa é os dois lados baterem) |
| `…DataWorld.TeamColor.Value` | `Blue` / `Yellow` (`--attacking-side` opcional) |
| `Environment.ParametersDialog.Environment.General.INET.Value` | `--inet` (default `lo`) — interface do `joinMulticastGroup` (`Utils::getNetworkInterface`) |
| `RefereeBase.comboBox` / `…CustomRef.Command.Value` | `CustomRef` / `Referee_Command_FORCE_START` (o gêmeo não fala com o game-controller) |
| `RobotNN."BehaviorBase NN".comboBox` | `--behavior` (`Player`/`Debug`/`MouseAndKeyboard`) para `NN < --n-robots`, `TurnedOff` para os demais (até `Robot15`; blocos ausentes são clonados do `Robot00`) |

Tudo o mais do perfil (parâmetros de navegação, planning, `DecisionBase=Trainer`, etc.) é preservado.
Ver `--help` para todas as flags.

## 3. Rodar

```bash
# terminal 1 (opcional): dtssl gui   -> modo Bridge (observa) ou Debug (joystick)
# terminal 2:
tools/ssl_unification/run_against_twin.sh --ssl-unification ~/ssl-unification --team yellow
#   = dtssl serve --backend fopdt --config config/bridge.json  (background, log em /tmp/dtssl_serve.log)
#   + ~/ssl-unification/bin/ssl-unification -running
tools/ssl_unification/run_against_twin.sh --team blue --backend mujoco-velocity --record results/sessao_01
```

Conferências: o log do `dtssl serve` mostra `pkts yellow=…` crescendo e `watchdog=0`; na GUI do
ssl-unification o campo é desenhado a partir do pacote de **geometria** (enviado no frame 0 e a cada
60 frames — até 1 s para aparecer). Sem o C++: `dtssl fake-strategy --team yellow --target 1 0.5`.
Sessões gravadas com `--record DIR` saem no mesmo contrato dos logs (`commands.parquet`,
`processed_robots.parquet`, só o time de `--team`) e podem ser avaliadas pelo harness (`dtssl replay`).
Os dois arquivos são escritos **ao encerrar** o gêmeo (feche a estratégia ou `Ctrl+C`; o script manda `SIGINT`
ao `dtssl serve`, que grava e imprime `recorded N rows (...) -> ...` no log). Nunca mate o gêmeo com `kill -9`.

## 4. Rede no WSL2

| Cenário | Como |
|---|---|
| **Gêmeo e estratégia dentro do WSL2** (recomendado) | funciona sem ajuste: multicast `224.5.23.2:10006` em `lo` (`IP_MULTICAST_IF=127.0.0.1`, `IP_MULTICAST_LOOP=1` no gêmeo; `INET=lo` no ssl-unification), controle em `127.0.0.1:10301/10302`, `SimulatorCommand` em `10300`. |
| **Gêmeo no Windows, estratégia no WSL2** (NAT, default do WSL) | multicast **não** atravessa o NAT. No Windows: `dtssl serve --unicast <IP_DO_WSL>:10006` (IP do WSL: `hostname -I` dentro do WSL; muda a cada boot). No WSL: `make_local_config.py … --sim-ip <IP_DO_HOST_WINDOWS_VISTO_DO_WSL> --inet eth0` (o gateway: `ip route \| awk '/default/ {print $3}'`). O `DataWorld` faz `bind(AnyIPv4, 10006)` — recebe unicast mesmo que o `joinMulticastGroup` falhe. Liberar UDP 10300–10302 (entrada) no firewall do Windows para a interface `vEthernet (WSL)`. |
| Alternativa ao caso anterior | `networkingMode=mirrored` em `%USERPROFILE%\.wslconfig` (Windows 11 22H2+; `wsl --shutdown` depois): WSL e Windows compartilham `127.0.0.1` e as interfaces — volta a valer o cenário 1 (`--inet lo`, `--sim-ip 127.0.0.1`). |
| **Gêmeo no WSL2, GUI/joystick no Windows** | mesma lógica invertida: `dtssl serve --unicast <IP_WINDOWS>:porta` para o que roda no Windows. |

`--multicast-if` do `dtssl serve` deve ser o IP da interface em que o *outro* lado escuta;
`--bind-ip 0.0.0.0` (default) aceita comandos de qualquer interface.

## 5. DualSense (PS5)

O joystick é tratado **pelo gêmeo** (`dtssl gui`, modo *Debug*: `pygame`/SDL2, eixos → `vx, vy, ω`
de corpo, `✕` chute, `○` chip, `R1` dribbler, D-pad troca de robô), nunca pela estratégia. O
ssl-unification só recebe visão e responde com `RobotControl` dos robôs com comportamento `Player`;
os robôs que o joystick controla devem ficar `TurnedOff` (ou fora de `--n-robots`) na config da
estratégia, senão os dois mandam comando para o mesmo id. O comportamento `Debug` do ssl-unification
é o "ManualPackage" da GUI dele (Vx/Vy/Vw digitados), não o joystick. No WSL2 o controle USB/Bluetooth
não é visível para o Linux por padrão — mais um motivo para o `dtssl gui` rodar no Windows.

## Verificação feita nesta refatoração

- `make_local_config.py --dry-run` executado contra `config/shared/ronaldinho/config.json` real
  (ssl-unification `5.0.0`, snapshot de 25/10/2025): 8 linhas alteradas + `Robot11..15` criados;
  chaves conferidas em `CommunicationSim.cpp::buildParameters`, `DataWorld.cpp::buildParameters`,
  `GeneralEnvironment.cpp` (`INET` = `MappedComboBox` pelo **nome** da interface), `main.cpp`
  (`MAX_ROBOTS=16`, flag `-running`), `MainWindow.cpp::loadEvent`.
- `build_wsl2.sh --config-team yellow --jobs 4` executado por Victor em 03/09/2026 no WSL2 **Ubuntu 26.04**
  (Python 3.14.4, Qt 6.4.0 via `qt.sh` em `/opt/qt`): `[100%] Built target ssl-unification`, `config/local`
  gerado. `run_against_twin.sh --team yellow` (gêmeo em `~/.venvs/dtssl`, tudo dentro do WSL): 185 s a
  `hz=60.0/60 late=0`, `yellow≈4 pacotes/frame`, `watchdog=0`, `kicks=45` — drop-in confirmado.
