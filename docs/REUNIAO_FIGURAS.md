# Conjunto de figuras da reunião — índice e roteiro

> Conjunto coletado em `results/figs/reuniao_20260626/`, ordenado pela narrativa.
> Todos os números abaixo vêm de arquivos em `results/` (citados em cada item).
> Nada foi recomputado; o gate **não** foi re-rodado. Marcações `[A VERIFICAR]`
> indicam valores que não casam exatamente com um arquivo-fonte.

---

## O que AFIRMAR / o que NÃO afirmar

**Afirmar (sustentado por arquivo):**
- **Posição em TRANSLAÇÃO**: o twin (FOPDT) **vence** o rSim/ODE e a cinemática
  ideal em todos os horizontes do bin de translação (gate modo A, veredito **GO**,
  N_indep=49). É a afirmação central. Fonte: `eval_twin_vs_rsim_modeA_20260617_0030.md`.
- A tarefa atual é **translação-dominada** (~99,6% das janelas) — contato/física
  fina não é necessária hoje. Fonte: `bin_distribution_20260619_000422.{md,csv}`.

**NÃO afirmar (limitações a declarar de proa):**
- **Heading / ω**: `w` é **placeholder** (ID física de ω reprovada). Os bins misto
  e rot ficam **INDETERMINADOS** pelo gate de ω. Não afirmar fidelidade de
  rotação. Fonte: `config/twin_params.json` (`"placeholder": true`),
  vereditos em `eval_twin_vs_rsim_modeA_20260617_0030.md`.
- **rSim como baseline default**: o rSim **não** seta velocidade inicial nem modela
  atraso de transporte — é uma **ameaça nomeada** (vantagem estrutural do twin no
  IC e no dead-time). Mencionar a justiça de IC (warm-up + re-âncora SE(2), modo A).
  Fonte: `phase0_replay/rsim_plant.py` (docstring), `eval_twin_vs_rsim.py`.
- **bins / distribuição**: população = **hold-out (10 eventos)**, é **PRÉVIA**, não
  as 5 partidas nem a operação. Fonte: cabeçalho de `bin_distribution_20260619_000422.md`.
- **bayesopt 9-param**: **NÃO promovido** (overfit no v1; v2 empata mas não supera o
  grey-box por DOF). O modelo robusto é vx/vy v2 + ω placeholder. Fonte:
  `eval_bayesopt_v2_wilcoxon_20260614_2130.csv`.

---

## Figuras (ordem da narrativa)

### 01 — Identificabilidade de ω (ganho × amplitude)
- **Arquivo:** `results/figs/reuniao_20260626/01_identificabilidade_omega_ganho.png`
- **Falar:** "O ganho de ω é plano ≈1,3–1,5 em toda a faixa de comando, **sem
  joelho de zona morta no ω de corpo** — os dados de malha fechada deixam estimar o
  ganho de ω, mas não validam ω como modelo de trajetória livre. Por isso ω fica
  placeholder e o heading é uma limitação caracterizada, não um descuido."
- **Fonte dos números:** `results/diag_omega_gain_by_band_20260613_2239.csv`
  (platô ≈1,35; pool 7405 amostras — ver `docs/RELATORIO_TECNICO_DESENVOLVIMENTO.md` §6, Ev. A).
- **Nota:** a figura de **fit hold-out de vx/vy** (overlay identificado×medido) está
  **FALTANDO** no repo — não há figura dedicada. Os números de fit (vx 86,7% /
  vy 87,1% em hold-out) vivem em texto (`RELATORIO_TECNICO` §"Re-identificação …",
  `results/CHANGELOG.md` 2026-06-14 10:24) e a validação SE(2) do vx/vy
  identificado vs placeholder está em `results/eval_vx_v2_se2_20260614_1024.csv` e
  `results/eval_vy_v2_se2_20260614_1028.csv`. Gerar o overlay de fit exigiria
  re-rodar a identificação (fora do escopo "não recompute"). **[A VERIFICAR: fit % não tem CSV próprio.]**

### 02 — Distribuição de bins (hold-out)
- **Arquivo:** `results/figs/reuniao_20260626/02_distribuicao_bins.png`
- **Falar:** "No hold-out, **99,6% das janelas são translação-dominada** (264 de
  265); 1 janela rot, 0 misto. A tarefa que validamos é essencialmente translação —
  é o que justifica focar o veredito no bin de translação e não precisar de contato."
- **Fonte dos números:** `results/bin_distribution_20260619_000422.csv`
  (trans 264 / 0,9962; rot 1 / 0,0038; TODOS 265). É **PRÉVIA** (hold-out, não as 5 partidas).

### 03 — Gate modo A, bin translação (e_pos e e_ang)
- **Arquivo:** `results/figs/reuniao_20260626/03_gate_trans_modoA_epos_eang.png`
- **Falar:** "Gate twin vs rSim (ODE), **modo A** (warm-up Lw=15 + re-âncora SE(2)),
  bin de translação: o twin tem **e_pos menor em todos os horizontes**, veredito
  **GO**. Em h=0,4 s (h_ref) o gap é **+0,093 m**, p=4,4e-11, effect +0,92,
  N_indep=49." (A figura traz dois painéis: e_pos à esquerda, e_ang à direita.)
- **Fonte dos números:** `results/eval_twin_vs_rsim_modeA_20260617_0030.md`
  (seção "trans-dominado" e tabela de vereditos: GO, gap@h_ref +0,0930, p 4,38e-11, effect +0,922).

### 04 — Gate modo A, bin rotação (heading / limitação de ω)
- **Arquivo:** `results/figs/reuniao_20260626/04_gate_rot_modoA_heading.png`
- **Falar:** "No bin de rotação o veredito é **INDETERMINADO (ω placeholder)** —
  N_indep=0 (1 só janela), sem inferência possível. É aqui que a limitação de
  heading/ω aparece explicitamente; não afirmamos fidelidade rotacional."
- **Fonte dos números:** `results/eval_twin_vs_rsim_modeA_20260617_0030.md`
  (seção "rot-dominado", N total=1 indep=0; veredito INDETERMINADO).

### 05 — Overlays de percurso (grid de eventos)
- **Arquivo:** `results/figs/reuniao_20260626/05_overlay_percurso_grid.png`
- **Falar:** "Trajetórias reais (preto) vs twin (azul) vs rSim (vermelho) em
  eventos do hold-out: o twin acompanha a referência de perto em translação;
  desvios crescem onde há rotação."
- **Fonte:** gerado por `phase0_replay/percurso_completo.py` (overlays, não
  recomputam o gate). Sem CSV numérico próprio — leitura qualitativa.

### 05b — Overlays de percurso (Square)
- **Arquivo:** `results/figs/reuniao_20260626/05b_overlay_percurso_square.png`
- **Falar:** "Mesma comparação no conjunto **Square** (12 eventos), padrão com mais
  curvas/cantos — útil para mostrar onde a deriva de heading domina."
- **Fonte:** `phase0_replay/percurso_square.py` (overlays).
- **Nota:** `square_01_01` tem grade irregular (registrado no `CHANGELOG`); leitura qualitativa.

### 06 — Histograma do gap por janela @ h=1.0 s (bin translação)
- **Arquivo:** `results/figs/reuniao_20260626/06_gap_hist_h1s_trans.png`
- **Falar:** "Distribuição honesta do gap (e_pos rSim − e_pos twin) por janela em
  h=1,0 s, bin translação, sem cherry-pick: **mediana +13,3 cm**, **twin melhor em
  85,6% das janelas** (226/264); o rSim vence em 38 janelas. Confirma que o ganho é
  da população, não de casos selecionados."
- **Fonte dos números:** `results/window_errors_20260619_000422.csv`
  (N=264 trans; mediana `gap_1.0s_m`=0,1335 m; fração gap>0 = 85,6%; gap<0 em 38).
- **Nota:** a figura embute a estatística; os valores acima foram recomputados do
  CSV e batem com o rótulo da figura.

### 06b — Overlays representativos (mediano / melhor / pior caso)
- **Arquivo:** `results/figs/reuniao_20260626/06b_overlays_representativos.png`
- **Falar:** "Casos mediano, melhor e pior do twin (ranqueados por gap@1.0s), bin
  translação, sem cherry-pick — mostra a forma do erro inclusive no pior caso."
- **Fonte:** `phase0_replay/holdout_report.py` (mesmo run do histograma,
  `window_errors_20260619_000422.csv`).

### 07 — bayesopt v2 (9 params) — RMSE SE(2) por horizonte
- **Arquivo:** `results/figs/reuniao_20260626/07_bayesopt_v2_horizons.png`
- **Falar:** "Calibração conjunta dos 9 params via bayesopt (proxy analítico no
  loop, treino amplo de 18 eventos): **bate a cinemática ideal com folga** (pool
  −0,098 m, p=7,6e-10) mas **empata e não supera** o grey-box vx/vy v2 (pool
  **+0,0041 m, pior**, p=0,040). Veredito: **NÃO promovido**; o modelo robusto
  segue grey-box por DOF + ω placeholder."
- **Fonte dos números:** `results/eval_bayesopt_v2_wilcoxon_20260614_2130.csv`
  (linha pool/NaN: `dlt_bo_vxvy`=+0,00414 m, p=0,0402; `dlt_bo_ideal`=−0,0979 m, p=7,56e-10).

### 07b — bayesopt v2 — ARD (sensibilidade por parâmetro)
- **Arquivo:** `results/figs/reuniao_20260626/07b_bayesopt_v2_ard.png`
- **Falar:** "A análise ARD mostra o custo dominado pelos params de **translação**;
  os de ω ficam no meio/fim — coerente com a tarefa translação-dominada e com a
  baixa identificabilidade de ω."
- **Fonte dos números:** `docs/RELATORIO_TECNICO_DESENVOLVIMENTO.md` §"bayesopt v2"
  (ranking ARD: Kvx 0,26; Tdvx 0,24; Kvy 0,22; … Kw 0,18; τw 0,09).
  **[A VERIFICAR: o ranking ARD está no relatório/figura, sem CSV dedicado em results/.]**

---

## Resumo: o que existia vs o que foi gerado

**Já existia (reusado, sem recomputar):**
- Gate modo A: `rsim_twin_{all,trans,rot}_20260617_0030.png` (mode A confirmado em `eval_twin_vs_rsim_modeA_20260617_0030.md`).
- Distribuição de bins (barras): `bins_20260619_000422.png` + `bin_distribution_20260619_000422.{md,csv}`.
- **Histograma do gap** @1.0 s: `gap_dist_20260619_000422.png` (já existia; não foi preciso gerar).
- `window_errors_20260619_000422.csv`, overlays representativos e contact-sheet.
- Overlays de percurso (grid + Square): `percurso_completo_grid_*`, `percurso_completo_grid_square_*`.
- bayesopt 9-param: `F4_bayesopt_v2_horizons_*`, `F7_bayesopt_v2_ard_*` (+ v1: F5/F6/F7).
- Identificabilidade de ω: `diag_omega_gain_amplitude_20260613_2239.png`.

**Gerado nesta tarefa:**
- Nenhuma figura nova: os dois itens candidatos a gerar (histograma do gap e barras
  de bins) **já existiam** com os mesmos dados (run `holdout_report.py`,
  `20260619_000422`). Apenas **coletei e renomeei** o conjunto em
  `results/figs/reuniao_20260626/` e escrevi este índice.

**FALTANDO:**
- Figura de **fit hold-out de vx/vy** (overlay identificado×medido): não existe no
  repo; gerá-la exigiria re-rodar a identificação. Números disponíveis em texto/CSV
  de validação (ver item 01).

**[A VERIFICAR]:**
- Fit % de vx/vy (86,7% / 87,1%) não tem CSV próprio (só texto/CHANGELOG).
- Ranking ARD do bayesopt v2 não tem CSV dedicado (só relatório/figura).
</content>
