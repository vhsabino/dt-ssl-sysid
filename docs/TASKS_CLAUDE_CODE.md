# TASKS_CLAUDE_CODE.md — pendências que exigem execução

> Criado em 2026-08-07 (sessão de revisão maior do artigo).
> **Regra de ouro:** nenhum número entra no `.tex` sem vir de artefato do
> repositório. Cada item abaixo corresponde a um `\TODO{}` no LaTeX ou a uma
> objeção de revisor que **não pode ser respondida por redação**.
> Nesta sessão **não** foi executado MATLAB, não foi re-treinado nada e nada em
> `data/` ou `models/` foi tocado.

Legenda de prioridade:
**P0** = bloqueia a submissão · **P1** = move a nota do revisor · **P2** = extensão JINT.

---

## R0 — [P0] Corrigir erro factual no `results/CHANGELOG.md` (2026-07-24 13:00, AÇÃO 2)

**Achado desta sessão.** A entrada afirma que a matriz `K_inv` de
`matlab/analytical/inverse_kinematics_solver.m` teria
`R_efetivo = 3.3245`, *"a 0.11% da constante DEPRECATED (3.3208)"*, e conclui
que `K_inv` *"parece construído sobre a MESMA geometria deprecated"*.
**Isso está errado.** Verificação direta:

```python
# soma da linha omega de K_inv = omega produzido por excitação uniforme w_i = 1 rad/s
sum([0.108516310225934, 0.076732618841300, 0.076732618841300, 0.108516310225934])
# = 0.370497858134468
1/0.370497858134468   # = 2.699070934000005
0.079601/0.029492     # = 2.699070934490710   <-- CAD, bate em 10 algarismos
```

Ou seja, o **agregado** da linha ω de `K_inv` é *exatamente* a geometria do
CAD (`R/r = 2.6991`), **não** a deprecated. O único defeito real é a
**distribuição** entre rodas: `{1,4}` e `{2,3}` diferem por fator exatamente
`√2` (`1.41421356`), quando corpo rígido exige linha uniforme com valor
`r/(4R) = 0.09262446`. A média dos quatro elementos atuais é
`0.092624464533617` — igual a `r/(4R)` a `1.8e-10`.

**Ação:** corrigir a entrada do CHANGELOG (nova entrada, sem reescrever
histórico, conforme guardrail) e **redirecionar o diagnóstico**: o problema não
é geometria deprecated, é assimetria de distribuição.

**Comando de verificação:**
```bash
python3 - <<'PY'
import numpy as np
K=np.array([0.108516310225934,0.076732618841300,0.076732618841300,0.108516310225934])
r,R=0.029492,0.079601
print('razao a/b        :',K[0]/K[1],'  sqrt2 =',np.sqrt(2))
print('1/soma(linha)    :',1/K.sum(),'  R/r CAD =',R/r)
print('media vs r/(4R)  :',K.mean(),r/(4*R))
PY
```

---

## R1 — [P0] Re-derivação da cinemática inversa (BLOQUEIA a subseção de coordenadas)

**Bloqueia:** `\TODO{BLOCKED}` em `latex/sections/03_method.tex`,
`\subsection{Coordinate conventions and replication}` (`sec:method:frames`).

**Estado do arquivo (verificado nesta sessão):**
`matlab/analytical/inverse_kinematics_solver.m` está **intocado desde o commit
raiz** `c283f47`:

```bash
git log --oneline --follow -- matlab/analytical/inverse_kinematics_solver.m
# c283f47 Initial commit: SSL digital twin pipeline, automation overlay, results
```

O `results/CHANGELOG.md` (2026-07-24) declara explicitamente:
*"correcao de matlab/analytical/inverse_kinematics_solver.m ... fica para
sessao futura"*. **A re-derivação NÃO está fechada.**

**Defeito confirmado.** Linha ω de `K_inv`:
`[0.10851631, 0.07673262, 0.07673262, 0.10851631]`, razão `√2` exata entre
rodas `{1,4}` e `{2,3}`. Contradiz (a) corpo rígido — as quatro rodas estão no
mesmo raio de contato, logo contribuem igualmente para ω; e (b) a telemetria de
firmware, que mostra `d_speed` **idêntico nas 4 rodas** em todos os 10 eventos
`rotate` (razão `1.0000` exata).

**Valor esperado após re-derivação:** linha ω uniforme
`[c,c,c,c]` com `c = r/(4R) = 0.09262446451677743`.

**Ação necessária (fora do escopo de redação):**
1. Recuperar os ângulos de montagem das 4 rodas do CAD
   (`config/robot_geometry.json` não tem os ângulos, só raios — **verificar**).
2. Remontar a matriz direta `K` (corpo → rodas) e recomputar `pinv(K)`.
3. Comparar com a `K_inv` atual, documentar a origem do fator `√2`.
4. Só então escrever a subseção de replicação.

**Critério de aceite:** linha ω uniforme; linhas `vx`/`vy` consistentes com os
ângulos do CAD; `1/soma(linha ω)` continua em `2.6991`.

---

## R2 — [P0] Ablação "rSim + atraso de transporte casado"

**Preenche:** `\TODO{ablation}` × 4 em `latex/tables/tab_twin_vs_rsim.tex` e
`\TODO{ablation not yet executed}` em `latex/sections/04_results.tex`.

**Definição:** aplicar o `Td` identificado do gêmeo à **saída** do rSim como
deslocamento puro (sem re-simulação), pontuando nas **mesmas** janelas,
horizontes e gate do run primário.

**Script a criar:** `phase0_replay/eval_rsim_delay_ablation.py`, reutilizando
`phase0_replay/eval_twin_vs_rsim.py` (modo A) e aplicando o shift inteiro
`m_i = ceil(Td_i/dt)` sobre a série de pose do rSim antes de `metrics.evaluate`.

```bash
python -m phase0_replay.eval_rsim_delay_ablation \
  --mode A --params config/twin_params.json \
  --holdout config/holdout_events.json --metrics config/metrics.json \
  --out results/eval_rsim_delay_ablation_$(date +%Y%m%d_%H%M).md
```

**BLOQUEIO PRÉ-EXISTENTE:** `docs/BACKLOG_EXTENSAO_JINT.md` (pendência 1)
registra que as trajetórias do run `20260617_0030` **nunca foram persistidas**
e que o `robosim` está indisponível no ambiente atual. Enquanto isso não for
resolvido, R2 **não é executável** e o parágrafo de ameaça à validade já
redigido em `06_limitations.tex` permanece como substituto.

---

## R3 — [P1] Recomputar a linha de malha fechada da Tabela III com o mesmo critério (revisor C5)

A nota de rodapé de `tab_omega_regime.tex` admite que a linha fechada foi
pontuada pelo critério antigo de regime-split (`31.9%` / `-11.2%`), não por um
`fit` hold-out único — o que **desmente** o título da própria tabela
(*"same identification tooling; only the excitation regime differs"*). É a
objeção mais barata de remover do artigo inteiro.

```matlab
% reaproveitar o pipeline de identificação com split event-wise, seed 42,
% aplicado aos eventos shoot_to_goal de alta rotação
run('src/bootstrap_paths.m');
identify_omega_from_splits('label','shoot_to_goal','holdout_mode','eventwise','seed',42);
```
Saída esperada: um número único de `fit` hold-out para a linha fechada,
substituindo `n/a†`.

---

## R4 — [P1] Sensibilidade dos 94,3% ao bracket do limiar (revisor C9)

Os `94.3%` são a estatística mais citada do artigo (abstract, Fig. A, Results,
Conclusão), derivados do limiar `0.581–0.600 rad/s`, cujo **bracket empírico é
`(0.5, 1.0]`** — bem mais largo. Reportar a fração também em `0.5` e `1.0`.

```bash
python scripts/omega_cmd_below_threshold.py \
  --splits data/extracted/2026-05-18_19-2-15/splits \
  --thresholds 0.5 0.581 0.600 1.0 \
  --out results/omega_threshold_sensitivity_$(date +%Y%m%d_%H%M).csv
```
*(script a criar; a lógica existente está em
`results/identificacao_omega_20260724.md` Etapa 4)*

---

## R5 — [P1] IC robusto para `K_ω` (revisor B2 — contradição interna)

O artigo declara que o Ljung–Box **rejeita brancura para os dois ajustes de
yaw** e, ao mesmo tempo, usa um IC assintótico de largura `±0.0024` sobre
`K_ω` para afirmar unidade e "refutar" `1.3`. Um IC assintótico de PEM
pressupõe resíduos brancos. **Ou** produzir um IC por bootstrap de eventos,
**ou** rebaixar a afirmação a descritiva no `.tex`.

```matlab
% bootstrap event-wise sobre os 4 eventos de treino do dataset rotate
bootstrap_omega_ci('n_boot',2000,'seed',42, ...
  'out','results/omega_ci_bootstrap_YYYYMMDD.csv');   % script a criar
```

---

## R6 — [P1] Incerteza na Tabela I (revisor C8)

Nove parâmetros, zero barras de erro. Acrescentar IC ou desvio entre eventos ao
menos para os seis parâmetros translacionais, a partir dos fits por evento já
existentes em `results/fit_holdout_vxvy_20260731_024049.csv`.

---

## R7 — [P1] Definir "hold-out fit" (revisor C7)

É o critério de aceitação de todas as três tabelas e do gate pré-registrado de
60%, e **nunca é definido** no artigo. Extrair a fórmula exata do código
(`automation/identify_trans_dof.m` / `src/identify_omega_from_splits.m`):
NRMSE? `fit` do `compare` do MATLAB? sobre qual sinal? por evento ou
concatenado? Uma linha resolve. **Não escrever de memória — ler o código.**

---

## R8 — [P2] Grade de horizonte unificada (revisor C6 / desvio D5)

Fidelidade usa `h ∈ {0.1 … 1.5} s`; gates por GDL usam `h ∈ {0.5, 1, 2, 2.5, 4} s`.
Re-executar uma das campanhas na grade da outra.

## R9 — [P2] Bootstrap por *cluster* de evento (revisor S7)

As 49 janelas "independentes" vêm de 10 eventos. O bootstrap de blocos trata
correlação serial *dentro* do segmento, não o agrupamento por evento.

## R10 — [P2] Estimadores closed-loop-aware (revisor B3)

IV / two-stage / joint input-output sobre os **mesmos** logs de competição.
É o item que converteria a peça central de "interpretação favorecida" em
"achado demonstrado". Grande esforço; extensão JINT.

## R11 — [P1] Link anonimizado de código/dados + artefato de pré-registro (revisor C10)

Sem timestamp verificável, "pre-registered" é retórica. Anonymous GitHub ou OSF
anonymous view resolve C10 e parte de R12 de uma vez.
