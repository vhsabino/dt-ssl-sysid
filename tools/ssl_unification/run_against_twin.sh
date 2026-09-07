#!/usr/bin/env bash
# run_against_twin.sh — sobe o gêmeo (`dtssl serve`) em background e a estratégia ssl-unification em
# primeiro plano com `-running` (botão play já acionado). Ao fechar a estratégia, o gêmeo é encerrado.
#
#   tools/ssl_unification/run_against_twin.sh --ssl-unification ~/ssl-unification --team blue
#   tools/ssl_unification/run_against_twin.sh --team yellow --backend mujoco-velocity --record results/sessao_01
#   tools/ssl_unification/run_against_twin.sh --team blue --no-serve            # gêmeo já roda no Windows
#   tools/ssl_unification/run_against_twin.sh --team blue --unicast 172.20.4.7:10006   # gêmeo aqui, estratégia lá
#
# Opções:
#   --ssl-unification PATH   raiz do checkout (default: $SSL_UNIFICATION ou ~/ssl-unification)
#   --team blue|yellow       cor do time; se config/local/config.json não existir, gera com make_local_config.py
#   --backend NAME           fopdt (default) | ideal | mujoco-velocity | mujoco-rollers   (dtssl serve --backend)
#   --unicast IP:PORT        repassa `--unicast` ao dtssl serve (visão por unicast, p/ atravessar o NAT do WSL2); repetível
#   --record DIR             dtssl serve --record DIR --record-team <--team> (grava commands/processed_robots.parquet do
#                            time da estrategia no contrato dos logs; os arquivos sao escritos ao ENCERRAR o gemeo)
#   --serve-args "..."       argumentos extras para dtssl serve (ex.: "--n-blue 6 --n-yellow 6 --speed 1.0")
#   --no-serve               não sobe o gêmeo (já está rodando em outro lugar, ex.: no Windows)
#   --no-running             não passa -running (a estratégia abre pausada)
#   --config-args "..."      argumentos extras para make_local_config.py quando a config é gerada
#   --log FILE               log do dtssl serve (default: /tmp/dtssl_serve.log)
#
# Portas (config/bridge.json): visão 224.5.23.2:10006 (multicast em lo), controle 10301 (blue) / 10302 (yellow),
# SimulatorCommand 10300. O joystick (DualSense) é tratado pelo gêmeo (`dtssl gui`, modo Debug), nunca pela estratégia.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
SSL_DIR="${SSL_UNIFICATION:-$HOME/ssl-unification}"
TEAM=""
BACKEND="fopdt"
UNICAST=()
RECORD=""
SERVE_ARGS=""
NO_SERVE=0
RUNNING=1
CONFIG_ARGS=""
LOG="/tmp/dtssl_serve.log"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ssl-unification) SSL_DIR="$2"; shift 2 ;;
    --team) TEAM="$2"; shift 2 ;;
    --backend) BACKEND="$2"; shift 2 ;;
    --unicast) UNICAST+=("--unicast" "$2"); shift 2 ;;
    --record) RECORD="$2"; shift 2 ;;
    --serve-args) SERVE_ARGS="$2"; shift 2 ;;
    --no-serve) NO_SERVE=1; shift ;;
    --no-running) RUNNING=0; shift ;;
    --config-args) CONFIG_ARGS="$2"; shift 2 ;;
    --log) LOG="$2"; shift 2 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m[run_against_twin]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[run_against_twin] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

BIN="$SSL_DIR/bin/ssl-unification"
[[ -x "$BIN" ]] || die "binário não encontrado: $BIN (rode tools/ssl_unification/build_wsl2.sh --dir $SSL_DIR)"

# ---- config/local: gera se faltar (precisa de --team) --------------------------------------------
LOCAL_CFG="$SSL_DIR/config/local/config.json"
if [[ ! -f "$LOCAL_CFG" ]]; then
  [[ -n "$TEAM" ]] || die "$LOCAL_CFG não existe; passe --team blue|yellow para gerá-la (make_local_config.py)"
  log "gerando $LOCAL_CFG (team=$TEAM)"
  # shellcheck disable=SC2086
  python3 "$HERE/make_local_config.py" --ssl-unification "$SSL_DIR" --team "$TEAM" \
    --bridge-json "$REPO_ROOT/config/bridge.json" $CONFIG_ARGS
elif [[ -n "$TEAM" ]]; then
  CUR="$(python3 - "$LOCAL_CFG" <<'EOF'
import json, sys
c = json.load(open(sys.argv[1]))["MainWindow"]
print(c["VisionBase"]["ParametersDialog"]["DataWorld"]["TeamColor"]["Value"].lower())
EOF
)"
  [[ "$CUR" == "$TEAM" ]] || log "AVISO: config/local existente é do time '$CUR', mas --team $TEAM foi pedido (regenere com make_local_config.py)"
fi

# ---- dtssl serve (background) -------------------------------------------------------------------
SERVE_PID=""
cleanup() {
  if [[ -n "$SERVE_PID" ]] && kill -0 "$SERVE_PID" 2>/dev/null; then
    log "encerrando dtssl serve (pid $SERVE_PID)"
    kill -INT "$SERVE_PID" 2>/dev/null || true
    for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$SERVE_PID" 2>/dev/null || break; sleep 0.3; done
    kill -KILL "$SERVE_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ $NO_SERVE -eq 0 ]]; then
  if command -v dtssl >/dev/null 2>&1; then
    DTSSL=(dtssl)
  elif python3 -c "import dtssl" 2>/dev/null; then
    DTSSL=(python3 -m dtssl.cli)
  else
    die "dtssl não encontrado (pip install -e '$REPO_ROOT[gui,mujoco,dev]' no mesmo ambiente)"
  fi
  CMD=("${DTSSL[@]}" serve --backend "$BACKEND" --config "$REPO_ROOT/config/bridge.json" "${UNICAST[@]}")
  [[ -n "$RECORD" ]] && CMD+=(--record "$RECORD" --record-team "$TEAM")   # grava o time da estrategia (default do serve seria blue)
  # shellcheck disable=SC2206
  [[ -n "$SERVE_ARGS" ]] && CMD+=($SERVE_ARGS)
  log "iniciando: ${CMD[*]}  (log: $LOG)"
  "${CMD[@]}" >"$LOG" 2>&1 &
  SERVE_PID=$!
  sleep 1.5
  kill -0 "$SERVE_PID" 2>/dev/null || { cat "$LOG" >&2; die "dtssl serve terminou logo após iniciar (ver log acima)"; }
  log "dtssl serve rodando (pid $SERVE_PID); primeiros pacotes de geometria em ~1 s"
else
  log "--no-serve: assumindo que o gêmeo já está no ar (Windows ou outro terminal)"
fi

# ---- estratégia (primeiro plano) ---------------------------------------------------------------
ARGS=()
[[ $RUNNING -eq 1 ]] && ARGS+=(-running)
log "iniciando $BIN ${ARGS[*]:-}  (config: $LOCAL_CFG)"
cd "$SSL_DIR"
"$BIN" "${ARGS[@]}"
