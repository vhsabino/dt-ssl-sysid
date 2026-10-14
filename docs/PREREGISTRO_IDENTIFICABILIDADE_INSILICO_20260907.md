# Pré-registro — Identificabilidade in-silico (C1): regime de excitação × ruído de medição × zona morta

**Gravado em:** 2026-09-07, ANTES de rodar o experimento completo. Os fatores, o estimador,
as seeds, o número de réplicas e as regras de decisão abaixo são fixados agora e não serão
ajustados depois de ver o resultado. Módulo reproduzível:
`dtssl analysis run identifiability_insilico` (`src/dtssl/analysis/identifiability_insilico.py`).

## Contexto e afirmação sob teste

- Achado central do artigo (SBR/LARS 2026, `latex/sections/04_results.tex` e `05_discussion.tex`):
  **a identificabilidade segue o regime de excitação, não o DOF**. Com a MESMA estrutura P1D
  (`G_i(s) = K_i e^{-Td_i s}/(τ_i s + 1)`) e a MESMA cadeia de estimação, ω em malha fechada
  (logs de competição, `shoot_to_goal`) deu `K_ω = 1,378`, fit hold-out 44,8 %
  (`results/r3_closedloop_omega_fit_20260810_1036.md`), enquanto a coleta dedicada de rotação
  pura em malha aberta (`rotate`) deu `K_ω = 1,0016`, fit hold-out 71,1 %
  (`results/identificacao_omega_20260724.md`, promovido). vx/vy foram identificados dos logs de
  competição com fit hold-out ~87 % (`models/sysid_vxvy_v2.mat`).
- O artigo localiza a não-linearidade dominante na **zona morta elétrica por roda** do firmware
  (`MOTOR_MIN_SPEED_RAD_S = 1,567 rad/s`, equivalente a 0,58–0,60 rad/s de guinada de corpo em
  rotação pura) e mostra que, em jogo, ela engaja em apenas ~2 % das amostras porque a translação
  já mantém as rodas girando; o comando de guinada é **diluído** (mediana de 1 % do setpoint por
  roda) e explica só 56 % da variância da rotação medida.
- Nos dados reais a verdade θ é desconhecida. Este experimento cria a verdade: o **próprio gêmeo**
  (`AnalyticFOPDTPlant` com o θ oficial) gera as trajetórias a partir de sequências de comando de
  cada regime, passa-as por uma cadeia de medição tipo visão e re-identifica θ por DOF com a mesma
  cadeia Python do artigo. A pergunta é: **em quais regimes a cadeia recupera θ\* conhecido, e o
  padrão de recuperação depende do regime ou do DOF?**

### O que o gerador pode e não pode reproduzir (declarado antes de rodar)

O gerador é o gêmeo linear (P1D por DOF, sem escorregamento, sem assimetria de tração, sem
perturbações) e os comandos são **repetidos em malha aberta** (não há controlador reagindo à
trajetória gerada). Portanto, R1 in-silico testa apenas o **conteúdo informacional** das
sequências de comando de competição (mais ruído de medição e zona morta) — NÃO o mecanismo de
diluição/realimentação que o artigo aponta como causa do `K_ω ≈ 1,38`. Consequência lida
antecipadamente: se ω for recuperado em R1 in-silico, isso **não contradiz** o artigo; localiza o
mecanismo real fora do gerador (dinâmica não modelada correlacionada ao comando sob realimentação),
que é exatamente a leitura de diluição do artigo. Se ω NÃO for recuperado em R1 in-silico, o
conteúdo de comando por si só (com zona morta/ruído) já basta para explicar a falha.

## Verdade (θ\*) e grade

- θ\* = θ oficial de `config/twin_params.json` (inalterado): vx {K 1,1192; τ 0,0718; Td 0,06905},
  vy {1,0524; 0,1273; 0,05648}, ω {1,0016; 0,0828; 0,08895}. `Ts = 1/60 s`.
- Gerador: `AnalyticFOPDTPlant(θ*)`, `reset(pose0, velb0=(0,0,0))`, `pose[k] = step(cmd[k-1], Ts)`,
  `pose[0] = pose0` (mesmo driver de `dtssl.sim.rollout.free_run` com `prev_cmds=None`: buffer de
  atraso vazio antes de t0). O atraso que a planta efetivamente aplica é inteiro:
  `ceil(Td*/Ts − 1e−9)` amostras = **5 (vx), 4 (vy), 6 (ω)**; o Td\* contínuo (4,14 / 3,39 / 5,34
  amostras) NÃO é recuperável abaixo dessa quantização.

## Fatores (desenho fatorial completo, por DOF)

**Fator A — regime de excitação** (cada regime = um conjunto de "eventos" = sequências de comando):

| regime | eventos | vx | vy | ω |
|---|---|---|---|---|
| R1 "comandos de competição (malha fechada)" | logs reais reproduzidos no gêmeo, pareamento do artigo | `front_to_back` (4) | `side_to_side` (13) | `shoot_to_goal` (18) |
| R2-rotate "rotação pura dedicada (malha aberta)" | `rotate` (10 eventos, ±0,25/±0,5/±1/±2,5/±5 rad/s, comando constante; vx = vy = 0) | rotate (sem excitação translacional) | rotate | rotate |
| R2-square "translação tipo malha aberta" | `square` (11 eventos) | square | square | square |
| R3 "excitação projetada" | 12 eventos sintéticos de 10,0 s (600 amostras), seed de desenho 42 | PRBS | PRBS | PRBS |

- Comandos de R1/R2 vêm de `ctx.segment(label, evento)` (grade uniforme 60 Hz do loader, ZOH),
  `pose0` do evento real, `velb0 = 0`.
- R3: em cada evento os TRÊS DOFs são excitados **simultaneamente** por sequências independentes
  de degraus constantes por trechos (tipo PRBS): duração de cada degrau ~ U(0,3; 1,2) s
  (arredondada a amostras), amplitude com sinal equiprovável e módulo ~ U(0,6; 1,5) m/s (vx, vy) e
  U(1,5; 4,0) rad/s (ω) — todas acima da zona morta; `pose0 = (0, 0, 0)`. O desenho é gerado UMA
  vez (`numpy.random.default_rng(42)`) e é o mesmo em todas as réplicas: só o ruído e o split
  mudam por réplica. Escolha declarada: excitação simultânea (e não um DOF por evento) porque é o
  análogo multi-DOF de um experimento projetado e mantém as rodas girando como em jogo.
- R2-rotate inclui os 4 eventos de amplitude ±0,25/±0,5 rad/s que o pré-registro de ω de
  2026-07-24 EXCLUIU do fit linear (regime de zona morta). Aqui entram deliberadamente: com a zona
  morta ligada esses eventos têm resposta nula e testam se o regime dedicado resiste ao mecanismo
  (os eventos de grande amplitude dominam o custo). Isso torna R2-rotate **conservador**.
- Para cada regime reporta-se a fração de amostras em que a zona morta ALTEROU o comando
  (qualquer componente e a componente do DOF), calculada com `apply_body_deadzone`.

**Fator B — ruído de medição** (i.i.d. por amostra, gaussiano, adicionado às poses geradas antes
do estimador): `none` (0; 0); `vision` (σ_pos = 2 mm em `position_x/y`, σ_θ = 0,01 rad em
`position_w`); `heavy` (5 mm, 0,03 rad). Mesma realização normal-padrão `z` por (réplica, evento),
escalada por σ (números aleatórios comuns entre níveis — comparação pareada). O heading é
entregue embrulhado em (−π, π] como a visão real.

**Fator C — zona morta do gerador**: `off` / `on`. Com `on`, cada comando passa por
`dtssl.sim.twin_world.apply_body_deadzone(vx, vy, w, 1.567)` (rodas abaixo de 1,567 rad/s zeradas,
corpo recuperado pela pseudo-inversa — a mesma implementação do gêmeo executável) ANTES da planta;
o **estimador sempre recebe o comando original** (como nos logs: a estratégia não sabe da máscara).
Limiar de `config/robot_limits.json: deadzone.wheel_min_speed_rad_s` (1,567; `enabled` é ignorado —
o fator C é quem liga).

**Simplificações declaradas da cadeia de medição:** poses e comandos na MESMA grade de 60 Hz
(sem amostragem assíncrona ~73 Hz da visão, sem perdas de quadro, sem latência de visão); ruído
branco (sem ruído colorido/quantização de pixel). Só os três fatores acima variam.

## Estimador (fixado)

1. Tabelas no contrato dos logs: `commands` (`timestamp` [s], `move_x`, `move_y`, `move_w`) e
   `processed_robots` (`timestamp`, `position_x/y` em **mm**, `position_w` em rad).
2. `(u, y) = common.legacy_uy_series(cmd, rob, dof, Ts, min_len=60, pos_scale=1/1000)` — a
   cadeia do artigo: interpolação linear do comando, Savitzky-Golay (janela 7, ordem 2) + diferenças
   centrais da pose, rotação mundo→corpo para vx/vy (y em m/s e rad/s).
3. Custo de erro de saída por DOF sobre os eventos de TREINO:
   `J(K, τ, Td) = Σ_eventos Σ_k (y[k] − simulate_fopdt(u, Ts, K, max(τ, 1e−4), Td, align="legacy")[k])²`
   (mesmo simulador e mesmos clamps de `r3_closedloop_omega_fit`).
4. **Busca**: o custo é constante por trechos em Td (atraso inteiro `m = ceil(Td/Ts)`). Piloto na
   célula idealizada (R3, ruído `none`, zona morta `off`, ÚNICA célula executada antes deste
   documento) mostrou que o Nelder-Mead 3-D a partir de X0 do artigo pára no patamar errado de Td
   e compensa com τ (viés de τ de +15 % a +53 % em dados SEM ruído), enquanto o perfil exaustivo
   recupera θ\* (K a 0,1 %, τ a 0,5–2 %). Por isso o estimador pré-registrado é
   **Nelder-Mead em (K, τ) para cada atraso inteiro `m ∈ {0, …, 12}` (0 a 0,2 s), escolhendo o `m`
   de menor custo de treino** — mesmo custo, mesmo modelo, mesmo simulador; só a busca em Td
   é exaustiva. X0 de (K, τ) = (1,0; 0,08) para vx/vy e (1,3; 0,03) para ω (os X0 de
   `loo_translational`/`r3` sem a componente Td); opções NM `maxiter=400, xatol=1e−4, fatol=1e−3`.
   Desvio em relação a `r3.compute` (NM 3-D) **declarado aqui**; o NM 3-D literal é rodado uma vez
   por DOF na célula idealizada e reportado para documentar o problema.
5. Convenção do atraso (documentada em `common.py`): `align="legacy"` aplica UMA amostra a menos
   de atraso efetivo que a planta. Logo o atraso efetivo estimado é `m_eff = m − 1` amostras
   (`Td_eff = (m − 1)·Ts`), comparável com o `ceil(Td*/Ts − 1e−9)` da planta. Todas as tabelas
   reportam `m_eff` ao lado de `Td*/Ts`.
6. Split por réplica: permutação seeded dos eventos do regime, `n_holdout = max(1, round(n/3))`
   (mesmo idioma de `r3`); fit nos eventos de treino; `fit %` (NRMSE, `common.fit_percent`)
   reportado como média sobre os eventos de hold-out e mediana sobre os de treino. Um evento com
   `y` constante (resposta nula pela zona morta, sem ruído) tem fit indefinido → NaN, excluído
   da média (`nanmean`). Um DOF cujos comandos de treino têm variância nula (ex.: vx em `rotate`)
   é **degenerado**: sem fit, estimativas NaN, célula não recuperável.

## Monte Carlo e seeds

- `n_rep = 20` réplicas por célula (regime × ruído × zona morta × DOF). Réplica `r`:
  seed do ruído `42 + r`; seed do split `42 + 1000 + r` (streams separados).
- Total planejado: 4 regimes × 3 ruídos × 2 zonas mortas × 3 DOFs × 20 = 1440 ajustes.
- Se o tempo total exceder ~40 min, roda-se com `n_rep = 12` e isso é declarado no artefato.
- Registrado por réplica: `K_hat, tau_hat, m_hat, Td_hat = m·Ts, Td_eff, fit_holdout_mean,
  fit_train_median, custo, eventos de hold-out, fração mascarada`.

## Métricas por célula e regra de decisão (FIXADAS)

Sobre as réplicas: mediana e IQR (P25–P75) de `K_hat`, `tau_hat`, `m_eff`; viés relativo da
mediana `(mediana − θ*)/θ*`. Quatro critérios:

1. `|viés_K| ≤ 10 %`;
2. `|viés_τ| ≤ 15 %`;
3. `|mediana(m_eff) − Td*/Ts| ≤ 1 amostra` (1/60 s);
4. `IQR(K_hat)/K* ≤ 20 %`.

**Escore de identificabilidade** = número de critérios satisfeitos (0–4);
**recuperado** ⇔ escore = 4. NaN em qualquer estatística ⇒ critério falha.

Célula **realista** = (`vision`, zona morta `on`); célula **idealizada** = (`none`, `off`).

## Hipóteses (fixadas antes de rodar) e o que as falsifica

- **H1** — ω é recuperado em R2-rotate e R3, mas NÃO em R1 com zona morta `on` (o achado do
  artigo, agora com verdade conhecida). Falsificada se ω for recuperado em R1/`on`
  (escore 4, |viés_K| ≤ 10 %) — leitura antecipada acima: o conteúdo de comando de competição
  basta para um gerador linear e o mecanismo real está fora do gerador.
- **H2** — vx/vy são recuperados em R1 (os comandos de competição excitam a translação) e em
  R3; degradados em R2-rotate (sem excitação translacional: degenerado). R2-square (translação
  tipo malha aberta) esperado recuperado. Falsificada se vx ou vy falharem em R1 ou R3 na célula
  realista.
- **H3** — o ruído alarga o IQR mas não enviesa K: `|viés_K| ≤ 10 %` em todos os níveis de ruído
  nas células com excitação do DOF, e `IQR(K)` não decrescente de `none` → `vision` → `heavy`.
  Falsificada se `heavy` levar |viés_K| > 10 % em uma célula em que `none` recupera.
- **H4** — a zona morta é o principal mecanismo de viés de ω em R1: o viés aparece com `on` e
  desaparece com `off` (a diferença de |viés_K| entre `on` e `off` em R1/ω explica a maior parte
  do viés de `on`). Falsificada se o viés de K em R1/ω/`on` ficar ≤ 10 % ou se for igual ao de
  `off`; nesse caso a zona morta NÃO explica o `K_ω ≈ 1,38` de malha fechada, reforçando a
  leitura de diluição/realimentação do artigo (que o gerador não contém).

**O que falsificaria a afirmação da tese ("o regime, não o DOF")** neste experimento: um padrão
de recuperação que dependa do DOF e não do regime — ex.: ω não recuperado em NENHUM regime
(inclusive R3, projetado, e R2-rotate, dedicado) enquanto vx/vy são recuperados em todos, ou
vx/vy recuperados mesmo sem excitação. A afirmação é corroborada se, para cada DOF fixo, o
escore varia com o regime (recuperado onde há excitação do DOF, não recuperado onde não há) e,
para cada regime com excitação de todos os DOFs (R3), os três DOFs são recuperados.

## Artefatos

`results/identifiability_insilico_<carimbo>.md` (cabeçalho de proveniência: commit, θ, dataset,
seed; tabelas por DOF; resumo regime × DOF nas células realista e idealizada; "Leitura"),
`.csv` (todas as réplicas) e `.json` (desenho + resumos por célula). Entrada em
`results/CHANGELOG.md`. Saída de console só ASCII (console Windows cp1252).

## Compromisso

Depois deste arquivo salvo, o experimento roda sem reabrir estas decisões. Qualquer desvio
necessário durante a execução (tempo, erro numérico, dado insuficiente) será registrado no
artefato e no CHANGELOG como desvio do pré-registro, não como edição silenciosa deste documento.
