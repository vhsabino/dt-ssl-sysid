# `train/` — custo do PSO, InitFcn legado e pré-processamento de logs (abr–mai/2026, ARQUIVADO)

Era `matlab/train/`.

| Script | Papel | Substituído por |
|---|---|---|
| `avaliar_gemeo_digital.m` | função de custo do PSO (`K_Matrix` → `SimulationInput` do `pid_v2` → custo) | `dtssl.eval` (métrica multi-horizonte) |
| `control_parameters.m` | `InitFcn` legado dos modelos `pid`/`pid_v2`: define `Ts=0.0167` (arredondado — conflitava com o `Ts=1/60` do SLDD, ver CHANGELOG 2026-07-24 19:35), ganhos PI do firmware (`Kp=0.3194`, `Ki=6.434`), modelo de motor de 2ª ordem; carregava `scripts\local\train\robocin_tests_id5.mat` (cache local, fora do git — caminho Windows substituído por raiz relativa) | SLDD `config/ssl_robot.sldd` + `InitFcn` mínimo do `pid_v3` (`K_Matrix = zeros(1,12)`) |
| `time_raw.m`, `time_sync.m` | leitura de logs exportados `.log.gz.txt` → buffers de câmera/comando a 60 Hz (ids/times hard-coded) | `dtssl etl extract` / `dtssl etl split` (`dtssl.data.extract`, `recordio`) |

`ensure_model_ready.m` (vivo, `matlab/dtssl/`) documenta por que os workarounds do `control_parameters`
deixaram de ser necessários em 2026-06-11. Sem entradas próprias no CHANGELOG.
