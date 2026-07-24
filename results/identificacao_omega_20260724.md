# Identificação FOPTD do DOF ω — dataset dedicado de rotação pura (malha aberta)

**Data:** 2026-07-24. **Pré-registro:** `docs/PREREGISTRO_OMEGA_20260724.md` (critérios
fixados ANTES da estimação). **Script:** `automation/identify_omega_rotate.m` +
`automation/eval_omega_v3_se2.m` (reusado sem modificação, só trocando o candidato).
**Seed:** 42. **Commit:** f87197e-dirty.

## Resumo executivo

**PROMOVIDO.** Os três gates obrigatórios do pré-registro (faixa física, fit
hold-out ≥60%, SE(2) Wilcoxon p<0,05 vs placeholder) passaram. K_ω = 1,0016
(IC95% [0,9993; 1,0040]) — confirma a hipótese central do artigo: o ganho
≈1,3–1,35 medido em malha fechada (logs de competição) era viés de correlação
comando↔perturbação, não ganho real de planta. `config/twin_params.json`
atualizado (`placeholder:false`); `models/sysid_omega_rotate_v1.mat` salvo.

## ETAPA 1 — Dados

Regime linear (6 eventos, ±1/±2,5/±5 rad/s): TREINO = `rotate_01_05`(+1),
`rotate_01_08`(−2,5), `rotate_01_09`(+5), `rotate_01_10`(−5); HOLD-OUT =
`rotate_01_06`(−1), `rotate_01_07`(+2,5) — split idêntico ao gravado em
`metadata.json` (D9). Zona morta (±0,25/±0,5) excluída do fit (ver Etapa 4).

**Desvio declarado vs pré-registro (metodológico, não muda critérios):** os
splits *padded* por evento (`splits/rotate/rotate_01_XX/*.parquet`, pad=0,2 s)
excluem deliberadamente o transiente (desenhados para estatística de
regime/QC). Testado empiricamente: rodando `procest` sobre essa janela padded,
**Td colapsa para 0** (não-observável sem o degrau em si). Por isso a
montagem do `iddata` usa o log contínuo pré-pad (`rotate_raw.csv`, leitura
apenas, nunca modificado), janela `[t_start−0,5 s, t_end]` de cada evento —
mesma reamostragem Ts=1/60, mesmo ZOH do comando, mesmo filtro SG, sem
detrend. Isso é uma correção necessária de identificabilidade, não uma
escolha pós-hoc sobre o resultado (decidida antes de rodar o `procest` real,
ao constatar Td=0 na primeira tentativa).

**Banda passante do filtro SG (win=7, ordem=2, fs=60 Hz — reamostrado
PRIMEIRO, filtrado DEPOIS, igual `identify_trans_dof.m`):** coeficientes
exatamente simétricos (`max|c(i)-c(N+1-i)| = 5,6e-17`) → filtro FIR de fase
zero para amostras interiores (o delay de grupo de (N-1)/2=3 amostras é
centrado, não desloca o sinal; só as 3 amostras de borda de cada evento usam
coeficientes assimétricos, <1% dos ~576 amostras/evento). **fc(-3dB) = 9,59 Hz**,
bem acima da banda estimada da planta (τ̂=0,0828 s → 1/(2πτ)≈1,92 Hz, ~5×
abaixo do corte) — filtro não distorce a dinâmica identificada. Ver
`results/figs/identificacao_omega_sgfreq_20260724_1727.png`.

**Nota:** ~96 ms (mencionado como referência) corresponderia a filtrar na
grade nativa da visão (~73 Hz) ANTES de reamostrar — não é o que
`identify_trans_dof.m`/esta sessão fazem (reamostram para 60 Hz primeiro); a
 janela real em tempo é 7/60≈116,7 ms.

## ETAPA 2 — Estimação

`procest('P1D')` multi-experimento sobre os 4 eventos de treino. Td0 inicial
por xcorr comando↔ω medido (log contínuo pré-pad, janela ±0,3 s ao redor de
cada transição de treino): {0,1167; 0,0833; 0,0833; 0,1000} s → mediana
0,0917 s.

| Parâmetro | Estimativa | IC 95% |
|---|---:|---:|
| K_ω | **1,0016** | [0,9993; 1,0040] |
| τ_ω | **0,0828 s** | [0,0801; 0,0855] |
| Td_ω | **0,0890 s** (5,34 passos de Ts=0,0167 s) | [0,0877; 0,0902] |

**Correlação τ–Td: ρ = −0,4735** — abaixo do limiar de alerta (\|ρ\|>0,8), não
sinalizado como limitação de identificabilidade grave, mas moderado (esperado
dado transitório curto, ~5-8 amostras a 60 Hz).

**Convenção de discretização:** o simulador (`parameter_estimation_model_pid_v3`)
implementa G_ω(s) como `TransferFcn`+`TransportDelay` **contínuos**, integrados
por solver de passo fixo (`FixedStepAuto`, `FixedStep=Ts=1/60 s`) — checado via
`getActiveConfigSet`. Não é substituição algébrica ZOH-exato (α=1−e^(−dt/τ))
nem Euler manual sobre um filtro discretizado à parte: é integração numérica
de passo fixo do modelo contínuo identificado por `procest`, que é o consumo
correto/esperado de um θ contínuo. Com Ts/τ≈0,0167/0,0828≈0,20, o erro de
discretização de um integrador RK de passo fixo é pequeno — consistente.

## ETAPA 3 — Validação (ordem fixada no pré-registro, sem ajuste pós-hoc)

| # | Critério | Resultado | Veredito |
|---|---|---|---|
| (i) | K∈[0,5;2], τ∈[0,02;0,5], Td≤0,15 | K OK, τ OK, Td OK | **PASSA** |
| (ii) | fit hold-out ≥60% | 71,1% média (`rotate_01_06`=65,0%, `rotate_01_07`=77,2%); fit treino mediana 83,2% | **PASSA** |
| (iii) | SE(2) multi-h vs placeholder, Wilcoxon p<0,05, candidato melhor | **todos os 5 horizontes**, ver tabela abaixo | **PASSA** |
| (iv) | Ljung-Box (informativo, caveat sgolay) | L=20, p≈0 (rejeita brancura) | *não é gate* — mesmo caveat da Etapa C: saída é derivada sgolay do heading, ruído colorido por construção, N grande ⇒ rejeição esperada mesmo com ganho correto |

### Gate (iii) — detalhe (18 eventos `shoot_to_goal`, candidato vs placeholder K=1/τ=0,1/Td=0)

| h (s) | n | mediana cand (m) | mediana plac (m) | Δmediana (m) | p (Wilcoxon) |
|---:|---:|---:|---:|---:|---:|
| 0,5 | 18 | 0,0488 | 0,0994 | **−0,0508** | 1,96e-4 |
| 1,0 | 18 | 0,0943 | 0,1786 | **−0,0896** | 1,96e-4 |
| 2,0 | 18 | 0,1927 | 0,3118 | **−0,1335** | 1,96e-4 |
| 2,5 | 18 | 0,2174 | 0,3533 | **−0,1542** | 1,96e-4 |
| 4,0 | 18 | 0,3691 | 0,5255 | **−0,1819** | 1,96e-4 |
| pool | 90 | 0,1352 | 0,2811 | **−0,1138** | **1,74e-16** |

Δ<0 = candidato MELHOR que placeholder — em TODOS os horizontes, com folga
crescente (candidato reduz o erro em até 35% @h=4s). Todos os 18 eventos
`shoot_to_goal` da campanha entram como "não_qualif" no relatório do script
(role treino/holdout é definido pelos eventos ROTATE, não pelos
`shoot_to_goal` — a rotulagem é irrelevante aqui: o teste avalia
generalização a um dataset totalmente diferente do usado no fit, por design).
Artefatos: `results/eval_omega_v3_se2_20260724_1723.csv`,
`results/eval_omega_v3_wilcoxon_20260724_1723.csv`,
`results/traj_eval_omega_v3_20260724_1723.mat`.

Figura (resposta ao degrau, medido vs simulado, treino e hold-out):
`results/figs/identificacao_omega_stepresponse_20260724_1727.png`

## ETAPA 4 — Caracterização da zona morta

- **Limiar empírico (dataset rotate):** bracket **(0,5; 1,0] rad/s** comandado
  — motor nunca acionado (PWM=0) em ±0,25 e ±0,5; ativo em ±1. Não medimos
  dentro do intervalo (sem escada fina entre 0,5 e 1,0) — **limitação
  declarada**.
- **Limiar teórico:** CAD → 1,567/2,6991 = **0,5806 rad/s**; firmware
  implícito → 1,567/2,61 = **0,6004 rad/s**. Reportado como **INTERVALO
  0,58–0,60 rad/s**, nunca valor pontual (`config/robot_geometry.json`).
- **Mecanismo confirmado (não atrito de corpo):** PWM=0 em ±0,25 e ±0,5 (motor
  nunca recebeu torque — não há o que o atrito precisaria vencer); PWM≠0 em
  ±1 e acima. Zona morta **ELÉTRICA POR RODA** (`MOTOR_MIN_SPEED_RAD_S=1,567
  rad/s`, `utils.h:42`, firmware `ssl-embedded`), ver
  `results/qc_rotate_20260724_125828.md` §7 e `config/robot_geometry.json`.

### Fração de comandos de ω mascarados nos logs de competição (RECALCULADA)

A afirmação histórica ("~84% dos comandos 'dentro'", CLAUDE.md/RELATORIO §4)
foi **reproduzida** nesta sessão: usava o limiar **0,3 rad/s** (zona morta
antiga hardcoded na IK do simulador, já removida em 2026-06-11) — **não**
0,472 como uma leitura apressada poderia sugerir. Recalculado para os 4
limiares relevantes, por label e pooled (46 splits, `|cmd_vw|`, robot_id
majoritário por evento):

| label | n | limiar antigo IK (0,3) | limiar deprecated (0,472) | limiar CAD (0,581) | limiar firmware corrigido (0,600) |
|---|---:|---:|---:|---:|---:|
| square | 11760 | 88,5% | 97,4% | 98,9% | 99,1% |
| shoot_to_goal | 7519 | 57,4% | 71,2% | 76,5% | 77,3% |
| side_to_side | 14281 | 93,0% | 96,4% | 97,9% | 98,2% |
| front_to_back | 3877 | 95,9% | 98,0% | 98,8% | 98,9% |
| **POOL (46 splits)** | **37437** | **84,8%** ✓ reproduz o "~84%" histórico | 91,8% | 94,0% | **94,3%** |

**Conclusão:** com o limiar corrigido (0,58–0,60 rad/s, ~2× o antigo 0,3), a
fração de comandos de ω abaixo do limiar de acionamento do motor sobe de
~85% para **~94%** — ainda mais comandos de rotação em jogos reais são
mascarados pela zona morta do que se pensava. Isso reforça a conclusão
central do projeto: ω não é bem excitado em malha fechada de competição
(shoot_to_goal, o label mais rico em rotação, ainda assim mascara 77,3%),
justificando por que a coleta dedicada (esta sessão) era necessária.

## ETAPA 5 — Comparação malha fechada vs malha aberta (peça central do artigo)

| | **Malha fechada** (`identify_omega_v3_linear.m`, candidato v3, 2026-06-13) | **Malha aberta** (esta sessão, dataset dedicado) |
|---|---:|---:|
| Fonte de dados | logs de competição, `shoot_to_goal`, \|cmd_ω\|>0,3 | dataset dedicado de rotação pura (vx=vy=0), escada de amplitudes |
| K | 1,307 | **1,0016** [0,9993; 1,0040] |
| τ | 0,0222 s | **0,0828 s** [0,0801; 0,0855] |
| Td | 0,1179 s | **0,0890 s** [0,0877; 0,0902] |
| fit hold-out | por regime (critério iv da época): alto 31,9% / baixo −11,2% (fit único não reportado, por desenho daquela sessão) | **71,1%** média (65,0%/77,2%) |
| (i) faixa física | OK | OK |
| (ii) gate de fit | n/a (critério antigo era ≥60% número único, relaxado para "por regime" naquela sessão) | **71,1% ≥ 60% OK** |
| (iii) SE(2) vs placeholder, pool | Δmediana **+0,0489 m** (PIOR) @h=4s, p=3,8e-9 (pool) — **REPROVA** | Δmediana **−0,1819 m** (MELHOR) @h=4s, p=1,74e-16 (pool) — **PASSA** |
| (iv) Ljung-Box | REPROVA (p≈0) | REPROVA (p≈0) — mesmo caveat sgolay em ambos |
| **Veredito** | **NÃO promovido** | **PROMOVIDO** |

### Hipótese testada: K_ω≈1,0 em malha aberta vs viés de correlação em malha fechada

**Confirmada com folga.** K=1,0016 (IC95% [0,9993;1,0040]) é estatisticamente
indistinguível de 1,0 — compatível com a hipótese de que o ganho ≈1,3–1,35
medido em malha fechada (`diag_omega_gain_amplitude.m`, 2026-06-13, e o
próprio candidato v3, K=1,307) era artefato de **viés de correlação
comando↔perturbação**: em malha fechada, o jogador/controle humano/tático
corrige a trajetória continuamente, e o comando de ω correlaciona-se com
perturbações não-modeladas (atrito do carpete, colisões, correções táticas)
de um jeito que infla o ganho aparente — não é ganho real de planta. Também
consistente com o próprio QC do dataset rotate (`results/qc_rotate_20260724_021248.md`
§8, K_ω medido ≈1,01/1,02/1,01 nos três degraus antes desta identificação
formal — já apontava nessa direção).

**Leitura para a tese/artigo:** este é o resultado mais forte da linha de
identificação de ω do projeto — não porque "vence" um teste isolado, mas
porque explica COERENTEMENTE por que a tentativa em malha fechada falhava
(vide δ crescente com horizonte no gate SE(2) da v3: super-rotação
amplificando deriva de heading) e por que a mesma estrutura, com dado limpo,
não só passa como MELHORA sistematicamente com o horizonte. É evidência
direta de um limite de identificabilidade de dados de malha fechada de
competição para este DOF específico — a contribuição metodológica central da
tese quanto a ω.

## ETAPA 6 — Promoção e registro

**PROMOVIDO.** Todos os 3 gates obrigatórios (i, ii, iii) passaram.

- `config/twin_params.json`: `dof.w` atualizado (`K=1,0016`, `τ=0,0828`,
  `Td=0,0890`, `placeholder:false`).
- `models/sysid_omega_rotate_v1.mat` salvo (theta0 completo — vx/vy de
  `sysid_vxvy_v2.mat` + ω novo —, theta_w, model_w, report).
- **Bins de rotação/misto re-rodados** (`phase0_replay.metrics_report`, twin
  vs `IdealKinematicPlant` — **não** vs rSim/grSim: `robosim` segue
  indisponível neste ambiente, bloqueio pré-existente documentado em sessões
  anteriores, não desta). Resultado honesto, não um "GO" forçado:

  | bin | N total | N indep | veredito |
  |---|---:|---:|---|
  | trans-dominado | 264 | 49 | **GO** (gap@h_ref=+0,0617 m, p=1,15e-8, effect=+0,832) |
  | misto | 0 | 0 | SEM POPULAÇÃO (não é mais "INDETERMINADO (placeholder)" — mudou de motivo, mas continua sem veredito: 0 janelas neste hold-out) |
  | rot-dominado | 1 | 0 | SEM POPULAÇÃO (N_indep=0 < N_min=10; único ponto disponível sugere gap@h_ref=+0,195 m mas sem poder estatístico) |

  A promoção de ω **não desbloqueia** um veredito real de rotação pura no
  gate twin-vs-baseline do hold-out de competição — não por causa do
  placeholder (que já não se aplica), mas porque o hold-out de 10 eventos de
  competição tem população quase nula de janelas rotação-dominadas (mesmo
  resultado qualitativo da auditoria de geometria anterior). Relatório:
  `results/phase0_metrics_report_20260724_1729.md`.

### Desvio declarado (registrado, não coleta adicional)

Amostra de 6 eventos no regime linear (4 treino / 2 hold-out), sem escada
fina entre 0,5 e 1,0 rad/s comandado — limiar de zona morta reportado como
intervalo (0,58–0,60), não localizado com precisão maior. Coleta adicional
dedicada **não realizada** por indisponibilidade do robô nesta janela de
tempo (deadline do artigo, 15/08/2026). Registrado como limitação explícita
do artigo, não escondido.

## Arquivos gerados

- `docs/PREREGISTRO_OMEGA_20260724.md` (pré-registro)
- `automation/identify_omega_rotate.m` (estimação)
- `automation/run_se2_gate_rotate.m` (wrapper batch do gate iii)
- `build/sysid_omega_rotate_v1_tmp.mat` (candidato intermediário)
- `models/sysid_omega_rotate_v1.mat` (**PROMOVIDO**)
- `config/twin_params.json` (atualizado, placeholder:false)
- `results/eval_omega_v3_se2_20260724_1723.csv` + `eval_omega_v3_wilcoxon_20260724_1723.csv` + `traj_eval_omega_v3_20260724_1723.mat`
- `results/figs/identificacao_omega_stepresponse_20260724_1727.{png,svg}`
- `results/figs/identificacao_omega_sgfreq_20260724_1727.{png,svg}`
- `results/phase0_metrics_report_20260724_1729.md` + figs `M1_metrics_*_20260724_1729.{png,svg}`
- Este relatório: `results/identificacao_omega_20260724.md`
