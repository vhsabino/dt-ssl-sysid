# Pré-registro — C1b-v2: RE-REGISTRO do adendo C1b (gerador físico) após a execução v1

**Gravado em:** 2026-09-07, DEPOIS de executar C1b-v1 e ANTES de qualquer execução v2. Este documento
é uma **emenda documentada**, não uma substituição: o pré-registro v1
(`docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_20260907.md`) e os seus artefatos
(`results/identifiability_insilico_mujoco-rollers_20260907_2306.*`,
`…_mujoco-rollers-delay_20260907_2311.*`, `…_mujoco-velocity_20260907_2304.*` e `_2305.*`) ficam
intocados e continuam sendo o registro do que foi previsto e do que saiu. Tudo o que não é listado
abaixo permanece **idêntico** a C1 e a C1b-v1 (gerador via `make_harness_plant`, zona morta dentro
do mundo, cadeia de medição, estimador perfil-NM em `m = 0..12`, `m_eff = m − 1`, split 2/3–1/3,
seeds: ruído `42 + rep`, split `1042 + rep`, desenho sintético 42; `n_rep = 12`).

## Por que re-registrar (o que v1 ensinou)

Em v1 as quatro hipóteses foram **formalmente falsificadas**, mas todas as falsificações rastreiam
duas escolhas do desenho, não o fenômeno:

1. **A célula de referência (R3 / none / off) está fora do envelope de rastreamento da rota b.**
   A excitação projetada de C1 (degraus simultâneos de até 1,5 m/s em vx/vy e 4,0 rad/s em ω) leva
   o modelo físico a escorregar: em R3 a rota b deu `K_vx = −0,44` com fit 2 %, `K_vy = 0,86` com
   fit 55 % e, para ω, fit 11 % com `τ_ref` inflado (0,067 s sem atraso; 0,110 s com atraso) —
   coerente com a caracterização prévia de v1 (`(vx, vy, ω) = (0, 2, 3)` → `ω ≈ −2,96 rad/s`;
   `(2, 0, 3)` → `+2,56`), enquanto em regime permanente a rota b rastreia bem comandos moderados
   (`vx = 1` → `K ≈ 0,997`; `vy = 1` → `0,994`; `ω = 3` → `0,995`; acoplamento `vy = 1 → ω ≈ −0,007`).
   Com essa referência, `dev_K(R1, vx) ≈ −255 %` e todo regime "limpo" de ω (R1-wonly, R2-rotate,
   τ ≈ 0,033 s) recebe `|dev_τ| > 50 %`.
2. **A bandeira composta `regime_bias` (K OU τ)** transformou o τ corrompido da referência em
   falsificação automática de H5/H6/H7, mesmo com o padrão de K exatamente o previsto
   (rota b + atraso: `K_ω(R1) = 1,368` vs `K_ω(R1-wonly) = 0,989` e `K_ω(R2-rotate) = 0,996`).

H8 (rota a reproduz C1) está **encerrada** em v1: K a ≤ 0,1 %, mesmo `m_eff`, 4/4 em todas as
células; o único desvio (τ de R3/vx, +1,48 %) desaparece com os limites de força/torque do servo
levantados (artefato `_2305`). Não é reavaliada aqui.

## O que muda em v2 (e SÓ isto)

**(a) Excitação projetada dentro do envelope da rota b — regime `R3-mild`.** Mesma construção de
R3 (12 eventos × 10,0 s, degraus constantes por trechos nos três DOFs simultaneamente, seed de
desenho 42, `pose0 = 0`), com amplitudes `|vx|, |vy| ~ U(0,3; 1,0) m/s`, `|ω| ~ U(0,5; 2,0) rad/s`
(sinal equiprovável) e duração de degrau `U(0,5; 1,5) s`. Justificativa: os números do piloto de
v1 acima (rastreamento correto até ~1 m/s de translação e ~3 rad/s em rotação pura; distorção só
em translação ≥ 2 m/s combinada com rotação ≥ 3 rad/s). R3 (agressivo) não é mais usado como
referência; fica disponível como regime opcional.

**(b) Referências por DOF = os regimes dedicados de malha aberta, não R3.**
`ω → R2-rotate / none / off` (o regime que promoveu ω no artigo; comando constante por evento,
sem translação); `vx, vy → R2-square / none / off` (11 eventos `square`, translação tipo malha
aberta com |ω| ≤ 0,8 rad/s). R2-square passa a fazer parte dos regimes executados.

**(c) Bandeiras separadas; o critério das hipóteses é SÓ K.** `regime_bias_K = |dev_K| > 10 %`
(`dev_K = (K_med − K_ref)/K_ref`). `dev_τ`, `dm_eff` (e a bandeira composta `regime_bias` de v1)
continuam **reportados descritivamente**, sem entrar no veredito. Razão: K é a grandeza da
afirmação do artigo (`K_ω` 1,00 vs 1,38); τ e Td do ajuste P1D a um modelo não-P1D são
descritores, não critérios.

Artefatos v2 com o sufixo: `results/identifiability_insilico_<generator>_v2_<carimbo>.{md,csv,json}`
(também para `fopdt`, para não colidir com os artefatos de C1). Console ASCII.

## Hipóteses re-registradas (regra K-only; lidas na célula realista `vision`/`on` e conferidas na
idealizada `none`/`off`)

- **H5'** — com o gerador físico, `dev_K(R1, ω) ≥ +10 %` (mesma direção do 1,3–1,38 do artigo)
  E `regime_bias_K` falsa em `R3-mild` para ω (R2-rotate é a própria referência, `dev = 0`).
  *Falsifica H5':* `dev_K(R1, ω) < +10 %` (o gerador físico, como entregue, não produz a inflação
  no nível pré-registrado; um desvio positivo menor é reportado como efeito parcial) OU
  `regime_bias_K` verdadeira em `R3-mild`.
- **H6'** — no controle `R1-wonly` (mesmos comandos de ω, `vx = vy = 0`) `regime_bias_K` é falsa
  (`|dev_K| ≤ 10 %`). *Falsifica H6':* `|dev_K(R1-wonly, ω)| > 10 %`. Leitura antecipada: com zona
  morta `on`, 74 % das amostras de R1-wonly são totalmente zeradas (v1) e `K` cai (0,93 em v1) —
  se o desvio negativo passar de 10 % só com `on`, é efeito da zona morta, não de acoplamento.
- **H7'** — vx e vy NÃO mostram dependência de regime comparável: `regime_bias_K` falsa em R1 para
  vx e para vy contra a referência `R2-square`. *Falsifica H7':* `|dev_K| > 10 %` em R1 para vx ou
  vy. Leitura antecipada (fixada agora): `front_to_back` comanda até 2,9 m/s e `side_to_side` até
  2,6 m/s, acima do envelope de ~1–2 m/s da rota b, enquanto `square` fica ≤ 2,0 m/s; um desvio
  **negativo** de `K_vx`/`K_vy` em R1 é assinatura de saturação de velocidade (ganho que cai com a
  amplitude), não de acoplamento translação→guinada — o sinal distingue os dois mecanismos, e a
  falsificação de H7' por saturação será registrada como tal.

**Ordem de prioridade dos geradores:** `mujoco-rollers-delay` é o primário (é o que reproduziu
1,368 em v1); `mujoco-rollers` é a réplica sem atraso. **Checagem de sanidade** (não é hipótese):
`fopdt` com `R3-mild` (`none`/`off`, `n_rep = 6`) deve recuperar θ\* (4/4) — garante que a mudança
de envelope não pode ser responsabilizada por nada.

**O que falsificaria a afirmação da tese** continua como em v1: o padrão de `regime_bias_K`
dependeria do DOF e não do regime.

## Compromisso

Depois deste arquivo salvo, v2 roda sem reabrir estas decisões; qualquer desvio necessário é
registrado no artefato como desvio do pré-registro v2.
