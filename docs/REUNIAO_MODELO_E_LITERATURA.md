# Preparação para reunião — o modelo, MATLAB e a literatura

> Relatório de verificação. Cada afirmação traz **arquivo + trecho** como
> evidência. Onde não há evidência no repo, está marcado **NÃO CONFIRMADO**.
> Não altera código, não escreve paper.
> Data de verificação: 2026-06-26. Repo: `Documents/digitaltwin`.

---

## SEÇÃO 1 — O que é o `AnalyticFOPDTPlant` (verificado no código)

**Arquivo:** `phase0_replay/plant.py` (classe `AnalyticFOPDTPlant`, linhas 64–135).
É um **porte fiel** de `automation/deadreckoning_p1d.m` — o "modelo promovido".
O nome diz "FOPDT" (First-Order Plus Dead-Time); o código confirma que isso é
literal: por DOF aplica **atraso de transporte → lag de 1ª ordem → ganho**, e
depois integra a pose corpo→mundo. Passo a passo, com evidência:

### O que ELE simula

**(a) ATRASO de transporte (Td / dead time) — SIM, por shift inteiro de amostras.**
Em `step` (linhas 100–109):
```python
if self.Td[i] <= 0.0:
    src = j                      # sem atraso
else:
    src = int(math.floor(j - self.Td[i] / dt + 1e-9))   # = j - ceil(Td/dt)
pos = src + self._base
if 0 <= pos < len(self._hist):
    ud[i] = self._hist[pos][i]
```
Não é um buffer circular de tamanho fixo: é um histórico `self._hist` de comandos
crus indexado para trás. O atraso em amostras é `floor(j - Td/dt)`, que o próprio
docstring (linhas 5–7) declara equivaler a **`ceil(Td/dt)`** — e enfatiza que é
**`ceil`, NÃO `round`** (ex.: `Td_vx/dt = 4.15 → 5 amostras`). Antes do início do
histórico, `ud=0` (o `if 0 <= pos`), reproduzindo o `'previous', 0` do MATLAB.
Confirmado contra a fonte: `deadreckoning_p1d.m:40` —
`ud = interp1(t, u, t - Td, 'previous', 0)`.

**(b) LAG de 1ª ordem (τ) — SIM, recursão ZOH exata.**
`step`, linhas 112–119:
```python
if self.tau[i] > 0.0:
    a = 1.0 - math.exp(-dt / self.tau[i])
    vlag_new[i] = self._vlag[i] + a * (ud[i] - self._vlag[i])
else:
    vlag_new[i] = ud[i]
vbody_new = self.K * vlag_new
```
Isto é a discretização **ZOH-exata** de `1/(τ s + 1)` (o `a = 1 - e^{-dt/τ}`),
idêntica a `deadreckoning_p1d.m:65-72` (`lag_filter`). O **ganho K** entra
depois, multiplicando: `v_corpo = K * v_lag` (linha 119; casa com `v = K*v(:)`
em `deadreckoning_p1d.m:50`). Caso `τ=0` → resposta instantânea (= comando
atrasado). Estado inicial: `vlag = velb0/K` (linhas 80–81) — no golden `velb0=0`.

**(c) CINEMÁTICA — só corpo→campo via heading; NÃO há cinemática de rodas / IK omni.**
`step`, linhas 121–127:
```python
th_new = self.th + 0.5 * dt * (vbody_new[2] + self._vw_prev)
c, s = math.cos(th_new), math.sin(th_new)
gx_new = c * vbody_new[0] - s * vbody_new[1]
gy_new = s * vbody_new[0] + c * vbody_new[1]
x_new = self.x + 0.5 * dt * (gx_new + self._gx_prev)
y_new = self.y + 0.5 * dt * (gy_new + self._gy_prev)
```
É integração **trapezoidal** (média de dois instantes — equivale ao `cumtrapz`
do MATLAB, `deadreckoning_p1d.m:29-31`) de uma rotação 2D pura corpo→mundo
parametrizada por `θ`. **Os três DOF de corpo `(vx, vy, w)` são tratados como
canais independentes**; não há matriz de rodas, raio de roda, ângulos de roda,
nem cinemática inversa/direta omni dentro do `step`. (Os campos `robot_radius`
/ `wheel_radius` existem em `config/twin_params.json` mas **não são lidos** por
`AnalyticFOPDTPlant` — confirmado: `plant.py` só usa `K`, `tau`, `Td`.)

**(d) Controle de motores / PID embarcado / zona morta por roda / atrito — NÃO modelados; estão "lumped" em K, τ, Td.**
Não há nenhum termo de PID, saturação, zona morta ou atrito em `plant.py`.
A própria estrutura do `deadreckoning_p1d.m` confirma a agregação: docstring
linhas 5–8 — "G_i(s) = K_i·e^{-Td_i s}/(τ_i s + 1) a cada comando de corpo …
exatamente a cadeia do modelo Simulink pid_v3 (TransferFcn → TransportDelay →
**rodas[identidade, dz=0]** → rotação → integradores)". Ou seja, no modelo
promovido as rodas são **identidade com zona morta zero**, e tudo (resposta de
motor, PI embarcado, atrito) está agregado nos três parâmetros por DOF.
Corroboração de que isso é uma escolha consciente e que a zona morta É por roda
(não de corpo): `docs/RELATORIO_TECNICO_DESENVOLVIMENTO.md:90` (Evidência B,
firmware) — `MOTOR_MIN_SPEED_RAD_S = 1,567 rad/s` é **setpoint de roda, depois
da IK**; o `d` "permanece por roda" e não é aplicado ao corpo.

### Diagrama de fluxo (por DOF i ∈ {vx, vy, w})

```
                          ┌─────────────────────── NÃO MODELADO (lumped em K,τ,Td) ───────────────────────┐
                          │  PID embarcado · cinemática inversa p/ 4 rodas · zona morta POR RODA (1,567   │
                          │  rad/s) · atrito · saturação PWM ±80 · dinâmica de motor individual           │
                          └──────────────────────────────────────────────────────────────────────────────┘

  cmd de CORPO            ATRASO                LAG 1ª ordem          GANHO          velocidade
  u_i[k] (vx,vy,w)  ──►   transporte Td   ──►   τ (ZOH exato)   ──►   K_i      ──►   de corpo atingida
                          ud=u[k-ceil(Td/dt)]   v=v+a(ud-v)           v_body=K·v     v_body=(vx,vy,w)
                          (floor(j-Td/dt))      a=1-e^{-dt/τ}
                                                                                          │
                                                                                          ▼
                                            integração corpo→campo (trapezoidal, via heading θ)
                                            θ[k] = θ[k-1] + ½dt(w[k]+w[k-1])
                                            x[k] = x[k-1] + ½dt( (cosθ·vx − sinθ·vy)[k] + [k-1] )
                                            y[k] = y[k-1] + ½dt( (sinθ·vx + cosθ·vy)[k] + [k-1] )
                                                                                          │
                                                                                          ▼
                                                                                   POSE (x, y, θ)
```

> **Para a pergunta "o que isso simula de verdade?":** um modelo **comportamental
> grey-box por DOF** (resposta entrada→velocidade de corpo + integração
> cinemática 2D), **não** um modelo físico de robô. Toda a física de baixo nível
> (motores, PI, rodas, atrito, zona morta) está **agregada** em três números por
> DOF.

---

## SEÇÃO 2 — Dependência de MATLAB/Simulink (crítico)

### O gate `eval_twin_vs_rsim.py` é Python puro em runtime — NÃO chama MATLAB.

Rastreio dos imports de `phase0_replay/eval_twin_vs_rsim.py` (linhas 29–36, 156):
```python
import numpy as np
from .io import repo_root
from .splits import load_holdout_segments
from .plant import AnalyticFOPDTPlant
from .rollout import rollout_segment, ...
from .metrics import evaluate, ...
from .params import load_twin_params
...
from .rsim_plant import RSimReplay
```
- O **twin** vem de `AnalyticFOPDTPlant` (Python puro, NumPy — Seção 1).
- O **rSim** vem de `RSimReplay` (`rsim_plant.py:47` → `import robosim`), o engine
  C++/ODE do rc-robosim via wheel — **não MATLAB**.
- Busca por imports de MATLAB/engine/subprocess em `phase0_replay/*.py`: as únicas
  ocorrências de "matlab" são `resample.matlab_colon` (uma reimplementação **em
  NumPy** do operador `:` do MATLAB — `resample.py:21`, docstring linhas 1–14) e
  comentários que citam os `.m` por proveniência. **Nenhuma chamada ao MATLAB
  Engine, a `matlab.engine`, a `sim()` ou a subprocess de `.m`.**

**`sim_aligned.m` (Simulink) e a identificação (iddata/sysid) são OFFLINE e NÃO
estão no loop do gate.**
- `automation/sim_aligned.m:5-13` usa `Simulink.SimulationInput` + `sim(simIn)` —
  é claramente Simulink, mas o próprio cabeçalho diz que é "Helper compartilhado
  (**Fase 3 do bayesopt**)", i.e., calibração/avaliação **offline**. Não é
  importado por nenhum `.py` (não é importável de Python; e o gate não o invoca).
- Os parâmetros entram no gate por um **arquivo JSON congelado**:
  `params.py:29-37` lê `config/twin_params.json`, cujo `source` é
  `models/sysid_vxvy_v2.mat` (`twin_params.json:2`). A identificação
  (System Identification Toolbox / `iddata` / `procest`) produziu esse `.mat`
  **uma vez, offline**; o gate só consome o JSON extraído dele.

### Golden test `AnalyticFOPDTPlant` vs `deadreckoning_p1d` e tolerância

**Arquivo:** `tests/test_plant_golden.py`.
- Fixtures golden existem: `tests/fixtures/plant_golden_shoot_to_goal_12_01.parquet`
  e `..._side_to_side_01_05.parquet` (geradas offline por
  `automation/export_plant_golden.m`, citado em `test_plant_golden.py:3`).
- **Tolerância do gate: `ATOL = 1e-6`** (`test_plant_golden.py:19`), aplicada ao
  `max|erro|` em `xs`, `ys`, `ths` (linhas 47–49). O comentário registra alvo
  "esquema idêntico deve aproximar 1e-9" (linha 19) — esse é o objetivo, não o
  threshold. **O valor de erro efetivamente atingido NÃO foi re-executado nesta
  sessão → NÃO CONFIRMADO** (o teste o imprime em `test_report_achieved_atol`,
  mas exige rodar pytest no env `rsim310`).
- Importante: o golden **compara Python contra um artefato pré-exportado** do
  MATLAB; gerar o artefato exige MATLAB, mas **rodar o golden test não** (lê
  parquet). Portanto MATLAB é necessário só para (re)gerar a fixture, não para o
  teste em si.

### VEREDITO explícito

- **Para rodar o gate `eval_twin_vs_rsim`, MATLAB NÃO É necessário.** É Python
  (NumPy) + o engine C++ `robosim`. Evidência: imports acima; ausência de
  qualquer chamada MATLAB em `phase0_replay/`.
- **MATLAB/Simulink É necessário SÓ para (re)identificar/calibrar parâmetros**
  (produzir `models/sysid_vxvy_v2.mat` → `config/twin_params.json`) e para
  (re)gerar as fixtures golden — tudo **offline**, fora do loop do gate.
  Evidência: `params.py:29-37`, `twin_params.json:2`, `sim_aligned.m`,
  `test_plant_golden.py:3`.
- **Dependência de runtime do gate quanto a MATLAB: nenhuma.**

---

## SEÇÃO 3 — Levar o modelo para o Isaac Sim (análise, não implementação)

O que o modelo **é** (Seção 1) determina a rota: é um modelo **comportamental
por DOF**, identificado em malha fechada, sem física de roda/contato. Isso pesa
fortemente a favor da rota (a).

### Rota (a) — embutir o FOPDT como dinâmica do robô-ego dentro do Isaac

Sobrescrever o `step` do robô-ego com a cadeia FOPDT (como já se fez no rSoccer/
rSim), usando o Isaac apenas por **contato + escala GPU**. O modelo
comportamental fica intacto.

**O que a rota (a) exigiria concretamente** (reaproveitando o que o rSim já
ensinou — `rsim_plant.py`):
1. **Interface de step idêntica à `Plant`** (`plant.py:51`): `step(cmd, dt)` que
   recebe **comando de CORPO `(vx, vy, w)`** e devolve pose. O `AnalyticFOPDTPlant`
   já é essa interface — bastaria adaptá-la para escrever a pose/velocidade no
   ator do Isaac a cada tick (análogo ao `RSimReplay.step`, `rsim_plant.py:148-152`).
2. **Frame de corpo + comando não rotacionado.** O rSim confirmou a convenção:
   ação `(vx, vy, w)` de corpo, `w` em rad/s, **sem** conversão angular
   (`rsim_plant.py:11-16, 74-80`). Reaproveitar isso evita re-descobrir ganhos.
3. **Grade temporal dt/substep.** O rSim mostrou o cuidado da grade 1/60 vs dt
   inteiro em ms, resolvido por **substep + interpolação linear**
   (`rsim_plant.py:18-21, 82-104`). O mesmo casamento de grade (substep do Isaac
   acumulando ~16,667 ms e leitura interpolada) seria necessário.
4. **Condição inicial de velocidade.** O FOPDT **aceita `velb0`** diretamente
   (`plant.py:77-82`, `vlag = velb0/K`) — vantagem sobre o rSim, que **não tem
   setter de velocidade** e precisa de warm-up + re-âncora SE(2)
   (`rsim_plant.py:22-37, 138-147`). Na rota (a) a CI de velocidade é trivial.
5. **Atraso de transporte.** Já vive no plant (histórico + `prime_delay`,
   `plant.py:91-93`); o Isaac não precisa modelar isso.

> Em resumo, rota (a) é majoritariamente **fiação** (mesma que o rSim já exigiu);
> a dinâmica já está validada por golden + gate.

### Rota (b) — reconstruir o robô como modelo FÍSICO do Isaac

Massas, inércias, atrito de roda omni, motores. **Isso abandona a identificação
comportamental** já validada e troca por um modelo físico que **traz nova carga
de calibração + validação**: estimar/medir massa, inércia, coeficientes de
atrito por roda e parâmetros de motor, e então **re-validar** contra os logs
(re-fazer o equivalente ao golden + gate SE(2) multi-horizonte). Nada disso está
feito no repo. A não-linearidade relevante (zona morta) é **por roda, após a IK**
(`RELATORIO_TECNICO:90`), então a rota (b) reabre exatamente o problema que a ID
de ω já mostrou ser difícil com os dados disponíveis (Seção 4).

### Contato é necessário para a tarefa atual? — Hoje, NÃO.

Evidência: `results/bin_distribution_20260619_000422.md:9-11` — distribuição de
bins do hold-out:

| bin | janelas densas | independentes | fração |
|---|---:|---:|---:|
| trans-dominado | 264 | 49 | **0,996** |
| misto | 0 | 0 | 0,000 |
| rot-dominado | 1 | 0 | 0,004 |

**~99,6% das janelas são translação-dominada**, e o veredito real do gate é o bin
de translação (`eval_twin_vs_rsim.py:7-8, 196-208`). A tarefa atual é predição de
trajetória livre-curso em movimento majoritariamente translacional — **sem
colisões no escopo**. Logo, o **contato/física fina não é necessário hoje**, o
que reforça a rota (a): usar Isaac por contato+GPU só faz sentido quando a tarefa
passar a exigir contato (próxima fase / RL), e mesmo aí o ego pode manter a
dinâmica FOPDT enquanto o Isaac fornece só o contato.

**Recomendação: rota (a).** Mantém a identificação validada, é majoritariamente
reuso da fiação já provada no rSim, e a tarefa atual nem exige contato.

---

## SEÇÃO 4 — "E se existir artigo que faz o mesmo?" (estratégia)

### Protocolo de diferenciação: a contribuição é a CONJUNÇÃO

A tese **não** é "construímos um gêmeo". Conforme `docs/01_definicao_pesquisa.md:31`,
as contribuições declaradas são **C1** (metodologia de identificação a partir de
logs de **malha fechada**), **C2** (gêmeo SSL aberto/reprodutível) e **C3**
(caracterização de **identificabilidade**, especialmente de Td/ω, nesse regime de
dados). E `RELATORIO_TECNICO:8` põe como contribuição central a "metodologia de
identificação grey-box **por DOF** … e **caracterização dos limites** desse tipo
de dado". A defesa é a **conjunção** {identificação por DOF + dado operacional de
malha fechada + caracterização de identificabilidade}, não qualquer peça isolada.

### Pontos de diferenciação mais defensáveis (do material do repo)

1. **Caracterização da NÃO-identificabilidade de ω, com 4 evidências
   convergentes** (`RELATORIO_TECNICO:86-98`):
   - **A — ganho×amplitude:** ganho plano ≈1,3–1,5 em toda a faixa, **sem joelho
     de zona morta no ω de corpo** (`diag_omega_gain_amplitude.m`, pool 7405).
   - **A2 — assimetria de sinal:** razão meas/cmd simétrica ≈1,3, **sem viés
     direcional recuperável** (`diag_omega_gain_sign.m`).
   - **B — firmware:** a zona morta é **POR RODA** (`MOTOR_MIN_SPEED_RAD_S =
     1,567 rad/s`, após a IK), logo invisível no ω de corpo — explica A.
   - **C — ID linear de ω REPROVA o gate:** θ_w identificável no ganho, mas
     candidato **pior** que placeholder em todos os horizontes (Wilcoxon pareado,
     pool p=3,8e-9); reprova (i) Ljung-Box e (iii) custo SE(2)
     (`identify_omega_v3_linear.m`, `eval_omega_v3_se2.m`).
   - **Veredito:** logs de malha fechada estimam o **ganho** de ω mas **não
     validam** ω como modelo free-run (`RELATORIO_TECNICO:98`). Esse é um
     **resultado de identificabilidade**, raro de ver caracterizado.

2. **Métrica SE(2) multi-horizonte com inferência estatística honesta.**
   `eval_twin_vs_rsim.py` aplica Wilcoxon não-sobreposto + moving-block bootstrap,
   gates por população (N_min) e por bin (linhas 1–8, 103–150). É uma metodologia
   de **validação**, não só um número de RMSE.

3. **Resultado NEGATIVO do bayesopt (honestidade + tensão parâmetro-vs-comportamento).**
   `RELATORIO_TECNICO:107-129`: bayesopt v1 **overfit** (K_w→0,516 no piso, não
   generaliza, pool +0,0148 m pior que vx/vy v2, p=0,0052); v2 com treino amplo
   sobe K_w→1,099 e **empata** o grey-box mas não o supera (pool +0,0041 m pior,
   p=0,040). Conclusão defensável: **dado de malha fechada não sustenta um ajuste
   comportamental conjunto de 9 params que supere o grey-box por DOF na
   translação**. Resultado negativo bem-caracterizado é diferenciação forte.

4. **Identificação por DOF com excitação limpa + validação em hold-out**, em
   contraste com parâmetros herdados nunca validados (`RELATORIO_TECNICO:63-74`):
   vx/vy v2 re-identificados, hold-out fit 86,7% / 87,1%, xcorr 0,99.

### Honestidade obrigatória: a SLR NÃO foi executada.

Evidência: `slr/` contém apenas `protocolo_slr.md` (o protocolo) e `slr/exports/`
está **vazio** (`ls slr/exports/` → sem arquivos). O protocolo descreve as fases
de triagem mas não há `triagem.csv`, extração, nem síntese.
**→ A revisão sistemática da literatura ainda NÃO foi rodada.** Logo, **não há
evidência no repo de qual é o estado-da-arte nem de onde há sobreposição**. A
diferenciação acima é a **defesa potencial**; sua validade depende de executar a
SLR para mapear o que de fato já existe. Declare isso à orientadora sem rodeios:
os pontos de diferenciação são fortes **como hipótese**, mas a confirmação de
ineditismo está **pendente da SLR**.

---

## Resumo por seção

- **§1 — O que é o `AnalyticFOPDTPlant`:** confirmado por código que simula
  atraso de transporte (shift `ceil(Td/dt)`), lag de 1ª ordem ZOH-exato, ganho K,
  e integração trapezoidal corpo→campo via heading. **Sem** cinemática de roda/IK
  omni; PID/zona morta/atrito **não modelados** (lumped em K,τ,Td). Diagrama
  incluído.
- **§2 — MATLAB:** o gate `eval_twin_vs_rsim` é **Python puro + engine C++
  robosim**; **não** chama MATLAB. Simulink (`sim_aligned.m`) e sysid são
  **offline**, fora do loop. Golden test compara contra fixture parquet
  pré-exportada, tolerância **1e-6**. Veredito: **MATLAB não é necessário p/ rodar
  o gate; só p/ (re)identificar parâmetros e (re)gerar fixtures**.
- **§3 — Isaac Sim:** recomendada a **rota (a)** (embutir FOPDT como dinâmica do
  ego, Isaac só p/ contato+GPU), majoritariamente reuso da fiação do rSim; CI de
  velocidade é trivial no FOPDT (vantagem sobre o rSim). Rota (b) abandona a ID
  validada e traz nova calibração. **Contato não é necessário hoje** (~99,6%
  translação).
- **§4 — Literatura:** a contribuição é a **conjunção** (ID por DOF + dado de
  malha fechada + caracterização de identificabilidade). Diferenciações mais
  defensáveis: não-identificabilidade de ω (4 evidências), métrica SE(2)
  multi-horizonte, resultado negativo do bayesopt. **A SLR NÃO foi executada** —
  a diferenciação depende dela.

## Itens NÃO CONFIRMADOS

1. **Valor de erro efetivamente atingido no golden test** (o alvo ~1e-9 do
   comentário): não re-executei pytest nesta sessão. A tolerância do gate (1e-6)
   e a existência das fixtures **estão** confirmadas.
2. **Estado-da-arte / sobreposição com a literatura:** indeterminável no repo
   porque a **SLR não foi executada** (`slr/exports/` vazio).
3. **Operação real (5 partidas):** a distribuição ~99,6% translação é do
   **hold-out (10 eventos)** e o próprio arquivo a marca como "PRÉVIA, não a
   operação" (`bin_distribution_20260619_000422.md:1-3`). A fração em operação
   plena não está medida.
</content>
</invoke>
