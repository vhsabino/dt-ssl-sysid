# Revisão manual do artigo — documento anotável

**Como usar.** Cada bloco tem um **ID estável** (ex.: `M-B¶2`). Escreva o
feedback referenciando o ID — eu aplico direto no `.tex` correto, sem
ambiguidade. Exemplos de feedback útil:

```
R-D¶3   cortar a última frase, ficou redundante
M-C¶2   trocar "free-running model output" por "simulated output"
L¶5     discordo: manter a comparação com rSim sem essa ressalva
A¶1     OK
```

Formas rápidas: `OK` (aprovado), `CORTAR`, `REESCREVER: ...`, `DÚVIDA: ...`.

**Legenda das notas**
🔴 decisão minha que você pode querer reverter · 🟡 mudou nesta sessão ·
🟢 responde a objeção de revisor · ⚪ inalterado desde 31/07

**Estado:** compila com 0 erros, 0 referências indefinidas, 0 `\TODO` visível.
9 páginas com `unsrt.bst`; esperado 8 com `IEEEtran.bst` (confirmar no Overleaf).

---

## T — Título

> **A Behavioral Digital Twin for Reality-Gap Mitigation in Omnidirectional
> Soccer Robots: Identifiability Follows the Excitation Regime, Not the Degree
> of Freedom**

🔴 **Nota.** Não é o título do brief. O literal pedido ("A Behavioral Model for
Reality-Gap Mitigation in Digital Twins of Omnidirectional Soccer Robots")
apagava o achado central e prometia mitigação de reality gap validada só em
janelas de translação contra um rSim não sintonizado — o que reforça o
bloqueador B5. Esta é a forma híbrida que você aprovou. **Se achar longo
demais, a alternativa é cortar tudo depois dos dois-pontos.**

---

## A — Abstract (≈240 palavras)

**A¶1**
> Robot soccer teams in the RoboCup Small Size League develop and validate
> control software largely in simulation, where simplified physics leaves a
> reality gap to the field. This paper presents a behavioral digital twin of an
> omnidirectional soccer robot, modeled as one first-order channel with dead
> time per degree of freedom. The two translational channels are identified
> directly from in-game competition logs, the data teams already record, and
> reach roughly 87 percent hold-out fit.

**A¶2**
> The yaw channel is not identifiable from those same logs, and we quantify why:
> 94.3 percent of commanded yaw-rate samples fall below the robot's per-wheel
> actuation threshold, and, more decisively, the yaw command contributes a median
> of one percent of what the four wheels are asked to do, so the rotation the
> vision system measures is dominated by disturbances the command did not
> produce. Yaw therefore requires a dedicated open-loop excitation campaign, from
> which the same model structure recovers a gain of 1.00, a time constant of 83
> milliseconds and a dead time of 89 milliseconds, reaching 71.1 percent hold-out
> fit and passing a pre-registered multi-horizon pose gate at all five horizons.

**A¶3**
> Fidelity is evaluated in free run over multiple horizons, using a re-anchored
> position error, against an ideal-kinematics baseline and against an untuned
> ODE-based league simulator; the twin outperforms both on translation-dominated
> windows with a large effect size under paired statistical testing. We offer
> this heterogeneity as a contribution rather than a caveat: which data a channel
> requires is set by the excitation regime the data contain, not by the degree of
> freedom itself.

🟡🟢 **Notas.** (1) O rascunho que você me passou dizia que o gêmeo é
identificado de logs *"rather than from dedicated excitation experiments"* — a
exata contradição que o T2 mandava corrigir. Reescrito. (2) A atribuição causal
a *correlation bias* foi **removida** (bloqueador B1: o revisor diz que o
abstract se compromete com uma causa que o experimento não isola). (3) rSim
qualificado como *untuned* (B5). (4) Sem símbolos matemáticos, como manda o
IEEE. 🔴 Cresceu de 179 para ~240 palavras por causa dos números de ω que o
brief pediu — **se quiser voltar a ~180, o corte natural é a segunda metade de
A¶2** (τ, Td e o gate).

---

## I — Introdução

**I¶1** ⚪
> In the RoboCup Small Size League (SSL), teams of fast omnidirectional
> four-wheeled robots are coordinated by software that is developed and validated
> largely in simulation. The reference simulation tools of the league implement a
> simplified omnidirectional wheel model on top of a rigid-body ODE engine [1],
> reinforcement-learning frameworks for robot soccer inherit that engine [2], and
> recent motion-planning policies for the SSL are trained inside these
> environments [3]. Because the simulated dynamic response deviates from the real
> robot, behaviors validated in simulation degrade on the field — the reality gap.

**I¶2** ⚪
> A higher-fidelity behavioral twin narrows this gap, but building one usually
> presumes either a detailed physical model or a dedicated excitation campaign
> with robot and field access. Competition logs are the data teams already have:
> body-frame velocity commands and vision poses recorded at ~60 Hz during
> closed-loop play. A twin identified from such logs would be cheap and
> reproducible — at the price of an identifiability question, since the data are
> collected under feedback and were never designed to excite the plant.

**I¶3** ⚪
> Digital twins of mobile robots validate fidelity behaviorally but obtain their
> models from white-box physics or purpose-collected data: simulation models of
> omnidirectional platforms are tuned on dedicated real trajectories [4], [5],
> identification pipelines design excitation sequences per parameter group [6],
> grey-box and real-time estimation for twins assume informative operating data
> [7], [8], and offline sim-to-real calibration presumes the pre-collected data
> excite the parameters of interest [9]. Whether a behavioral twin can be
> identified from closed-loop *operational* logs — and which degrees of freedom
> such logs support — has, to our knowledge, not been characterized.

**I¶4** 🟡
> This paper models an omnidirectional SSL robot as three decoupled
> first-order-plus-dead-time (FOPDT) channels, one per degree of freedom (DOF),
> and evaluates fidelity in free run over multiple horizons with a re-anchored
> position error, against an ideal-kinematics baseline and against rSim, the ODE
> engine of the rSoccer environment [2]. The translational channels identify
> cleanly from competition logs (hold-out fit ~87%) and the twin outperforms rSim
> on translation-dominated windows with a large, statistically gated effect. The
> yaw channel does not: the *same* model structure fails every acceptance gate on
> closed-loop data and passes all pre-registered gates on a small dedicated
> open-loop collection, with the discrepancy explained by how little of the
> actuation the yaw command accounts for — 94.3% of commanded yaw-rate samples
> fall below the robot's own actuation threshold, and in play the yaw term is a
> median 1% of the per-wheel setpoint — rather than by the model.
> Identifiability, in this data regime, is a property of the excitation, not of
> the DOF. The result is thus a contribution to robot modeling and, at the same
> time, a higher-fidelity behavioral plant for the robot simulation and
> visualization tools on which robot soccer development relies.

🟡 **Nota.** O trecho do mecanismo foi reescrito para incluir a diluição (1%).
Antes dizia só "explained by the robot's own actuation threshold", o que é a
formulação que o revisor mostrou ser autocontraditória (ver R-D¶3).

**I¶5 — Contribuições** 🟡🟢
> **(C1)** A per-DOF grey-box (FOPDT) identification methodology for an
> omnidirectional robot from *closed-loop* competition logs, with per-DOF
> hold-out validation.
> **(C2)** A free-run, multi-horizon, re-anchored fidelity protocol with
> motion-stratified windows and a statistically gated verdict (paired
> non-overlapping Wilcoxon, moving-block bootstrap, effect size).
> **(C3)** A validated comparison showing the twin attains higher *translational*
> fidelity than rSim on translation-dominated windows.
> **(C4)** A characterization of yaw identifiability as a function of the
> *excitation regime*, with a quantified mechanism: the same FOPDT structure
> fails on closed-loop competition logs and passes every pre-registered gate on a
> dedicated open-loop collection, because in play the yaw command contributes
> only ~1% of what the wheels are asked to do, leaving the measured rotation
> dominated by disturbances the command did not produce.

🟢 **Nota (C4).** Antes terminava com *"the contrast pointing to the inflated
closed-loop gain as correlation bias rather than plant gain"* — a afirmação
causal que o revisor atacou em B1 e que **contradizia o abstract já suavizado**.
Agora afirma o mecanismo medido, não a causa inferida.
🔴 **Ponto para você:** C3 continua prometendo "higher translational fidelity
than rSim" sem a ressalva de que o rSim não foi sintonizado. A ressalva está em
L¶5. **Quer qualificar C3 aqui também?** O revisor reclamou exatamente disso.

---

## RW — Related Work

**RW¶1** 🔴🟡
> **Behavioral twins and identification of omnidirectional robots.** Digital
> twins of mobile platforms are typically validated behaviorally, by comparing
> simulated and real trajectories rather than parameters [10], [11], and grey-box
> identification has been evaluated as the model-generating module of a twin,
> found sensitive to the informativeness of its input data [7]. Work on
> omnidirectional platforms assumes dedicated experiments: the Otbot project
> designs one experiment per parameter group [6], and simulation models of highly
> dynamic omnidirectional robots are tuned against motion-capture trajectories,
> either manually and per trajectory [4] or by black-box optimization over a few
> high-impact parameters [5]. The per-DOF FOPDT structure adopted here is the
> classic first-order-plus-dead-time process model of control practice [12].
> Closest in spirit to using logs as-is, DROPO estimates domain-randomization
> distributions from an offline, pre-collected dataset [9]; such approaches
> presume the offline data excite the parameters being estimated — the assumption
> this paper interrogates.

🔴 **Nota.** **Fundi três parágrafos temáticos em um só** por orçamento de
página (~0,3 pág. economizada). Nenhuma citação foi removida. Custo: perdeu-se a
estrutura por eixos, que o revisor havia elogiado ("enxuto mas pertinente…
bem feito para 6 páginas"). **Se sobrar página, este é o primeiro lugar a
desfazer** — versão longa em `docs/BACKLOG_EXTENSAO_JINT.md` item F.

**RW¶2** ⚪
> **SSL simulators and league context.** The SSL's reference simulator, grSim,
> adopts a simplified dynamic model of the omni wheels for real-time performance
> [1]; the rSoccer framework derives its rSim engine from grSim for
> reinforcement-learning workloads [2], and planning policies are trained in such
> environments [3]. A Simscape multibody (white-box) twin of an SSL robot reports
> trajectory RMSE of 150–240 mm on game scenarios [13]. League practice routinely
> records vision poses, odometry, and onboard velocities [14], and SSL firmware
> converts body commands into per-wheel velocity loops [15] — the actuation chain
> behind the per-wheel dead-zone analyzed in Sec. IV-D.

**RW¶3** ⚪
> **Closed-loop identification.** That feedback correlates the input with
> unmeasured disturbances, breaking methods that work in open loop, is classic
> [16]–[18], as is the role of persistent excitation in prediction-error
> estimation [19].

**RW¶4 — Gap** ⚪
> No prior work, to our knowledge, identifies a behavioral twin of an
> omnidirectional robot from closed-loop *operational* logs and characterizes, on
> the same platform and model structure, which degrees of freedom that regime can
> and cannot identify.

---

## F1 — Figura 1 (arquitetura, TikZ, largura dupla)

Blocos: `SSL protobuf match logs (.log.gz)` → `ETL / event extraction → Parquet`
→ `Per-DOF segmentation & window labeling` → `Grey-box FOPDT identification per
DOF` → *(θ, 9 params.)* → `Twin: three decoupled channels vx, vy, ω` →
`Body-to-field rotation + SE(2) integration` → `Free-run evaluation: re-anchored
e_pos, H horizons`. Ramo tracejado: `rotate_raw.csv — dedicated open-loop yaw
excitation`, rotulado *"feeds the ω channel only"*. Ramos de comparação:
`Ideal kinematics`, `rSim (ODE)`, `rSim + Td (ablation)`.

🟡 **Notas.** (1) O bloco dizia *"Inverse kinematics / SE(2) composition"* —
**errado**: `plant.py` não usa cinemática inversa em lugar nenhum. Corrigido
para rotação corpo→campo + integração. (2) 🔴 **O bloco `rSim + Td (ablation)`
continua no diagrama, mas a ablação não foi executada e a linha saiu da
Tabela IV.** Ou removo o bloco, ou mantenho e a legenda diz "pending" — hoje
diz. **Sua chamada.**

---

## M — Método

**M-A¶1 — Per-DOF FOPDT twin** ⚪
> We model the robot as three decoupled single-input single-output channels, one
> per degree of freedom (DOF) i ∈ {vx, vy, ω}, each a
> first-order-plus-dead-time (FOPDT) transfer function from commanded to attained
> body velocity, **G_i(s) = K_i·e^(−Td_i·s)/(τ_i·s+1)** (Eq. 1), with per-DOF gain
> K_i, time constant τ_i, and transport delay Td_i. The body-frame commands vx, vy
> (longitudinal/lateral, m/s) and ω (yaw rate, rad/s) are the inputs; the outputs
> are the attained body velocities. The full parameter vector has fixed order
> [K_vx, τ_vx, Td_vx, K_vy, τ_vy, Td_vy, K_ω, τ_ω, Td_ω] (nine parameters). This
> is a *behavioral* (observational) model: it targets the input-to-pose response,
> not a white-box description of wheel/contact mechanics.

**M-B¶1 — Discretização e integração de pose** ⚪
> The twin is simulated on a uniform grid with step Δt = 1/60 s: each DOF's
> command is delayed by a zero-order-hold (ZOH) integer shift of
> m_i = ⌈Td_i/Δt⌉ samples (zero before the segment start), passed through the
> exact ZOH first-order update v_i[k] = v_i[k−1] + (1 − e^(−Δt/τ_i))(u^d_i[k] −
> v_i[k−1]), and scaled to the attained body velocity v̂_i[k] = K_i·v_i[k]
> (instantaneous for τ_i → 0). The body velocity is rotated through the current
> heading and integrated to the field frame by the trapezoidal rule; an
> independent reconciliation of this plant against the high-fidelity Simulink
> model agrees to ≤ 6 mm in position and ≤ 9×10⁻⁴ rad in heading on a reference
> event.

🔴 **Nota.** O revisor (C12) pediu para **descrever ou remover** o
*"high-fidelity Simulink model"*: aparece uma vez, nunca é descrito, e o leitor
não sabe por que concordar com ele significa algo. **Não resolvi.** Opções:
(a) uma frase dizendo o que é; (b) cortar a cláusula inteira. **Decida.**

**M-B¶2 — Dead-time quantization** 🟡🟢
> Three conventions a replication must match. The first-order update is the
> *exact* ZOH discretization α_i = 1 − e^(−Δt/τ_i), not an Euler step Δt/τ_i (at
> τ_vx = 0.072 s they differ by 18%). The delay is an integer shift
> m_i = ⌈Td_i/Δt⌉ — a *ceiling* — so the applied delay always exceeds the
> identified one, by +14.3, +10.2 and +11.1 ms for vx, vy, ω (12–21% of Td_i);
> the ±21% robustness check of Sec. IV-D is a perturbation over exactly this
> residual. Identification and replay both run at Δt = 1/60 s, the nominal vision
> rate, onto which the irregular raw logs are resampled.

🟢 **Nota.** Fecha a pendência T6. **Verifiquei o código antes de escrever:**
`plant.py` usa `1 - exp(-dt/tau)` (ZOH exato) e `floor(j - Td/dt)` ≡ `ceil` —
texto e implementação concordam, não houve divergência a reportar. Os três
resíduos são aritmética direta sobre `config/twin_params.json` e explicam de
onde vem o "±21%" que já estava no artigo.

**M-C¶1 — Dados e pré-processamento** 🟡
> The data are closed-loop competition logs of a single omnidirectional
> 4-wheeled SSL robot, decoded from the league protocol stream into per-event
> body-frame commands and field-frame pose at ~60 Hz (heading unwrapped).
> Measured body velocity, used only for identification and for the initial
> condition, is a Savitzky–Golay derivative of the vision position rotated into
> the body frame. The native grid is irregular (command bursts); identification
> resamples to Δt = 1/60 s, while the fidelity metric uses time-based windows on
> the native grid. The dataset comprises 46 events across four motion labels
> (front_to_back, side_to_side, shoot_to_goal, square); a frozen list of 10 events
> is held out and never used for fitting. **The Savitzky–Golay differentiator uses
> window 7 and polynomial order 2.**

🟢 **Nota.** A última frase é nova — o revisor listou "ordem e janela do
Savitzky–Golay" entre os hiperparâmetros ausentes que puxam a nota de
reprodutibilidade para 2,5/5.

**M-C¶2 — Definition of hold-out fit** 🟢 *(subseção nova)*
> Throughout, *fit* is the normalized-RMSE goodness of fit of the MATLAB
> `compare` routine in *simulation* (not one-step prediction),
> **fit = 100·(1 − ‖y − ŷ‖₂ / ‖y − ȳ‖₂) [%]** (Eq. 2), where y is the *measured
> body velocity* of the DOF being identified, ŷ the free-running model output,
> and ȳ the mean of y. It is computed *per event* and then averaged over the
> hold-out events; the 60% acceptance gate applies to that average. Events are
> partitioned by `rng(42)` followed by a random permutation, with ⌈n/3⌉ events
> assigned to the hold-out.

🟢 **Nota.** Fecha **C7**, que o revisor classificou como corrigível e
obrigatório: *"'hold-out fit' é o critério central de aceitação e nunca é
definido"*. Tudo lido de `automation/identify_trans_dof.m` (linhas 47–64 e 112),
nada de memória.

**M-D¶1 — Identificação** ⚪
> Each translational DOF is identified independently as a P1D (FOPDT) model by
> prediction-error minimization, with an event-level hold-out (seed 42). The
> excitation diagnostic selects the cleanest source label per DOF: vx from
> front_to_back and vy from side_to_side (command-to-velocity cross-correlation
> ≈ 0.99). The yaw channel is treated separately: a direct P1D fit on the
> highest-rotation closed-loop label fails validation (Sec. IV-D), so we identify
> ω from a dedicated open-loop collection instead, reporting both attempts for
> contrast.

**M-E¶1 — Excitação dedicada de yaw** ⚪
> The dedicated dataset is single-session and single-robot with vx = vy = 0
> throughout: an alternating-sign staircase of commanded yaw rates {0.25, 0.5, 1,
> 2.5, 5} rad/s, ~10 s per step (ten events). The two lowest amplitudes never
> engage the motors (zero commanded PWM) and serve only to characterize the
> per-wheel dead-zone (Sec. IV-D); the remaining six events form the linear
> regime, split event-wise into four training and two hold-out events under the
> same pipeline as vx, vy. Given the small sample, the acceptance criteria —
> physical bounds, hold-out fit ≥ 60%, and the multi-horizon SE(2) gate against
> the closed-loop placeholder — were fixed and committed *before* estimation,
> guarding against post-hoc adjustment of criteria to the result.

🔴 **Nota.** O revisor (C10/pergunta 12) diz que "committed before estimation"
sem hash nem timestamp verificável **é promessa, não mecanismo**. Um link
anonimizado resolveria. Ver C¶3.

**M-F¶1 — Geometric constants** 🟡🟢
> All quantities are SI (meters, radians); no result is stated in millimeters or
> degrees. Two constants matter, because the commanded-yaw actuation threshold is
> derived from them: the wheel-contact radius R = 0.079601 m and the wheel radius
> r = 0.029492 m from CAD, giving R/r = 2.6991. Their ratio converts the
> firmware's per-wheel motor threshold (1.567 rad/s) into a body-frame yaw rate.
> An earlier ratio, R/r = 3.3208, was used project-wide until it was refuted; it
> comes from the firmware's own header (R = 0.0880 m), and what is refuted is that
> *physical premise*, not the fact that the robot really does compute its
> setpoints with it. Three independent sources place the true ratio near 2.7: CAD
> as above; firmware telemetry, where the post-clamp wheel setpoint scales as
> exactly 2.61·|ω_cmd| above the dead-zone; and the measured body response,
> K_ω ≈ 1.01, which is consistent with unit gain only under the corrected constant
> (the same data give a spurious ≈ 1.35 under the deprecated one). The residual
> 3.3% spread between the first two is reported, not resolved (Sec. VI).

**M-F¶2 — Auditoria de impacto** 🟢
> Correcting the constant moves no number quoted here: e_pos is purely
> translational (the combined SE(2) scalar, the only quantity that would weight
> heading by R, is disabled in the metric configuration), so R enters only the
> rotational-fraction ratio used to bin windows — and re-binning under the
> corrected radius reproduces the same 264/1/0 distribution.

🔴 **Nota.** A **tabela de unidades foi removida do build** por orçamento de
página (~0,2 pág.). As três constantes que o texto usa estão inline. O arquivo
`latex/tables/tab_units.tex` continua no repo. **Se quiser a tabela de volta,
diga — mas ela custa uma página que hoje não temos.**
**Correção factual importante:** o brief supunha que os "3,3%" do revisor eram
má-leitura do 3,3208 depreciado. **Não são** — é (2,6991−2,61)/2,6991, e o
revisor cita como *elogio* à honestidade.

**M-G¶1 — Coordinate conventions** 🟡🟢 *(subseção nova; estava `\TODO` BLOQUEADO)*
> Commands and attained velocities live in the *body* frame: vx is longitudinal
> (robot forward), vy is lateral (left positive), and ω is yaw rate about the
> upward z axis, counter-clockwise positive. Pose is integrated in the *field*
> frame through the rotation applied in Sec. III-B, i.e. Ẋ = vx·cosθ − vy·sinθ and
> Ẏ = vx·sinθ + vy·cosθ, with θ unwrapped.

**M-G¶2**
> One consequence matters for replication: the twin is defined *entirely* in
> body-velocity space. No wheel-level kinematics appears in the identification,
> the plant, or the metric — the chain is command → delay → lag → gain → rotation
> → integration. Per-wheel geometry enters at one point only, and not as a
> modeling choice: converting the firmware's actuation threshold into a body yaw
> rate for the excitation analysis of Sec. IV-D. A replication needs the two radii
> of Sec. III-F and nothing else about the layout.

🟢 **Nota — isto era um bloqueio e deixou de ser.** No PDF que você mandou esta
subseção aparecia **com título e corpo vazio**. Eu a tinha marcado `\TODO
BLOQUEADO` porque `inverse_kinematics_solver.m` tem assimetria √2 na linha de ω.
Nesta sessão li `plant.py` linha a linha: **o gêmeo não usa cinemática inversa em
nenhum resultado do artigo**. Logo o defeito da matriz não contamina o paper e a
subseção pôde ser escrita e fechada. A correção da matriz (R1) continua pendente
no repositório, mas **não bloqueia a submissão**.

**M-H¶1 — Free-run e métrica multi-horizonte** ⚪
> Fidelity is measured in *free-run*: from the true pose at a window anchor t₀ the
> twin is driven only by the command stream, never re-anchored inside the window
> (no teacher forcing, which would measure single-step noise and inflate apparent
> fidelity). Segments are cut into overlapping windows at a fixed stride, each
> re-anchored to the true SE(2) pose at t₀ and rolled out to H_max = 90 samples
> (1.5 s). We report, *separately*, the Euclidean position error e_pos(w,h) and the
> wrapped absolute heading error e_ang(w,h) at h ∈ {6,12,24,42,60,90} samples
> ({0.1,0.2,0.4,0.7,1.0,1.5} s), with reference horizon h_ref = 24 (0.4 s). e_pos
> is the claim of this paper; e_ang is reported but bounded by the population of
> rotation-rich windows available (Sec. IV-B), independently of whether ω is
> identified.

**M-H¶2 — Estratificação e gate estatístico** ⚪
> Each window is binned by its rotational fraction r = a_rot/(a_rot + a_trans),
> where a_trans and a_rot accumulate translational command magnitude and yaw rate
> scaled by the robot radius. Windows are *translation-dominated* (r < 0.2),
> *mixed* (0.2 ≤ r ≤ 0.5), or *rotation-dominated* (r > 0.5). Curves use all
> (dense) windows; inference uses only *non-overlapping* windows (stride ≥ H_max)
> for a paired one-sided Wilcoxon signed-rank test, plus a moving-block bootstrap
> (block ~H_max) for the gap confidence interval, with any sign/order divergence
> flagged; effect size is the rank-biserial correlation of the paired differences.
> A bin receives a **GO** verdict only if, at all h ≥ h_ref, the gap is positive
> and non-decreasing, p < α (α = 0.05), the effect size ≥ 0.2, and the bootstrap CI
> excludes zero, subject to N_min = 10 independent windows; below N_min a bin is
> **INDETERMINATE**.

🟢 **Nota.** O revisor chamou este protocolo de *"a melhor parte do artigo"* e
*"generalizável"*. **Não cortei nada aqui de propósito**, mesmo sob pressão de
página.

**M-H¶3 — Grade de horizontes** 🔴⚪
> All results use the SE(2) (full-pose) re-anchor above, but two independently
> implemented harnesses with different horizon grids: the fidelity results
> (Sec. IV-C) use the grid given above, while the per-DOF promotion gates
> (Secs. IV-A and IV-D) reuse an earlier campaign harness with
> h ∈ {0.5, 1, 2, 2.5, 4} s. Each result is reported on its native grid, flagged
> at each point, rather than recomputed.

🔴 **Nota.** É o **C6** do revisor: *"a impressão é de artigo montado a partir de
campanhas antigas"*. Honesto, mas custa credibilidade. Unificar exige
re-executar uma campanha (R8). **Você quer investir nisso antes de submeter?**

**M-I¶1 — Baselines** ⚪
> We compare the twin against two baselines under the *same* windows, horizons,
> and gate. The first is an *ideal-kinematics* plant in which the attained body
> velocity equals the command instantaneously (no gain, lag, or delay), integrated
> by the same trapezoidal scheme. The second is **rSim**, the ODE-based physics
> engine of the rSoccer environment, driven by the same body-frame commands with
> motion control disabled so that the engine dynamics are isolated. rSim provides
> no velocity setter at reset (the robot starts from rest), so two
> initial-condition fairness modes are used: **Mode A** (primary) warms the engine
> up over L_w = 15 samples with the real pre-anchor commands and then applies a
> rigid SE(2) re-anchor at t₀, mirroring how the twin is seeded with the real body
> velocity; **Mode B** (robustness) uses no warm-up and discards the first 15
> samples for *both* plants. The twin's transport delay has no counterpart in
> rSim, which is precisely where the twin is expected to win at short horizons.

---

## R — Resultados

**R-A¶1 — Modelo identificado** 🟡
> Table II reports the per-DOF parameters. Both translational channels identify
> as fast FOPDT models with hold-out fit 86.7% (vx) and 87.1% (vy); under the
> multi-horizon SE(2) gate against the previous (slower) parameters they improve
> every event-by-horizon cell (vx: 20/20; vy: 65/65), roughly halving the median
> position error at 2.5 s (vy: 0.141 vs. 0.334 m). The yaw channel ω is also
> identified, from a separate open-loop dataset, with hold-out fit 71.1%; the
> reasons for the separate data source, and the contrast with the failed
> closed-loop attempt, are in Sec. IV-D. All three channels are deterministic
> bit-for-bit under re-execution (identical seed, data, and toolbox version):
> re-running the identification pipeline reproduces all nine parameters to 0.0
> absolute difference.

**TB2 — Tabela II** 🟡 **← era o defeito fatal do PDF**

| DOF | K | τ (s) | Td (s) | hold-out fit |
|---|---|---|---|---|
| vx | 1.119 | 0.072 | 0.069 | 86.7 % |
| vy | 1.052 | 0.127 | 0.056 | 87.1 % |
| ω  | 1.002 | 0.083 | 0.089 | 71.1 % |

*Legenda:* "Identified per-DOF FOPDT parameters and hold-out fit. All three
channels are identified (no placeholder); ω uses a dedicated open-loop
rotation-only collection, not the closed-loop competition logs used for vx, vy."
*Nota de rodapé:* "Fit is Eq. 2, averaged over hold-out events. Dispersion across
those events: vy ±0.8 p.p. (4 events); ω 65.0/77.2 (2 events); vx has a single
hold-out event, so no dispersion is available. Parameter confidence intervals
are not reported — see Sec. IV-D for why the estimator's asymptotic intervals
are not trustworthy here."

🔴🟢 **Nota crítica.** **No PDF que você enviou, esta tabela mostrava ω como
`fixed placeholder` (K=1.000, τ=0.100, Td=0.000, fit "—") com a legenda
*"closed-loop yaw not identifiable"*** — contradizendo o abstract, R-A¶1 e a
Tabela V do mesmo documento. O repositório já tinha a versão correta: **era
dessincronia Overleaf ↔ repo**. Sozinho, isso garantiria rejeição.
**Re-sincronize o Overleaf antes de compilar.**
A nota de rodapé (dispersão) é nova e responde ao **C8**.

**R-B¶1 — Distribuição de movimento do hold-out** 🟡
> The hold-out windows are overwhelmingly translation-dominated: of 265 dense
> windows (49 independent), 264 fall in the translation bin (99.6%), one is
> rotation-dominated, and none are mixed. This conditions the analysis:
> translational fidelity is the statistically powered claim, while the rotation
> and mixed bins lack the population to support a verdict. This population is
> unaffected by the yaw model: re-running the bin classification and the
> twin-vs-ideal gate after ω was identified reproduces the same distribution
> (264/1/0) and leaves mixed and rotation-dominated **NO POWER** (N_indep = 0), now
> for lack of rotation-rich competition windows rather than for lack of a yaw
> model. Every verdict below is therefore scoped to the translation bin
> (N_indep = 49), and the rotational fidelity of the twin remains unverified
> against a competition-like distribution, independently of whether ω is
> identified (see Limitations).

🟡 **Nota.** A **tabela de composição da validação foi retirada do build**
(orçamento): os três números já estão neste parágrafo. Arquivo mantido em
`latex/tables/`. Também corrigi aqui uma **redundância que eu tinha
introduzido** (o "NO POWER" aparecia duas vezes).

**F2 — Figura 2** 🔴🟢
> *Measured vs. simulated yaw rate on the dedicated open-loop staircase (training
> and hold-out events). This is the same model structure and the same
> identification tooling that fail on competition logs; what changes is the
> excitation regime of the data.*

🔴 **Nota — decisão que você pode querer reverter.** Era `figure*` de largura
dupla com **dois painéis** (fit vx/vy + degrau de ω). Reduzi a **coluna única,
só o painel de ω**, por orçamento (~0,5 pág.). Justificativa: a translação já
tem a Fig. 3 e a Tabela IV; o degrau de ω é o resultado central e não tem
substituto. 🟢 Responde ao **S1** (o pedido de figura mais forte do revisor: o
leitor nunca via resposta medida vs. simulada). **Se ainda faltar página, esta
figura é o próximo corte (~0,3 pág.) — mas aí o S1 volta a ficar aberto.**

**R-C¶1 — Twin vs. rSim** ⚪
> On translation-dominated windows (Mode A), the twin's median position error is
> *below* rSim's at every horizon, and the gap *grows* with the horizon (Table IV,
> Fig. 3). At the reference horizon h_ref = 0.4 s the gap is +0.093 m (e_pos: 0.038
> vs. 0.131 m), with paired non-overlapping Wilcoxon p = 4.4×10⁻¹¹ and rank-biserial
> effect +0.922 (N_indep = 49). Across horizons the effect size ranges from +0.731
> (1.5 s) to +0.980 (0.2 s); the moving-block bootstrap CI excludes zero at every
> horizon and agrees in sign and order with the Wilcoxon test (no divergence flag),
> so the bin receives a **GO** verdict.

**TB4 — Tabela IV** 🟡

| h (s) | twin e_pos | rSim e_pos | gap (m) | p | effect |
|---|---|---|---|---|---|
| 0.10 | 0.0077 | 0.0572 | +0.0495 | 1.6e−13 | +0.979 |
| 0.20 | 0.0177 | 0.0935 | +0.0758 | 1.2e−13 | +0.980 |
| 0.40 | 0.0382 | 0.1312 | +0.0930 | 4.4e−11 | +0.922 |
| 0.70 | 0.0644 | 0.1731 | +0.1087 | 8.2e−9 | +0.838 |
| 1.00 | 0.0919 | 0.2144 | +0.1225 | 1.3e−9 | +0.871 |
| 1.50 | 0.1229 | 0.2927 | +0.1699 | 1.0e−6 | +0.731 |

🟡 **Nota.** No PDF que você mandou esta tabela **estourava a coluna**: os
expoentes de p saíam cortados ("1.6×10−") e a coluna `effect` **sumia inteira**.
Corrigido com `tabcolsep` + notação compacta. 🔴 **A linha da ablação
`rSim + Td` foi removida** — ela estava com `[TODO: ablation]` **visível no PDF**,
o que é fatal numa submissão. A ablação segue não executada (bloqueada:
trajetórias do rSim nunca persistidas). A ameaça à validade ficou em L¶5.

**F3 — Figura 3** ⚪
> *Free-run position fidelity vs. horizon on translation-dominated hold-out
> windows, twin (FOPDT) vs. rSim (ODE engine of rSoccer), Mode A (N = 264 dense,
> 49 independent). Left: median e_pos. Right: gap (rSim − twin) with moving-block
> bootstrap 95% CI. Dotted line marks h_ref = 0.4 s.*

**R-C¶2 — Robustez e segundo baseline** ⚪
> Without warm-up (Mode B, first 15 samples dropped for both plants) rSim's
> rest-start penalty widens the gap (+0.282 m at h_ref, p = 4.4×10⁻¹⁴, effect
> +0.987), so Mode A is the conservative primary setting; against ideal kinematics
> the twin is also **GO** on translation (gap +0.063 m at h_ref, p = 8.5×10⁻⁷,
> effect +0.736).

**R-C¶3 — Erro de heading** ⚪
> Heading error carries no verdict, since the rotation and mixed bins lack
> scorable population. Descriptively, the twin's median e_ang grows from 0.013 to
> 0.090 rad over h = 0.1–1.5 s, below the ideal-kinematics baseline (0.023 to
> 0.095 rad) at every horizon; against rSim, however, it is *larger* at long
> horizons — the position claim does not transfer to heading (Sec. VI).

🟢 **Nota.** A frase final já reconhece o cruzamento com o rSim — era o **C4** do
revisor (cherry-picking). A inconsistência numérica que ele apontou (**C3**,
0,090 vs ≈0,103) **deixou de existir**: o painel de e_ang que discordava foi
gerado com o placeholder de ω e já tinha sido removido da figura em 31/07.

**R-D¶1 — Yaw: falha em malha fechada** ⚪
> A direct P1D fit of the yaw channel on high-rotation *closed-loop* competition
> events gives (K_ω, τ_ω, Td_ω) ≈ (1.35, 0.035, 0.106) with hold-out fit 52.6%
> (below the 60% acceptance threshold), and using it *worsens* free-run position
> because the gain > 1 amplifies accumulated heading drift; it is not promoted. A
> per-amplitude gain analysis shows a flat effective gain of ≈ 1.3–1.5 across the
> closed-loop command range, with no dead-zone knee visible in the *body*-frame yaw
> signal. A linear re-identification restricted to the high-rotation closed-loop
> regime fails whiteness (Ljung–Box rejects) and is **NO-GO** on the multi-horizon
> gate: it is *worse* than the placeholder at every horizon, pooled gap +0.0489 m
> at 4 s, p = 3.8×10⁻⁹.

**R-D¶2 — Mesma estrutura, dados diferentes** 🟡🟢
> Firmware inspection locates the dominant non-linearity as an *electrical,
> per-wheel* dead-zone, applied to each wheel setpoint *after* the firmware's
> command kinematics — not a body-frame Hammerstein dead-zone that a closed-loop
> fit could absorb. Re-deriving the commanded-yaw dead-zone from this per-wheel
> threshold and the robot's wheel-to-contact-radius ratio places it at
> 0.58–0.60 rad/s of body yaw rate — reported as an interval, never a point
> estimate, because the two independent geometric sources agree only to that
> precision. Recomputing the fraction of *commanded* yaw-rate samples in the
> competition logs that fall below this corrected threshold gives 94.3% pooled
> across all 46 splits, and 77.3% even on shoot_to_goal, the label richest in
> rotation. **The conclusion does not hinge on where inside the empirical bracket
> (0.5, 1.0] rad/s the threshold is placed: the pooled fraction moves only from
> 92.5% at 0.5 rad/s to 97.6% at 1.0 rad/s (72.8% to 87.9% on shoot_to_goal), so
> the statistic is bracket-robust rather than threshold-tuned.**

🟢 **Nota.** A frase em negrito é nova e fecha o **C9**. O revisor previu: *"se
a fração não cair no extremo superior, é evidência gratuita a favor"*. Não cai.
Também corrigi "applied after the inverse kinematics" → "after the firmware's
command kinematics", porque M-G agora diz que o gêmeo **não** usa cinemática
inversa e as duas frases se contradiziam.

**R-D¶3 — The threshold does not suppress yaw — it buries it** 🟢🟡 **← o núcleo novo**
> Read naively, the previous paragraph predicts something that does *not* happen.
> If 94.3% of yaw commands were truly unactuated — command present, motion absent
> — a command-to-velocity fit over those samples should *deflate* the apparent
> gain, and a dead-zone knee should be visible in the body-frame yaw signal.
> Neither occurs: the closed-loop gain is inflated to 1.3–1.5 and the
> per-amplitude analysis above shows no knee. The resolution is that the threshold
> is applied *per wheel, after* the command kinematics, and in competition the
> wheels are already turning because of translation. Among the sub-threshold
> samples the median per-wheel translational setpoint is 24.0 rad/s, 15× the
> 1.567 rad/s motor clamp (median commanded speed 1.0 m/s), and between 97.3% and
> 97.8% of those samples have at least one wheel driven above the clamp; only
> 2.2%–2.7% have all four wheels clamped. Those ranges are swept over nine
> plausible wheel-angle layouts, since the mounting angles are not documented, and
> the conclusion is invariant to the choice. The yaw command is therefore not
> suppressed in play; it is *diluted*, contributing a median of 1.0% of the
> per-wheel setpoint (90th percentile 5.7%).

**R-D¶4**
> This reframes the statistic. The 94.3% is not a claim that the actuator is idle
> — it is a signal-to-noise statement: what the wheels are asked to do is 99%
> translation. Both anomalies dissolve, because nothing is being zeroed (so the
> gain has no reason to deflate) and the dead-zone engages in only ~2% of samples
> (so no knee should appear). It also identifies what the inflated gain is
> measuring: with the yaw command at 1% of the actuation, the measured yaw is
> dominated by rotation the command did not produce — slip, contact, traction
> asymmetry — and under feedback those disturbances are precisely what the
> controller is reacting to, hence correlated with the command. The dedicated
> collection removes the dilution rather than the feedback: with vx = vy = 0 the
> translational term vanishes and the yaw command becomes the entire actuation.

🟢 **Nota — este é o maior ganho da sessão.** Resolve o **B4**, que o revisor
chamou de *"onde um revisor cético vai parar exatamente aqui"* e para o qual o
artigo *"não dá resposta"*. Efeito colateral: **enfraquece o B1**, porque a
explicação concorrente ("amplitude/zona morta") deixa de concorrer — a zona
morta demonstradamente não engaja. Números de
`results/omega_excitation_analysis_20260807_133917.json`; o pipeline foi
validado reproduzindo os 94,33% / 77,26% do artefato de julho.

**R-D¶5 — Identificação em malha aberta** 🟡🟢
> We therefore identify ω from the dedicated open-loop collection, using the
> *same* P1D structure and identification tooling. The result is K_ω = 1.0016,
> τ_ω = 0.0828 s, Td_ω = 0.0890 s, with hold-out fit 71.1% (65.0% / 77.2% per
> event), above the pre-registered 60% gate; the correlation between τ and Td is
> moderate (ρ = −0.47), below the 0.8 alert threshold. **We deliberately attach
> *no* confidence interval to K_ω: the estimator's asymptotic interval presupposes
> white residuals, and the Ljung–Box test rejects whiteness for both yaw fits
> (Sec. VI), so that interval would understate uncertainty by an unknown factor
> over four training events. The comparison we rely on is the point estimate
> against the closed-loop one — 1.00 versus 1.3–1.5, a 30–50% discrepancy that no
> plausible widening of an interval would close — not a formal test of K_ω = 1.**
> On the multi-horizon SE(2) gate against the same placeholder, evaluated on the
> same closed-loop shoot_to_goal population used to fail the closed-loop
> candidate, the open-loop model is *better* at all five horizons, pooled gap
> −0.1138 m, p = 1.7×10⁻¹⁶ — the sign of the verdict inverts relative to the
> closed-loop attempt on the identical gate.

🟢 **Nota.** O trecho em negrito fecha o **B2**, uma contradição interna que o
revisor classificou como bloqueadora: a Seção VI dizia que o Ljung–Box rejeita
brancura, e a Seção IV usava um IC assintótico de ±0,0024 para "refutar" 1,3.
**O IC foi removido**, não reinterpretado.

**TB5 — Tabela V** ⚪ 🔴

| | K_ω | τ_ω (s) | Td_ω (s) | hold-out fit |
|---|---|---|---|---|
| Closed-loop | 1.307 | 0.0222 | 0.1179 | n/a† |
| Open-loop (dedicated) | **1.0016** | **0.0828** | **0.0890** | **71.1 %** |

| | gate Δmediana (pool) | gate p |
|---|---|---|
| Closed-loop | +0.0489 m (pior) | 3.8×10⁻⁹ |
| Open-loop | **−0.1138 m (melhor)** | **1.7×10⁻¹⁶** |

🔴 **Nota — item aberto de maior retorno.** A nota de rodapé † admite que a
linha de malha fechada foi pontuada por um **critério diferente** (regime-split
31,9%/−11,2%), o que **desmente o próprio título da tabela** ("same
identification tooling; only the excitation regime differs"). É o **C5** do
revisor e a objeção mais barata de eliminar do artigo inteiro. **Recomendo
executar R3** (recomputar essa linha com o mesmo hold-out) antes de submeter.

**R-D¶6 — Interpretação** 🟡
> K_ω = 1.0016 is descriptively near unity and far from the closed-loop estimate
> 1.3–1.35; we read the contrast between the two point estimates, not the
> precision of either. The account consistent with the dilution analysis above is
> that closed-loop commanded yaw correlates with the unmodeled disturbances that
> dominate the measured rotation — a property of the *data regime*, not of the DOF.
> Session and surface still co-vary between the two campaigns (Sec. VI). The SE(2)
> gate verdict for all three DOFs is unchanged under a ±21% perturbation of Td to
> its neighboring integer-step quantization.

🟡 **Nota.** Removi aqui a **repetição do bloco de determinismo bit-exato** (o
revisor, S6, apontou três menções e chamou de *"substituição retórica"* diante
da falta de código público). Ficou uma menção só, em R-A¶1.

**R-D¶7 — Controle negativo** 🟡
> A joint 9-parameter Bayesian calibration under the same multi-horizon cost beats
> the ideal baseline on the hold-out (pooled −0.098 m, p = 7.6×10⁻¹⁰) but not the
> per-DOF model (pooled +0.0041 m, p = 0.040, wrong direction), and is not
> promoted: closed-loop logs do not sustain a joint fit that improves on per-DOF
> identification — the same excitation lesson that motivated the dedicated yaw
> collection.

🟡 **Nota.** Condensado (~40% menor). O revisor **elogia** este resultado
negativo nominalmente, então não cortei o conteúdo, só a prosa.

---

## D — Discussão

**D-A¶1** 🟡
> The central finding is not that yaw is harder to model than translation, but
> that the *same* model structure, fit with the *same* tooling, gives opposite
> verdicts depending on the excitation regime: on closed-loop logs the yaw P1D
> fails every axis (marginal bounds, sub-threshold fit, SE(2) gate worse than a
> no-dynamics placeholder), while on a small dedicated open-loop collection it
> passes every pre-registered gate with near-unity gain. Framed as a property of
> the *data* rather than of ω: closed-loop competition commands do not excite yaw
> enough to identify it — the yaw command is a median 1% of what the wheels are
> asked to do, and 94% of yaw-rate samples sit below the robot's own actuation
> threshold, even on the label richest in rotation — whereas the same logs excite
> vx, vy persistently; nothing in the pipeline distinguishes the DOFs, only the
> data does.

🟡 **Nota.** "with a gain statistically indistinguishable from unity" → "with
near-unity gain", coerente com a remoção do IC (B2).

**D-B¶1 — What the inflated closed-loop gain is measuring** 🟡🟢 *(subseção retitulada)*
> The closed-loop gain estimate (K_ω ≈ 1.3–1.35) is not merely imprecise; it is
> systematically wrong in the same direction across two independent closed-loop
> attempts (a direct high-rotation fit and a regime-restricted linear fit), and the
> open-loop point estimate (K_ω = 1.0016) sits 30–50% away from it. The dilution
> result of Sec. IV-D tells us what the closed-loop estimator is actually fitting.
> Because the yaw command accounts for about 1% of the per-wheel setpoint in play,
> most of the rotation the vision system measures was not produced by that command:
> it comes from slip, contact and traction asymmetry generated by the translational
> motion. A regression of measured yaw on commanded yaw is then dominated by
> whatever correlates with the command — and under feedback the controller issues
> yaw precisely in response to those disturbances, which is the textbook
> closed-loop identification hazard [16]–[18]. The failure mode observed downstream
> is consistent: a gain > 1 *worsens* free-run position by amplifying accumulated
> heading drift.

**D-B¶2**
> We stress what this does and does not settle. It removes the reading that the
> actuation threshold simply switches yaw off — the threshold engages in only ~2%
> of competition samples — and replaces it with dilution, which is measurable and
> quantified. It does not, by itself, isolate feedback from dilution as the
> operative cause, because the dedicated collection removes both at once (Sec. VI).

🟢 **Nota.** O título era *"Correlation bias as the mechanism, not a
coincidence"* — exatamente a formulação que o **B1** acusa de exceder a
evidência. Agora descreve o que o estimador mede, e D-B¶2 delimita
explicitamente o que fica em aberto.

**D-C¶1 — Where the twin beats rSim** 🟡
> On translation-dominated windows the twin's advantage over the ODE-based rSim
> engine grows with horizon. Our reading is that the transport delay and
> first-order lag in Eq. 1 capture a short-horizon response that a rigid-body ODE
> engine without an explicit delay term structurally cannot. It should not be
> over-read: a residual initial-velocity mismatch also accumulates with horizon,
> and the comparison is fitted-versus-untuned (Sec. VI).

🔴 **Nota.** Encurtei porque a ressalva completa está em L¶5 — mas o **B6** do
revisor diz que o argumento "gap cresce ⇒ vantagem dinâmica" é *logicamente
inválido*, já que erro de velocidade inicial também cresce linearmente.
**A frase ainda afirma a leitura dinâmica primeiro e ressalva depois.**
Se quiser ser mais duro consigo mesmo, inverta a ordem.

**D-C¶2 — Why not synthesize the missing rotation set** 🔴🟡
> Generating the missing rotation-rich population from a high-fidelity multibody
> simulation would let the twin pass a gate no physical rotation was involved in:
> agreement between a reduced and a richer model is a statement about two models,
> whereas this paper's claim is error against *measured* pose. The correct
> substitute is real data from a regime that excites the DOF, as in the dedicated
> collection.

🔴 **Nota.** Você pediu este parágrafo no T5.1 como recusa a uma sugestão de
revisor. **O revisor nunca fez essa sugestão** — as três menções a Simulink no
relatório dele são o C12, que pede o oposto (descrever ou remover a referência
ao modelo de reconciliação). Mantive porque o argumento é bom por si, mas
enquadrado como decisão de projeto. **Encurtei ~50% por orçamento. Se a página
apertar, é candidato natural a corte, porque não responde a ninguém.**

**D-D¶1 — Lição metodológica** 🟡
> In the SSL, closed-loop operational data are the naturally abundant resource —
> league practice is to record vision poses, odometry and onboard velocities
> routinely [14] — whereas a dedicated open-loop campaign requires robot access
> outside that routine. The pattern — a model that looks unidentifiable under one
> data regime and identifies cleanly under another, with the discrepancy traced to
> a measurable property of the actuation rather than to the model structure — is
> not specific to this robot's yaw channel: "this DOF is not identifiable" claims
> drawn from competition logs alone should be treated as claims about the available
> excitation, not about the system, until checked against a regime that persistently
> excites the DOF in question.

🟡 **Nota.** Dizia *"explained by a quantifiable actuation threshold"* — o que
**passou a estar errado** depois de R-D¶3, já que o limiar não é a explicação
(a diluição é). Corrigido nesta rodada.
🔴 O revisor (pergunta 10) questiona quanto disto é evidência e quanto é o
princípio de excitação persistente já conhecido desde Ljung. **Vale considerar
uma frase reconhecendo isso.**

---

## L — Limitações

**L¶1 — Amostra pequena** ⚪
> The open-loop yaw fit uses six linear-regime events (four training, two
> hold-out) from a single collection session, with no fine amplitude sweep between
> 0.5 and 1.0 rad/s — hence the commanded-yaw dead-zone is reported only as the
> interval 0.58–0.60 rad/s, with empirical bracket (0.5, 1.0] rad/s. More broadly,
> all identification and evaluation data come from one robot and one
> data-collection context; we report no cross-robot or cross-session variability.
> Pre-registered acceptance criteria and bit-exact determinism under re-execution
> mitigate, but do not replace, replication.

**L¶2 — Fidelidade rotacional não verificada** ⚪
> Identifying ω resolves the *parameter*, but the twin-vs-baseline gate on
> competition-like data still returns no verdict for mixed and rotation-dominated
> windows, because the hold-out has essentially none (0 mixed, 1 rotation-dominated
> of 265), not because of a placeholder. The rotational fidelity of the twin, as
> opposed to the yaw estimate itself, is not validated against a distribution
> resembling competition play.

**L¶3 — O contraste não é experimento de fator único** 🟡🟢
> The two yaw campaigns differ in loop topology, in the ratio of commanded yaw to
> commanded translation, and in session. The dilution analysis narrows this: it
> rules out the simplest alternative — that the actuation threshold merely switches
> yaw off, which would hold for only ~2% of competition samples — and identifies
> the yaw-to-translation ratio as the operative variable. It does not separate that
> ratio from feedback, because the dedicated collection removes both at once
> (vx = vy = 0 eliminates the dilution *and* the loop). Distinguishing them needs an
> open-loop arm with translation superimposed, which we did not collect. We also
> diagnose the bias of direct prediction-error identification on closed-loop data
> without attempting the closed-loop-aware estimators (instrumental-variable,
> two-stage, joint input–output) that the cited literature proposes; whether those
> recover the yaw dynamics from the same logs is open.

🟢 **Nota.** Reescrito à luz da diluição. Antes dizia que a cobertura de
amplitude era *"plausivelmente suficiente"* como explicação concorrente — a
análise nova **refuta** isso, então a limitação ficou mais precisa e mais forte.
A última frase reconhece o **B3** (estimadores closed-loop-aware não tentados).

**L¶4 — Constantes cinemáticas** 🟡
> The 3.3% CAD-versus-firmware spread in R/r (Sec. III-F) is unresolved; the
> likely cause is version drift between inspected source and flashed binary. An
> earlier body-frame dead-zone constant of 0.3 rad/s has no recoverable provenance
> and is superseded by the per-wheel threshold used here.

**L¶5 — Métrica, baselines e escopo** 🟡🟢
> The Ljung–Box test rejects residual whiteness for both yaw fits; as
> pre-registered it is informative, not a gate, since the Savitzky–Golay derivative
> colors residuals by construction. rSim is evaluated at default parameters (a
> re-tuned engine could narrow the gap), and modes A/B bracket, but do not remove,
> the asymmetry that only the twin has an explicit delay term. Two consequences
> must be stated plainly. First, the twin has nine parameters fitted to this robot
> while rSim has none fitted to it, so the comparison bounds what an untuned
> reference simulator delivers on this task; it is not evidence of a general
> dynamical advantage. Second, and more pointedly, the ideal-kinematics baseline —
> zero parameters, no dynamics — also outperforms rSim at the reference horizon by
> our own numbers, which indicates that a substantial share of rSim's deficit comes
> from the replay harness (rest start, no velocity setter, motion control disabled)
> rather than from its physics. An ablation that applies the twin's identified Td
> to the rSim output as a pure output-side shift would bound the portion of the gap
> attributable to the delay term alone; *we did not run it for this version*, so
> that portion is currently unquantified and the translational claim should be read
> as an upper bound on the twin's advantage.

**L¶6 — Escopo dos dados** 🟡
> All results come from a single dataset and hold-out split drawn from the same
> operating regime; the native grid is irregular and the free-run initial condition
> relies on noisy vision-derived velocity — mitigated by resampling and filtering,
> not eliminated.

🟢 **Nota (L¶5).** É a resposta ao **B5**: o revisor mostrou que, pelos números
do próprio artigo, a cinemática ideal (≈0,101 m) **bate o rSim** (0,131 m) — um
modelo de zero parâmetros superando o motor ODE da liga. Omitir isso seria
indefensável, então está dito explicitamente. 🟡 Também corrigi aqui uma
**referência quebrada que eu tinha criado**: o texto apontava para uma ablação
em IV-C que eu havia removido do corpo.

---

## C — Conclusão

**C¶1** 🟡
> A per-DOF FOPDT twin of an omnidirectional SSL robot, identified mostly from
> closed-loop competition logs, attains validated translational fidelity: it beats
> the ODE-based rSim engine on translation-dominated hold-out windows at every
> horizon, with a gap that grows with horizon and effect sizes of +0.731 to +0.980
> (**GO** verdict). The yaw channel was identified from a small dedicated open-loop
> collection, after characterizing *why* closed-loop logs cannot support it: 94.3%
> of commanded yaw-rate samples fall below the per-wheel actuation threshold, and —
> more to the point — the yaw command contributes a median 1% of the per-wheel
> setpoint during play, so the measured rotation is dominated by disturbances the
> command did not produce. That dilution, not an idle actuator, is what makes the
> closed-loop gain estimate inflate to 1.3–1.5 where a dedicated open-loop
> collection recovers unity. The methodological lesson travels beyond this robot: a
> claim that a DOF is not identifiable from operational logs is a claim about the
> available excitation, and should be tested against a regime that actually excites
> that DOF.

🟢 **Nota.** Terminava com *"which we read as correlation bias rather than plant
gain"* — mesma sobre-conclusão do B1. Substituído pelo mecanismo medido.

**C¶2 — Availability** 🔴🟢 *(parágrafo novo)*
> The identification and evaluation pipelines, the parameter and metric
> configurations, the frozen hold-out list, and the pre-registration document
> (committed before estimation, with its commit timestamp) are released with the
> paper; the competition and dedicated-excitation datasets are version-tracked
> alongside them. Reproducing the rSim comparison additionally requires a
> documented Linux/ODE environment.

🔴 **AÇÃO SUA, OBRIGATÓRIA.** Falta o **link anonimizado** (Anonymous GitHub ou
OSF anonymous view). Sem URL, o **C10** continua aberto — e o revisor deu nota
**2,5/5** em reprodutibilidade justamente por isso, dizendo que sem artefato
verificável *"'pre-registered' é retórica"*. É o item mais barato da lista.

**C¶3 — Trabalhos futuros** ⚪
> Future work includes validating rotational fidelity against a rotation-rich
> window distribution, which the competition hold-out does not provide; a
> low-amplitude open-loop arm to separate loop topology from amplitude coverage;
> cross-log and multi-robot replication; and higher-fidelity behavioral simulation
> as a substrate for learning-based motion planning, so far trained on simplified
> engines [3].

🔴 **Nota.** "a low-amplitude open-loop arm to separate loop topology from
amplitude coverage" está **desatualizada** frente a L¶3, que agora diz que o
braço necessário é *open-loop com translação superposta* (para separar diluição
de realimentação), não baixa amplitude. **Sugiro alinhar.**

---

# Resumo do que eu quero que você decida

| # | Bloco | Decisão |
|---|---|---|
| 1 | **TB5** | Executar **R3** (recomputar a linha de malha fechada com o mesmo hold-out)? É a objeção mais barata que resta (C5) e hoje a nota de rodapé desmente o título da tabela. |
| 2 | **C¶2** | Inserir o link anonimizado. Sem isso o C10 fica aberto. |
| 3 | **F2** | A Fig. 2 fica (responde S1) ou sai (~0,3 pág.) se o Overleaf estourar 8 páginas? |
| 4 | **F1** | Manter o bloco `rSim + Td (ablation)` no diagrama, já que a ablação não rodou? |
| 5 | **M-B¶1** | Descrever ou remover o *"high-fidelity Simulink model"* (C12)? |
| 6 | **I¶5 / C3** | Qualificar C3 com "against an untuned rSim" já nas contribuições? |
| 7 | **M-H¶3** | Investir em unificar a grade de horizontes (C6/R8) antes de submeter? |
| 8 | **C¶3** | Alinhar "low-amplitude open-loop arm" com L¶3. |
| 9 | **RW¶1** | Se sobrar página, desfazer a fusão dos três parágrafos? |
| 10 | **D-C¶1** | Inverter a ordem (ressalva antes da leitura dinâmica), dado o B6? |

**Fora do artigo, ainda aberto:** R0 (corrigir a entrada errada do
`results/CHANGELOG.md`, que afirma `R_efetivo = 3,3245` quando o valor é
2,699070934) e R1 (re-derivar a matriz de cinemática inversa) — nenhum dos dois
bloqueia a submissão.
