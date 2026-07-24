# Relatório Técnico de Desenvolvimento — Gêmeo Digital SSL
*Documento vivo. Registra o que foi feito, por quê, com que resultado e o que está pendente. Atualizado a cada marco. Última atualização: 24/07/2026.*

---

## 0. Sumário do projeto
**Objetivo:** gêmeo digital de fidelidade observacional comportamental do robô SSL omnidirecional 4 rodas (RobôCIn v2025), identificado a partir de logs de competição em malha fechada (pose a 60 Hz).
**Contribuição central (tese):** metodologia de identificação grey-box por grau de liberdade (DOF) calibrada por otimização bayesiana, e caracterização dos limites desse tipo de dado.
**Modelo:** por DOF i ∈ {vx, vy, ω}: G_i(s) = K_i · e^(−Td_i·s) / (τ_i·s + 1). Vetor de 9 parâmetros, ordem fixa [K_vx, τ_vx, Td_vx, K_vy, τ_vy, Td_vy, K_ω, τ_ω, Td_ω].
**Stack:** MATLAB/Simulink + SLDD, Python (ETL, SLR), DVC+Git, System Identification Toolbox, bayesopt.
**Prazo:** submissão de artigo até 31/07/2026 (qualificação). Vertente RL = próximo passo, pós-identificação.
**Periódico-alvo (a confirmar encaixe):** Robot Learning (ELSP), special issue learning-based planning — VERIFICAR deadline, APC e adequação de escopo com a orientadora.

---

## 1. Arquitetura verificada do simulador (modelo pid_v3)
- Free-run genuíno: nenhuma injeção de pose real no estado simulado (teacher forcing foi removido e confirmado ausente — 174 blocos inventariados).
- Condições iniciais paramétricas (x0, y0, θ0) — antes eram fixas em pose de log antigo.
- Cadeia de rodas (IK→FK) = identidade fora de não-linearidades (pinv exata da matriz K); ganho de regime = 1 por DOF (teste unitário).
- Zonas mortas parametrizadas, default 0 (ver §4, defeito 2 e §6).
- InitFcn mínimo (consome só K_Matrix; provado via Simulink.findVars).
- SLDD restaurado após cada rodada (onCleanup) — configuração canônica não muda por efeito colateral.
- run_one apenas simula; a métrica vive no orquestrador.
- **Limite estrutural:** SLDD impõe τ ≥ 0,01 s; o baseline "ideal exato" só existe via dead-reckoning analítico fora do Simulink.

## 2. Métrica de fidelidade (definição canônica)
**Pergunta:** partindo do estado verdadeiro, quanto o gêmeo deriva em h segundos sem correção?
- **Free-run**, nunca teacher forcing (este último mede só ruído de 1 passo e infla a fidelidade).
- Trajetória fatiada em **janelas por tempo** de duração h (overlap 0,5); RMSE de posição por janela; agregação por mediana (robustez).
- **Duas âncoras, sempre reportadas:** *translação* (herda heading acumulado — mostra efeito de longo prazo) e *SE(2)* (alinha pose completa — isola dinâmica intra-janela; é a definição alinhada ao propósito declarado de fidelidade em horizonte).
- Âncora SE(2) válida em pós-processamento (sem re-simular) pela **equivariância SE(2)** do modelo (corpo-frame + cadeia identidade); âncora de heading usa θ truth **filtrado** (mediana móvel 0,2 s) para não girar a janela por ruído de visão em t₀.
- Horizontes avaliados: h ∈ {0,5; 1; 2; 2,5; 4} s.
- **Pendência estatística:** afirmações de "vence" exigem Wilcoxon pareado (ainda não aplicado).

## 3. Dados
- 46 splits válidos, labels: front_to_back (4), shoot_to_goal (18), side_to_side (13), square (11).
- **Grade temporal irregular em todos os splits** (rajadas de ~2 ms em square/side_to_side/front_to_back; ~20 ms em shoot_to_goal). Consequência crítica: avaliações antigas que contavam janela por amostra colapsavam para janela única em 34/46 eventos. Corrigido (janela por tempo).
- Identificação de ω regrada para Ts=1/60 antes do procest (build_omega_iddata) — não afetada pela irregularidade.
- Versionamento: DVC (data/extracted + data/recorded), 674 arquivos. Remote único local — segundo remote (HD) pendente.

## 4. Defeitos de validade encontrados e corrigidos (linha do tempo dos números)
| # | Defeito | Sintoma | Correção | Efeito no RMSE (square ref.) |
|---|---|---|---|---|
| 1 | Condições iniciais fixas | quadrado deslocado/girado | ICs paramétricas | 2,30 m → 0,405 m |
| 2 | Zona morta ±0,3 rad/s hardcoded na IK | θ simulado congelado; 84% dos comandos "dentro" | removida (parametrizada) | 0,405 → 0,65 m (validade ↑, erro real exposto) |
| 3 | Grade temporal irregular | janela colapsada em 34/46 | janela por tempo | inverteu manchetes; ver §5 |
| 4 | Proveniência fraca (hash, SLDD sujo) | commits "no-commit"; SLDD mutado | hash no início + onCleanup restore | — |
**Verificação matemática (11/06):** simulador reproduzido por integração analítica independente com erro máx 4,6 mm (x), 5,7 mm (y), 0,0009 rad (θ). O gêmeo implementa exatamente o modelo declarado.

## 5. Resultados atuais (campanha de 46 cenários)
**Medianas por label (h=2,5 s; translação / SE(2), m):**
| label | ideal_analytic | ω placeholder | ω candidato |
|---|---|---|---|
| front_to_back | 0,353 / 0,272 | 0,379 / 0,294 | 0,437 / 0,314 |
| shoot_to_goal | 0,381 / 0,406 | 0,420 / 0,359 | 0,487 / 0,437 |
| side_to_side | 0,276 / 0,236 | 0,357 / 0,335 | 0,369 / 0,340 |
| square | 0,320 / 0,281 | 0,482 / 0,338 | 0,565 / 0,360 |
| **global** | **0,339 / 0,322** | 0,434 / 0,340 | 0,518 / 0,372 |

**Medianas globais por horizonte (SE(2), m):** 0,5→{ideal 0,106; placeholder 0,096; cand 0,098} · 1→{0,179; 0,176; 0,181} · 2→{0,278; 0,302; 0,330} · 2,5→{0,316; 0,340; 0,371} · 4→{0,383; 0,441; 0,515}.
**Leitura:** erro ~0,10 m @0,5 s e ~0,32–0,34 m @2,5 s = 8–13% da distância percorrida em malha aberta. Dinâmica identificada dá vantagem ligeira em h≤1 s e vence em shoot_to_goal sob SE(2); ideal lidera horizontes longos.

### Re-identificação e validação de vx/vy v2 (2026-06-14) — PROMOVIDO
vx/vy eram herdados do trabalho antigo: já P1D (K,τ,Td), mas **nunca validados em hold-out** (`rmse_val=NaN` no `report` do `sysid_initial`). Re-identificados por DOF, mesma estrutura P1D, com a velocidade medida **derivada da posição da visão** (Savitzky-Golay) e rotacionada ao corpo por θ; 1 experimento por evento, sem detrend; hold-out por evento (≈⅔/⅓, seed 42). Excitação (Fase 1, `check_excitation_trans.m`): vx limpo em **front_to_back** (xcorr 0,99), vy em **side_to_side** (xcorr 0,99); Td0 model-free vx≈0,15 / vy≈0,18 s, consistente com ω.

| DOF | antigo (K,τ,Td) | **novo (K,τ,Td)** | fit hold-out | fonte (eventos) |
|---|---|---|---|---|
| vx | 0,989 · 0,128 · 0,171 | **1,119 · 0,072 · 0,069** | **86,7%** (1 ev) | front_to_back (4) |
| vy | 0,949 · 0,242 · 0,105 | **1,052 · 0,127 · 0,057** | **87,1%** (4 ev) | side_to_side (13) |

**Gate SE(2) multi-horizonte vs placeholder** (`eval_theta_se2_vs_placeholder.m`; candidato simulado no mesmo pipeline Simulink, placeholder reusado da campanha `traj_eval_campaign_20260611_2238.mat`, sem re-rodar os 138 baselines): ambos melhoram em **todos** os horizontes e **todos** os eventos — vx **20/20**, vy **65/65** (event×horizonte), inclusive nos hold-out (vx Δ=−0,193 m; vy Δ=−0,13…−0,19 m). Medianas SE(2) h=2,5: vx **0,124 vs 0,293 m**; vy **0,141 vs 0,334 m** (~55% de redução). Wilcoxon pareado: **vy per-horizonte p=2,4e‑4** (n=13); **vx** per-horizonte p=0,125 (n=4 = piso do teste) mas **multi-h pooled p=8,9e‑5** (efeito unânime). Faixa física: ambos OK. **Veredito do gate: ambos PROMOVIDOS** → `models/sysid_vxvy_v2.mat` (vx/vy novos + ω placeholder). Confirma a hipótese: o gap residual em horizonte médio/longo sob SE(2) era de **vx/vy** (placeholder lento, τ/Td grandes herdados sem validação); o modelo mais rápido (τ/Td menores) reduz a deriva de posição translacional. Artefatos: `results/check_excitation_trans_20260614_1018.csv`, `results/eval_vx_v2_*_20260614_1024.csv`, `results/eval_vy_v2_*_20260614_1028.csv`, trajetórias `results/traj_eval_v{x,y}_v2_*.mat`.

## 6. Identificação de ω — estado e plano (diretiva da orientadora: identificar ω antes de prosseguir)
**Tentativa 1 (candidato, NÃO promovido):** θ_w={K=1,353; τ=0,0354 s; Td=0,1058 s}; fit 52,6% em hold-out (< critério antigo de 60%). Td≈106 ms consistente com latência visão→rádio (valida a estrutura). Piora a posição vs placeholder → diagnóstico: ganho identificado em eventos de alta rotação não transfere; provável viés de malha fechada + ausência de modelo de não-linearidade.
**Observação da orientadora (decisiva):** robô vai bem em alta velocidade, mal em baixa → **não-linearidade estática (zona morta/atrito)**. A zona morta de ±0,3 hardcoded era provavelmente conhecimento empírico da equipe; volta agora como parâmetro **identificado** (estrutura Hammerstein: zona morta → dinâmica linear).
**Plano de identificação (em execução):**
- Etapa A — diagnóstico H-b nos dados existentes: ganho efetivo por faixa de amplitude de |cmd_ω| (defasado por Td₀). Assinatura esperada: ganho ≈0 em baixas faixas, platô em altas; meia-altura ≈ largura da zona morta. Decide se K=1,35 era artefato de reta ajustada a curva com joelho.
- Etapa B — experimento dedicado (se houver robô): escada de amplitudes, degraus altos, rampas lentas, vx=vy=0.
- Etapa C — identificação 2 estágios: linear (procest P1D) nos comandos altos → K,τ,Td; depois zona morta d (fminbnd) com linear congelado. Conferência: idnlhw 'deadzone'.
- Etapa D — firmware: extrair a zona morta/saturação real codificada → número-âncora de validação.
**Novos critérios de aceite (substituem o fit≥60%):** (i) resíduo branco (Ljung-Box) no regime alto; (ii) parâmetros em faixa física; (iii) melhora no custo SE(2) multi-horizonte vs placeholder nos eventos ricos em rotação, com Wilcoxon p<0,05; (iv) fit reportado por regime (alto/baixo), nunca número único.

### Execução 2026-06-13 (diagnóstico ganho×amplitude, firmware, ID linear)
*Sessão de 4 etapas (A diagnóstico, A2 assimetria, B firmware, C ID linear). Mapeia o "Etapa A" do plano acima; o "experimento dedicado" e o "firmware" do plano foram, respectivamente, adiado (sem robô) e executado aqui (B).*

**A — Ganho efetivo × amplitude** (`automation/diag_omega_gain_amplitude.m`; 18 shoot_to_goal; Td₀=0,142 s por xcorr; heading suavizado Savitzky-Golay→derivada; pool 7405 amostras). Ganho = inclinação `robustfit(meas_ω~cmd_ω)` por faixa de |cmd_ω|: **plano ≈1,3–1,5 em toda a faixa**, sem joelho de zona morta no ω de **corpo**. O platô ≈1,35 **coincide** com o K=1,353 da Tentativa 1 → aquele K não era artefato de reta ajustada a curva com joelho; é ganho real ≈1,35. Faixa 0–0,1 dominada por ruído (mean|meas|=0,36 rad/s com mean|cmd|=0,05). Saída: `results/diag_omega_gain_by_band_20260613_2239.csv`, `results/figs/diag_omega_gain_amplitude_20260613_2239.{png,pdf}`.

**A2 — Assimetria de sinal** (`automation/diag_omega_gain_sign.m`; reuso do pool, sem re-suavizar/re-defasar). No regime confiável (|cmd_ω|≥0,3) a razão meas/cmd é **simétrica ≈1,3** entre sentidos (Δ≤0,11; sem viés direcional); faixas baixas com se 0,4–0,9 (a inclinação por sinal é mau estimador aí). **Sem assimetria recuperável** nestes dados — coerente com firmware simétrico (B). `results/diag_omega_gain_by_sign_band_20260613_2312.csv`.

**B — Firmware** (`ssl-embedded`, C++/mbed STM32; leitura apenas, fora do git/DVC do doutorado). A não-linearidade de ω é **POR RODA, depois da cinemática inversa**, não no ω de corpo. Zona morta viva: `PID_Controller.cpp:94` — `if (fabs(desired_rad_s) < MOTOR_MIN_SPEED_RAD_S) desired_rad_s=0`, com `MOTOR_MIN_SPEED_RAD_S = 1,567 rad/s` (setpoint de roda; `utils.h:42`); a IK `convertToWheel` (`kinematics.cpp:61-68`) é linear pura. **Conversão p/ corpo (rotação pura)**: ω_d = 1,567·(robot_radius/wheel_radius) = 1,567·(0,0265/0,0880) = **0,472 rad/s** (≈27°/s); com translação **não há ω_d de corpo escalar** (cada roda cruza 1,567 rad/s em ω distinto) → explica a invisibilidade no shoot_to_goal (A). **Simétrica** (`fabs`). Saturação superior por roda **±80 PWM** (`PID_Controller.cpp:157-164`; 30 em jogo): corta resposta alta, **não cria** ganho>1 — o ≈1,35 não vem do firmware. Mapa afim assimétrico (+57,71/−60,51, `utils.cpp:81-93`) existe mas é **código morto** (grep: nenhuma chamada; caminho vivo usa PI puro). **Implicação:** a estrutura Hammerstein com **d no ω de corpo não corresponde à física**; d é grandeza por roda.

**C — Identificação do ω linear** (`automation/identify_omega_v3_linear.m`; regime |cmd_ω|>0,3 em segmentos contíguos com pad 0,2 s, multi-experimento, sem detrend; 9 treino/5 hold-out, seed 42; mesmos 14 eventos qualificados). **θ_w = {K=1,307; τ=0,0222 s; Td=0,1179 s}**. Validação (critérios novos):
- **(ii) faixa física: OK** — K∈[0,5;2], τ∈[0,02;0,5], Td≤0,15.
- **(iv) fit por regime:** alto **31,9%** / baixo **−11,2%** — o linear só descreve o regime excitado.
- **(i) Ljung-Box: REPROVA** — h=1, p≈0, L=20 lags. *Caveat:* a saída é derivada suavizada (sgolay) do heading da visão ⇒ ruído **colorido por construção**, e N grande (milhares de amostras) ⇒ rejeição esperada; o teste não isola inadequação do **ganho**. Whiteness não é demonstrável neste tipo de dado.
- **(iii) custo SE(2) multi-horizonte vs placeholder: REPROVA** (`automation/eval_omega_v3_se2.m`; candidato simulado no MESMO pipeline Simulink, placeholder **reusado** da campanha `traj_eval_campaign_20260611_2238.mat`; 18 eventos; sem re-simular a campanha). Candidato **PIOR** em todos os horizontes: Δmediana(cand−plac) = +0,0065 / +0,0141 / +0,0310 / +0,0415 / +0,0489 m em h={0,5;1;2;2,5;4} s, **Wilcoxon pareado** p={2,0e-4; 3,9e-4; 3,3e-3; 9,6e-3; 4,3e-2}; pool p=3,8e-9. Penalidade **cresce com h** = super-rotação (K>1) amplificando deriva de heading no replay open-loop. `results/eval_omega_v3_se2_20260613_2340.csv`, `results/eval_omega_v3_wilcoxon_20260613_2340.csv`, `results/traj_eval_omega_v3_20260613_2340.mat`.

**Veredito:** `models/sysid_omega_v3_linear_candidate.mat` salvo, **NÃO promovido** (reprova (i) e (iii)). Achado central (limite do dado, contribuição da tese): logs de malha fechada permitem estimar o **ganho** de ω (≈1,3, fisicamente plausível) mas **não validam** ω como modelo free-run — o próprio ganho >1 que os dados exibem piora a posição em replay. A **largura da zona morta d permanece por roda** (firmware 1,567 rad/s de roda) e só será calibrável com **coleta dedicada de rotação pura** (vx=vy=0, escada de amplitudes). O modelo expõe `d` como gancho (default 0; valor de firmware documentado mas **não aplicado ao corpo**, pois corromperia eventos com translação). **bayesopt segue bloqueado** até essa coleta.

**Contraste com vx/vy (ver §5, 2026-06-14):** ao contrário de ω, vx/vy **passam** os mesmos gates (fit hold-out ~87%, faixa física, SE(2) Wilcoxon p<0,05 na direção certa) e foram **promovidos** (`sysid_vxvy_v2.mat`). A assimetria é informativa para a tese: a translação é observável em malha fechada (excitação limpa, xcorr 0,99) e o gêmeo melhora; a rotação não é validável como free-run (ganho >1 de malha fechada + zona morta por roda). ω permanece placeholder no θ promovido.

### Atualização 2026-07-24 — D3 (experimento dedicado recebido) + D9 (constante cinemática corrigida)

**D3 (correção de status):** o parágrafo "Execução 2026-06-13" acima registra que, do plano de identificação de ω, "o firmware" foi executado (Etapa B/D) mas "o experimento dedicado" (Etapa B do plano original, §6: "escada de amplitudes, degraus altos, rampas lentas, vx=vy=0") ficou **adiado (sem robô)** naquela data. Esse experimento **foi executado** (coleta de ~04–05/07/2026, robô yellow #6) e recebido nesta sessão como `data/extracted/2026-05-18_19-2-15/splits/rotate/rotate_raw.csv` (log multiplexado, armazenado sob a pasta do log mais antigo, 2026-05-18_19-2-15, reaproveitada como container — ver `results/CHANGELOG.md` 2026-07-24). Padronizado em 10 eventos (`rotate_01_01..10`, escada ±0,25/±0,5/±1/±2,5/±5 rad/s) com o mesmo contrato de `square/`; QC em `results/qc_rotate_*.md`. Este parágrafo estava desatualizado quanto a esse ponto — corrigido aqui.

**D9 (constante cinemática R/r corrigida):** a constante `robot_radius/wheel_radius = 0,088/0,0265 = 3,3208` citada no parágrafo "B — Firmware" acima (usada para derivar `ω_d = 1,567·(0,0265/0,0880) = 0,472 rad/s`) **não tinha rastreabilidade documental** e foi **refutada** por três evidências independentes e convergentes, todas com o dataset `rotate` recém-recebido: (a) CAD medido em 2026-07-24 (R_contato=79,601 mm, r_roda=29,492 mm → R/r=2,6991); (b) constante implícita no firmware/telemetria — `telemetry.d_speed` (setpoint de roda pós-clamp de zona morta) escala **exatamente** como `2,61·|cmd_ω|` em todas as amplitudes ativas do dataset `rotate`, não como `3,3208·|cmd_ω|`; (c) resposta de corpo medida via visão no mesmo dataset: K_ω≈1,01 (`results/qc_rotate_20260724_021248.md` §8) — consistente com ganho ≈1 quando a constante correta é usada, ao invés do ganho ≈1,35 relatado nas sessões de 13/06 (`diag_omega_gain_amplitude.m`) sob a constante deprecated. **Consequência:** o limiar de zona morta de ω comandado não é o valor pontual 0,472 rad/s; é o **intervalo 0,58–0,60 rad/s** (`1,567/2,6991=0,5806` a `1,567/2,61=0,6004`), sempre reportado como intervalo, nunca como ponto — consistente empiricamente com o dataset `rotate` (PWM=0 em ±0,5 rad/s comandado, motor ativo em ±1,0). A conclusão metodológica original **permanece válida e não muda**: a zona morta é **por roda** (`MOTOR_MIN_SPEED_RAD_S=1,567 rad/s`, `utils.h:42`, firmware `ssl-embedded`), e uma estrutura Hammerstein com zona morta no ω de corpo **não corresponde à física** — só o número do limiar muda. Fonte única de verdade: `config/robot_geometry.json` (blocos `physical`/`firmware`/`deprecated`). Uma questão de menor porte fica **declarada em aberto**: a constante hardcoded lida em `kinematics.h` do commit `eb57531` (2026-05-06) do firmware ainda é 3,3208 (não 2,61); a hipótese mais provável é deriva de versão entre esse commit e o binário efetivamente flasheado no robô durante a coleta de 04–05/07/2026 — não confirmado nesta sessão. Detalhe completo em `results/qc_rotate_20260724_125828.md` §5 e §7 (a versão anterior, `qc_rotate_20260724_021248.md`, permanece intacta para comparação — continha as leituras equivocadas de "déficit de ganho" e "zona morta de corpo por atrito estático", ambas corrigidas).

### Atualização 2026-07-24 (continuação) — Identificação FOPTD de ω, malha aberta: PROMOVIDO

**Pré-registro** (`docs/PREREGISTRO_OMEGA_20260724.md`, critérios fixados ANTES de rodar):
(i) K∈[0,5;2], τ∈[0,02;0,5], Td≤0,15; (ii) fit hold-out ≥60% (critério original do
projeto, reinstalado dado que agora o dado é de malha aberta dedicada); (iii) gate
SE(2) multi-horizonte vs placeholder, Wilcoxon p<0,05 em todos os horizontes;
(iv) Ljung-Box informativo (caveat sgolay, não é gate).

**Dados:** os 6 eventos do regime linear do dataset `rotate` (±1/±2,5/±5 rad/s;
TREINO={+1,−2,5,+5,−5}, HOLD-OUT={−1,+2,5} — mesma partição do QC de D9). Espelha
`identify_trans_dof.m` (vx/vy): P1D, `procest`, SG win=7/ordem=2 reamostrado a
Ts=1/60 primeiro, sem detrend. **Desvio declarado**: os splits *padded* por evento
excluem o transiente por design (pad 0,2 s) — testado empiricamente que isso faz
Td colapsar a 0 (não-observável); a montagem do `iddata` usa por isso o log
contínuo pré-pad (`rotate_raw.csv`, leitura apenas), janela `[t_start−0,5s, t_end]`
de cada evento, mesma reamostragem/filtro.

**Resultado:** θ_ω = {K=**1,0016** [IC95% 0,9993;1,0040]; τ=**0,0828 s**
[0,0801;0,0855]; Td=**0,0890 s** [0,0877;0,0902]}; correlação τ-Td ρ=−0,47 (abaixo
do limiar de alerta 0,8). Fit hold-out **71,1%** média (65,0%/77,2% por evento;
mediana treino 83,2%) — passa (ii). Faixa física OK — passa (i). Gate SE(2)
(`eval_omega_v3_se2.m`, MESMA metodologia da Etapa C, 18 `shoot_to_goal`): candidato
**MELHOR** que o placeholder em **todos os 5 horizontes** (Δmediana pool=**−0,1138 m**,
p=**1,74e-16**; por horizonte Δ=−0,051 a −0,182 m, p=1,96e-4 em todos) — passa (iii).
Ljung-Box rejeita (p≈0, mesmo caveat de sempre) — informativo, não reprova.

**Todos os 3 gates obrigatórios passaram → PROMOVIDO.** `config/twin_params.json`
atualizado (`dof.w.placeholder:false`); `models/sysid_omega_rotate_v1.mat` salvo.
Bins rotação/misto do gate twin-vs-baseline re-rodados (`phase0_replay.metrics_report`,
twin vs `IdealKinematicPlant` — rSim/`robosim` segue indisponível neste ambiente):
trans-dominado GO (gap+0,062 m, p=1,15e-8); misto/rot **SEM POPULAÇÃO** (0 e 1
janela no hold-out de 10 eventos de competição — não é mais o gate de placeholder,
é escassez real de dado rotação-dominado no hold-out).

**Leitura central (peça do artigo):** K≈1,0016 é estatisticamente indistinguível
de 1 — confirma a hipótese de que o ganho ≈1,3–1,35 medido em malha fechada
(§6, `diag_omega_gain_amplitude.m`, e o candidato v3 K=1,307) era **viés de
correlação comando↔perturbação** de dado de malha fechada, não ganho real de
planta. Contraste direto: v3 (malha fechada) reprovava (i)-Ljung-Box (mesmo
caveat) e (iii)-SE(2) (Δmediana pool **+0,0489 m**, PIOR, p=3,8e-9); esta
identificação (malha aberta dedicada) passa (iii) com Δmediana pool **−0,1138 m**,
MELHOR, p=1,74e-16 — mesma estrutura, dado diferente, veredito invertido. Essa é
a contribuição metodológica central da tese quanto a ω: caracterizar o LIMITE de
identificabilidade de dados de malha fechada de competição, resolvido com coleta
dedicada.

**Zona morta (Etapa 4, complementa D9):** fração de `|cmd_ω|` mascarada nos 46
splits de competição, recalculada com o limiar corrigido (0,58–0,60 rad/s, vs o
antigo 0,3 rad/s da IK — a claim histórica "~84%" foi REPRODUZIDA com threshold
0,3, não 0,472 como se poderia supor): pool sobe de 84,8% (threshold antigo 0,3)
para **94,3%** (threshold firmware corrigido 0,600); por label, `shoot_to_goal`
(o mais rico em rotação) vai de 57,4% para 77,3%. Reforça: mesmo o label mais
favorável mascara >3/4 dos comandos de ω — a coleta dedicada não era opcional.

**Desvio/limitação declarada:** amostra de 6 eventos no regime linear (4/2),
sem escada fina entre 0,5 e 1,0 rad/s comandado (limiar de zona morta fica como
intervalo, não ponto). Coleta adicional não realizada por indisponibilidade do
robô nesta janela (deadline do artigo SBR, 15/08/2026) — registrado como
limitação explícita, não escondida. Detalhe completo, figuras e tabelas:
`results/identificacao_omega_20260724.md`.

## 7. Calibração (decisão de método)
- PSO sobre constantes cinemáticas → **substituído** por identificação grey-box + bayesopt (validado pela orientadora; PSO como baseline **não** será mantido).
- bayesopt minimiza J(θ) = RMSE SE(2) multi-horizonte; entra no pipeline **somente após** ω promovido.
- **Pendência (RESOLVIDA 14/06):** definição exata do custo congelada em `automation/bo_cost.m` (ver abaixo).

### Execução — bayesopt v1 (Cenário B: fidelidade COMPORTAMENTAL, 2026-06-14)
*Decisão deliberada (Cenário B): calibrar os 9 params otimizando custo de trajetória, não fidelidade de parâmetro. Roda com ω em placeholder (ID física de ω reprovada); o objetivo é justamente expor a tensão parâmetro-vs-comportamento.*

**Custo congelado** (`bo_cost.m`): J = mediana_eventos[ wmean_h SE(2)(h) ] + λ·mediana_eventos[ wmean_h RMSE_heading(h) ], h∈{0,5;1;2;2,5;4} s, peso ∝ 1/h (norm.), âncora SE(2) com θ truth filtrado; **simula no MESMO pipeline Simulink** dos baselines. **Validação (Fase 0):** bo_cost(placeholder) reproduz as trajetórias salvas da campanha com **dif 0,0000 m**. **λ=1,171** (Fase 1: iguala contribuição heading↔posição no vx/vy v2 — J_pos=0,0592 m = λ·J_head). Custo ~50–70 s/sim (modelo lento) ⇒ 100 avaliações em **5 eventos de treino** cobrindo os 3 DOFs; validação em **10 eventos de hold-out** não vistos.

**bayesopt** (`run_bayesopt_v1.m`; 9 `optimizableVariable`, faixas SLDD K[0,5;2]/τ[0,02;0,5] log/Td[0;0,15]; EI-plus; determinístico; warm-start com vx/vy v2+ω placeholder, placeholder antigo e o ω candidato reprovado — semeia o GP, não fixa nada). **J: 0,1183 → 0,1048** (−11% no treino). θ_opt: vx{K=1,091;τ=0,079;Td=0,029}, vy{K=1,097;τ=0,021;Td=0,143}, **ω{K=0,516;τ=0,459;Td=0,106}**. **K_w no PISO (0,516)** — vs físico ≈1,35 e placeholder 1,0: o ótimo comportamental **suprime ω**. **ARD:** Kvy/Kvx dominam o custo (sens. 1,00/0,81); os params de ω são os **menos** sensíveis (Kw 0,19; Td_w 0,12; τ_w 0,03) — a posição é regida pela translação.

**Gate hold-out (Fase 3, `eval_bayesopt_holdout.m`):** θ_bayesopt **bate a cinemática ideal** (SE(2) pool −0,078 m, Wilcoxon p=1,4e‑4) **mas é significativamente PIOR que vx/vy v2** (pool **+0,0148 m, p=0,0052**, direção errada; pior em h≤1 s). O heading no hold-out tampouco melhora (0,215 vs 0,193 rad, p=0,23) — o K_w→0,5 **não generaliza**. **→ OVERFIT** aos 5 eventos de treino. **Veredito do gate: NÃO promovido** → `models/sysid_bayesopt_v1_candidate.mat`. O modelo robusto continua **vx/vy v2 + ω placeholder** (`sysid_vxvy_v2.mat`).

**Leitura para a tese:** o K_w→0,516 quantifica a **tensão parâmetro-vs-comportamento** (o custo de treino prefere ω atenuado, longe do físico ≈1,35) — coerente com a ID física de ω reprovada (§6). Porém a calibração comportamental com poucos eventos **overfit** e o **grey-box validado em hold-out generaliza melhor**: dado de malha fechada não sustenta nem ω físico nem ω comportamental fora da amostra. Refinamento (mais eventos de treino / custo sub-amostrado mais barato) é o próximo passo; nesta iteração o bayesopt **não** é promovido. Figuras: `results/figs/F5_bayesopt_holdout_horizons_*`, `F6_bayesopt_convergence_*`, `F7_bayesopt_ard_*`.

### Execução — bayesopt v2 (Caminho 2: proxy analítico no loop + treino amplo, 2026-06-14)
*Hipótese do v1: o overfit foi por **dado** (5 eventos para 9 params), não por método. Gargalo: o custo Simulink (**~9,5 s/sim**, medido) impede treino amplo. Estratégia (Caminho 2): usar um **proxy analítico barato** (dead-reckoning P1D, `bo_cost_proxy.m`, **~1,6 ms/sim** — 6000× mais rápido) no LOOP do bayesopt, validando antes que ele preserva o ranking de candidatos; toda a validação final e o gate continuam no Simulink fiel.*

**Resultado metodológico — verificação de ranking do proxy (Fase 0, GATE).** `automation/phase0_proxy_ranking.m`: 25 θ variados (22 por Latin Hypercube nas faixas do SLDD + os pontos conhecidos vx/vy v2, placeholder, ω candidato) × 6 eventos cobrindo os 3 DOFs; para cada θ calculou-se J pelo proxy analítico e J pelo Simulink fiel (mesmo pipeline dos baselines). **Spearman ρ = 0,9992** (ρ de J_pos = 0,9938; Pearson r = 0,9990); J_proxy ≈ J_sim com diferença ≤ 0,01 m em todos os 25 θ — muito melhor que o caveat documentado de ~0,2 m, porque os θ aqui são físicos (τ ≥ 0,02 s) onde a integração analítica casa com o Simulink, ao contrário do θ "ideal" (τ→0). Como ρ ≥ 0,85, o proxy preserva o ranking ⇒ **Caminho 2 liberado**. *Contribuição metodológica da tese:* um proxy analítico barato pode substituir o simulador fiel **no loop** de calibração desde que se demonstre a preservação de ranking — habilitando orçamentos de avaliação 1–2 ordens de grandeza maiores. Artefatos: `build/phase0_ranking.mat`, `results/phase0_proxy_ranking_20260614_2105.csv`, `results/figs/F0_proxy_ranking_20260614_2105.{png,pdf}`.

**bayesopt amplo (Fases 1–2, `run_bayesopt_v2_proxy.m`).** 9 params nas faixas do SLDD (K[0,5;2], τ[0,02;0,5] log, Td[0;0,15]), função = `bo_cost_proxy` (MESMA fórmula de `bo_cost`, λ=1,171) em **18 eventos de treino estratificados** (3 front_to_back + 6 side_to_side + 9 shoot_to_goal, determinístico seed 42, **fora dos 10 de hold-out**), EI-plus, determinístico, **400 avaliações**, warm-start (vx/vy v2 + placeholder + ω candidato). **J_treino_proxy 0,2500 → 0,2252 (−10%)**. **θ_opt:** vx{K=1,097; τ=0,020; Td=0,108}, vy{K=1,153; τ=0,020; Td=0,148}, **ω{K=1,099; τ=0,028; Td=0,123}**. **K_w = 1,099 — NÃO mais no piso 0,516 do v1**: o ótimo comportamental com treino amplo **não suprime ω**; o "ω suprimido" do v1 era artefato de 5 eventos. **ARD balanceado** (Kvx 0,26; Tdvx 0,24; Kvy 0,22; τvx 0,19; **Kw 0,18**; …; τw 0,09) — os params de ω agora estão no **meio**, não no fim como no v1.

**Confirmação no Simulink fiel + gate hold-out (Fase 3, `eval_bayesopt_v2_holdout.m`).** θ_opt do proxy re-avaliado no Simulink fiel nos 10 hold-out vs (a) cinemática ideal e (b) vx/vy v2, RMSE SE(2) multi-horizonte + Wilcoxon. **Proxy ≈ Simulink também no ótimo:** hold-out J_proxy 0,2711 vs J_sim 0,2751 (dif **0,004 m**); treino dif 0,017 m — a fidelidade do proxy se sustenta no ponto que mais importa.
- **vs ideal:** vence em **todos** os horizontes (Δmediana −0,065 / −0,104 / −0,123 / −0,125 / −0,086 m em h={0,5;1;2;2,5;4}; **pool −0,0979 m, Wilcoxon p=7,6e-10**).
- **vs vx/vy v2:** **pool +0,0041 m (pior), p=0,040** (direção errada). Empata em h≤2 (p=0,49–0,70), perde levemente em h≥2,5. **Por label:** empata shoot_to_goal (rotação; Δmediana −0,0006; **vence o evento difícil shoot_to_goal_12_01 em −0,22…−0,27 m** @ h=2–2,5), mas perde side_to_side (+0,0185) e front_to_back (+0,0062). **→ GATE FALHA: NÃO promovido** → `models/sysid_bayesopt_v2_candidate.mat`. O modelo robusto continua **vx/vy v2 + ω placeholder** (`sysid_vxvy_v2.mat`).

**Leitura para a tese (mais conclusiva, agora com treino amplo).** (1) O **método do proxy é validado de ponta a ponta** (ρ=0,9992; J_proxy≈J_sim ≤0,01 m em varredura e 0,004 m no ótimo do hold-out) — resultado metodológico reaproveitável. (2) O **overfit do v1 era por dado, não por método**: com 18 eventos o K_w sobe do piso 0,516 para 1,099 (perto do placeholder, ainda **abaixo** do físico ≈1,35 ⇒ tensão parâmetro-vs-comportamento **muito mais branda**) e o ARD reequilibra. (3) Ainda assim, **dado de malha fechada não sustenta um ajuste comportamental conjunto de 9 params que supere o grey-box por DOF na translação**: vx/vy v2 foram identificados com excitação limpa (xcorr 0,99) e o bayesopt conjunto **troca um pouco de translação por rotação** sem ganho líquido em posição. ω agora **contribui positivamente** (K≈1,1, empata rotação, vence o evento de rotação mais difícil) mas não o bastante para inverter a métrica de posição agregada. O bayesopt comportamental **bate a cinemática ideal com folga** e **chega à paridade** com o grey-box (vs o v1, que perdia) — mas o **grey-box validado por DOF segue o modelo promovido**. Figuras: `results/figs/F4_bayesopt_v2_horizons_*` (central), `F6_bayesopt_v2_convergence_*`, `F7_bayesopt_v2_ard_*`.

## 8. Decisões e pendências
**Confirmadas na reunião (12/06):** sequência B (artigo = identificação/validação; RL é o próximo passo, não removido); critérios de aceite novos (§6) adotados; bayesopt confirmado; PSO baseline descartado.
**Pendentes:** status do 01_definicao_pesquisa.md (validar); encaixe/deadline/APC do periódico-alvo; coleta de dados dedicados (tentar); SLR ainda não iniciada (terceira semana — próximo fim de semana); segundo remote DVC; Wilcoxon nas comparações; privacidade do repo.
**Aposentado:** ω candidato (substituído pela identificação Hammerstein).

## 9. Próximos passos imediatos
1. Etapa A (diagnóstico de ganho×amplitude) nos dados atuais.
2. Etapa D (firmware → zona morta real).
3. Etapa C (identificação 2 estágios) com os dados disponíveis; coleta dedicada se possível.
4. Validar com os novos critérios; promover sysid_omega_v3 se aprovado.
5. Só então: congelar custo do bayesopt e calibrar os 9 parâmetros.
