# Relatório Técnico de Desenvolvimento — Gêmeo Digital SSL
*Documento vivo. Registra o que foi feito, por quê, com que resultado e o que está pendente. Atualizado a cada marco. Última atualização: 14/06/2026.*

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

## 7. Calibração (decisão de método)
- PSO sobre constantes cinemáticas → **substituído** por identificação grey-box + bayesopt (validado pela orientadora; PSO como baseline **não** será mantido).
- bayesopt minimiza J(θ) = RMSE SE(2) multi-horizonte; entra no pipeline **somente após** ω promovido.
- **Pendência:** definição exata do custo (âncora/horizontes/agregação) a congelar ANTES da 1ª iteração de BO.

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
