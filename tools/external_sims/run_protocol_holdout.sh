#!/usr/bin/env bash
# run_protocol_holdout.sh — C2b de ponta a ponta no WSL2: para cada simulador da liga, sobe o simulador, sonda,
# roda `dtssl analysis run protocol_holdout` (hold-out do artigo via ssl-simulation-protocol, em tempo real),
# derruba o simulador; ao final reanalisa os caches dos dois numa única tabela (`from_cache`).
#
#   tools/external_sims/run_protocol_holdout.sh                       # grsim e erforce, delay=both, repeat=1
#   tools/external_sims/run_protocol_holdout.sh --sims grsim --repeat 2
#   tools/external_sims/run_protocol_holdout.sh --sims erforce --delay none --no-merge
#   tools/external_sims/run_protocol_holdout.sh --merge-only          # só a tabela conjunta dos caches existentes
#   tools/external_sims/run_protocol_holdout.sh --sims grsim --smoke   # 1 evento, ~2 min: valida o ambiente, NAO e resultado
#   tools/external_sims/run_protocol_holdout.sh --delay none --preroll 0.5   # C2b2: <sim> e <sim>+preroll (pre-registro C2B2)
#
# Opções:
#   --sims a,b        simuladores de config/external_sims.json (default: grsim,erforce; um de cada vez: mesmas portas)
#   --delay both|none|theta   variantes (default both: <sim> e <sim>+delay)
#   --repeat N        repetições do replay inteiro por variante (default 1; 2 = reporta repetibilidade)
#   --python PATH     interpretador com o dtssl instalado (default: ~/.venvs/dtssl/bin/python, ou o do PATH)
#   --no-merge        não gera o artefato conjunto ao final
#   --merge-only      pula os replays e gera o artefato conjunto de results/_cache_protocol_*.npz
#   --keep-up         não derruba o simulador ao terminar cada replay
#   --smoke           só o primeiro evento do hold-out (max_events=1): teste de fumaça do ambiente, nunca resultado
#   --preroll S       pré-rolagem de S segundos (C2b2): cada variante também roda como <variante>+preroll (0 = desligado)
#   --preroll-only    com --preroll: só as variantes +preroll (sem as cruas)
#   --out DIR         diretório de saída (default: results/ do repo; use outro para o --smoke)
#
# Tempo: ~8 min por variante (265 janelas x 1,5 s + cauda; +2 min com pré-rolagem de 0,5 s); grsim+erforce com
# delay=both, repeat=1 ~35 min; C2b2 (--delay none --preroll 0.5) ~40 min.
# Saída: results/protocol_holdout_<stamp>.{md,json,csv} por simulador + um conjunto; caches em
# results/_cache_protocol_*.npz (+ .stats.json), ignorados pelo git. Registrar no results/CHANGELOG.md.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
SIMS="grsim,erforce"; DELAY="both"; REPEAT=1; PY=""; MERGE=1; MERGE_ONLY=0; KEEP_UP=0; SMOKE=0; OUT=""; PREROLL="0"; PREROLL_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sims) SIMS="$2"; shift 2 ;;
    --delay) DELAY="$2"; shift 2 ;;
    --repeat) REPEAT="$2"; shift 2 ;;
    --python) PY="$2"; shift 2 ;;
    --no-merge) MERGE=0; shift ;;
    --merge-only) MERGE_ONLY=1; shift ;;
    --keep-up) KEEP_UP=1; shift ;;
    --smoke) SMOKE=1; shift ;;
    --out) OUT="$2"; shift 2 ;;
    --preroll) PREROLL="$2"; shift 2 ;;
    --preroll-only) PREROLL_ONLY=1; shift ;;
    -h|--help) sed -n '2,29p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m[protocol_holdout]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[protocol_holdout] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

if [[ -z "$PY" ]]; then
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then PY="$VIRTUAL_ENV/bin/python"
  elif [[ -x "$HOME/.venvs/dtssl/bin/python" ]]; then PY="$HOME/.venvs/dtssl/bin/python"
  else PY="python3"; fi
fi
"$PY" -c "import dtssl, dtssl.sim.protocol_plant" 2>/dev/null || die "dtssl não importa com $PY (pip install -e $REPO_ROOT[dev] no venv do WSL)"
cd "$REPO_ROOT"
"$PY" -m dtssl.cli info >/dev/null 2>&1 || die "dtssl info falhou em $REPO_ROOT (dataset/config acessíveis?)"

MARK="$(mktemp)"
touch "$MARK"
EXTRA_KW=()
[[ $SMOKE -eq 1 ]] && EXTRA_KW+=("max_events=1")
RUN_KW=()
[[ "$PREROLL" != "0" ]] && RUN_KW+=("preroll=$PREROLL")
[[ $PREROLL_ONLY -eq 1 ]] && RUN_KW+=("preroll_only=1")
OUT_ARGS=()
[[ -n "$OUT" ]] && OUT_ARGS+=(--out "$OUT")
RES_DIR="${OUT:-results}"

if [[ $MERGE_ONLY -eq 0 ]]; then
  IFS=',' read -r -a LIST <<<"$SIMS"
  for SIM in "${LIST[@]}"; do
    SIM="$(echo "$SIM" | tr -d ' ')"; [[ -n "$SIM" ]] || continue
    log "==== $SIM: subindo o simulador"
    "$HERE/simctl.sh" "$SIM" start
    log "==== $SIM: sonda (teleporte + 1 janela de 1 s)"
    "$PY" -m dtssl.sim.protocol_plant --sim "$SIM" || { "$HERE/simctl.sh" "$SIM" log; "$HERE/simctl.sh" "$SIM" stop; die "sonda falhou em $SIM"; }
    log "==== $SIM: dtssl analysis run protocol_holdout --kw sims=$SIM delay=$DELAY repeat=$REPEAT ${RUN_KW[*]:-}  (tempo real; ~8 min por variante)"
    T0=$(date +%s)
    "$PY" -m dtssl.cli analysis run protocol_holdout "${OUT_ARGS[@]}" --kw "sims=$SIM" "delay=$DELAY" "repeat=$REPEAT" quiet=true "${RUN_KW[@]}" "${EXTRA_KW[@]}" \
      || { [[ $KEEP_UP -eq 1 ]] || "$HERE/simctl.sh" "$SIM" stop; die "análise falhou em $SIM"; }
    log "==== $SIM: concluído em $(( $(date +%s) - T0 )) s"
    [[ $KEEP_UP -eq 1 ]] || "$HERE/simctl.sh" "$SIM" stop
  done
fi

if [[ $MERGE -eq 1 ]]; then
  if [[ $MERGE_ONLY -eq 1 ]]; then
    CACHES=$(ls "$RES_DIR"/_cache_protocol_*.npz 2>/dev/null | tr '\n' ',' | sed 's/,$//')
  else
    CACHES=$(find "$RES_DIR" -maxdepth 1 -name '_cache_protocol_*.npz' -newer "$MARK" | sort | tr '\n' ',' | sed 's/,$//')
  fi
  [[ -n "$CACHES" ]] || die "nenhum cache $RES_DIR/_cache_protocol_*.npz para reanalisar"
  log "==== artefato conjunto a partir de: $CACHES"
  "$PY" -m dtssl.cli analysis run protocol_holdout "${OUT_ARGS[@]}" --kw "from_cache=$CACHES" quiet=true "${EXTRA_KW[@]}"
fi
rm -f "$MARK"
log "artefatos: $(ls -t "$RES_DIR"/protocol_holdout_*.md 2>/dev/null | head -3 | tr '\n' ' ')"
log "lembrete: registrar no results/CHANGELOG.md e commitar results/protocol_holdout_*.{md,json,csv} no Windows"
