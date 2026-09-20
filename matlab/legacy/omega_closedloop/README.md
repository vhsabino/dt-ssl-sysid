# `omega_closedloop/` — identificação de ω com dados de malha fechada (jun/2026, ARQUIVADO)

Era `automation/`. Todas as tentativas de identificar o DOF ω a partir dos logs de competição
(comandos de malha fechada da estratégia, label `shoot_to_goal`). Nenhum candidato passou o
gate SE(2); o resultado científico que sobreviveu é o **contraste** com a identificação em malha
aberta (`matlab/dtssl/identify_omega_rotate.m`, PROMOVIDA em 24/07/2026): mesma estrutura P1D,
dado diferente, veredito invertido (K≈1,3 de malha fechada = viés de correlação comando↔perturbação).

| Script | Papel | Entradas do `results/CHANGELOG.md` que gerou |
|---|---|---|
| `check_excitation.m` | diagnóstico de excitação de `move_w` por evento (std, nº de frequências, xcorr, Td0) — critério de seleção dos 14 eventos "qualificados" | `results/check_excitation_20260611_0852.csv` (sem entrada própria; citado por `identify_omega_from_splits`) |
| `identify_omega_from_splits.m` | Tentativa 1: `procest('P1D')` multi-experimento nos splits (9 treino / 5 hold-out, seed 42) | 2026-06-11 09:55 — `theta_w {K=1.3533, tau=0.0354, Td=0.1058}`, fit hold-out 52,6 % (<60 %) → **NÃO aprovado**; `models/sysid_initial_v2_candidate.mat` |
| `diag_omega_gain_amplitude.m` | Etapa A: ganho efetivo por faixa de \|cmd_w\| (robustfit), pool 7405 amostras | 2026-06-13 22:39 — ganho plano ~1,3–1,5, sem joelho de zona morta no ω de corpo |
| `diag_omega_gain_sign.m` | Etapa A2: assimetria de sinal do ganho | 2026-06-13 23:12 — sem assimetria recuperável |
| `identify_omega_v3_linear.m` | Etapa C: P1D só no regime alto (\|cmd_w\|>0,3, segmentos com pad 0,2 s) | 2026-06-13 23:40 — `{K=1.307, tau=0.0222, Td=0.1179}`; gate SE(2) **REPROVOU** (candidato pior em todos os horizontes, pool p=3,8e-9); `models/sysid_omega_v3_linear_candidate.mat`. Corrigido em 2026-07-24 16:00 (linha 138: zona morta lida de `config/robot_geometry.json`, intervalo 0,581–0,600 rad/s) |

Gate usado por estes candidatos: `matlab/dtssl/eval_omega_v3_se2.m` (vivo, reutilizado em 24/07).

Dependem de: `data/extracted/2026-05-18_19-2-15/splits/shoot_to_goal/*` (DVC),
`results/traj_eval_campaign_20260611_2238.mat` e `results/diag_omega_gain_amplitude_*.mat`
(não versionados), `models/sysid_initial.mat` (era `results/sysid_initial.mat`).
