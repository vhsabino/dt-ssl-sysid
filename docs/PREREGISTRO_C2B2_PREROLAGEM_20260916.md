# Pré-registro: C2b2, pré-rolagem no replay via protocolo (grSim e ER-Force sem a desvantagem da condição inicial)

**Gravado em:** 2026-09-16, ANTES de qualquer execução contra grSim ou ER-Force com pré-rolagem (só o
auto-teste contra `dtssl serve` foi rodado, na nuvem). Os critérios abaixo ficam fixados agora e não serão
ajustados depois de ver o resultado. Código: `src/dtssl/sim/preroll.py`, `ProtocolPlant(pre_roll=...)` em
`src/dtssl/sim/protocol_plant.py`, opção `preroll` de `dtssl analysis run protocol_holdout`; script
`tools/external_sims/run_protocol_holdout.sh --delay none --preroll 0.5`. O resultado de 10/09
(`results/protocol_holdout_20260910_0211`) não é reexecutado nem sobrescrito: este é um experimento novo,
com carimbo novo e entrada própria no `results/CHANGELOG.md`.

## Contexto e o que já foi visto (declaração de peeking)

- C2b (`results/protocol_holdout_20260910_0211.md`, `results/CHANGELOG.md` de 2026-09-10): `e_pos` mediano
  das janelas em `h_ref = 0,4 s`, bin translacional: gêmeo 0,0388 m; `fopdt_v0=0` 0,1137; `erforce` 0,0881;
  `erforce+delay` 0,0555; `grsim` 0,2389; `grsim+delay` 0,2335. H1 corroborada nos dois simuladores, H2 parcial
  (o atraso não reduz o erro do grSim), H3 corroborada: mesmo com os estados zerados em t0 o gêmeo vence o
  grSim, e a condição inicial explica 37 % do gap do grSim (o resto é física e atuação).
- Lido no código-fonte dos simuladores (10/09): o grSim reinicia o robô no `TeleportRobot` e converte a
  velocidade em setpoint dos motores sob limite de aceleração, então toda janela parte do repouso; o ER-Force
  aplica a velocidade linear e perde a de guinada (`teleport_omega=false`).
- O instrumento novo: em vez de impor a condição inicial pelo teleporte, o robô é teleportado P amostras antes
  de t0 e conduzido pelo prefixo real de comandos gravados; em t0 o simulador está no estado que a SUA dinâmica
  produziu, e a trajetória simulada é re-ancorada em SE(2) na pose real de t0 (a mesma re-ancoragem que a
  métrica já assume para toda planta). Auto-teste (`tests/test_protocol_plant.py`): `dtssl serve` (fopdt,
  Td = 0) + `ProtocolPlant(pre_roll=0,5)` reproduz a referência em processo `PreRollPlant(AnalyticFOPDTPlant)`
  com erro máximo por janela abaixo de 3 mm (tolerância do teste no Linux; medido na nuvem em 16/09: 1,9 mm,
  contra 0,2 mm do caminho sem pré-rolagem; a diferença vem da estimativa de `tau0` no teleporte, que agora
  acontece com o robô ainda longe da condição de t0).
- Observado no teste com evento sintético gerado pelo próprio gêmeo: o gêmeo conduzido pelo prefixo chega a
  t0 mais perto do seu estado interno verdadeiro do que quando o harness impõe a velocidade derivada da
  posição. Isso é uma propriedade do teste, não um resultado, e motiva a hipótese de controle H4' abaixo.
- **Nenhum número de grSim ou ER-Force com pré-rolagem foi visto.**

## Pergunta

*Quanto do gap dos simuladores da liga em relação ao gêmeo era a desvantagem da condição inicial que o
protocolo não deixava impor, e o gêmeo continua vencendo os simuladores quando essa desvantagem é removida?*

## Desenho (FIXADO)

- **Janelas e métrica:** as mesmas do C2b (`config/holdout_events.json`, 10 eventos, 265 janelas, stride 15,
  H_max 90, `config/metrics.json`), `e_pos`/`e_ang` re-ancorados SE(2), bin translacional, `h_ref = 24`
  amostras (0,4 s). Referência = `AnalyticFOPDTPlant` com o θ oficial, inalterado. A grade de janelas não
  muda: o `lookback` das variantes com pré-rolagem sobe de 15 para 30 amostras só para expor o prefixo
  (`rollout_segment` limita o prefixo por `min(t0, lookback)`; a primeira janela admissível é a mesma).
- **Pré-rolagem:** `pre_roll = 0,5 s` (P = 30 amostras a 60 Hz; de 4 a 7 constantes de tempo do θ oficial).
  Janelas cujo prefixo gravado é mais curto (as primeiras de cada evento) usam o que existe e são contadas
  (`preroll_short`). Pose do teleporte = pose real de t0 retroextrapolada em linha reta pela velocidade de
  mundo de t0 durante P·dt; velocidade do teleporte = velocidade de corpo pedida pelo primeiro comando do
  prefixo (o que o simulador faz com ela é problema dele, como no C2b). Prefixo e janela são transmitidos numa
  única sequência a 60 Hz de relógio de parede; a âncora continua sendo o primeiro quadro em que o teleporte
  aparece; as poses da janela são interpoladas em `P·dt + h·dt` e re-ancoradas na pose real de t0
  (`dtssl.sim.preroll.reanchor_se2`).
- **Variantes:** `grsim`, `grsim+preroll`, `erforce`, `erforce+preroll` (`delay=none`, `preroll=0.5`,
  `repeat=1`), rodadas na mesma sessão para que a comparação cru × pré-rolagem não dependa de diferenças de
  máquina entre noites. Coluna de controle `fopdt+preroll` (o gêmeo submetido ao mesmo procedimento) ao lado
  de `fopdt` e `fopdt_v0=0`. A combinação `+delay+preroll` é secundária: só se houver tempo, em execução
  separada (`--delay theta --preroll 0.5 --preroll-only`), reportada descritivamente.
- **Simuladores e endpoints:** os mesmos builds e o mesmo `config/external_sims.json` do C2b (grSim `fe2bd29`,
  ER-Force `38563d1`, conforme o CHANGELOG de 2026-09-10); nenhuma sintonia.
- **Janelas perdidas:** teleporte não visto (`anchor_failures`), sem visão em torno de t0 depois da pré-rolagem
  (`reanchor_failures`) ou cobertura insuficiente (`short_windows`) valem NaN, são excluídas das medianas e
  contadas.

## Hipóteses e critérios (FIXADOS; por evento, n = 10, `h_ref = 0,4 s`)

- **H1' (grSim: a condição inicial era parte do gap):** a mediana por evento de `e_pos` de `grsim+preroll` é
  ≥ 25 % menor que a de `grsim` na mesma sessão (o `fopdt_v0=0` do C2b prevê ~31 % se a pré-rolagem remover a
  desvantagem inteira). Corroborada se ≥ 25 %; parcial entre 10 % e 25 %; falsificada se < 10 % ou se piorar.
- **H2' (ER-Force: efeito menor, só a guinada):** `erforce+preroll` reduz a mediana por evento de `e_pos` em
  ≥ 10 % em relação a `erforce`. Falsificada se a redução for < 10 %; se piorar em mais de 5 %, a pré-rolagem
  está interagindo com a lógica de parada do ER-Force (o robô para 0,1 s depois do último comando) e isso será
  dito assim.
- **H3' (o gêmeo continua vencendo sem a desvantagem):** o gêmeo (`fopdt`) vence `grsim+preroll` e
  `erforce+preroll` em ≥ 8/10 eventos, Wilcoxon unilateral pareado (gêmeo < simulador) p < 0,05 e
  rank-biserial ≥ +0,5, para cada um. Corroborada se valer para os dois; parcial se para um; falsificada se
  para nenhum. É a hipótese que importa para a tese: a conclusão do C2b não pode depender da desvantagem.
- **H4' (controle do procedimento):** a mediana de janelas de `fopdt+preroll` em `h_ref` difere da de `fopdt`
  em no máximo 20 % (relativo; 0,0388 m → até 0,0078 m). Se passar, `fopdt` continua sendo a referência das
  variantes `+preroll`. Se falhar, a pré-rolagem altera o próprio gêmeo e H3' será reavaliada também contra
  `fopdt+preroll`, com as duas leituras reportadas.
- **V' (validade do instrumento, pré-condição de H1' a H4'):** os quatro critérios V do C2b (janelas perdidas
  ≤ 5 %, agora incluindo `reanchor_failures`; jitter médio de envio < 2 ms com ≤ 1 % dos envios atrasados
  > 10 ms; espalhamento da latência do teleporte < 1 quadro; `tau0` estimado em ≥ 50 % das janelas) e, para as
  variantes `+preroll`, `preroll_short` ≤ 10 % das janelas. Se V' falhar numa variante, os números dela são
  reportados como inválidos e a causa vai para o artefato.

Reportados descritivamente (sem critério): `e_ang` por horizonte; os seis horizontes de `e_pos`;
`grsim+preroll` contra `fopdt_v0=0` (a comparação inversa: o gêmeo sem condição inicial contra o grSim com
condição inicial); diagnóstico do replay (P mediano, `preroll_short`, `reanchor_failures`); custo; a
comparação com C2a (`mujoco-rollers` 0,0729 m, `mujoco-rollers-delay` 0,0477 m) e com o rSim do artigo
(0,129 m), lembrando que esses foram avaliados em processo com a velocidade inicial imposta.

## Limitações declaradas

- No grSim o `tau0` do teleporte continua não identificável (o robô está em repouso no teleporte; a estimativa
  satura em 0), como no C2b. Com a re-ancoragem em t0, um erro de `tau0` vira um deslocamento de tempo comum
  a toda a janela (efeito de segunda ordem sobre `e_pos`), e é o mesmo nas variantes cru e `+preroll`.
- A pose do teleporte é retroextrapolada em linha reta: só importa para o robô ficar dentro do campo e para a
  âncora; a trajetória é re-ancorada em t0 de qualquer forma.
- A pré-rolagem custa 0,5 s por janela: cerca de 2 min a mais por variante.

## Artefatos

`results/protocol_holdout_<carimbo>.{md,json,csv}` por simulador + um conjunto (`from_cache`, que mescla
também as variantes cruas da mesma sessão); `results/_cache_protocol_<variante>_<carimbo>.npz` + `.stats.json`
(gitignored; reanálise offline; o `.stats.json` guarda `pre_roll_s`). Console ASCII. Entrada no
`results/CHANGELOG.md` com commits dos simuladores, PC/WSL, tempo de parede e os vereditos de H1' a H4' e V'.

## Compromisso

Depois deste arquivo salvo, o módulo roda sem reabrir estas decisões; desvios necessários são registrados no
artefato e no CHANGELOG como desvio do pré-registro. Se o resultado sugerir um `pre_roll` diferente (mais
longo, ou o prefixo inteiro disponível), isso é um experimento novo, com pré-registro novo.
