# Pré-registro — C4: plausibilidade da sessão em malha fechada (estratégia real × gêmeo) vs logs de competição

**Gravado em:** 2026-09-08, ANTES de rodar `dtssl analysis run closed_loop_stats`. Os critérios abaixo
são fixados agora, para as **distribuições completas**, e não serão ajustados depois de ver o
resultado. Sem seeds (tudo determinístico).

## Contexto e o que já foi visto (declaração de peeking)

- Victor gravou uma sessão em malha fechada da estratégia real do RobôCIn (`ssl-unification`) jogando
  contra o gêmeo `fopdt` (`dtssl serve --record`): `results/sessao_01/{commands,processed_robots}.parquet`
  no contrato dos logs (6 robôs, ids 0–5, 220 s, 60 Hz; o robô 0 comporta-se como goleiro, ~25 % parado).
- `session_report` (`src/dtssl/analysis/session_report.py`) JÁ mostrou, sobre as linhas brutas: |v_cmd|
  mediana 0,484 m/s (p90 1,451), |w_cmd| mediana 0,206 rad/s (p90 1,462), |w_cmd| < 0,58 rad/s em 76,4 %
  vs 76,5 % nos 18 eventos `shoot_to_goal`, parado 14,7 % vs 4,0 %. **Essas medianas foram vistas antes
  deste documento**; nenhum dos critérios P1–P5 abaixo foi calculado antes. Os limiares são fixados
  a priori para as distribuições completas (não só medianas), sobre uma grade comum de 60 Hz (abaixo).

## Pergunta

*O gêmeo produz jogo parecido com o de competição?* — i.e., quando a estratégia real fecha a malha
sobre o gêmeo, os **comandos** que ela emite têm distribuições comparáveis às dos logs reais de
competição. Isto testa o par (estratégia + gêmeo), não a fidelidade do gêmeo a um robô isolado.

## Dados

- **Sessão** (`sessions="results/sessao_01"`; várias sessões separadas por vírgula são agrupadas e
  também reportadas uma a uma). **Jogadores de campo** = todos os robôs da sessão exceto o de maior
  fração parada (|v| < 0,05 m/s e |w| < 0,1 rad/s), que é reportado à parte (o "goleiro").
- **Competição** = os eventos rotulados do dataset `2026-05-18_19-2-15` que existem localmente
  (`C.list_events`, `C.read_event_csv`). **Pool de competição (critérios) = os 46 eventos de jogo**
  (`front_to_back` 4, `side_to_side` 13, `shoot_to_goal` 18, `square` 11) — os mesmos 46 splits do
  artigo. **Desvio declarado em relação ao brief (56 eventos):** `rotate` (10 eventos) é a coleta
  dedicada de rotação pura em malha aberta com comandos constantes escritos à mão, não jogo da
  estratégia; entra só na tabela descritiva por rótulo.
- **Ressalva de seleção (declarada):** os eventos de competição são **segmentos rotulados por manobra**
  (selecionados por conterem movimento: parado 4 %), não jogo contínuo; a sessão é jogo contínuo de
  220 s (parado 9–16 % nos jogadores de campo). Diferenças na massa perto de zero são esperadas por
  construção e são reportadas, não corrigidas (os critérios valem para as distribuições completas).
  Descritivamente reporta-se também a comparação sem as amostras paradas.
- **Grade comum:** todas as estatísticas de comando são calculadas na grade uniforme de 60 Hz (ZOH,
  `interp_previous` do loader, grade `arange(t0, t_fim, 1/60)`), tanto para a sessão (nativa) quanto
  para a competição (comandos logados em rajadas de 2–10 ms) — ponderação uniforme no tempo. Os
  números do `session_report` (linhas brutas) são repetidos descritivamente para continuidade.
- **Lado medido** (descritivo, não critério): |v_meas| de `velocity_x/y` (mm/s → m/s) do
  `processed_robots` — na competição é o robô real (visão), na sessão é o gêmeo — e a razão de
  rastreamento `mediana(|v_meas|)/mediana(|v_cmd|)`.

## Critérios (FIXADOS; jogadores de campo da sessão vs pool de competição de 46 eventos)

- **P1** Distância de Wasserstein-1 (`scipy.stats.wasserstein_distance`) entre as distribuições de
  |v_cmd| ≤ 0,20 m/s E entre as de |w_cmd| ≤ 0,20 rad/s.
- **P2** Fração de amostras com |w_cmd| < 0,58 rad/s (equivalente de corpo da zona morta por roda de
  1,567 rad/s): diferença sessão − competição dentro de ±10 pontos percentuais.
- **P3** Fração de saturação |v_cmd| > 2,9 m/s: diferença dentro de ±2 pontos percentuais.
- **P4** Medianas por janela (sessão cortada em janelas de 10 s por robô de campo; janelas com menos
  de metade das amostras esperadas são descartadas; ~110 janelas) vs medianas por evento (46):
  Mann-Whitney bilateral (`scipy.stats.mannwhitneyu`) p > 0,05 OU |δ de Cliff| ≤ 0,33 — para a
  mediana de |v| E para a de |w| (as duas têm de passar).
- **P5** Rugosidade do comando: mediana de |Δv_cmd| por tick de 60 Hz (norma da diferença do vetor
  (vx, vy) entre ticks consecutivos, por robô/evento, agrupada) da sessão dentro de um fator 2 da
  competição (razão em [0,5; 2]). Salvaguarda técnica declarada: se uma das medianas for 0 (comandos
  repetidos), o critério é avaliado sobre a média de |Δv_cmd|, e isso é dito no artefato.

**Veredito** = número de critérios satisfeitos (0–5). **Plausível** ≥ 4; **parcial** = 3;
**não plausível** ≤ 2 — significaria que a estratégia, fechando a malha sobre o gêmeo, emite
comandos com amplitude/velocidade angular/saturação/rugosidade fora do que emite contra o robô real,
ou seja, o gêmeo induz um regime de jogo diferente. Também reportados (descritivos): KS bilateral
(`ks_2samp`, estatística e p) de |v| e |w|; quantis p10/25/50/75/90/99 e máximo; fração parada;
frações da zona morta por roda (`apply_body_deadzone`, 1,567 rad/s: comando alterado / zerado);
|Δw| por tick; ticks por minuto com chute reto/chip armados; tudo por robô, por sessão e por rótulo.

## Artefatos

`results/closed_loop_stats_<carimbo>.md` (+ `.json` com tudo) e UMA figura
`results/figs/closed_loop_stats_<carimbo>.png` (ECDF de |v_cmd| e |w_cmd|, sessão vs competição,
linha da zona morta em 0,58 rad/s). Console ASCII.

## Compromisso

Depois deste arquivo salvo, o módulo roda sem reabrir estas decisões; desvios necessários são
registrados no artefato como desvio do pré-registro.
