# Mapeamento do artigo de periódico: seção, conteúdo, artefato, número, figura e estado

*Escrito em 23/09/2026 pelo chat do artigo (lote 1). Alvo: Digital Engineering (Elsevier), special issue
VSI:DTE_DigiTwin2026, prazo 15/12/2026, extensão do artigo aceito no SBR/LARS 2026 (#34344). Esqueleto
em `latex_journal/` (classe `elsarticle`, `elsarticle-num`). Regra de ouro: nenhum número entra no
manuscrito sem uma entrada em `results/CHANGELOG.md` ou um artefato em `results/` citado pelo nome;
nenhuma referência fora de `latex_journal/refs/references.bib` (cópia de `latex/refs/references.bib`)
ou da lista de incluídos da SLR; nenhum parágrafo copiado do SBR, que é citado como versão preliminar.
Este documento é o mapa de trabalho; o estado de cada lote fica no doc `claude/estado-artigo-journal.md`
do Projeto.*

## 1. Como as tabelas e figuras são geradas

Tudo em `latex_journal/tables/` e `latex_journal/figures/` sai de módulos do `dtssl` que leem os
artefatos de `results/` (nunca o dataset), com o cabeçalho listando as fontes. Não editar à mão.

| Saída | Comando | Fontes lidas |
|---|---|---|
| `tables/tab_journal_identified.tex` | `dtssl analysis run journal_tables --kw tables=identified` | `config/twin_params.json`; CHANGELOG 2026-06-14 10:24 e 2026-07-24 17:35 (fits hold-out 86,7 / 87,1 / 71,1 %); `loo_translational_20260810_1743.md`; `r3_closedloop_omega_fit_20260810_1036.md` |
| `tables/tab_journal_insilico_yaw.tex` | `... tables=insilico_yaw` | `identifiability_insilico_20260907_1552.json` (C1); `identifiability_insilico_mujoco-rollers_v2_20260907_2048.json` e `..._mujoco-rollers-delay_v2_20260907_2044.json` (C1b v2) |
| `tables/tab_journal_baselines.tex` | `... tables=baselines` | `epos_eang_three_models_20260810_1022.md`; `negcontrol_perevent_20260810_1035.md`; `eval_rsim_delay_ablation_20260809_2154.md`; `backends_holdout_20260907_1515.{md,csv}`; `protocol_holdout_20260910_0211.json`, `_20260918_1326.json`, `_20260920_1143.json` |
| `tables/tab_journal_robustness.tex` | `... tables=robustness` | `ablation_orderfree_20260810_1021.md`; `causal_ic_check_20260810_1102.md`; `gate_window_vs_event_20260810_1743.md`; `negcontrol_perevent_20260810_1035.md`; `eval_rsim_delay_ablation_20260809_2154.md`; `loo_translational_20260810_1743.md` |
| `tables/tab_journal_closed_loop.tex` | `... tables=closed_loop` | `closed_loop_stats_20260907_2137.json`; CHANGELOG 2026-09-07 21:37 (leitura post hoc 5/5) |
| `tables/tab_journal_coupling.tex` | `... tables=coupling` | `coupled_mimo_check_20261014_1211.json` (primária), `coupled_mimo_check_control-fopdt_20261014_1211.json` (C-), `coupled_mimo_check_control-mujoco-rollers-delay_20261014_1216.json` (C+); CHANGELOG 2026-10-14 12:11 |
| `figures/fig_journal_identifiability.pdf` | `dtssl fig fig_journal_identifiability` | os três `.json` de C1 e C1b v2 acima; `r3_closedloop_omega_fit_20260810_1036.md`; `config/twin_params.json` |
| `figures/fig_journal_league_sims.pdf` | `dtssl fig fig_journal_league_sims` | `protocol_holdout_20260910_0211.json`, `_20260918_1326.json`, `_20260920_1143.json` |
| `figures/fig_journal_closed_loop.pdf` | `dtssl fig fig_journal_closed_loop` (`--kw source=data` reconstrói as ECDFs exatas com o dataset; o padrão desenha os quantis do artefato) | `closed_loop_stats_20260907_2137.json` |

Testes sem dataset: `tests/test_journal_artifacts.py` (os números que as tabelas usam, conferidos contra
os artefatos) e `tests/test_coupled_mimo_check.py` (MIMO, sintético). Parser e leitores:
`src/dtssl/analysis/journal_artifacts.py`.

## 2. Seção por seção

Legenda de estado: **pronto** = tabela ou figura gerada e colocada no esqueleto; **fonte pronta** = os
números existem e estão registrados, falta o texto; **pendente** = depende de execução, decisão ou
material que ainda não existe.

### 1 Introduction (`sections/01_introduction.tex`)

- Conteúdo: reality gap nas plataformas de futebol de robôs e nos gêmeos de robôs móveis; a camada de
  planta do gêmeo (comando para movimento); os dados operacionais que a equipe já grava; a pergunta (o
  que esses dados identificam e o que não identificam); contribuições; relação com o SBR.
- Contribuições candidatas (fechar com a orientadora): (1) identificabilidade como propriedade do regime
  de excitação e da realimentação (C1, C1b, r3); (2) mecanismo do viés de yaw: acoplamento translação
  para guinada (C1b e a checagem MIMO); (3) regra de triagem antes do ajuste (`excitation_per_dof`,
  fração de atuação por comando); (4) protocolo de fidelidade observacional pré-registrado, agnóstico ao
  simulador, com condição inicial justa (harness, C2b, C2b2); (5) comparação com física e simuladores
  da liga sob as mesmas janelas e a mesma métrica (C2a, C2b, C2b2); (6) plausibilidade em malha fechada
  (B3, C4).
- Fontes: SBR seção I (reescrever), plano §2 (tese), `references.bib`.
- Obrigatório: "A preliminary version of this work appeared in [SBR]; this article adds ...".
- Estado: pendente (texto do WP4). A entrada `sbr2026preliminary` em `refs/own.bib` é um placeholder
  até o camera-ready ter DOI ou páginas.

### 2 Related work (`sections/02_related_work.tex`)

- Conteúdo: gêmeos de robôs móveis (construção e validação); identificação grey-box para gêmeos;
  identificação em malha fechada; calibração sim-to-real a partir de dados; simuladores da liga e RL.
- Fontes: SBR seção II; `docs/BACKLOG_EXTENSAO_JINT.md` item F; lista de incluídos da SLR quando o
  Victor trouxer (RQ1 e RQ2). Referências já verificadas: as 20 de `references.bib`.
- Lacuna: o ER-Force não tem entrada no `.bib`; citar o simulador exige uma fonte verificada (repositório
  ou artigo) trazida pelo Victor ou pela SLR. Nenhuma referência nova é inventada.
- Estado: pendente (WP4 + SLR).

### 3 Robot, data and instrumentation (`sections/03_robot_data.tex`)

- Conteúdo: o robô (4 rodas omni em 60/135/225/300 graus, R = 0,079601 m, r = 0,029492 m); firmware
  (PI por roda, zona morta por roda 1,567 rad/s, equivalente de corpo 0,58 a 0,60 rad/s); visão SSL a
  60 Hz; logs de competição (46 eventos em 4 rótulos, hold-out congelado de 10 eventos em
  `config/holdout_events.json`); coleta dedicada de rotação em escada (D9); sessão gravada da estratégia
  real contra o gêmeo (B3: 220 s, 6 robôs); cadeia de medição (adaptar a figura de setup do
  camera-ready, com as fotos que o Victor vai fornecer).
- Fontes: `config/robot_geometry.json`, `config/holdout_events.json`, CHANGELOG 2026-07-24 02:12 (D9,
  `rotate`), 2026-06-13 (zona morta do firmware), 2026-09-07 20:59 (B3), `results/session_report_sessao_01_20260907_2059.md`.
- Estado: fonte pronta; texto pendente. A figura de setup depende das fotos (camera-ready).

### 4 Models and estimators (`sections/04_models.tex`)

- Conteúdo: planta FOPDT por DOF de corpo (Eq. do SBR); modelo acoplado de primeira ordem da checagem
  MIMO, `y_i[k] = A_i y_i[k-1] + sum_j B_ij u_j[k-1-M_ij]`; discretização e alinhamento (convenção da
  planta: `m = ceil(Td/dt)`, 5/4/6 amostras); estimadores (P1D por erro de predição no MATLAB para o θ
  promovido; mínimos quadrados separáveis em erro de saída com busca exaustiva de atrasos para a
  checagem MIMO); regra de triagem antes do ajuste (variância explicada pelo comando alinhado: vx 0,959,
  vy 0,936, ω 0,557; fração de atuação por comando de ω, `omega_excitation_analysis_20260807_133917.json`).
- Fontes: `config/twin_params.json`; `docs/PREREGISTRO_MIMO_CHECK_20260923.md`;
  `results/excitation_per_dof_20260810_1022.md`; CHANGELOG 2026-06-14 10:24 e 2026-07-24 17:35.
- Estado: fonte pronta; texto pendente.

### 5 Validation protocol (`sections/05_protocol.tex`)

- Conteúdo: harness free-run (janelas re-ancoradas em SE(2), stride 15, H_max 90, horizontes 0,1 a
  1,5 s, h_ref 0,4 s, bins de movimento; 265 janelas densas, 49 não sobrepostas, 10 eventos); gate
  pré-registrado por janela e unidade de análise por evento; estatística pareada (Wilcoxon unilateral,
  rank-biserial, bootstrap por evento); replay via ssl-simulation-protocol (teleporte, relógio de parede,
  âncora da visão, tau0) e a pré-rolagem de 0,5 s; critérios de validade do instrumento (V e V');
  pré-registros e desvios declarados (C1b v1 mantida e re-registrada como v2; C4 com referência ao pool
  mantida e leitura post hoc declarada). O harness e o servidor aparecem como método, não como
  contribuição de plataforma.
- Fontes: `config/metrics.json`; `docs/PREREGISTRO_*.md` (omega 24/07, C1 e C1b 07/09, C4 08/09, C2b
  10/09, C2b2 16/09, MIMO 23/09); `results/gate_window_vs_event_20260810_1743.md`.
- Estado: fonte pronta; texto pendente.

### 6 Results I: identifiability follows the excitation regime (`sections/06_results_identifiability.tex`)

- Conteúdo: modelo identificado (Tab. `tab:identified`: vx 1,119 / 0,072 / 0,069 s, fit 86,7 %; vy
  1,052 / 0,127 / 0,056 s, 87,1 %; ω 1,002 / 0,083 / 0,089 s, 71,1 % na coleta dedicada; LOO vx
  84,3 ± 2,0 % em 4 dobras, vy 82,8 ± 2,7 % em 13); o ajuste de yaw em malha fechada (K 1,378, τ
  0,043, Td 0,112, fit 44,8 %, não promovido); diluição (ω recebe cerca de 1 % da atuação por roda nos
  logs de competição; 56 % da variância explicada); C1: o gerador linear recupera θ* sempre que há
  excitação (fit % mede SNR, não viés; 10 de 60 células com fit hold-out abaixo de 60 %); C1b v2: o
  gerador físico com acoplamento reproduz a inflação (rollers 1,156 e 1,143; rollers + atraso 1,160
  na célula idealizada e 1,270 com ruído e zona morta, isto é +16,5 % e +27,4 % sobre a referência
  pré-registrada 0,996 do mesmo gerador), o controle sem translação a remove (0,988 / 0,930), a
  rotação dedicada dá 0,996. A diluição de ω vem de `omega_excitation_analysis_20260807_133917.json`:
  razão mediana do yaw sobre a translação na atuação por roda 0,0099 (cerca de 1 %), 94,0 % das
  amostras do pool abaixo do equivalente de corpo da zona morta (77,3 % em `shoot_to_goal`).
- Tabelas e figuras: `tab_journal_identified` (pronto), `tab_journal_insilico_yaw` (pronto),
  `fig_journal_identifiability` (pronto).
- Fontes: CHANGELOG 2026-09-07 15:52 (C1), 20:38 (C1b v1, mantida) e 20:45 (C1b v2);
  `results/r3_closedloop_omega_fit_20260810_1036.md`; `results/loo_translational_20260810_1743.md`.
- Estado: texto pendente.

### 7 Results II: cross-coupling between channels (`sections/07_results_coupling.tex`)

- Conteúdo: o resultado pré-registrado da checagem MIMO (`coupled_mimo_check`): M1 (primária: o modelo
  acoplado melhora o fit hold-out por canal em pelo menos 3 pontos percentuais com contribuição cruzada
  de pelo menos 10 %?), M2 (mecanismo: o ganho direto de yaw estimado com as entradas de translação cai
  em direção a 1,0016?), M3 (uso: o acoplado reduz e_pos no harness com o gate do artigo?), controles
  C- (gerador FOPDT desacoplado, sem acoplamento espúrio) e C+ (gerador `mujoco-rollers-delay`, o
  acoplamento conhecido é recuperado).
- Fontes: `docs/PREREGISTRO_MIMO_CHECK_20260923.md`; artefatos `results/coupled_mimo_check_20261014_1211.{md,json,csv}`
  (primária), `results/coupled_mimo_check_control-fopdt_20261014_1211.*` (C-) e
  `results/coupled_mimo_check_control-mujoco-rollers-delay_20261014_1216.*` (C+); CHANGELOG 2026-10-14 12:11;
  tabela `tables/tab_journal_coupling.tex` (`journal_tables --kw tables=coupling`).
- Resultado (executado em 14/10/2026, os três comandos do §7 do pré-registro, sem alteração): M1 não importa
  (ganho de fit < 1 p.p. em todo DOF, termos cruzados < 6 % do RMS direto); M2 falsificada (G_ww 1,419 → 1,414
  contra 1,0016; premissa reproduzida, +41,7 %); M3 não melhora (6/10, p 0,46); C- OK; C+ com premissa não
  reproduzida (+7,2 %, abaixo dos 10 %), leitura post hoc marcada no CHANGELOG e na seção.
- Estado: rascunho da seção escrito em 14/10 a partir dos artefatos (texto e tabela gerada); revisar a voz e
  decidir se a leitura post hoc do C+ fica na seção ou vai para as limitações.

### 8 Results III: fidelity against physics and league simulators (`sections/08_results_fidelity.tex`)

- Conteúdo: o modelo contra todas as baselines, mesmas janelas e mesma métrica (Tab. `tab:baselines`):
  cinemática ideal 0,1005 por janela / 0,1177 por evento (10/10); rSim stock 0,1293 e rSim + atraso
  casado 0,1822 (o gap alarga); MuJoCo rota a 0,0388 / 0,0421 (embedding do gêmeo, 7/10, p 0,22),
  rota b sem sintonia 0,0729 / 0,0791 (10/10), rota b + atraso 0,0477 / 0,0487 (9/10); grSim teleporte
  cru 0,2389 / 0,2421 / 0,2329 por janela nas sessões de 10/09, 18/09 e 20/09; grSim + atraso 0,2335;
  grSim pré-rolado 0,0996 / 0,0809 (por evento 0,1106 / 0,0975); ER-Force cru 0,0881 / 0,0856 /
  0,0874; ER-Force + atraso 0,0555 (9/10); ER-Force pré-rolado 0,0934 / 0,0940 (por evento 0,1114 nas
  duas). Condição inicial: modelo com estados zerados 0,1137, pré-rolado 0,0406 (+4,5 %). Repetibilidade
  entre sessões: variantes cruas de 10/09 e 20/09 dentro de 2 % por evento (entrada de 20/09); com a
  sessão de 18/09, o grSim cru por janela vai de 0,2329 a 0,2421 (4 %); o grSim pré-rolado dá 0,0996
  contra 0,0809 por janela e 0,1106 contra 0,0975 por evento, a variante menos repetível. Robustez
  (Tab. `tab:robustness`): Shapley τ 55 % /
  Td 43 % / K 2 % de 0,0617 m; velocidade constante 0,1600; v0 causal 0,0468 (gap por evento +0,0706,
  10/10); unidade de análise (janela n = 49: +0,0541, p 1,2e-8, rb 0,633; evento n = 10: +0,0689,
  p 9,8e-4, rb 1,000); controle negativo bayesiano +0,0038 m, 7/10, p 0,042, rb 0,40; heading
  (`epos_eang_three_models`: e_ang do gêmeo 0,0440 contra 0,0668 ideal e 0,0635 rSim em 0,4 s; em 1,5 s
  0,0895 / 0,0953 / 0,0936).
- Baseline sintonizada (C3 ou rSim com parâmetros ajustados): só se a orientadora aprovar (WP3); hoje a
  tabela diz "stock parameters" e "untuned".
- Tabelas e figuras: `tab_journal_baselines` (pronto), `tab_journal_robustness` (pronto),
  `fig_journal_league_sims` (pronto: painel a, e_pos por horizonte das 7 variantes; painel b, medianas
  por evento em h_ref por sessão).
- Fontes: CHANGELOG 2026-09-07 15:15 (C2a), 2026-09-10 02:11 (C2b), 2026-09-18 13:26 (C2b2 sessão 1,
  entrada anexada por este lote), 2026-09-20 11:43 (C2b2 sessão 2) e a linha de correção de 23/09;
  2026-08-09 (ablação rSim + Td); entrada retroativa de 23/09 para os artefatos de 09 a 11/08.
- Lacuna conhecida: o rSim não tem mediana por evento em nenhum artefato (só por janela, run de
  17/06 nunca persistido); a tabela mostra "--". Regenerar exigiria o rSim no PC e uma execução nova
  registrada (fora do lote 1).
- Estado: texto pendente.

### 9 Results IV: closed-loop plausibility (`sections/09_results_closed_loop.tex`)

- Conteúdo: a estratégia real (ssl-unification) jogando contra o gêmeo no WSL2 (sessão B3: 220 s,
  6 robôs, goleiro excluído das estatísticas de campo); round trip recorder para harness ao nível do mm
  (e_pos 0,0000 a 0,0002 m); C4: 2/5 critérios contra o pool de 46 eventos (pré-registrado), 5/5
  contra o rótulo de jogo `shoot_to_goal` (post hoc, declarado: 28 dos 46 eventos do pool são manobras
  roteirizadas); o regime de yaw diluído reaparece (|ω_cmd| abaixo de 0,58 rad/s em 71,8 % das amostras
  na sessão, 90,5 % no pool, 74,5 % no rótulo de jogo); distâncias W1 0,326 / 0,387 (pool) e 0,179 /
  0,127 (jogo); razão mediana |v_meas|/|v_cmd| 0,865 no gêmeo contra 0,944 no robô real (descritivo,
  CHANGELOG 21:37).
- Tabelas e figuras: `tab_journal_closed_loop` (pronto), `fig_journal_closed_loop` (pronto, quantis;
  ECDF exata com `--kw source=data` no PC).
- Fontes: `results/session_report_sessao_01_20260907_2059.md`; `results/closed_loop_stats_20260907_2137.json`;
  CHANGELOG 2026-09-07 20:59 (B3) e 21:37 (C4); `docs/PREREGISTRO_C4_MALHA_FECHADA_20260908.md`.
- Estado: texto pendente.

### 10 Discussion (`sections/10_discussion.tex`)

- Conteúdo: o que o modelo compra (τ e Td, condicionados à velocidade medida; K quase nada);
  identificabilidade como propriedade do dado e da realimentação, não do canal; quando um gêmeo físico é
  necessário (rota b + atraso chega a 0,0477 sem sintonia; o pré-rolado do grSim chega a 0,08 a 0,10);
  a regra de triagem na prática; generalização do protocolo a outros gêmeos (sem prometer RL nem
  Isaac Sim).
- Estado: pendente (WP4).

### 11 Limitations and threats to validity (`sections/11_limitations.tex`)

- Conteúdo: as sete limitações do SBR (amostra de yaw pequena e de uma sessão; um robô e um contexto;
  contraste não single-factor; estimadores closed-loop-aware não tentados; Ljung-Box; constantes
  cinemáticas; rSim sem sintonia); as do camera-ready (desacoplamento, sem saturação, aceleração ou zona
  morta no modelo, slip só pelos parâmetros, envelope dos dados); as novas (instrumento em tempo real;
  tau0 do grSim; ER-Force sem ω no teleporte; repetibilidade da pré-rolagem do grSim entre sessões;
  pré-registros com referência errada mantidos e re-registrados; hold-out 99,6 % translacional; rotação
  não validada em free-run).
- Observação: a versão íntegra de 9 parágrafos das limitações não existe mais em disco nem no git
  (`latex/` só entrou no git em 02/09, commit 6807dd6, já com a versão condensada). Reescrever a partir
  das fontes: `docs/BACKLOG_EXTENSAO_JINT.md` item A, CHANGELOG e artefatos.
- Estado: pendente (WP4).

### 12 Conclusion, availability, CRediT, declarations (`sections/12_conclusion.tex`)

- Availability: repositório público com DOI (WP5; D3 congelado); logs de competição, coleta dedicada e
  sessão B3 via DVC; um `dtssl analysis run <nome>` por número. Declaração de IA generativa exigida pela
  Elsevier. Autoria e CRediT com a orientadora.
- Estado: pendente.

## 3. Discrepâncias encontradas e o que foi feito

1. Sessão de 18/09 do C2b2 sem registro: entrada `2026-09-18 13:26` anexada ao CHANGELOG por este
   lote (números exatos dos `.json`), mais linha de correção da entrada de 20/09 (segunda sessão; H4'
   +4,5 % e piora do ER-Force +11,9 % com os valores completos; vereditos inalterados). Os artefatos
   de 18/09 entram no `git add` sugerido.
2. Artefatos de 09 a 11/08 sem entrada: entrada retroativa única de 23/09 (só registro, nenhuma
   execução). `results/_BROKEN_loo_translational_20260810_1742.md` continua em `results/` no PC apesar
   da entrada de 02/09; nunca citar.
3. `06_limitations.tex` íntegro: irrecuperável (ver seção 11). Fechado.
4. `latex/` do repo é o build de 10/08; a versão aceita foi copiada pelo Victor para
   `paper/sbr2026_accepted/` e o patch do camera-ready está em `paper/sbr2026_camera_ready/`. O
   manuscrito novo vive em `latex_journal/`. Nada em `latex/` foi tocado.
5. Rigor da tese: redigir como "mesmas janelas e mesma métrica; hipóteses pré-registradas para os
   simuladores da liga e para as rotas MuJoCo"; rSim é o motor do rSoccer (derivado do grSim), avaliado
   em processo em 17/06 antes da prática de pré-registro, com v0 imposta.
6. Faixa B do camera-ready: corrigida no `CAMERA_READY_NOTES.md` (B2) para parear as variantes
   certas (grsim+preroll 0,0975 com erforce+preroll 0,1114; o teleporte cru do ER-Force, 0,0995, é a
   baseline otimista).
7. CHANGELOG 2026-09-02 com o placeholder `commit <hash da branch no PC>`: continua sendo o P1 do B2
   do chat do gêmeo; não tocado aqui.
8. Mediana por evento do rSim inexistente (seção 8). Aberto; decisão de regenerar ou não com a
   orientadora (só se C3 for aprovado, porque exigiria o rSim no PC).

## 4. Decisões pendentes (com quem)

| Decisão | Com quem | Bloqueia |
|---|---|---|
| Título do periódico (opção 1 vs opção 2 do plano) e contribuições (seis ou menos) | orientadora | seções 1 e 12 |
| Baseline sintonizada (C3) ou rSim com parâmetros ajustados | orientadora | seção 8, WP3 |
| Faixa B no camera-ready (D1) | orientadora | camera-ready |
| Fonte verificada para o ER-Force; lista de incluídos da SLR | Victor / SLR | seção 2 |
| Autoria, CRediT, declaração de IA, agradecimentos e financiamento | Victor + orientadora | seção 12 |
| Repositório público e DOI (WP5) | Victor | seção 12 |
