#!/usr/bin/env bash
# simctl.sh — sobe/derruba um simulador da liga (grSim ou ER-Force simulator-cli) em background no WSL2, com
# log e pid em ~/external_sims/, e confere se as portas do ssl-simulation-protocol responderam.
#
#   tools/external_sims/simctl.sh grsim   start|stop|status|log|probe
#   tools/external_sims/simctl.sh erforce start|stop|status|log|probe
#   tools/external_sims/run_grsim.sh start        # atalhos equivalentes
#   tools/external_sims/run_erforce.sh start
#
# Opções (depois do comando):
#   --bin PATH        binário (default: ~/grsim/bin/grSim | ~/erforce/build/bin/simulator-cli, ou o que
#                     install_*_wsl.sh imprimiu)
#   --args "..."      argumentos extras para o simulador (grSim default: "--headless -platform offscreen";
#                     ER-Force default: "-g 2020B --realism None")
#   --timeout S       espera pela porta 10300 (default 20 s)
#
# Os dois simuladores usam as MESMAS portas (visão 224.5.23.2:10020, controle 10301/10302, SimulatorCommand 10300):
# só um pode estar de pé por vez. `probe` = `python -m dtssl.sim.protocol_plant --sim <nome>` (teleporte + 1 janela).
set -euo pipefail

SIM="${1:-}"; CMD="${2:-status}"
[[ -n "$SIM" ]] || { sed -n '2,18p' "$0"; exit 2; }
shift 2 || true
BIN=""; EXTRA=""; TIMEOUT=20
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bin) BIN="$2"; shift 2 ;;
    --args) EXTRA="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m[simctl %s]\033[0m %s\n' "$SIM" "$*"; }
die()  { printf '\033[1;31m[simctl %s] ERRO:\033[0m %s\n' "$SIM" "$*" >&2; exit 1; }

case "$SIM" in
  grsim)
    DEFAULT_BIN="$HOME/grsim/bin/grSim"
    DEFAULT_ARGS="--headless -platform offscreen"
    ;;
  erforce)
    DEFAULT_BIN="$HOME/erforce/build/bin/simulator-cli"
    DEFAULT_ARGS="-g 2020B --realism None"
    ;;
  *) die "simulador desconhecido: $SIM (grsim | erforce)" ;;
esac
BIN="${BIN:-$DEFAULT_BIN}"
ARGS="${EXTRA:-$DEFAULT_ARGS}"
STATE="$HOME/external_sims"; mkdir -p "$STATE"
PIDF="$STATE/$SIM.pid"; LOGF="$STATE/$SIM.log"

alive() { [[ -f "$PIDF" ]] && kill -0 "$(cat "$PIDF")" 2>/dev/null; }
port_open() {              # UDP port bound? (ss when available, else /proc/net/udp{,6} with the port in hex)
  if command -v ss >/dev/null 2>&1; then ss -lun 2>/dev/null | grep -qE "[:.]$1[[:space:]]"
  else grep -qiE ":$(printf '%04X' "$1") " /proc/net/udp /proc/net/udp6 2>/dev/null; fi
}
open_ports() {             # the league ports currently bound, for the status line
  for p in 10020 10300 10301 10302; do port_open "$p" && printf '%s ' "$p"; done
}

case "$CMD" in
  start)
    if alive; then log "já está rodando (pid $(cat "$PIDF"))"; exit 0; fi
    [[ -x "$BIN" ]] || die "binário não encontrado: $BIN (rode tools/external_sims/install_${SIM}_wsl.sh ou passe --bin)"
    if port_open 10300; then die "a porta 10300 já está em uso (outro simulador de pé? simctl.sh grsim|erforce stop)"; fi
    log "subindo: $BIN $ARGS  (log: $LOGF)"
    # shellcheck disable=SC2086
    nohup "$BIN" $ARGS >"$LOGF" 2>&1 &
    echo $! >"$PIDF"
    for _ in $(seq 1 "$((TIMEOUT * 2))"); do
      if port_open 10300 && port_open 10301; then break; fi
      alive || { tail -20 "$LOGF"; die "o processo terminou antes de abrir as portas (veja $LOGF)"; }
      sleep 0.5
    done
    port_open 10300 || { tail -20 "$LOGF"; die "porta 10300 não abriu em ${TIMEOUT}s (veja $LOGF)"; }
    log "pronto: pid $(cat "$PIDF"); portas UDP abertas: $(open_ports)"
    ;;
  stop)
    if alive; then
      log "encerrando pid $(cat "$PIDF")"
      kill "$(cat "$PIDF")" 2>/dev/null || true
      for _ in $(seq 1 20); do alive || break; sleep 0.25; done
      alive && kill -9 "$(cat "$PIDF")" 2>/dev/null || true
    else
      log "não está rodando"
    fi
    rm -f "$PIDF"
    ;;
  status)
    if alive; then log "rodando (pid $(cat "$PIDF")); portas UDP abertas: $(open_ports)"; else log "parado"; fi
    ;;
  log)
    tail -n 50 "$LOGF" 2>/dev/null || log "sem log em $LOGF"
    ;;
  probe)
    alive || die "não está rodando (simctl.sh $SIM start)"
    PY="${PYTHON:-python3}"
    if [[ -z "${VIRTUAL_ENV:-}" && -x "$HOME/.venvs/dtssl/bin/python" ]]; then PY="$HOME/.venvs/dtssl/bin/python"; fi
    log "sonda: $PY -m dtssl.sim.protocol_plant --sim $SIM"
    "$PY" -m dtssl.sim.protocol_plant --sim "$SIM"
    ;;
  *) die "comando desconhecido: $CMD (start | stop | status | log | probe)" ;;
esac
