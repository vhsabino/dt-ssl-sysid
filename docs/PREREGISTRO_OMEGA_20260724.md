# Pré-registro — Identificação FOPTD do DOF ω (dataset dedicado de rotação pura)

**Gravado em:** 2026-07-24, ANTES de rodar qualquer estimação. Os critérios abaixo
são fixados agora e não serão ajustados depois de ver o resultado. Este arquivo é
a defesa metodológica da amostra pequena (6 eventos no regime linear).

## Contexto
- Resultado destina-se ao artigo SBR (deadline 15/08/2026).
- Tentativas anteriores de identificar ω (malha fechada, logs de competição):
  Tentativa 1 (`identify_omega_from_splits.m`, shoot_to_goal): K=1,353 τ=0,0354
  Td=0,1058, fit_val 52,6% — NÃO promovido. Etapa C (`identify_omega_v3_linear.m`,
  regime alto |cmd_ω|>0,3): K=1,307 τ=0,0222 Td=0,1179 — reprova (i) Ljung-Box e
  (iii) SE(2), NÃO promovido (`docs/RELATORIO_TECNICO_DESENVOLVIMENTO.md` §6).
- Esta sessão usa o dataset DEDICADO de rotação pura (malha aberta, vx=vy=0,
  escada de amplitudes), recebido e padronizado em 2026-07-24
  (`data/extracted/2026-05-18_19-2-15/splits/rotate/rotate_01_01..10`,
  `results/qc_rotate_20260724_125828.md`).

## Regra de comparabilidade
Toda escolha metodológica espelha `automation/identify_trans_dof.m` (vx/vy,
PROMOVIDO): mesma estrutura P1D, mesmo filtro (Savitzky-Golay win=7 ordem=2),
mesma grade (Ts=1/60, reamostrada por `interp1` a partir do parquet nativo),
mesmo protocolo sem detrend, mesma ferramenta (`procest`). Desvios são
justificados abaixo, item a item.

## Dados (fixado)
- **Regime linear (6 eventos):** ±1, ±2,5, ±5 rad/s.
  **TREINO** = `rotate_01_05` (+1), `rotate_01_08` (−2,5), `rotate_01_09` (+5),
  `rotate_01_10` (−5).
  **HOLD-OUT** = `rotate_01_06` (−1), `rotate_01_07` (+2,5).
  Split idêntico ao já gravado em `metadata.json` de cada evento (sessão D9,
  2026-07-24) — NÃO é uma nova randomização; é a atribuição literal por
  amplitude já registrada (`config/robot_geometry.json`, CHANGELOG D9).
- **Zona morta (4 eventos):** ±0,25, ±0,5 rad/s — EXCLUÍDOS do fit linear
  (não entram em treino nem hold-out); usados só na Etapa 4.
- **u** = `move_w` de `commands.parquet` (ZOH via `interp1(...,'previous',0)`),
  já em corpo/SI, sem rotação/escala — idêntico a `identify_trans_dof.m`.
- **y** = ω medido = `gradient(sgolayfilt(unwrap(position_w), 2, 7)) / Ts`,
  calculado na grade UNIFORME Ts=1/60 obtida por `interp1` a partir de
  `processed_robots.parquet` — idêntico ao padrão de
  `identify_omega_v3_linear.m::load_uy` e ao `load_uy_trans` de vx/vy (mesma
  ordem de operações: reamostra para 60 Hz primeiro, filtra depois).
- **SEM detrend** — âncora o ganho pelo degrau do comando, igual vx/vy
  (`identify_trans_dof.m` comentário: "SEM detrend (ancora o ganho pelo swing
  do comando)").
- 1 experimento por evento, `iddata` multi-experimento via `merge()` para o
  conjunto de treino — idêntico a vx/vy.
- Seed 42 (bookkeeping/reprodutibilidade; a atribuição treino/holdout aqui é
  literal, não passa por `randperm`, então o seed não afeta o resultado, mas
  é registrado por convenção do projeto).

### Desvio D-preregistro-1 (declarado): fonte da janela SG
`identify_trans_dof.m`/`identify_omega_v3_linear.m` aplicam o Savitzky-Golay
DEPOIS de reamostrar para Ts=1/60 (60 Hz), não na grade nativa da visão
(~73 Hz). Esta sessão segue a MESMA ordem (reamostra→filtra) por
comparabilidade. Isso significa que a duração da janela SG em tempo real é
7/60 ≈ 116,7 ms (não ~96 ms, que corresponderia a filtrar a 73 Hz nativos
antes de reamostrar). A análise de banda passante da Etapa 1 será feita para
fs=60 Hz, consistente com o que o filtro efetivamente vê nesta metodologia.

## Critérios de aprovação (FIXADOS — não mudam depois de ver o resultado)

**(i) Faixas físicas** (idêntico a vx/vy e ao critério original do projeto):
K_ω ∈ [0,5; 2,0], τ_ω ∈ [0,02; 0,5] s, Td_ω ≤ 0,15 s. GATE (deve passar).

**(ii) Limiar de fit no hold-out:** fit médio no hold-out ≥ 60% — o critério
ORIGINAL do projeto para ω (CLAUDE.md, anterior à relaxação da Etapa C, que
só foi necessária porque os dados de malha fechada não sustentavam nem esse
patamar). vx/vy nunca precisaram de relaxação (86,7%/87,1% em hold-out,
folgadamente acima de 60%) — reinstalar 60% aqui é a escolha mais comparável
com vx/vy, agora que os dados são de malha aberta dedicada. Métrica: `fit`
do `compare()` do System Identification Toolbox (normalized RMSE fit %),
reportado por evento de hold-out e como média — mesma métrica/relato de
`identify_trans_dof.m`. GATE (deve passar).

**(iii) Gate SE(2) multi-horizonte vs placeholder:** Wilcoxon pareado p<0,05
em TODOS os horizontes h∈{0,5;1;2;2,5;4} s, candidato melhor que o
placeholder atual (K=1, τ=0,1, Td=0), nos eventos ricos em rotação
(shoot_to_goal, mesma população da campanha salva
`results/traj_eval_campaign_20260611_2238.mat`) — reusa
`automation/eval_omega_v3_se2.m` sem modificação, só trocando o candidato.
GATE (deve passar em todos os horizontes, mesmo critério usado para reprovar
a Etapa C).

**(iv) Ljung-Box:** reportado (resíduos do procest, `lbqtest`) COM o caveat
já documentado para a Etapa C: a saída é uma derivada suavizada por sgolay
do heading da visão, portanto o ruído é colorido por construção, e N grande
tende a rejeitar H0 mesmo com o ganho correto — **não é gate**, é
informativo/diagnóstico.

**Promoção:** SE (i) E (ii) E (iii) passarem → promove para
`config/twin_params.json` (placeholder:false) e `models/`. SE qualquer um
falhar → NÃO promove; documenta como resultado negativo (mais forte que os
anteriores, por vir de dado dedicado).

## Itens adicionais a reportar (não são gates, são rigor metodológico)
- Intervalos de confiança dos 3 parâmetros (`procest`/`getcov` ou
  equivalente) e matriz de correlação; sinalizar como limitação de
  identificabilidade se |ρ(τ,Td)| > 0,8.
- Td em segundos e em passos de Ts (Td/0,0167).
- Convenção de discretização (ZOH exato vs Euler) e conferência com o que o
  simulador (`parameter_estimation_model_pid_v3`) efetivamente executa.
- Frequência de corte efetiva do filtro SG (win=7, ordem=2, fs=60 Hz) e
  confirmação de fase zero.
- Zona morta (Etapa 4): limiar reportado como INTERVALO 0,58–0,60 rad/s
  (nunca ponto), evidência de PWM, fração de comandos mascarados nos logs
  de competição recalculada com o limiar novo.

## Compromisso
Depois deste arquivo salvo, a sequência ETAPA 1→6 roda sem reabrir estas
decisões. Qualquer desvio necessário durante a execução (ex.: dado
insuficiente, erro numérico) será registrado explicitamente no relatório
final como desvio do pré-registro, não como edição silenciosa deste
documento.
