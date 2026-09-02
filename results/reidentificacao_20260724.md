# Re-execução completa da identificação — verificação de determinismo e consistência

**Data:** 2026-07-24. **Commit:** 6fc2f42-dirty. **Regra:** nada sobrescrito — todos
os artefatos originais (`models/sysid_vxvy_v2.mat`, `models/sysid_omega_rotate_v1.mat`)
ficam intactos; re-execuções salvas com sufixo `_rerun_<timestamp>` em `build/`.

## Resumo executivo

**Determinismo confirmado bit-a-bit** para vx, vy e ω (diferença absoluta = 0,0
em todos os 9 parâmetros). `config/robot_geometry.json` **não entra** no
pipeline de identificação por DOF (confirmado, grep vazio). O gate SE(2)
**passa nos dois vizinhos de quantização de Td** (floor e ceil) para os 3
DOFs — robusto a uma perturbação de até ~20% em Td. O simulador **não
quantiza Td** (TransportDelay contínuo, sem arredondamento) — a pergunta da
Parte C sobre "buffer discreto de N passos" parte de uma premissa que não se
confirma; documentado como achado. Threshold 0,3 rad/s rastreado até a **raiz
da árvore git** (commit inicial), sem origem documentável além disso.

**Nada diverge — nada precisa ser revertido ou re-promovido.**

---

## PARTE A — Determinismo de vx/vy

Re-executado `automation/identify_trans_dof('x')` e `identify_trans_dof('y')`
com os defaults da função (idênticos aos que geraram `sysid_vxvy_v2.mat`:
Ts=1/60, SgWin=7, SgOrder=2, FracHold=1/3, Seed=42, TdMax=0.15).

| Parâmetro | Original (v2) | Re-execução | Δ absoluta | Δ relativa |
|---|---:|---:|---:|---:|
| K_vx | 1,1192138689630451 | 1,1192138689630451 | **0,0** | **0,0** |
| τ_vx | 0,071783703021734604 | 0,071783703021734604 | **0,0** | **0,0** |
| Td_vx | 0,06905 | 0,06905 | **0,0** | **0,0** |
| K_vy | 1,0524082182376091 | 1,0524082182376091 | **0,0** | **0,0** |
| τ_vy | 0,12733127726773819 | 0,12733127726773819 | **0,0** | **0,0** |
| Td_vy | 0,056483333333333337 | 0,056483333333333337 | **0,0** | **0,0** |

Splits de hold-out também idênticos: vx → `{front_to_back_01_01}`; vy →
`{side_to_side_01_05, _06, _07, side_to_side_02_03}`. Fit hold-out reproduzido
exatamente (vx 86,7%; vy 86,8%/86,3%/87,3%/88,1%, média 87,1%).

**Critério do pré-registro desta verificação:** diferença > 1e-9 indicaria
não-determinismo. **Resultado: diferença = 0,0 exato** (não apenas < 1e-9) —
o pipeline é determinístico bit-a-bit dado o mesmo seed, dados e versão de
toolbox nesta máquina.

**`config/robot_geometry.json` no pipeline vx/vy:** `grep -n
"robot_radius\|wheel_radius\|robot_geometry\|0\.088\|0\.0265\|R_over_r"
automation/identify_trans_dof.m` → **vazio**. Confirmado explicitamente: o
grey-box por DOF identifica comando de corpo (`move_x`/`move_y`, já SI, sem
rotação/escala) → velocidade de corpo medida (derivada da posição da visão,
rotacionada por θ) — a cinemática de rodas não entra em nenhum ponto desta
identificação. Nenhum efeito a quantificar porque a constante não é
consumida aqui.

Artefato: `build/sysid_trans_rerun_20260724_180935.mat`.

## PARTE B — Determinismo de ω

Re-executado `automation/identify_omega_rotate()` (defaults idênticos aos
que geraram `sysid_omega_rotate_v1.mat`).

| Parâmetro | Original (v1) | Re-execução | Δ absoluta | Δ relativa |
|---|---:|---:|---:|---:|
| K_ω | 1,001623094853084 | 1,001623094853084 | **0,0** | **0,0** |
| τ_ω | 0,082760156368187524 | 0,082760156368187524 | **0,0** | **0,0** |
| Td_ω | 0,088950000000000001 | 0,088950000000000001 | **0,0** | **0,0** |

Split idêntico (treino/hold-out por evento, literal, não randomizado); fit
hold-out reproduzido exatamente (71,090978%). **Determinismo bit-a-bit
confirmado**, mesmo critério da Parte A.

**Por que o pipeline é determinístico (rastreado, não assumido):** seed fixa
(`rng(42)`) nos dois casos; split de ω é literal (lista hardcoded de eventos,
nem passa por `randperm`); Td0 inicial de ω é um valor pré-computado
hardcoded no script (documentado como desvio na sessão anterior), não
recalculado a cada rodada; `procest('P1D')` é uma otimização determinística
(sem multi-start, sem inicialização aleatória) dada a mesma `iddata` e o
mesmo ponto inicial — não há paralelismo nem estado de otimizador que
sobreviva entre chamadas. Não achei nenhuma fonte de não-determinismo para
rastrear porque **não houve nenhuma**.

Artefato: `build/sysid_omega_rerun_20260724_181006.mat`.

---

## PARTE C — Quantização de Td e discretização

### 1. Como o simulador implementa o atraso

Inspecionado via `get_param` nos 3 blocos `TransportDelay` do modelo
`parameter_estimation_model_pid_v3` (`Digital Twin/Transport Delay{,1,2}`):

```
DelayTime: Td_vx / Td_vy / Td_w   (variável SLDD, valor CONTÍNUO em segundos)
InitialOutput: 0
BufferSize: 1024
```

**Achado (contradiz a premissa da pergunta):** o bloco `TransportDelay` do
Simulink é **contínuo por natureza** — mantém um buffer de histórico
(tamanho 1024 amostras) e **interpola** para reconstruir o valor em `t − Td`
exatamente, para qualquer Td real. **Não há arredondamento de Td para um
número inteiro de passos em nenhum ponto do modelo** — nem floor, nem round,
nem ceil. O `Td_w=0,0890 s` (ou `Td_vx=0,06905`, `Td_vy=0,056483`) é usado
tal como identificado, sem quantização. A única "discretização" presente é a
do **solver de integração** (ode3, ver item 3), que afeta a TODA a dinâmica
contínua igualmente, não é algo específico do atraso.

Portanto a pergunta original ("buffer discreto de N passos? qual
arredondamento?") **não se aplica** — não existe tal quantização para
documentar. A análise de sensibilidade abaixo (item 2) é, por isso, um teste
de robustez hipotético ("e se alguém quantizasse Td, por exemplo ao portar
para uma implementação discreta?"), não a verificação de um mismatch real.

### 2. Sensibilidade do gate SE(2) à quantização hipotética de Td

Construídos 6 candidatos (θ completo = `sysid_vxvy_v2` + `sysid_omega_rotate_v1`,
com **apenas** o Td do DOF em teste substituído pelo vizinho inteiro de passos),
avaliados com `automation/eval_theta_se2_vs_placeholder.m` (MESMO script/
metodologia do gate original) nos mesmos eventos/label de cada DOF.

| DOF | Td contínuo (s) | passos | Td floor (s) | Δ% floor | Td ceil (s) | Δ% ceil | gate floor | gate ceil |
|---|---:|---:|---:|---:|---:|---:|---|---|
| vx | 0,06905 | 4,14 | 0,06667 (4) | −3,4% | 0,08333 (5) | +20,7% | **PASSA** | **PASSA** |
| vy | 0,056483 | 3,39 | 0,05000 (3) | −11,5% | 0,06667 (4) | +18,0% | **PASSA** | **PASSA** |
| ω | 0,08895 | 5,34 | 0,08333 (5) | −6,3% | 0,10000 (6) | +12,4% | **PASSA** | **PASSA** |

Detalhe (pool de todos os horizontes, Δ<0 = candidato melhor que placeholder):

| DOF | passos | n pool | Δmediana pool (m) | p (pool) | per-h p mínimo…máximo |
|---|---:|---:|---:|---:|---|
| vx | 4 | 20 | −0,1357 | 8,86e-05 | 0,125 (todos — **piso do teste, n=4**, igual ao gate original) |
| vx | 5 | 20 | −0,1335 | 8,86e-05 | 0,125 (todos — mesmo piso) |
| vy | 3 | 65 | −0,1097 | 2,41e-12 | 2,44e-4 (todos) |
| vy | 4 | 65 | −0,1113 | 2,41e-12 | 2,44e-4 (todos) |
| ω | 5 | 90 | −0,1135 | 1,74e-16 | 1,96e-4…1,96e-4 |
| ω | 6 | 90 | −0,1132 | 1,87e-16 | 1,96e-4…2,33e-4 |

**Veredito: o gate SE(2) passa em AMBOS os vizinhos de quantização, nos 3
DOFs, sem exceção.** A direção (candidato melhor) e a significância (pool
p≪0,05) são robustas a uma perturbação de até ±21% em Td — o resultado da
identificação não é frágil a essa escolha de discretização hipotética. Para
vx, o piso do teste (n=4 → p mínimo possível = 0,125 por horizonte) é
**idêntico ao já documentado no gate original** (`RELATORIO_TECNICO` §5) —
não é uma limitação nova introduzida pela quantização.

Artefatos: `results/eval_tdquant_{vx_4steps,vx_5steps,vy_3steps,vy_4steps,w_5steps,w_6steps}_{se2,wilcoxon}_*.csv`
+ `results/traj_eval_tdquant_*.mat`.

### 3. Convenção de discretização do primeiro grau

- **Identificação (`procest`):** modelo `idproc('P1D')` é **contínuo por
  construção** (`m.Ts == 0`, convenção MATLAB para "contínuo"). Não há ZOH
  nem Euler aplicado pelo `procest` — ele ajusta diretamente os parâmetros
  de uma função de transferência contínua `K·e^(−Td·s)/(τs+1)` aos dados
  amostrados, usando integração numérica interna do toolbox para simular
  durante a otimização/`compare()`.
- **Simulador:** `TransferFcn` **contínuo** + `TransportDelay` **contínuo**,
  integrados pelo solver `ode3` (Bogacki–Shampine, RK explícito de 3ª ordem)
  em passo fixo `FixedStepSize=0,0167 s` (=Ts) — confirmado via
  `out.SimulationMetadata.ModelInfo.SolverInfo` numa simulação real
  (`Type: 'Fixed-Step', Solver: 'ode3', FixedStepSize: 0.0167`).
- **Convenção usada: NENHUMA das duas é ZOH-exato (α=1−e^(−dt/τ)) nem Euler
  explícito manual.** Ambos os lados (identificação e simulador) tratam o
  modelo como genuinamente contínuo e usam integração numérica de ordem
  superior (não a aproximação de 1ª ordem que Euler faria). **Não há
  divergência de convenção para quantificar** — os dois lados são
  consistentes por construção (mesmo modelo contínuo, dois integradores
  numéricos diferentes mas ambos de ordem ≥3 na simulação e "exatos" na
  identificação dentro do toolbox). Erro de discretização do `ode3` a
  passo fixo Ts=1/60 é pequeno dado Ts/τ ∈ {0,233 (vx); 0,131 (vy); 0,202
  (ω)} — já caracterizado como consistente na sessão de identificação de ω
  (2026-07-24, `results/identificacao_omega_20260724.md`).

**Achado colateral registrado (não fazia parte do pedido, mas explica um
erro real encontrado durante esta verificação):** ao investigar o solver,
uma tentativa de simulação falhou com `"Symbol 'Ts' has multiple
inconsistent definitions"` — causada por uma variável `Ts` **residual no
workspace base do MATLAB** (deixada por um cálculo ad-hoc de sessão
anterior, valor arredondado `0,0167` conflitando com o `Ts` preciso do SLDD,
`1/60`). Resolvido com `clear Ts` antes de `ensure_model_ready`. Não é um
bug do pipeline — é uma armadilha de sessões MATLAB interativas longas;
`automation/run_td_quantization_case.m` agora inclui `clear Ts` defensivo.

---

## PARTE D — Proveniência do threshold 0,3 rad/s

Rastreado via `git log --oneline --follow` + `git show` em toda a árvore.

**Achado:** o limiar `if abs(omega) < 0.3, omega = 0; end` (junto com
`|vx|<0,1`, `|vy|<0,1`) aparece **verbatim, com o mesmo comentário genérico
`% --- ZONAS MORTAS ---` e sem justificativa física**, tanto em
`matlab/analytical/kinematicSolver.m` quanto no chart Stateflow
`inverse_kinematics` de `simulink/parameter_estimation_model_pid_v3.slx`,
em **ambos os casos já presente no commit `c283f47`** ("Initial commit: SSL
digital twin pipeline...", 2026-06-11 07:25:52 −0300) — **a raiz da árvore
git deste repositório**. Não há commit anterior a rastrear; a mensagem do
commit inicial é scaffolding genérico, sem explicar a origem do valor.

Removido/zerado no commit `eb97620` ("Parametrize wheel-chain dead zones
with default 0 (disabled)", 2026-06-11 17:26:04), cuja mensagem **confirma o
efeito medido** (84% do `cmd_vw` mascarado) mas **também não cita a origem**
do valor 0,3.

**Conclusão:** 0,3 rad/s é conhecimento herdado de **antes** da criação
deste repositório — provavelmente da era de calibração PSO (o próprio
`kinematicSolver.m` é parametrizado para receber um vetor `Action` do PSO) —
sem fonte documentada rastreável. Registrado em
`config/robot_geometry.json` → `deprecated.omega_body_deadzone_rad_s_0_3_ik`
(+ `_provenance` e `_note`, incluindo a observação de que 0,3 também estava
**errado em magnitude**: menor que o limiar elétrico real de 0,58–0,60
rad/s de corpo).

---

## Arquivos gerados/alterados nesta sessão

- `results/reidentificacao_20260724.md` (este relatório)
- `build/sysid_trans_rerun_20260724_180935.mat` (Parte A, novo, não sobrescreve v2)
- `build/sysid_omega_rerun_20260724_181006.mat` (Parte B, novo, não sobrescreve v1)
- `automation/run_td_quantization_gate.m` (versão inicial, loop único — descoberto
  contaminação de estado do SLDD entre casos, mantido só como registro do problema)
- `automation/run_td_quantization_case.m` (versão corrigida, 1 processo MATLAB
  isolado por caso — usada para os 6 resultados finais)
- `results/eval_tdquant_*_{se2,wilcoxon}_*.csv` + `results/traj_eval_tdquant_*.mat` (12+6 arquivos, Parte C)
- `config/robot_geometry.json` (bloco `deprecated`, nova entrada `omega_body_deadzone_rad_s_0_3_ik` — Parte D)

**Não tocados (guardrail):** `data/`, `latex/`, `models/sysid_vxvy_v2.mat`,
`models/sysid_omega_rotate_v1.mat`, `config/twin_params.json` (nada foi
promovido/re-promovido nesta sessão — não havia divergência a resolver).

## Conclusão

Todos os quatro objetivos (A determinismo vx/vy, B determinismo ω, C
quantização/discretização, D proveniência 0,3) foram verificados
positivamente ou documentados como "não se aplica" (C.1). **Nenhum achado
exige reversão de promoção, correção de parâmetro, ou nova coleta.** O
pipeline de identificação, do dado bruto ao θ final, é reproduzível
bit-a-bit nesta máquina/versão de toolbox, e o resultado é robusto a uma
fonte plausível de perturbação (quantização de Td) que, de qualquer forma,
não ocorre de fato no simulador.
