#!/usr/bin/env bash
# run_grsim.sh — atalho: tools/external_sims/simctl.sh grsim start|stop|status|log|probe [opções]
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/simctl.sh" grsim "${@:-status}"
