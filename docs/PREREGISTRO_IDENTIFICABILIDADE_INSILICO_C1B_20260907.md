# Pré-registro — Adendo C1b: identificabilidade in-silico com o GERADOR FÍSICO (MuJoCo rota b)

**Gravado em:** 2026-09-07, ANTES de rodar qualquer estimação com gerador MuJoCo. Estende
`docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md` (C1): tudo o que não é redefinido aqui
(cadeia de medição, estimador perfil-NM em `m = 0..12`, seeds, split 2/3–1/3, `legacy_uy_series`,
regra de convenção `m_eff = m − 1`) permanece **idêntico**. Módulo: o mesmo
`dtssl analysis run identifiability_insilico`, agora com o kwarg `generator`.

## Motivação (resultado de C1)

Em C1 (`results/identifiability_insilico_20260907_1552.md`, commit df833af, rodado no PC) o gerador era o próprio gêmeo linear:
todos os DOFs foram recuperados em todas as células com excitação do DOF, inclusive ω em R1
(comandos de competição) com zona morta ligada e ruído de visão (`K_ω` 0,996). Logo o
`K_ω ≈ 1,3–1,38` do ajuste em malha fechada do artigo NÃO vem do conteúdo de comando, do ruído
i.i.d. nem da zona morta; vem de algo que o gerador linear não tem. **Hipótese de C1b:** acoplamento
cruzado translação→guinada do robô real, correlacionado com os comandos de ω da estratégia.

O modelo físico da rota b (`mujoco-rollers`: chassi + 4 rodas omni + roletes livres, sem
sintonia, geometria nominal, receita de contato de Wan et al. 2026, `docs/refactor_notes/physics.md`)
exibe esse acoplamento. **Caracterização prévia do gerador (sem estimação, 2026-09-07):** em
regime permanente o acoplamento é pequeno (comando `vy = 1 m/s` → `ω ≈ −0,007 rad/s`; `vx = 1` →
`−0,0002`), mas nos **transitórios** um degrau de `vy = 1 m/s` produz picos de guinada de
±1,5 rad/s nas 5 primeiras amostras (média +0,48 rad/s nos primeiros 0,25 s) e, com translação e
rotação combinadas em alta velocidade, a resposta de guinada é distorcida ou invertida
(comando `(vx, vy, ω) = (0, 2, 3)` → `ω ≈ −2,96 rad/s`; `(2, 0, 3)` → `+2,56`; com parasitas
`vx ≈ 0,11` e `vy ≈ −0,31 m/s`). Também há acoplamento guinada→translação em rotação alta, mas os
rótulos de R1 de vx (`front_to_back`, |ω| ≤ 0,84 rad/s) e vy (`side_to_side`, |ω| ≤ 0,85 exceto um
evento) têm pouca rotação. A rota a (`mujoco-velocity`) embute a própria `AnalyticFOPDTPlant`:
com os limites de atuador padrão (150 N / 3 N·m) desvia da planta analítica ≤ 6 mm em 10 s de
degraus agressivos (R3) e ≤ 0,5 mm num evento real; sem os limites, < 1e−5 m.

## Desenho (o que muda em relação a C1)

- **Gerador** (`generator`): `mujoco-rollers` (rota b, sem atraso de transporte — principal),
  `mujoco-rollers-delay` (rota b + tap de atraso `ceil(Td*/Ts)` por DOF aplicado ao comando,
  `WorldPlant(delay="theta")`; roda se (b) levar < 15 min) e `mujoco-velocity` (rota a; sanidade).
  Planta construída por `dtssl.sim.world_plant.make_harness_plant(name, θ*, **opts)`; UMA planta por
  (gerador, zona morta), reutilizada entre eventos (`reset(pose0, velb0=0)` reancora), fechada ao fim.
- Trajetória por evento exatamente como em C1: `pose[0] = pose0`, `pose[k] = step(cmd[k−1], Ts)`,
  `velb0 = 0`, sem `prime_delay` (buffer vazio). Gerada UMA vez por (regime, evento, zona morta) e
  reutilizada por todas as réplicas de ruído e splits.
- **Zona morta (fator C) nos geradores MuJoCo:** `world_opts["deadzone"] = True` — o
  `MuJoCoWorld` aplica o MESMO limiar de firmware (1,567 rad/s por roda): rota a = mesma regra de
  corpo de `apply_body_deadzone` (roda mascarada → pseudo-inversa); rota b = **por roda**, no
  setpoint de cada atuador (é o que o firmware faz). O estimador continua vendo o comando original.
  As frações "mascaradas" reportadas usam a mesma regra por roda (`mask_deadzone`).
- **Regimes:** R1 (pareamento do artigo), **R1-wonly** (CONTROLE: as MESMAS sequências de R1 com
  `vx = vy = 0`, mantendo `ω`; avaliado só para o DOF ω), R2-rotate, R3. R2-square é omitido para
  poupar tempo. Ruído: `none`, `vision`. Zona morta: `off`, `on`.
- `n_rep = 12` para os geradores MuJoCo (limitação de tempo; seeds iguais às de C1: ruído
  `42 + rep`, split `1042 + rep`, desenho R3 42). Sanidade rota a: `regimes = R1, R3`, `none`, `off`,
  `n_rep = 6`.
- **Artefatos** com o gerador no nome: `results/identifiability_insilico_<generator>_<carimbo>.{md,csv,json}`;
  título e cabeçalho declaram o gerador. Saída de console ASCII.

## Métricas e regra de decisão (FIXADAS)

Para um gerador físico θ\* **não é a verdade do modelo** (o modelo não é P1D); a pergunta passa a
ser *a estimativa P1D depende do regime?* Por DOF:

- **Referência** = mediana das estimativas (K, τ, m_eff) na célula **R3 / `none` / `off`** do
  próprio gerador (excitação projetada, sem ruído, sem zona morta).
- Por célula: mediana/IQR de K, τ, m_eff e fit hold-out (como em C1) e **desvio da referência**
  `dev_K = (K_med − K_ref)/K_ref`, `dev_τ = (τ_med − τ_ref)/τ_ref`, `dm = m_eff_med − m_eff_ref`.
- **Bandeira `regime_bias`** = `|dev_K| > 10 %` OU `|dev_τ| > 15 %`. Substitui "recuperado"; as
  bandeiras contra θ\* são reportadas apenas para `mujoco-velocity` (a verdade é o gêmeo embutido).
- Célula realista = (`vision`, `on`); idealizada = (`none`, `off`). As hipóteses são lidas na
  célula realista e conferidas na idealizada.

## Hipóteses (fixadas antes de rodar)

- **H5** — com o gerador físico, `K_ω` em R1 desvia da referência R3 em **≥ +10 %** (mesma direção
  do 1,3–1,38 do artigo), enquanto em R2-rotate e R3 `regime_bias` é falsa para ω.
  *Falsifica H5:* `dev_K(R1, ω) < +10 %` (inclusive desvio negativo — o gerador físico, como
  entregue, não produz a inflação de malha fechada) OU `regime_bias` verdadeira também em R2-rotate
  (o desvio não seria dependente do regime).
- **H6** — o desvio desaparece no controle **R1-wonly** (`|dev_K(R1-wonly, ω)| ≤ 10 %`,
  `regime_bias` falsa): sem translação não há acoplamento cruzado. *Falsifica H6:* R1-wonly com
  `regime_bias` verdadeira — então o desvio de R1 (se houver) viria do conteúdo dos comandos de ω
  (amplitude/duração) e não da translação. Nota: com zona morta `on`, R1-wonly tem MAIS amostras
  totalmente zeradas que R1 (sem translação as rodas não são "levantadas" acima do limiar) — o
  efeito da zona morta é lido comparando `on` vs `off` dentro de R1-wonly.
- **H7** — vx e vy NÃO mostram dependência de regime comparável: `regime_bias` falsa em R1 para
  vx e vy. Expectativa declarada: o acoplamento da rota b vai da translação PARA ω (guinada
  parasita nos transitórios de translação), e os rótulos de R1 de vx/vy têm pouca rotação;
  a distorção guinada→translação só aparece em rotação alta combinada (não presente em
  `front_to_back`/`side_to_side`). *Falsifica H7:* `regime_bias` verdadeira em R1 para vx ou vy.
- **H8** — `mujoco-velocity` como gerador reproduz o resultado de C1: em R1 e R3 (`none`, `off`)
  K e τ medianos dentro de **1 %** dos valores do artefato de C1 (`_1552`) e o mesmo `m_eff`;
  bandeiras "recuperado" 4/4 para os três DOFs (a verdade é o gêmeo embutido). *Falsifica H8:*
  qualquer DOF fora de 1 % ou `m_eff` diferente — apontaria para os limites de força/torque do
  servo da rota a, não para a cadeia de estimação.

## O que este experimento NÃO decide

Se H5 falhar, a conclusão é sobre o modelo físico *como entregue* (sem sintonia): a rota b pode
não reproduzir o acoplamento do robô real. A afirmação da tese ("o regime, não o DOF") continua
sendo testada pelo padrão: para cada DOF, `regime_bias` deve mudar com o regime (R1 vs R1-wonly vs
R2-rotate vs R3) e não com o DOF.

## Compromisso

Depois deste arquivo salvo, C1b roda sem reabrir estas decisões; desvios necessários (tempo,
erro numérico, dado insuficiente) são registrados no artefato como desvio do pré-registro.
