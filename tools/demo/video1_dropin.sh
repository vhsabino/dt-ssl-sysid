#!/usr/bin/env bash
# video1_dropin.sh - Video 1 (D5): o ssl-unification jogando contra o gemeo (drop-in do grSim), tudo no WSL2.
#
#   tools/demo/video1_dropin.sh check     # so confere os pre-requisitos (venv, binario, config do time, WSLg, portas)
#   tools/demo/video1_dropin.sh run       # check + sobe o gemeo e a estrategia (janela Qt via WSLg); Ctrl+C encerra os dois
#   tools/demo/video1_dropin.sh watch     # (2.o terminal) acompanha o log do gemeo: hz=60.0 late=0 ... watchdog=0 kicks=N
#   tools/demo/video1_dropin.sh gl-check  # diagnostico da aba 3D no WSLg: qual par Qt/PyOpenGL (egl ou glx) funciona
#   tools/demo/video1_dropin.sh gui       # como o run, mas o gemeo e a GUI (dtssl gui --mode bridge, janela no WSLg com o
#                                         # campo 2D, os plots e a aba 3D) em vez do dtssl serve sem janela; precisa do
#                                         # extra [gui] no venv do WSL (o proprio comando diz como instalar)
#
# Roteiro: docs/RUNBOOK_VIDEOS_D5_20260916.md. Numeros de referencia do cenario 6.1 (03/09): 185 s a 60 Hz,
# watchdog=0, kicks=45 (results/CHANGELOG.md e claude/backlog-decisao-2026-09.md).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
SSL_DIR="${SSL_UNIFICATION:-$HOME/ssl-unification}"
TEAM="${TEAM:-yellow}"
VENV="$HOME/.venvs/dtssl"
LOG="/tmp/dtssl_serve.log"
GUI_LOG="/tmp/dtssl_gui.log"
CMD="${1:-check}"

say()  { printf '\033[1;32m[video1]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[video1] AVISO:\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[video1] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

port_open() {
  if command -v ss >/dev/null 2>&1; then ss -lun 2>/dev/null | grep -qE "[:.]$1[[:space:]]"
  else grep -qiE ":$(printf '%04X' "$1") " /proc/net/udp /proc/net/udp6 2>/dev/null; fi
}

# --- OpenGL no WSLg: o Qt (janela) e o PyOpenGL (aba 3D) precisam falar com o MESMO GL. Se o Qt cria o contexto
# por EGL e o PyOpenGL procura por GLX (o default no Linux), todo paint da aba 3D falha com
# "Attempt to retrieve context when no valid context" (a GUI segue; a aba 3D fica vazia). gl_probe testa um par.
gl_probe() {   # $1 = egl | glx ; exit 0 se PyOpenGL enxerga o contexto do Qt
  local pair="$1"
  (
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
    if [[ "$pair" == "egl" ]]; then export QT_XCB_GL_INTEGRATION=xcb_egl PYOPENGL_PLATFORM=egl
    else export QT_XCB_GL_INTEGRATION=xcb_glx; unset PYOPENGL_PLATFORM; fi
    timeout 20 python - <<'PY' 2>/dev/null
import sys
from PySide6 import QtWidgets, QtOpenGLWidgets
app = QtWidgets.QApplication([])
w = QtOpenGLWidgets.QOpenGLWidget(); w.resize(64, 64); w.show()
for _ in range(20): app.processEvents()
w.makeCurrent()
from OpenGL import GL
r = GL.glGetString(GL.GL_RENDERER)
if not r: sys.exit(1)
print(r.decode(errors="replace"))
PY
  )
}
gl_setup() {   # exporta o par que funciona; sem par, a GUI abre sem a aba 3D (--no-3d)
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
  GUI_ARGS="${GUI_ARGS:-}"
  if [[ "$GUI_ARGS" == *--no-3d* ]]; then say "aba 3D desligada por GUI_ARGS"; return; fi
  local r
  for pair in "${GL_PAIR:-egl}" glx egl; do
    if r="$(gl_probe "$pair")"; then
      say "OpenGL ok com o par $pair (renderer: $r)"
      if [[ "$pair" == "egl" ]]; then export QT_XCB_GL_INTEGRATION=xcb_egl PYOPENGL_PLATFORM=egl
      else export QT_XCB_GL_INTEGRATION=xcb_glx; unset PYOPENGL_PLATFORM; fi
      return
    fi
  done
  warn "PyOpenGL nao enxerga o contexto do Qt em nenhum par (egl/glx): abrindo a GUI sem a aba 3D (--no-3d)"
  GUI_ARGS="$GUI_ARGS --no-3d"
}

check() {
  say "1/7 repo: $REPO_ROOT"
  [[ -f "$REPO_ROOT/pyproject.toml" ]] || die "nao estou no repo (rode de /mnt/c/Users/victo/Documents/digitaltwin)"
  say "2/7 venv do WSL: $VENV"
  [[ -x "$VENV/bin/python" ]] || die "venv ausente: python3 -m venv $VENV && $VENV/bin/pip install -e '$REPO_ROOT[dev]'"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  python -c "import dtssl" 2>/dev/null || die "dtssl nao importa no venv ($VENV/bin/pip install -e '$REPO_ROOT[dev]')"
  say "3/7 dtssl info"
  python -m dtssl.cli info >/dev/null 2>&1 || die "dtssl info falhou (dataset/config?)"
  say "4/7 binario da estrategia: $SSL_DIR/bin/ssl-unification"
  [[ -x "$SSL_DIR/bin/ssl-unification" ]] || die "binario ausente: bash tools/ssl_unification/build_wsl2.sh --force-os --config-team $TEAM --jobs 4"
  say "5/7 config/local do time $TEAM"
  local cfg="$SSL_DIR/config/local/config.json"
  if [[ -f "$cfg" ]]; then
    python3 "$HERE/../ssl_unification/make_local_config.py" --ssl-unification "$SSL_DIR" --team "$TEAM" \
      --bridge-json "$REPO_ROOT/config/bridge.json" --out /tmp/video1_config.json >/dev/null
    if python3 - "$cfg" /tmp/video1_config.json <<'PY'
import json, sys
a, b = (json.load(open(f, encoding="utf-8")) for f in sys.argv[1:3])
sys.exit(0 if a == b else 1)
PY
    then say "config/local ja e a config do gemeo para o time $TEAM"
    else
      warn "config/local difere da config do gemeo para o time $TEAM (ficou de outro uso, ex.: ER-Force); regenerando"
      cp "$cfg" "/tmp/video1_config_backup_$(date +%Y%m%d_%H%M%S).json"
      cp /tmp/video1_config.json "$cfg"
    fi
  else
    say "config/local ausente: run_against_twin.sh a gera com --team $TEAM"
  fi
  say "6/7 WSLg (janela Qt): DISPLAY=${DISPLAY:-<vazio>} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<vazio>}"
  [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]] || die "sem DISPLAY: WSLg inativo. No PowerShell: wsl --shutdown, depois abra o Ubuntu de novo"
  say "7/7 portas UDP 10300-10302 livres"
  for p in 10300 10301 10302; do
    port_open "$p" && die "porta $p em uso (dtssl serve, grSim ou ER-Force de pe?): tools/external_sims/simctl.sh grsim stop; simctl.sh erforce stop; pkill -f 'dtssl.cli serve'"
  done
  say "tudo pronto. Proximo: tools/demo/video1_dropin.sh run   (e, no 2.o terminal, tools/demo/video1_dropin.sh watch)"
}

case "$CMD" in
  check) check ;;
  run)
    check
    say "subindo o gemeo (dtssl serve, fopdt, log $LOG) e a estrategia (-running). A janela Qt aparece como janela do Windows."
    say "Ctrl+C ou fechar a janela da estrategia encerra os dois. Log final do gemeo: tail -3 $LOG"
    cd "$REPO_ROOT"
    exec bash "$REPO_ROOT/tools/ssl_unification/run_against_twin.sh" --ssl-unification "$SSL_DIR" --team "$TEAM" --log "$LOG"
    ;;
  gui)
    check
    python -c "import PySide6, pyqtgraph, pygame" 2>/dev/null || die "extra [gui] ausente no venv do WSL. Instale (2 a 5 min): \
  $VENV/bin/pip install -e '$REPO_ROOT[gui]'
  Se a janela nao abrir depois disso (erro 'xcb'/'could not load the Qt platform plugin'), faltam libs do sistema: \
  sudo apt install -y libxcb-cursor0 libxkbcommon-x11-0 libxcb-xinerama0 libgl1 libegl1 libdbus-1-3"
    port_open 10300 && die "porta 10300 em uso: outro gemeo de pe (pkill -f 'dtssl.cli serve'; pkill -f 'dtssl.gui')"
    gl_setup
    say "abrindo a GUI do gemeo como servidor (dtssl gui --mode bridge --team $TEAM; log $GUI_LOG). Janela Qt via WSLg."
    cd "$REPO_ROOT"
    # shellcheck disable=SC2086
    python -m dtssl.gui --mode bridge --team "$TEAM" --config "$REPO_ROOT/config/bridge.json" $GUI_ARGS >"$GUI_LOG" 2>&1 &
    GUI_PID=$!
    trap 'kill -INT $GUI_PID 2>/dev/null || true' EXIT INT TERM
    for _ in $(seq 1 40); do
      port_open 10300 && break
      kill -0 "$GUI_PID" 2>/dev/null || { tail -30 "$GUI_LOG"; die "a GUI terminou antes de abrir as portas (log acima)"; }
      sleep 0.5
    done
    port_open 10300 || { tail -30 "$GUI_LOG"; die "a GUI nao abriu a porta 10300 em 20 s (log acima)"; }
    say "GUI de pe (pid $GUI_PID): campo 2D com os 12 robos, plots do robo selecionado, aba 3D (CAD); barra de status com hz e pacotes."
    say "subindo a estrategia (-running) contra ela. Feche a janela da estrategia (ou Ctrl+C) para encerrar os dois."
    bash "$REPO_ROOT/tools/ssl_unification/run_against_twin.sh" --ssl-unification "$SSL_DIR" --team "$TEAM" --no-serve || true
    ;;
  gl-check)
    check
    for pair in egl glx; do
      if r="$(gl_probe "$pair")"; then say "par $pair: OK (renderer: $r)"; else warn "par $pair: PyOpenGL nao enxerga o contexto do Qt"; fi
    done
    say "o 'gui' escolhe sozinho o primeiro par que funciona (GL_PAIR=egl|glx forca; GUI_ARGS=--no-3d desliga a aba 3D)"
    ;;
  watch)
    [[ -f "$LOG" ]] || die "sem $LOG ainda (rode 'video1_dropin.sh run' no outro terminal; no modo 'gui' o proprio painel mostra hz e pacotes)"
    say "linha [stats] a cada 5 s: hz=60.0/60 late=0 | yellow= crescendo (comandos da estrategia) | watchdog=0 | kicks= crescendo"
    exec tail -f "$LOG"
    ;;
  *) sed -n '2,14p' "$0"; exit 2 ;;
esac
