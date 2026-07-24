# Planejamento de escrita — Paper SBR/LARS 2026 (Robótica 2026, João Pessoa)

*Documento de PLANEJAMENTO. NÃO é o paper. Produzido a partir da varredura do
repositório `digitaltwin` (não da memória). Onde o dado do repo não foi
encontrado, está marcado **[A VERIFICAR]**. Data de produção: 2026-06-23.*

> **Convenção de idioma:** este plano está em PT-BR (documento interno). O paper
> em si é em **EN** (regra do projeto: `CLAUDE.md` §Convenções).

---

## 0. Dados da chamada (confirmados — não rebuscar)

- **6 páginas**, formato **IEEE**, **inglês**, **DOUBLE-BLIND** (sem nomes,
  instituição, agradecimentos ou auto-referências identificáveis).
- Templates IEEE (Word/LaTeX/Overleaf). Submissão via sistema **SBC**.
- **Datas:** site abre 01/05/2026 · **DEADLINE 15/07/2026** · notificação
  15/08/2026 · camera-ready 15/09/2026.
- Melhores papers → convidados para **versão estendida no JINT** (Journal of
  Intelligent & Robotic Systems).
- **Tópicos diretos:** "Robot soccer"; "Robot simulation and visualization
  tools"; "Robot modeling"; "Robot planning, reasoning, communication,
  adaptation, and learning".

> ⚠️ **Nota de calendário interna:** `ROADMAP.md` e o `RELATORIO_TECNICO`
> referenciam um prazo de qualificação **31/07/2026** e alvos JINT/MDPI. O alvo
> SBR/LARS (15/07) é **anterior** e mais curto. Reconciliar os dois calendários é
> ponto de decisão (ver §8).

---

## PASSO 1 — Inventário do repositório

### 1.1 Resultados VALIDADOS (com números, execução registrada)

Todos com proveniência em `results/CHANGELOG.md` (commit hash + seed + θ).

| # | Resultado validado | Números | Artefato-fonte |
|---|---|---|---|
| V1 | **Re-ID grey-box vx/vy v2 (PROMOVIDO)** P1D `K/(τs+1)·e^(−Td·s)`, hold-out por evento, seed 42 | vx {K=1.1192; τ=0.0718 s; Td=0.0691 s} **fit hold-out 86.7%**; vy {K=1.0524; τ=0.1273 s; Td=0.0565 s} **fit 87.1%** | `models/sysid_vxvy_v2.mat`; `automation/identify_trans_dof.m`; `results/check_excitation_trans_20260614_1018.csv` |
| V2 | **Gate SE(2) multi-h vx/vy v2 vs placeholder** | vx 20/20 (ev×h) melhoram, vy 65/65; medianas h=2.5 s: vx 0.124 vs 0.293 m, vy 0.141 vs 0.334 m (~55% redução); Wilcoxon vy per-h p=2.4e-4, pool vx p=8.9e-5 | `results/eval_vx_v2_se2_20260614_1024.csv`, `results/eval_vy_v2_se2_20260614_1028.csv` (+ `_wilcoxon`, `traj_eval_v*_v2_*.mat`) |
| V3 | **Métrica canônica SE(2) re-ancorada multi-horizonte** (janelas por tempo, overlap 0.5, θ-truth filtrado movmedian 0.2 s) | h∈{0.1,0.2,0.4,0.7,1.0,1.5} s (harness Python) / {0.5,1,2,2.5,4} s (campanha MATLAB); h_ref=24 amostras (0.4 s); N_min=10; α=0.05; bootstrap MBB bloco 6 | `phase0_replay/metrics.py`; `automation/rmse_pos_rebased_se2.m` |
| V4 | **Twin (FOPDT) vs Ideal cinemático — GO translação** | gap@h_ref(0.4 s)=**+0.0633 m**, p=8.54e-7, effect +0.736; vence em TODOS os h no bin translação | `results/phase0_metrics_report_20260616_0811.md` |
| V5 | **Twin vs rSim (rSoccer/ODE) — GO translação (Modo A)** | gap@h_ref=**+0.0930 m**, p=4.38e-11, effect +0.922; (Modo B, sem warm-up) gap@h_ref=+0.2820 m, p=4.44e-14, effect +0.987 | `results/eval_twin_vs_rsim_modeA_20260617_0030.md`, `..._modeB_20260617_0031.md`; `phase0_replay/rsim_plant.py`, `eval_twin_vs_rsim.py` |
| V6 | **Distribuição de bins** (hold-out 10 eventos) | trans-dominado 264 densas / 49 indep (**99.6%**); misto 0; rot-dominado 1 / 0 indep | `results/bin_distribution_20260619_000422.md/.csv`; `results/window_errors_20260619_000422.csv` |
| V7 | **Reconciliação analítico vs Simulink fiel** (modelo implementa o que declara) | max\|Δx\|=4.6 mm, \|Δy\|=5.7 mm, \|Δθ\|=0.0009 rad no square_01_01 | `RELATORIO_TECNICO` §4; CHANGELOG 2026-06-11 17:25 |
| V8 | **Proxy analítico preserva ranking do Simulink** (suporte metodológico) | Spearman ρ(J)=**0.9992**, ρ(J_pos)=0.9938; ~1.6 ms/sim vs ~9.5 s/sim | `results/phase0_proxy_ranking_20260614_2105.csv`; `results/figs/F0_proxy_ranking_*.pdf` |
| V9 | **Resultado NEGATIVO validado: bayesopt 9-param não supera grey-box por DOF na translação** | v1 overfit (5 ev; K_w→piso 0.516); v2 (proxy, treino 18 ev, 400 avals): bate ideal (pool −0.098 m, p=7.6e-10) mas NÃO bate vx/vy v2 (pool +0.0041 m, p=0.040) — empata rotação, perde translação | `results/eval_bayesopt_v2_holdout_20260614_2130.csv` (+ `_wilcoxon`); `models/sysid_bayesopt_v2_candidate.mat` (não promovido) |
| V10 | **Re-ID grey-box ω v1 (PROMOVIDO, 2026-07-24) — dataset DEDICADO de rotação pura, malha aberta** P1D, hold-out por evento (2/6), seed 42 | K=**1.0016** [IC95% 0.9993;1.0040] (≈1.0!), τ=**0.0828 s** [0.0801;0.0855], Td=**0.0890 s** [0.0877;0.0902]; fit hold-out **71.1%** (65.0%/77.2%); gate SE(2) vs placeholder (18 `shoot_to_goal`, Wilcoxon): candidato MELHOR em **todos os 5 horizontes**, Δmediana pool=**−0.1138 m**, p=**1.74e-16**. Confirma que K≈1.3–1.35 de malha fechada era viés de correlação comando↔perturbação, não ganho de planta. | `results/identificacao_omega_20260724.md`; `docs/PREREGISTRO_OMEGA_20260724.md`; `models/sysid_omega_rotate_v1.mat`; `automation/identify_omega_rotate.m`; `results/eval_omega_v3_se2_20260724_1723.csv` (+`_wilcoxon`) |

### 1.2 PARCIAL / PENDENTE (honestidade sobre o que NÃO está validado)

| # | Item | Estado | Evidência |
|---|---|---|---|
| P1 | **~~Identificação de ω~~ RESOLVIDO 2026-07-24 → ver V10** | Histórico (SUPERADO, mantido só como contraste metodológico): de **logs de malha fechada** (competição), ω era não-identificável — candidato {K=1.353; τ=0.0354; Td=0.1058}, fit 52.6%, piorava posição, reprovava Ljung-Box e o gate SE(2) (Δmediana pool +0.0489 m PIOR, p=3.8e-9). Com o **dataset dedicado de rotação pura em malha aberta** (V10), ω identifica-se limpo (K≈1.0, fit hold-out 71.1%, SE(2) MELHOR em todos os h, p=1.74e-16) e foi **PROMOVIDO** (`placeholder:false` em `config/twin_params.json`). **A narrativa do paper deve mudar**: de "limitação honesta" (ω não-identificável) para "resultado positivo + contribuição metodológica" (malha fechada de competição não sustenta identificação de ω; malha aberta dedicada resolve, e o contraste K≈1.3 vs K≈1.0 é evidência direta de viés de correlação comando↔perturbação em dado de malha fechada). Isso afeta a estrutura das seções V/VI (ver notas abaixo, linhas ~146-147, ~187, ~194-209) — revisão de narrativa ainda **NÃO feita** nesta sessão, só os fatos/tabelas foram corrigidos. | CHANGELOG 2026-06-11/13 (histórico); CHANGELOG 2026-07-24 (V10); `RELATORIO_TECNICO` §6; `results/identificacao_omega_20260724.md` |
| P2 | **Zona morta de ω** | Confirmada **POR RODA** no firmware (MOTOR_MIN_SPEED 1.567 rad/s roda → **0.58–0.60 rad/s de corpo, sempre reportado como INTERVALO, nunca valor pontual**; ver `config/robot_geometry.json`, provado por CAD medido 2026-07-24 [R/r=2.6991] + constante implícita no firmware/telemetria do dataset `rotate` [R/r=2.61] + K_ω≈1.01 medido — o antigo 0.472 usava R/r=3.3208 sem rastreabilidade e foi **refutado**). Hammerstein com zona morta no corpo **não corresponde** à física → estrutura de modelo inadequada para o regime de dados. | CHANGELOG 2026-06-13 (Etapa B, ssl-embedded); CHANGELOG 2026-07-24 (D9, correção da constante); `results/qc_rotate_*.md` |
| P3 | **Bins rotação/misto** | Re-rodado 2026-07-24 pós-promoção de ω (V10): **ainda SEM VEREDITO**, mas por motivo diferente agora — não é mais o gate de placeholder (removido), é população: hold-out de 10 eventos de competição tem 0 janelas "misto" e so 1 "rot-dominado" (N_indep=0 < N_min=10). twin vs `IdealKinematicPlant` (rSim/`robosim` segue indisponível neste ambiente, bloqueio pré-existente): trans-dominado **GO** (gap@h_ref=+0.0617 m, p=1.15e-8, effect+0.832); misto/rot **SEM PODER**. | `results/phase0_metrics_report_20260724_1729.md` (supersede V4/V6 p/ o DOF ω); V4/V5/V6 (histórico, vx/vy-only) |
| P4 | **RL (Abordagem A)** | **Não há conteúdo no repositório** sobre a Abordagem A/RL além de menção a "vertente RL = próximo passo". Sem ambiente, política ou resultado versionado. → trabalho **FUTURO citado**, não conteúdo. | `ROADMAP.md` Trilha B F6; ausência de código RL no repo **[A VERIFICAR com a orientadora se há material fora do repo]** |
| P5 | **Validação cross-log / 2º dataset** | **Não existe.** Único dataset extraído: `2026-05-18_19-2-15` (46 eventos, 1 robô, team `allies`). | `data/extracted/`; `DESIGN.md` §2 |
| P6 | **rSim em ambiente padrão** | rSim (`rc-robosim`) **não compila** em Windows/cp314 (falta ODE). Resultados V5 vieram de env Linux dedicado (cp310/ODE). Reprodutibilidade exige documentar o ambiente. | `docs/RSIM_EXPLORATION.md`; `rsim_plant.py` cabeçalho |
| P7 | **SLR / Related Work** | **EM DÍVIDA.** Só existe `slr/protocolo_slr.md` + `slr/scripts/slr_pipeline.py`. **NÃO há** `slr/incluidos.bib`, `triagem.csv`, nem extração. Guardrail do projeto: citar só de `slr/incluidos.bib` (ainda inexistente). | `slr/` (varredura); `CLAUDE.md` §Guardrails |

### 1.3 Figuras já existentes (candidatas a entrar no paper)

- `results/figs/F4_horizons_eval_horizons_medianas_20260611_2325.pdf` — RMSE × horizonte × modelo (**candidata a figura central**).
- `results/figs/F1_dotplot_eval_campaign_20260611_2238.pdf` — dot-plot RMSE por evento, cores por label.
- `results/figs/rsim_twin_{all,trans,rot}_20260617_0030.{png,svg}` — twin vs rSim por bin (Modo A).
- `results/figs/F0_proxy_ranking_20260614_2105.pdf` — validação do proxy (apoio metodológico / mais para JINT).
- `results/figs/diag_omega_gain_amplitude_20260613_2239.pdf` — ganho de ω por faixa (apoio à não-identificabilidade).
- `results/figs/F2_overlays_traj_eval_campaign_20260611_2238.pdf` — overlays de trajetória.
- `results/figs/bins_20260619_000422.{png,svg}`, `contact_trans_*`, `representative_*` — distribuição/curvas do harness Python.

> **Atenção de coerência:** há **duas** grades de horizonte (Python {0.1…1.5}s e
> MATLAB {0.5…4}s) e **duas** âncoras (translação e SE(2)). Padronizar UMA
> apresentação no paper para não confundir o revisor (ponto de "pronto" da Fase 4).

---

## PASSO 2 — Enquadramento nos 4 tópicos diretos

| Tópico da chamada | Encaixe | Evidência no repo | Força |
|---|---|---|---|
| **Robot simulation and visualization tools** | O artefato central É um simulador (gêmeo digital) e a contribuição é **fidelidade medida contra o simulador SSL padrão (rSim/grSim, ODE)** com vereditos estatísticos. | V5 (twin vence rSim em translação, effect ≥0.92), V4, métrica SE(2) multi-h | **ALTA** |
| **Robot modeling** | Núcleo metodológico: **identificação grey-box FOPDT por DOF** de logs de malha fechada; caracterização de identificabilidade (Td, ω). | V1, V2, P1/P2 (não-identificabilidade de ω) | **ALTA** |
| **Robot soccer** | Domínio = RoboCup **SSL**, robô omnidirecional 4 rodas, dados de competição. | dataset, contrato de dados (`DESIGN.md` §2) | **MÉDIA** (domínio, não contribuição) |
| **Robot planning, reasoning, … and learning** | Só via **RL como trabalho futuro**; sem conteúdo de aprendizado no recorte. | P4 (sem material no repo) | **BAIXA** (não usar como primário) |

### Recomendação (sujeita à decisão da orientadora — ver §8)

**Tópico primário recomendado: "Robot simulation and visualization tools"**, com
**"Robot modeling"** como secundário e **"Robot soccer"** como domínio.

**Justificativa:** o *claim* mais forte e auto-contido em 6 páginas é "um gêmeo
grey-box barato, identificado de logs de competição, **supera o simulador SSL de
referência em fidelidade de trajetória de curto/médio horizonte**" (V5, effect
0.92–0.99). Isso fala diretamente ao tópico de simulação/ferramentas e tem o
maior impacto para a audiência SBR/LARS (todos usam grSim/rSim). "Robot modeling"
sustenta o *como*. O ângulo de RL não tem lastro no repo e enfraqueceria um paper
double-blind se forçado.

**Ângulo de título (rascunhos, EN, sem auto-identificação):**
- "A Behavioral Digital Twin of an Omnidirectional Soccer Robot: Per-DOF Grey-Box
  Identification from Closed-Loop Logs Outperforms an ODE Simulator in Short-Horizon Fidelity"
- "Closing the Reality Gap with Cheap Models: Grey-Box Per-DOF Twins vs. ODE
  Simulation for Omnidirectional Soccer Robots"
- (variante modeling-first) "Per-DOF Grey-Box Identification of an Omnidirectional
  Robot from Competition Logs: A Multi-Horizon SE(2) Fidelity Study"

---

## PASSO 3 — Recorte de 6 páginas (e mapa para a extensão JINT)

### 3.1 Hipótese de recorte (AVALIADA: fecha em 6 páginas)

O paper SBR é o **resultado de FIDELIDADE do gêmeo**, composto por três peças que
já têm números validados:

1. **Identificação grey-box por DOF** (translação): V1 + V2.
2. **Twin vs simulador ODE (rSim/grSim) em SE(2) multi-horizonte:** V4 + V5 + V6
   (protocolo de bins, gates, Wilcoxon não-sobreposto + bootstrap + effect size).
3. **Caracterização honesta da não-identificabilidade de ω** de malha fechada:
   P1 + P2 (transformada de fraqueza em **contribuição** — é um achado).

O **RL (Abordagem A)** entra **só como trabalho futuro citado**, não como conteúdo.

### 3.2 O que vai no SBR (6 pg) vs o que fica para a extensão JINT

| Conteúdo | SBR (6 pg) | Extensão JINT |
|---|---|---|
| FOPDT por DOF, pipeline de dados, métrica SE(2) multi-h | ✅ enxuto | ✅ completo (derivação equivariância SE(2), ablations) |
| Twin vs Ideal (V4) | ✅ | ✅ |
| Twin vs rSim/grSim translação (V5), bins, gates | ✅ (resultado-âncora) | ✅ + rotação quando ω existir |
| Não-identificabilidade de ω (P1/P2) | ✅ como **limitação/achado** (1 parágrafo + 1 figura de apoio) | ✅ tratamento completo (Hammerstein, firmware, Ljung-Box, coleta dedicada) |
| bayesopt 9-param (V9, resultado negativo) | ➖ **mencionar em 1–2 frases** (justifica por que grey-box por DOF) | ✅ história completa (proxy ρ=0.999, ARD, overfit por dado) |
| RL / Abordagem A | ➖ só "future work" (1 frase) | ✅ vertente completa |
| Validação cross-log / 2º dataset | ➖ (não existe; declarar limitação) | ✅ (P5 — coletar) |
| SLR completa | ➖ **mini-revisão focada** (ver §8 decisão) | ✅ SLR completa (Kitchenham) |

### 3.3 Esqueleto de 6 páginas (IEEE 2-col) — orçamento de espaço

| Seção | Páginas | Conteúdo | Consome |
|---|---|---|---|
| I. Introduction | 0.75 | Reality gap em SSL; logs de competição; contribuições C1–C3 | `docs/01_definicao_pesquisa.md` |
| II. Related Work | 0.75 | **mini-revisão** (BLOQUEADA pela SLR — §8) | `slr/incluidos.bib` (**inexistente**) |
| III. Method | 1.5 | FOPDT por DOF; pipeline protobuf→splits→Sav-Golay; métrica SE(2) multi-h; baselines (ideal, rSim/grSim) | `DESIGN.md`, `RELATORIO_TECNICO` §1–2, `phase0_replay/` |
| IV. Experimental Setup | 0.5 | Robô; dataset (46 ev / 10 hold-out); config da métrica; gates | `DESIGN.md` §2–3, `splits.py` |
| V. Results | 1.5 | **Fig. central** RMSE×h×modelo; Tab. twin vs ideal + twin vs rSim; bins; ω não-identificável | V2,V4,V5,V6,P1 |
| VI. Discussion | 0.5 | Limitações (ω, excitação malha fechada, 1 dataset); ameaças à validade | P1–P6 |
| VII. Conclusion + Future Work | 0.25 | Recap; coleta dedicada de rotação; **vertente RL** | `ROADMAP.md` Trilha B |
| Refs | ~0.5 | — | SLR |

**Veredito:** **fecha em 6 páginas** SE a Related Work for mini-revisão (não a SLR
completa) e o ω for tratado como 1 parágrafo + 1 figura de apoio. O risco de
estouro vem de (a) querer contar a história do bayesopt, (b) duas grades de
horizonte/duas âncoras. **Alternativa se estourar:** mover a figura twin-vs-ideal
para inline-mention e manter só a figura twin-vs-rSim + tabela; cortar overlays.

---

## PASSO 4 — Plano de escrita em FASES (entregável principal)

Ordenado por dependência. Esforço relativo em "pontos" (1 = ~meia sessão).
Marcação: 🟢 **PODE JÁ** (material existe) · 🔴 **BLOQUEADO**.

### Fase 0 — Decisões de escopo + setup do template (esforço 1) 🟢
- **Objetivo:** travar os pontos de decisão de §8 com a orientadora; criar projeto
  IEEE (Overleaf/LaTeX) double-blind.
- **Produz:** repositório do paper (`paper/sbr2026/`), `main.tex` com template IEEE.
- **Consome:** este documento; templates IEEE.
- **Dependências:** decisões de §8 (recorte, tópico, escopo SLR).
- **Pronto quando:** decisões registradas; compila um PDF vazio no template certo.

### Fase 1 — Method + Experimental Setup (esforço 3) 🟢 PODE JÁ
- **Objetivo:** escrever III e IV — todo o material existe e está validado.
- **Produz:** §III, §IV.
- **Consome:** `DESIGN.md` (contrato de dados, interface Plant, métrica),
  `RELATORIO_TECNICO` §1–3, `phase0_replay/{schema,io,plant,metrics,splits}.py`,
  `config/ssl_robot.sldd` (ordem dos 9 params).
- **Dependências:** Fase 0.
- **Pronto quando:** modelo, pipeline, métrica e gates descritos de forma que um
  terceiro reproduza; números de config (h, overlap, N_min, α) conferem com V3.

### Fase 2 — Results (esforço 3) 🟢 PODE JÁ
- **Objetivo:** escrever §V com as tabelas e a figura central.
- **Produz:** §V + figura central + 1–2 tabelas.
- **Consome:** V2 (`eval_v*_v2_se2_*`), V4 (`phase0_metrics_report_*`), V5
  (`eval_twin_vs_rsim_mode{A,B}_*`), V6 (`bin_distribution_*`), figura
  `F4_horizons_*` ou `rsim_twin_trans_*`; ω de apoio `diag_omega_gain_amplitude_*`.
- **Dependências:** Fase 1 (definições da métrica precisam existir antes).
- **Pronto quando:** toda afirmação numérica rastreia a um arquivo de `results/`;
  UMA grade de horizonte e UMA âncora escolhidas e usadas de forma consistente;
  Modo A vs Modo B explicado (justiça de IC).

### Fase 3 — Discussion + Conclusion + Future Work (esforço 2) 🟢 PODE JÁ
- **Objetivo:** §VI e §VII; transformar P1–P6 em limitações honestas e ganchos.
- **Produz:** §VI, §VII.
- **Consome:** P1–P6; `ROADMAP.md` Trilha B (RL como futuro).
- **Dependências:** Fase 2.
- **Pronto quando:** limitações (ω, 1 dataset, excitação malha fechada) explícitas;
  RL citado em 3ª pessoa, anonimizado (ver Fase 5).

### Fase 4 — Introduction (esforço 2) 🟢/🟡
- **Objetivo:** §I com contribuições C1–C3 e posicionamento.
- **Produz:** §I.
- **Consome:** `docs/01_definicao_pesquisa.md` (problema, lacuna, contribuições).
- **Dependências:** depende **parcialmente** da Related Work (a "lacuna" hoje é
  hipótese — `docs/01` diz "[PREENCHER após SLR]"). Pode rascunhar já e fechar a
  frase de lacuna após a SLR.
- **Pronto quando:** contribuições alinhadas ao que §V realmente entrega (não
  prometer ω nem RL).

### Fase 5 — Related Work (esforço 3–5) 🔴 **BLOQUEADO — CAMINHO CRÍTICO**
- **Objetivo:** §II a partir da SLR.
- **Produz:** §II + `slr/incluidos.bib`.
- **Consome:** `slr/protocolo_slr.md`, `slr/scripts/slr_pipeline.py` → **falta**
  executar busca, triagem (Fase 1/2 Kitchenham), extração e síntese.
- **Dependências:** **A SLR está EM DÍVIDA (P7).** Sem `incluidos.bib` não há
  Related Work, e o guardrail proíbe citar de memória. **Este é o item de caminho
  crítico — não é detalhe.**
- **Pronto quando:** `incluidos.bib` populado; mini-revisão escrita; lacuna de §I
  fechada com evidência (não hipótese).

### Fase 6 — Anonimização double-blind (esforço 1) 🟢 (ver detalhamento abaixo)
- **Objetivo:** neutralizar TODO ponto de auto-identificação.
- **Produz:** versão double-blind compliant.
- **Dependências:** todas as seções escritas.
- **Pronto quando:** checklist de §6.1 100% verde.

### Fase 7 — Revisão IEEE + montagem final (esforço 2) 🟢
- **Objetivo:** caber em 6 pg, formatação IEEE, figuras legíveis em P&B, revisão
  de inglês, checklist de submissão (declaração de uso de IA, dados/código).
- **Pronto quando:** PDF ≤6 pg, double-blind check passou, referências só de
  `incluidos.bib`.

### Caminho crítico (visual)
```
Fase 0 ─┬─ Fase 1 ─ Fase 2 ─ Fase 3 ─┐
        └─ Fase 4 (parcial) ─────────┼─ Fase 6 ─ Fase 7 ─ SUBMISSÃO
   Fase 5 (SLR) ════[CAMINHO CRÍTICO]═┘
   ^ começa em PARALELO no dia 1; dimensiona o cronograma
```
Método/Resultados (Fases 1–3) podem ser escritos JÁ. **O gargalo é a Fase 5.**

---

## 6. Anonimização double-blind (detalhe)

### 6.1 Checklist de pontos de auto-identificação a neutralizar

| # | Ponto de identificação | Onde aparece hoje | Como neutralizar |
|---|---|---|---|
| A1 | **"RobôCIn"** (nome da equipe) | `CLAUDE.md`, `DESIGN.md`, `RELATORIO_TECNICO` §0 | Remover; usar "an SSL team" / "a competition team". |
| A2 | **"UFPE" / Pernambuco / Doutorado** | `CLAUDE.md` título | Não citar instituição nem grau. |
| A3 | **"nosso trabalho anterior" / "trabalho antigo"** (vx/vy herdados) | `RELATORIO_TECNICO` §5 | Reescrever em 3ª pessoa: "a previously reported model" / "prior per-DOF parameters", sem dono. |
| A4 | **Robô "v2025" da equipe** | vários | "an omnidirectional 4-wheel SSL robot"; evitar versão que ligue à equipe. |
| A5 | **rSoccer / rSim como "base do nosso RL"** | `RSIM_EXPLORATION.md` | Citar rSoccer/rSim **como ferramenta de terceiros** (cita o paper rSoccer na 3ª pessoa), nunca como "nossa base". |
| A6 | **Paper-base de RL (Abordagem A)** | [A VERIFICAR] não está no repo | Citar em **3ª pessoa** como literatura ("a recent RL approach for SSL [ref]"); jamais "we previously proposed" / "our environment". |
| A7 | **Firmware `ssl-embedded`** (repo da equipe) | CHANGELOG 2026-06-13 | Se citado, "the robot firmware"; não linkar ao repositório nominal. |
| A8 | **Repositório público / DVC / link de dados** | `paper/outline_artigo.md` checklist | Substituir por "available upon publication" ou link anonimizado (anonymous.4open.science). |
| A9 | **Agradecimentos / financiamento** | — | **Omitir** na versão de submissão; reinserir no camera-ready. |
| A10 | **Metadados do PDF/LaTeX** (autor, \author) | template | Usar bloco anônimo do template IEEE; limpar metadados do PDF. |
| A11 | **Nomes de arquivo/figura com pistas** | `apresentacao/orientacao_*` | Renomear assets neutros antes de exportar. |
| A12 | **Auto-citações** no .bib | `incluidos.bib` (a criar) | Marcar e redigir auto-citações na 3ª pessoa neutra; checar que não revelam autoria por padrão de citação. |

### 6.2 Como citar sem se identificar
- **rSoccer/rSim** e **grSim**: ferramentas de terceiros → citação normal em 3ª
  pessoa ("We compare against rSim [X], the ODE-based SSL simulator …").
- **Paper-base de RL (Abordagem A):** tratar como literatura externa; "a recent
  reinforcement-learning method for SSL [Y] motivates the need for higher-fidelity
  simulation" — **nunca** "our prior RL work".
- **Trabalhos do próprio grupo (TDPs/ETDPs, papers anteriores):** citar na 3ª
  pessoa, sem "we"/"our"; evitar frase que só faça sentido se o leitor souber que
  é o mesmo autor.

---

## 7. Cronograma REVERSO (dimensionado pela SLR, não pelo deadline)

Âncora: **DEADLINE 15/07/2026**. Hoje: 23/06/2026 → ~3 semanas até o deadline
(o `ROADMAP` previa ~12 semanas para qualificação; **aqui o tempo é curto** — por
isso a SLR como mini-revisão focada é quase obrigatória; ver §8).

> **Princípio:** o cronograma é dimensionado pela **Fase 5 (SLR)**, o caminho
> crítico, com **folga reservada** para revisão IEEE + double-blind check.

| Semana | Janela | Foco (paralelo) | Marco |
|---|---|---|---|
| S-3 | 23–29/06 | **SLR arranca (Fase 5)** — busca + dedup + triagem fase 1 ‖ Fases 1–2 (Method+Results) escritas | `incluidos.bib` parcial; rascunho III–V |
| S-2 | 30/06–06/07 | **SLR fase 2 + síntese (Fase 5)** ‖ Fases 3–4 (Disc/Concl/Intro) | mini-revisão redigida; lacuna de §I fechada |
| S-1 | 07–13/07 | Integração; Fase 6 (anonimização); Fase 7 (corte 6 pg + revisão inglês) | PDF completo double-blind |
| S-0 | 14–15/07 | **Folga reservada**: double-blind check final + checklist SBC + submissão | **SUBMISSÃO 15/07** |

> ⚠️ **Risco dominante:** a SLR (do zero) em ~2 semanas é apertada. Se a decisão
> for SLR completa, o cronograma **não fecha** sem comprometer a folga — daí o
> ponto de decisão §8 sobre mini-revisão vs SLR completa, e a alternativa de mirar
> CTDR/expandir prazo. **Não trave o paper na SLR:** plano B = mini-revisão
> estruturada (mapping) no SBR, SLR completa fica para a extensão JINT/qualificação.

---

## 8. PONTOS DE DECISÃO (dependem de você/orientadora — NÃO resolvidos aqui)

1. **Recorte final SBR vs escopo JINT.** Confirmar a hipótese de §3 (fidelidade do
   gêmeo no SBR; ω completo + RL + mais validação no JINT)? Ou incluir mais no SBR?
2. **Tópico primário.** Aceitar "Robot simulation and visualization tools" (recomendado)
   ou priorizar "Robot modeling"? (Afeta título, framing e enquadramento na chamada.)
3. **SLR: completa ou mini-revisão focada?** Caminho crítico. Mini-revisão cabe no
   prazo; SLR completa provavelmente **não** cabe até 15/07 sem perder folga.
4. **Alvo: SBR principal vs CTDR** (e/ou aceitar o risco do prazo curto vs mirar
   outro alvo/data). Decisão de calendário: reconciliar com o prazo interno
   31/07/2026 do `ROADMAP`.
5. **[A VERIFICAR / decisão] Material de RL (Abordagem A):** existe paper-base/
   ambiente fora do repo para citar em 3ª pessoa? Qual a referência exata?
6. **Enquadrar o simulador comparado como "grSim" ou "rSim"?** Os resultados (V5)
   são vs **rSim** (rSoccer/ODE); a literatura SSL fala mais em **grSim**. Decidir
   como nomear o baseline sem prometer o que não foi medido.

---

## 9. Resumo executivo (3 linhas para validação humana)

- **Escrevível JÁ (material validado):** Method, Experimental Setup, Results,
  Discussion — todo o núcleo de fidelidade (vx/vy v2 fit ~87%; twin vence ideal e
  rSim em translação com effect 0.74–0.99; ω honestamente não-identificável).
- **Caminho crítico = Related Work, bloqueado pela SLR EM DÍVIDA** (sem
  `incluidos.bib`); decisão mini-revisão vs SLR completa define se o prazo 15/07 fecha.
- **Recorte recomendado:** paper de fidelidade do gêmeo (grey-box por DOF + twin vs
  rSim/grSim em SE(2) multi-h + não-identificabilidade de ω); RL = future work
  citado; pendências de §8 são suas/da orientadora, não decididas aqui.
