#!/usr/bin/env bash
# video2_erforce.sh - Video 2 (D5): o ER-Force rodando e avaliado pelo gemeo, tudo no WSL2, passo a passo.
#
#   tools/demo/video2_erforce.sh check      # pre-requisitos: venv, simulator-cli, portas livres, config do ER-Force
#   tools/demo/video2_erforce.sh start      # sobe o simulator-cli (-g 2020B --realism None) e mostra status
#   tools/demo/video2_erforce.sh probe      # teleporte + 1 janela de 1 s: "window_ok": true, latencia, tau0, moved_m
#   tools/demo/video2_erforce.sh replay     # um evento real do hold-out replayado no ER-Force pelo harness (tabela e_pos + PNG)
#   tools/demo/video2_erforce.sh strategy   # (opcional) o ssl-unification jogando DENTRO do ER-Force (janela Qt); Ctrl+C volta
#   tools/demo/video2_erforce.sh stop       # derruba o simulator-cli e restaura a config/local do gemeo, se foi trocada
#   tools/demo/video2_erforce.sh all        # check, start, probe, replay, stop (sem a estrategia)
#
# Roteiro: docs/RUNBOOK_VIDEOS_D5_20260916.md. Numeros de referencia do C2b (10/09, results/CHANGELOG.md):
# e_pos mediano em 0,4 s: gemeo 0,039 m, ER-Force 0,088 (+atraso 0,056), grSim 0,239.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
SIMCTL="$REPO_ROOT/tools/external_sims/simctl.sh"
SSL_DIR="${SSL_UNIFICATION:-$HOME/ssl-unification}"
TEAM="${TEAM:-yellow}"
VENV="$HOME/.venvs/dtssl"
OUT="${OUT:-/tmp/demo_erforce}"
EVENT_LABEL="${EVENT_LABEL:-side_to_side}"
EVENT="${EVENT:-side_to_side_01_05}"
STATE="$HOME/external_sims"; mkdir -p "$STATE"
CFG_BACKUP="$STATE/config_local_before_erforce.json"
CMD="${1:-check}"

say()  { printf '\033[1;32m[video2]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[video2] AVISO:\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[video2] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

activate() {
  [[ -x "$VENV/bin/python" ]] || die "venv ausente: python3 -m venv $VENV && $VENV/bin/pip install -e '$REPO_ROOT[dev]'"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  cd "$REPO_ROOT"
}

port_open() {
  if command -v ss >/dev/null 2>&1; then ss -lun 2>/dev/null | grep -qE "[:.]$1[[:space:]]"
  else grep -qiE ":$(printf '%04X' "$1") " /proc/net/udp /proc/net/udp6 2>/dev/null; fi
}

check() {
  activate
  say "1/5 dtssl no venv"
  python -c "import dtssl, dtssl.sim.protocol_plant" 2>/dev/null || die "dtssl nao importa ($VENV/bin/pip install -e '$REPO_ROOT[dev]')"
  python -m dtssl.cli info >/dev/null 2>&1 || die "dtssl info falhou (dataset/config?)"
  say "2/5 simulator-cli do ER-Force: $HOME/erforce/build/bin/simulator-cli"
  [[ -x "$HOME/erforce/build/bin/simulator-cli" ]] || die "ausente: tools/external_sims/install_erforce_wsl.sh"
  say "3/5 endpoint 'erforce' em config/external_sims.json"
  python - <<'PY' || die "endpoint erforce nao carrega"
from dtssl.sim.protocol_plant import load_endpoint
e = load_endpoint("erforce"); print(f"      {e.host} vis {e.vision_ip}:{e.vision_port} ctrl {e.control_port} team {e.team} id {e.robot_id} teleport_omega={e.teleport_omega}")
PY
  say "4/5 estado do simulator-cli"
  "$SIMCTL" erforce status
  say "5/5 portas 10300-10302 (devem estar livres antes do start, ou do ER-Force depois)"
  if port_open 10300 && ! "$SIMCTL" erforce status 2>/dev/null | grep -q rodando; then
    die "porta 10300 em uso por outro processo (grSim? dtssl serve?): simctl.sh grsim stop; pkill -f 'dtssl.cli serve'"
  fi
  say "ok. Sequencia do video: start -> probe -> replay -> (strategy) -> stop"
}

start_sim() {
  activate
  "$SIMCTL" erforce start
  "$SIMCTL" erforce status
}

probe_sim() {
  activate
  say "sonda: python -m dtssl.sim.protocol_plant --sim erforce   (esperado: \"window_ok\": true, moved_m ~0,5 em 1 s a 0,5 m/s)"
  python -m dtssl.sim.protocol_plant --sim erforce
}

replay_event() {
  activate
  mkdir -p "$OUT"
  say "replay do evento real $EVENT_LABEL/$EVENT no ER-Force pelo harness (tempo real: ~1 min; janelas de 1,5 s + cauda)"
  say "  dtssl replay $EVENT_LABEL $EVENT --plant proto:erforce --out $OUT"
  python -m dtssl.cli replay "$EVENT_LABEL" "$EVENT" --plant proto:erforce --out "$OUT"
  local png
  png="$(ls -t "$OUT"/replay_*.png 2>/dev/null | head -1 || true)"
  if [[ -n "$png" ]]; then
    say "figura: $png  (abrindo no Windows)"
    if command -v wslpath >/dev/null 2>&1 && command -v explorer.exe >/dev/null 2>&1; then
      explorer.exe "$(wslpath -w "$png")" >/dev/null 2>&1 || true
    fi
  fi
  say "para comparar na fala: o mesmo evento com o gemeo:  dtssl replay $EVENT_LABEL $EVENT --plant fopdt --out $OUT"
}

strategy() {
  activate
  "$SIMCTL" erforce status | grep -q rodando || die "ER-Force nao esta rodando (video2_erforce.sh start)"
  [[ -x "$SSL_DIR/bin/ssl-unification" ]] || die "binario da estrategia ausente: $SSL_DIR/bin/ssl-unification"
  local cfg="$SSL_DIR/config/local/config.json"
  if [[ -f "$cfg" && ! -f "$CFG_BACKUP" ]]; then cp "$cfg" "$CFG_BACKUP"; say "config/local do gemeo guardada em $CFG_BACKUP"; fi
  # ER-Force: visao 224.5.23.2:10020 pela interface da rota default do WSL (eth0); controle 10301/10302 em 127.0.0.1
  local inet
  inet="$(ip route 2>/dev/null | awk '/default/ {print $5; exit}')"; inet="${inet:-eth0}"
  say "gerando config/local para o ER-Force (time $TEAM, visao porta 10020 em $inet)"
  python3 "$REPO_ROOT/tools/ssl_unification/make_local_config.py" --ssl-unification "$SSL_DIR" --team "$TEAM" \
    --vision-ip 224.5.23.2 --vision-port 10020 --inet "$inet" --sim-ip 127.0.0.1
  say "estrategia contra o ER-Force (janela Qt). Feche a janela ou Ctrl+C para voltar; depois: video2_erforce.sh stop"
  bash "$REPO_ROOT/tools/ssl_unification/run_against_twin.sh" --ssl-unification "$SSL_DIR" --team "$TEAM" --no-serve || true
}

stop_sim() {
  "$SIMCTL" erforce stop || true
  local cfg="$SSL_DIR/config/local/config.json"
  if [[ -f "$CFG_BACKUP" ]]; then
    cp "$CFG_BACKUP" "$cfg" && rm -f "$CFG_BACKUP"
    say "config/local do gemeo restaurada"
  fi
}

case "$CMD" in
  check) check ;;
  start) start_sim ;;
  probe) probe_sim ;;
  replay) replay_event ;;
  strategy) strategy ;;
  stop) stop_sim ;;
  all) check; start_sim; probe_sim; replay_event; stop_sim ;;
  *) sed -n '2,12p' "$0"; exit 2 ;;
esac
