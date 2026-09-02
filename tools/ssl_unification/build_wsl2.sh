#!/usr/bin/env bash
# build_wsl2.sh — clone + dependências + build do ssl-unification (RobôCIn) no WSL2 Ubuntu 22.04/24.04.
# Idempotente: pode ser executado várias vezes; cada etapa é pulada se já estiver feita.
#
#   tools/ssl_unification/build_wsl2.sh                       # clona em ~/ssl-unification e compila
#   tools/ssl_unification/build_wsl2.sh --dir ~/src/ssl-unification --jobs 8
#   tools/ssl_unification/build_wsl2.sh --no-deps --qt skip   # só cmake/build (deps já instaladas)
#   tools/ssl_unification/build_wsl2.sh --config-team yellow  # + gera config/local apontando ao gêmeo
#
# Opções:
#   --dir PATH          checkout existente ou destino do clone (default: ~/ssl-unification)
#   --repo URL          default https://github.com/robocin/ssl-unification.git
#   --branch NAME       branch a usar no clone (default: o default do remoto)
#   --update            git pull --ff-only + submodule update num checkout existente (default: não puxa)
#   --no-deps           não roda scripts/setup.py (apt) — use quando já instalou tudo
#   --qt script|apt|skip  como obter o Qt 6: 'script' = scripts/ubuntu/qt.sh do projeto (aqtinstall em /opt/qt,
#                       default); 'apt' = pacotes qt6-*-dev do Ubuntu (6.2 no 22.04, 6.4 no 24.04); 'skip'
#   --qt-version V      versão para o modo 'script' (default 6.4.0)
#   --jobs N            paralelismo do build (default: nproc)
#   --clean             apaga build/ antes de configurar
#   --force-os          prossegue mesmo fora de Ubuntu 22.04/24.04
#   --config-team blue|yellow   ao final, gera config/local com make_local_config.py (demais flags via --config-args "...")
#   --config-args "..." argumentos extras para make_local_config.py (ex.: "--n-robots 6 --behavior Debug --inet eth0")
#
# Nenhuma alteração em C++ (decisão D6 da SPEC): só config/local + este script de build.
set -euo pipefail

DIR="${HOME}/ssl-unification"
REPO_URL="https://github.com/robocin/ssl-unification.git"
BRANCH=""
UPDATE=0
NO_DEPS=0
QT_MODE="script"
QT_VERSION="6.4.0"
JOBS="$(nproc 2>/dev/null || echo 4)"
CLEAN=0
FORCE_OS=0
CONFIG_TEAM=""
CONFIG_ARGS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) DIR="$2"; shift 2 ;;
    --repo) REPO_URL="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --update) UPDATE=1; shift ;;
    --no-deps) NO_DEPS=1; shift ;;
    --qt) QT_MODE="$2"; shift 2 ;;
    --qt-version) QT_VERSION="$2"; shift 2 ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --clean) CLEAN=1; shift ;;
    --force-os) FORCE_OS=1; shift ;;
    --config-team) CONFIG_TEAM="$2"; shift 2 ;;
    --config-args) CONFIG_ARGS="$2"; shift 2 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log()  { printf '\033[1;34m[build_wsl2]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[build_wsl2] AVISO:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[build_wsl2] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 0. ambiente
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  case "${ID:-}-${VERSION_ID:-}" in
    ubuntu-22.04|ubuntu-24.04) log "Ubuntu ${VERSION_ID} detectado" ;;
    *) if [[ $FORCE_OS -eq 1 ]]; then warn "SO ${ID:-?} ${VERSION_ID:-?} não testado (prosseguindo por --force-os)";
       else die "esperado Ubuntu 22.04 ou 24.04 (WSL2); use --force-os para tentar mesmo assim"; fi ;;
  esac
else
  [[ $FORCE_OS -eq 1 ]] || die "/etc/os-release ausente; use --force-os"
fi
if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
  log "WSL2 detectado (kernel: $(uname -r))"
else
  warn "não parece WSL2 — tudo bem, o script funciona em Ubuntu nativo também"
fi
command -v git >/dev/null || die "git não encontrado (sudo apt install git)"

# ---------------------------------------------------------------- 1. clone / update
if [[ -d "$DIR/.git" ]]; then
  log "checkout existente em $DIR"
  if [[ $UPDATE -eq 1 ]]; then
    git -C "$DIR" pull --ff-only
  fi
  git -C "$DIR" submodule update --init --recursive
else
  [[ -e "$DIR" ]] && die "$DIR existe mas não é um clone git"
  log "clonando $REPO_URL -> $DIR (recursivo: cmake-common, soccer-common, scripts-ubuntu-common)"
  if [[ -n "$BRANCH" ]]; then
    git clone --recursive --branch "$BRANCH" "$REPO_URL" "$DIR"
  else
    git clone --recursive "$REPO_URL" "$DIR"
  fi
fi
[[ -f "$DIR/CMakeLists.txt" && -f "$DIR/scripts/setup.py" ]] || die "$DIR não contém CMakeLists.txt/scripts/setup.py"

# ---------------------------------------------------------------- 2. dependências (apt) — scripts/setup.py do projeto
if [[ $NO_DEPS -eq 0 ]]; then
  log "instalando dependências essenciais via scripts/setup.py (sudo apt): boost cmake clang-format doxygen g++ open-gl protobuf zlib"
  # 'qt' faz parte de essentials.txt, mas é tratado separadamente abaixo (o qt.sh chama 'who' para chown,
  # que devolve vazio em sessões WSL sem login e derruba o setup.py --essentials inteiro).
  ESSENTIALS="$(grep -v -E '^\s*(qt)?\s*$' "$DIR/scripts/essentials.txt" | tr '\n' ' ')"
  ( cd "$DIR/scripts" && sudo apt-get update -qq && sudo ./setup.py --install $ESSENTIALS )
  sudo apt-get install -y -qq libglu1-mesa-dev freeglut3-dev python3-pip >/dev/null
fi

# ---------------------------------------------------------------- 3. Qt 6 (cmake/utils.cmake procura $HOME/qt, $HOME/Qt, /opt/qt, /opt/Qt/<ver>/gcc_64)
first_qt_dir() { local d; for d in "$HOME"/qt/*/gcc_64 "$HOME"/Qt/*/gcc_64 /opt/qt/*/gcc_64 /opt/Qt/*/gcc_64; do
                   [[ -d "$d" ]] && { echo "$d"; return 0; }; done; return 1; }
have_qt_dir() { first_qt_dir >/dev/null; }
have_qt_apt() { [[ -d /usr/lib/x86_64-linux-gnu/cmake/Qt6 ]] || [[ -d /usr/lib/aarch64-linux-gnu/cmake/Qt6 ]]; }
case "$QT_MODE" in
  script)
    if have_qt_dir; then
      log "Qt 6 já instalado em $(first_qt_dir)"
    else
      log "instalando Qt ${QT_VERSION} com scripts/ubuntu/qt.sh (aqtinstall -> /opt/qt; leva alguns minutos)"
      ( cd "$DIR/scripts" && sudo bash ubuntu/qt.sh "$QT_VERSION" /opt/qt ) || warn "qt.sh terminou com erro (normalmente só o chown final em WSL); conferindo /opt/qt"
      have_qt_dir || die "Qt não encontrado em /opt/qt após qt.sh; tente --qt apt"
      sudo chown -R "$(id -un):$(id -gn)" /opt/qt 2>/dev/null || true
    fi ;;
  apt)
    if have_qt_apt; then
      log "Qt 6 (apt) já presente"
    else
      log "instalando Qt 6 via apt (qt6-base-dev, svg, opengl)"
      sudo apt-get install -y -qq qt6-base-dev qt6-base-dev-tools libqt6svg6-dev libqt6opengl6-dev libqt6openglwidgets6 \
        libgl1-mesa-dev libxkbcommon-dev >/dev/null || sudo apt-get install -y qt6-base-dev qt6-base-dev-tools libqt6svg6-dev
    fi ;;
  skip) log "Qt: pulado por --qt skip" ;;
  *) die "--qt deve ser script|apt|skip" ;;
esac

# ---------------------------------------------------------------- 4. configure + build (Release)
cd "$DIR"
[[ $CLEAN -eq 1 ]] && { log "limpando build/"; rm -rf build; }
if [[ ! -f build/CMakeCache.txt ]]; then
  log "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release"
  cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
else
  log "build/ já configurado (use --clean para reconfigurar)"
fi
log "cmake --build build -j${JOBS}"
cmake --build build -j"${JOBS}"

# CMakeLists.txt do projeto: add_subdirectory(src ${CMAKE_CURRENT_SOURCE_DIR}/bin) -> executável em <repo>/bin
BIN="$DIR/bin/ssl-unification"
[[ -x "$BIN" ]] || BIN="$(find "$DIR/bin" "$DIR/build" -maxdepth 3 -type f -name ssl-unification -perm -u+x 2>/dev/null | head -1 || true)"
[[ -n "$BIN" && -x "$BIN" ]] || die "binário ssl-unification não encontrado após o build (procurei em $DIR/bin e $DIR/build)"
mkdir -p "$DIR/config/local"

# ---------------------------------------------------------------- 5. config/local (opcional)
if [[ -n "$CONFIG_TEAM" ]]; then
  log "gerando config/local para o time $CONFIG_TEAM"
  # shellcheck disable=SC2086
  python3 "$HERE/make_local_config.py" --ssl-unification "$DIR" --team "$CONFIG_TEAM" $CONFIG_ARGS
fi

log "OK"
echo
echo "  binário : $BIN"
echo "  config  : $DIR/config/local/config.json  (gere com: python3 $HERE/make_local_config.py --ssl-unification $DIR --team blue|yellow)"
echo "  rodar   : $HERE/run_against_twin.sh --ssl-unification $DIR --team blue   # sobe 'dtssl serve' e o ssl-unification -running"
