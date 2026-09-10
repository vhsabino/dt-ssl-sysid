#!/usr/bin/env bash
# run_erforce.sh — atalho: tools/external_sims/simctl.sh erforce start|stop|status|log|probe [opções]
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/simctl.sh" erforce "${@:-status}"
