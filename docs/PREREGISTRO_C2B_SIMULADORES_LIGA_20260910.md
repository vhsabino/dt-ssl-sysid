# Pré-registro — C2b: simuladores da liga (grSim, ER-Force) no hold-out via ssl-simulation-protocol

**Gravado em:** 2026-09-10, ANTES de qualquer execução contra grSim ou ER-Force (os simuladores ainda não
foram compilados no WSL2 do PC; só o auto-teste contra `dtssl serve` foi rodado). Os critérios abaixo são
fixados agora e não serão ajustados depois de ver o resultado. Módulo: `dtssl analysis run protocol_holdout`
(`src/dtssl/analysis/protocol_holdout.py`); scripts: `tools/external_sims/`.

## Contexto e o que já foi visto (declaração de peeking)

- O artigo compara o gêmeo ao rSim (rc-robosim, ODE) no mesmo hold-out: `e_pos` mediano em `h_ref = 0,4 s`
  gêmeo 0,039 m vs rSim 0,129 m (10/10 eventos, Wilcoxon p ≤ 8,5e-7); rSim + Td identificado fecha parte do
  gap (ablação de atraso, `eval_rsim_delay_ablation`).
- C2a (`results/backends_holdout_20260907_1515.md`) já mostrou, nas mesmas janelas: `mujoco-rollers` (rota b,
  física sem sintonia) 0,0729 m e `mujoco-rollers-delay` 0,0477 m vs gêmeo 0,0388 m; gêmeo vence a rota b
  10/10 (p = 0,001) e a rota b + atraso 9/10 (p = 0,010).
- Auto-teste do replay via protocolo (`tests/test_protocol_plant.py`, `tests/test_protocol_holdout.py`):
  `dtssl serve` (fopdt, Td = 0) + `ProtocolPlant(delay="theta")` reproduz a planta analítica com erro máximo
  ≤ 0,5 mm por janela (H = 90), 0 falhas de âncora — o **instrumento** não introduz erro mensurável.
- Lido no código-fonte (10/09/2026): grSim ignora a velocidade do teleporte (reinicia o robô; toda janela parte
  do repouso); ER-Force aplica a velocidade linear e aplica a de guinada no eixo errado (enviamos 0).
  **Nenhum número de grSim/ER-Force foi visto.**

## Pergunta

*Os simuladores da liga, como saem da caixa, reproduzem o robô RobôCIn melhor ou pior do que o gêmeo
comportamental, nas mesmas janelas e com a mesma métrica?* — e quanto do gap é (i) atraso de transporte
(variante `+delay`) e (ii) a condição inicial que o protocolo não deixa impor (coluna `fopdt_v0=0`).

## Desenho (FIXADO)

- **Janelas e métrica:** o hold-out do artigo (`config/holdout_events.json`, 10 eventos, 265 janelas, stride 15,
  H_max 90, `config/metrics.json`), `e_pos`/`e_ang` re-ancorados SE(2), bin translacional, `h_ref = 24` amostras
  (0,4 s). Referência = `AnalyticFOPDTPlant` com o θ oficial (inalterado).
- **Variantes:** `grsim`, `grsim+delay`, `erforce`, `erforce+delay` (`delay=both`), `repeat = 1` para o
  resultado principal; uma segunda execução (`repeat = 2`) de UM simulador só para reportar repetibilidade
  (|Δe_pos| por janela entre execuções, mediana e p90) — descritivo.
- **Simuladores:** grSim (branch default do `RoboCup-SSL/grSim`, headless, defaults: ODE 60 Hz, visão 60 Hz,
  sem ruído; robô = perfil `.ini` default) e ER-Force `simulator-cli -g 2020B --realism None` (branch default de
  `robotics-erlangen/framework`; Bullet; visão 66,67 Hz, atraso 35 ms; `command_delay` 0). Commits registrados
  no artefato (`tools/external_sims/install_*_wsl.sh` imprime; anotar no CHANGELOG). Sem qualquer sintonia dos
  simuladores ao robô RobôCIn (é o ponto).
- **Endpoints:** `config/external_sims.json` como está neste commit (`multicast_if 0.0.0.0`, `teleport_omega
  false` no ER-Force, `clear_others true`: bola parada num canto, demais robôs removidos).
- **Janelas perdidas:** uma janela cujo teleporte não aparece na visão (`anchor_failures`) ou sem cobertura de
  quadros (`short_windows`) vale NaN, é excluída das medianas e **contada**. Critério de validade do
  instrumento (abaixo) exige poucas.

## Hipóteses e critérios (FIXADOS; por evento, n = 10, `h_ref = 0,4 s`)

- **H1 (gêmeo vs liga sem sintonia):** o gêmeo vence cada simulador cru (`grsim`, `erforce`) em ≥ 8/10
  eventos, com Wilcoxon unilateral pareado (gêmeo < simulador) p < 0,05 e rank-biserial ≥ +0,5.
  Corroborada se valer para os dois simuladores; parcial se para um; falsificada se para nenhum.
- **H2 (atraso explica parte do gap):** `<sim>+delay` reduz a mediana por evento de `e_pos` em relação a
  `<sim>` em ≥ 20 % (relativo) para cada simulador — o análogo do rSim + Td e do `mujoco-rollers-delay`
  (34 % em C2a). Falsificada se a redução for < 20 % ou se `+delay` piorar. (Não se espera que `+delay`
  alcance o gêmeo: o modelo de robô continua sem sintonia.)
- **H3 (a condição inicial não é a história toda):** a mediana de janelas de `fopdt_v0=0` em `h_ref` fica
  **abaixo** da de `grsim` e de `grsim+delay` — i.e., mesmo com a desvantagem de partir do repouso, o FOPDT
  identificado supera a física do grSim; se `fopdt_v0=0` ≥ `grsim+delay`, o gap do grSim é explicado pela
  condição inicial, não pela física, e isso será dito assim.
- **V (validade do instrumento, pré-condição para H1–H3):** janelas perdidas ≤ 5 % (≤ 13 de 265) por
  variante, jitter médio de envio < 2 ms com ≤ 1 % dos envios atrasados > 10 ms (um comando atrasado deixa o
  anterior valendo por mais tempo: o efeito é proporcional à variação entre comandos consecutivos),
  `teleport_latency_spread` < 1 quadro, e `tau0` estimado em ≥ 50 % das janelas. Se V falhar para uma variante, os números dela são reportados como **inválidos**
  (não entram nas hipóteses) e a causa vai para o artefato.

Reportados descritivamente (sem critério): `e_ang` por horizonte; todos os seis horizontes de `e_pos`;
diagnóstico do replay; custo; repetibilidade; a comparação com os números do rSim do artigo (fonte:
`results/CHANGELOG.md`), lembrando que o rSim foi avaliado em processo (sem protocolo, com a velocidade
inicial imposta).

## Artefatos

`results/protocol_holdout_<carimbo>.{md,json,csv}` por simulador + um conjunto (`from_cache`);
`results/_cache_protocol_<variante>_<carimbo>.npz` + `.stats.json` (gitignored; reanálise offline). Console
ASCII. Entrada no `results/CHANGELOG.md` com commits dos simuladores, PC/WSL e tempo de parede.

## Compromisso

Depois deste arquivo salvo, o módulo roda sem reabrir estas decisões; desvios necessários (p.ex. um
simulador que não compila no Ubuntu 26.04, portas, perfis de realismo) são registrados no artefato e no
CHANGELOG como desvio do pré-registro.
