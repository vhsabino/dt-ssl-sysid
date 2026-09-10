#!/usr/bin/env bash
# install_grsim_wsl.sh — clone + dependências + build do grSim (RoboCup-SSL) no WSL2 Ubuntu 22.04/24.04/26.04,
# para servir de baseline "física da liga" no harness do gêmeo (C2b, `dtssl analysis run protocol_holdout`).
# Idempotente: cada etapa é pulada se já estiver feita. Nada é instalado fora de $HOME além dos pacotes apt.
#
#   tools/external_sims/install_grsim_wsl.sh                 # ~/grsim, deps via sudo apt, build Release
#   tools/external_sims/install_grsim_wsl.sh --no-deps       # deps já instaladas (sem sudo)
#   tools/external_sims/install_grsim_wsl.sh --dir ~/src/grsim --jobs 8 --update
#
# Opções:
#   --dir PATH      checkout existente ou destino do clone (default: ~/grsim)
#   --repo URL      default https://github.com/RoboCup-SSL/grSim.git
#   --ref REF       tag/branch/commit a usar (default: o default do remoto; use uma tag para reprodutibilidade)
#   --update        git pull --ff-only num checkout existente
#   --no-deps       não roda apt (única etapa que exige sudo)
#   --jobs N        paralelismo do build (default: nproc)
#   --clean         apaga build/ antes de configurar
#
# ETAPA COM SUDO: só o `apt-get install` (etapa 1). O VarTypes é baixado e compilado pelo próprio CMake do grSim
# (ExternalProject) quando não está instalado no sistema — sem sudo.
# Depois: tools/external_sims/run_grsim.sh start   (headless, `-platform offscreen`; portas 10020/10300-10302)
set -euo pipefail

DIR="${HOME}/grsim"
REPO_URL="https://github.com/RoboCup-SSL/grSim.git"
REF=""
UPDATE=0
NO_DEPS=0
JOBS="$(nproc 2>/dev/null || echo 4)"
CLEAN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) DIR="$2"; shift 2 ;;
    --repo) REPO_URL="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --update) UPDATE=1; shift ;;
    --no-deps) NO_DEPS=1; shift ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --clean) CLEAN=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m[install_grsim]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[install_grsim] AVISO:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[install_grsim] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then log "WSL2 detectado"; else warn "não parece WSL2 (tudo bem em Ubuntu nativo)"; fi

# ---- 1. dependências (sudo) -----------------------------------------------------------------------
# grSim (INSTALL.md): Qt 5 (qtbase5-dev existe até o Ubuntu 26.04: 5.15.18), ODE em precisão dupla (o pacote
# do Ubuntu já é), protobuf, boost (VarTypes), OpenGL (mesmo headless o binário linka contra libGL).
PKGS=(git build-essential cmake pkg-config qtbase5-dev libqt5opengl5-dev libgl1-mesa-dev libglu1-mesa-dev
      libprotobuf-dev protobuf-compiler libode-dev libboost-dev)
if [[ $NO_DEPS -eq 0 ]]; then
  log "etapa 1/4: apt-get install (sudo): ${PKGS[*]}"
  sudo apt-get update -qq || warn "apt-get update terminou com erros (repositório de terceiros fora do ar?) — seguindo com os índices existentes"
  # pacotes que não existem nesta versão do Ubuntu são pulados com aviso (ex.: libqt6opengl6-dev foi absorvido
  # pelo qt6-base-dev no 26.04)
  AVAIL=()
  for p in "${PKGS[@]}"; do
    pol="$(apt-cache policy "$p" 2>/dev/null || true)"
    if [[ -z "$pol" ]] || grep -q 'Candidate: (none)' <<<"$pol" || ! grep -q 'Candidate:' <<<"$pol"; then
      warn "pacote $p não existe neste Ubuntu — pulado"
    else
      AVAIL+=("$p")
    fi
  done
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${AVAIL[@]}"
else
  log "etapa 1/4: pulada (--no-deps)"
fi
for t in cmake protoc g++ qmake; do command -v "$t" >/dev/null 2>&1 || command -v "/usr/lib/qt5/bin/$t" >/dev/null 2>&1 || warn "$t não está no PATH"; done

# ---- 2. clone ------------------------------------------------------------------------------------
if [[ -d "$DIR/.git" ]]; then
  log "etapa 2/4: checkout existente em $DIR"
  if [[ $UPDATE -eq 1 ]]; then git -C "$DIR" pull --ff-only; fi
else
  log "etapa 2/4: git clone $REPO_URL -> $DIR"
  git clone "$REPO_URL" "$DIR"
fi
if [[ -n "$REF" ]]; then git -C "$DIR" checkout --quiet "$REF"; fi
log "grSim em $(git -C "$DIR" rev-parse --short HEAD) ($(git -C "$DIR" log -1 --format=%cd --date=short))"

# ---- 3. cmake + build ----------------------------------------------------------------------------
BUILD="$DIR/build"
if [[ $CLEAN -eq 1 && -d "$BUILD" ]]; then rm -rf "$BUILD"; fi
# CMake >= 4.0 (Ubuntu 26.04) recusa projetos com cmake_minimum_required < 3.5 (VarTypes/ODE externos);
# a variável de ambiente abaixo é a válvula oficial e vale também para os ExternalProject filhos.
export CMAKE_POLICY_VERSION_MINIMUM="${CMAKE_POLICY_VERSION_MINIMUM:-3.5}"
if [[ -x "$DIR/bin/grSim" && $CLEAN -eq 0 && $UPDATE -eq 0 ]]; then
  # reconfigurar um build existente do grSim quebra (o protobuf externo já instalado passa a ser "encontrado" e os
  # makefiles ficam com dependências órfãs): só recompila com --clean ou --update
  log "etapa 3/4: $DIR/bin/grSim já existe — build pulado (use --clean para recompilar do zero)"
else
  if [[ $UPDATE -eq 1 && -d "$BUILD" ]]; then rm -rf "$BUILD"; fi
  log "etapa 3/4: cmake -S $DIR -B $BUILD (Release) + build -j$JOBS"
  # só o alvo grSim (o cliente Qt de exemplo não é necessário)
  cmake -S "$DIR" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release -DBUILD_CLIENTS=OFF >"$BUILD.cmake.log" 2>&1 \
    || { tail -40 "$BUILD.cmake.log"; die "cmake falhou (log: $BUILD.cmake.log; um build anterior incompleto? tente --clean)"; }
  cmake --build "$BUILD" --target grSim -j"$JOBS" >"$BUILD.build.log" 2>&1 \
    || { tail -60 "$BUILD.build.log"; die "build falhou (log: $BUILD.build.log)"; }
fi

BIN=""   # o CMakeLists do grSim manda o executável para <repo>/bin/grSim (não para build/)
for cand in "$DIR/bin/grSim" "$BUILD/bin/grSim" "$BUILD/grSim"; do [[ -x "$cand" ]] && { BIN="$cand"; break; }; done
[[ -n "$BIN" ]] || die "binário grSim não encontrado em $DIR/bin nem em $BUILD (veja $BUILD.build.log)"

# ---- 4. config ao lado do binário --------------------------------------------------------------
# Rodando de dentro de $HOME o grSim procura os .ini dos robôs em <dir do binário>/../config/ (configwidget.cpp);
# copiamos a pasta config do repo para lá (idempotente). O estado da GUI/física fica em ~/.grsim.xml.
CFG_DST="$(dirname "$BIN")/../config"
mkdir -p "$CFG_DST"
cp -u "$DIR"/config/*.ini "$CFG_DST/" 2>/dev/null || true
log "etapa 4/4: config em $CFG_DST ($(ls "$CFG_DST" | wc -l) arquivos)"

cat <<EOF

OK: grSim compilado.
  binário : $BIN
  headless: $BIN --headless -platform offscreen
  próximo : tools/external_sims/run_grsim.sh start        (sobe em background; portas 10020 visão, 10300-10302)
            python -m dtssl.sim.protocol_plant --sim grsim (sonda: teleporte + 1 janela)
EOF
