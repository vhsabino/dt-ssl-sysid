#!/usr/bin/env bash
# install_erforce_wsl.sh — clone + dependências + build do `simulator-cli` do framework ER-Force (Bullet) no WSL2
# Ubuntu 22.04/24.04/26.04, para servir de baseline "física da liga" no harness do gêmeo (C2b).
# Idempotente. Só o alvo `simulator-cli` é compilado (README do ER-Force: "make simulator-cli"), sem V8/Ra.
#
#   tools/external_sims/install_erforce_wsl.sh                 # ~/erforce, deps via sudo apt, build Release
#   tools/external_sims/install_erforce_wsl.sh --no-deps       # deps já instaladas (sem sudo)
#   tools/external_sims/install_erforce_wsl.sh --dir ~/src/erforce --jobs 8 --update
#
# Opções:
#   --dir PATH      checkout existente ou destino do clone (default: ~/erforce)
#   --repo URL      default https://github.com/robotics-erlangen/framework.git
#   --ref REF       tag/branch/commit (default: o default do remoto)
#   --update        git pull --ff-only num checkout existente
#   --no-deps       não roda apt (única etapa que exige sudo)
#   --jobs N        paralelismo do build (default: nproc)
#   --clean         apaga build/ antes de configurar
#
# ETAPA COM SUDO: só o `apt-get install` (etapa 1). O CMake do ER-Force baixa e compila Bullet/Eigen (e o protobuf,
# se o do sistema não servir) de downloads.robotics-erlangen.de — precisa de rede, não de sudo.
# Depois: tools/external_sims/run_erforce.sh start   (simulator-cli -g 2020B --realism None; portas 10020/10300-10302)
set -euo pipefail

DIR="${HOME}/erforce"
REPO_URL="https://github.com/robotics-erlangen/framework.git"
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
    -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m[install_erforce]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[install_erforce] AVISO:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[install_erforce] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then log "WSL2 detectado"; else warn "não parece WSL2 (tudo bem em Ubuntu nativo)"; fi

# ---- 1. dependências (sudo) -----------------------------------------------------------------------
# COMPILE.md do ER-Force (Ubuntu 22.04/24.04): cmake protobuf-compiler libprotobuf-dev qt6-base-dev libqt6opengl6-dev
# g++ libssl-dev libglu1-mesa-dev (+ libusb/sdl2/qt6svg só para Ra/transceiver, dispensáveis para o simulator-cli).
PKGS=(git build-essential cmake pkg-config qt6-base-dev libqt6opengl6-dev libgl1-mesa-dev libglu1-mesa-dev
      libprotobuf-dev protobuf-compiler libssl-dev)
if [[ $NO_DEPS -eq 0 ]]; then
  log "etapa 1/3: apt-get install (sudo): ${PKGS[*]}"
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
  log "etapa 1/3: pulada (--no-deps)"
fi

# ---- 2. clone ------------------------------------------------------------------------------------
if [[ -d "$DIR/.git" ]]; then
  log "etapa 2/3: checkout existente em $DIR"
  if [[ $UPDATE -eq 1 ]]; then git -C "$DIR" pull --ff-only; fi
else
  log "etapa 2/3: git clone $REPO_URL -> $DIR"
  git clone "$REPO_URL" "$DIR"
fi
if [[ -n "$REF" ]]; then git -C "$DIR" checkout --quiet "$REF"; fi
log "ER-Force framework em $(git -C "$DIR" rev-parse --short HEAD) ($(git -C "$DIR" log -1 --format=%cd --date=short))"

# ---- 3. cmake + build do alvo simulator-cli --------------------------------------------------------
BUILD="$DIR/build"
if [[ $CLEAN -eq 1 && -d "$BUILD" ]]; then rm -rf "$BUILD"; fi
# CMake >= 4.0 (Ubuntu 26.04) recusa projetos com cmake_minimum_required < 3.5 (o Bullet 2.83 externo, p.ex.);
# a variável de ambiente abaixo é a válvula oficial e vale também para os ExternalProject filhos.
export CMAKE_POLICY_VERSION_MINIMUM="${CMAKE_POLICY_VERSION_MINIMUM:-3.5}"
if [[ -x "$BUILD/bin/simulator-cli" && $CLEAN -eq 0 && $UPDATE -eq 0 ]]; then
  log "etapa 3/3: $BUILD/bin/simulator-cli já existe — build pulado (use --clean para recompilar do zero)"
else
  log "etapa 3/3: cmake -S $DIR -B $BUILD (Release, DOWNLOAD_V8=OFF) + build simulator-cli -j$JOBS (baixa Bullet/Eigen)"
  cmake -S "$DIR" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release -DDOWNLOAD_V8=OFF -DBUILD_FIRMWARE=OFF >"$BUILD.cmake.log" 2>&1 \
    || { tail -40 "$BUILD.cmake.log"; die "cmake falhou (log: $BUILD.cmake.log; um build anterior incompleto? tente --clean)"; }
  cmake --build "$BUILD" --target simulator-cli -j"$JOBS" >"$BUILD.build.log" 2>&1 \
    || { tail -60 "$BUILD.build.log"; die "build falhou (log: $BUILD.build.log)"; }
fi

BIN=""
for cand in "$BUILD/bin/simulator-cli" "$BUILD/src/simulator/simulator-cli" "$(find "$BUILD" -name simulator-cli -type f -perm -u+x 2>/dev/null | head -1)"; do
  [[ -n "$cand" && -x "$cand" ]] && { BIN="$cand"; break; }
done
[[ -n "$BIN" ]] || die "binário simulator-cli não encontrado em $BUILD (veja $BUILD.build.log)"
[[ -f "$DIR/config/simulator/2020B.txt" ]] || warn "config/simulator/2020B.txt não existe neste checkout; veja ls $DIR/config/simulator"

cat <<EOF

OK: ER-Force simulator-cli compilado.
  binário : $BIN
  uso     : $BIN -g 2020B --realism None      (geometria Div B; realismo None = sem ruído, atraso de visão 35 ms)
  próximo : tools/external_sims/run_erforce.sh start   (sobe em background; portas 10020 visão, 10300-10302)
            python -m dtssl.sim.protocol_plant --sim erforce
EOF
