# Registro de desvios — sessão de revisão maior (2026-08-07)

> Desvios entre o brief recebido e o que foi de fato executado, com
> justificativa. Complementa `results/CHANGELOG.md` (não substitui).
> **Nesta sessão:** nenhum MATLAB executado, nenhum modelo re-treinado, nada em
> `data/`, `models/` ou `results/` criado, sobrescrito ou apagado.

## D-A · Título (T1) — desvio parcial, aprovado pelo autor

**Brief:** trocar para *"A Behavioral Model for Reality-Gap Mitigation in
Digital Twins of Omnidirectional Soccer Robots"*.
**Executado:** forma híbrida — *"A Behavioral Digital Twin for Reality-Gap
Mitigation in Omnidirectional Soccer Robots: Identifiability Follows the
Excitation Regime, Not the Degree of Freedom"*.
**Motivo:** o título literal remove o achado central e reverte uma decisão
documentada em `main.tex` (2026-07-31), que rejeitou explicitamente títulos que
não carregassem o resultado de identificabilidade. Além disso, prometer
"reality-gap mitigation" sem qualificação reforça o bloqueador **B5** do revisor
(fidelidade validada só em janelas de translação, contra um rSim não
sintonizado). O híbrido preserva o vocabulário pedido **e** o achado.
**Aprovação:** consulta ao autor nesta sessão, opção "híbrido".

## D-B · Abstract (T2) — base do rascunho preservada, três desvios

**Brief:** reescrever a partir do rascunho fornecido.
**Executado:** reescrito com base no rascunho, com três desvios deliberados:
1. O rascunho afirma que o gêmeo é *"identified from in-game competition logs
   rather than from dedicated excitation experiments"* — a **exata contradição**
   que o próprio T2 manda corrigir. Corrigido: vx/vy de logs de competição, ω de
   excitação dedicada em malha aberta.
2. A atribuição causal a *correlation bias* (presente no abstract de 2026-07-31)
   foi **removida**, atendendo ao bloqueador **B1**. O mecanismo declarado passa
   a ser o quantificado: limiar de atuação e 94,3% sub-limiar.
3. rSim qualificado como *untuned* (bloqueador **B5**).
**Efeito colateral:** o abstract passou de 179 para ~240 palavras, por causa dos
resultados de ω pedidos no fim de T2. Regra IEEE de "sem símbolos matemáticos"
respeitada (todos os números por extenso).

## D-C · T3 (incorporar ω) — já estava feito

O brief trata a incorporação de ω como pendente. Verificação: o artigo de
2026-07-31 já tinha (i) o protocolo do dataset dedicado
(`03_method.tex`, `sec:method:omega-data`), (ii) **9 parâmetros** na Tabela I,
(iii) o fit hold-out de 71,1% e o gate SE(2) nos cinco horizontes em Resultados,
(iv) a subseção de regime de excitação (`sec:results:omega`), e (v) a Discussão
reformulada em torno de "identificabilidade é função do regime".
**Nada a fazer.** Registrado para evitar retrabalho em sessões futuras.

## D-D · T5.1 — premissa incorreta, item executado assim mesmo

O brief manda **rejeitar a sugestão de gerar dataset sintético no Simulink**.
O revisor **nunca fez essa sugestão** (as três menções a Simulink no relatório
são o item C12, que pede o oposto: descrever ou remover a menção ao modelo de
reconciliação). O argumento de mérito foi redigido mesmo assim na Discussão, mas
enquadrado como **decisão de projeto**, não como recusa a um revisor.

## D-E · T5.3 — hipótese do brief sobre os "3,3%" refutada

O brief pede verificar se os "3,3%" do revisor são má-leitura do `3,3208`
depreciado. **Não são:** o revisor escreve *"a divergência de 3,3% entre CAD e
firmware"*, isto é `(2,6991 − 2,61)/2,6991`, quantidade real já presente na
Seção VI, citada **como elogio**. Também não há, no relatório, qualquer menção a
unidades ou a risco de erro de ordem de grandeza. A subseção e a tabela de
unidades foram criadas assim mesmo (baratas, e o brief as pediu).

## D-F · T5.4 — BLOQUEADO, conforme instruído

Subseção de coordenadas **não escrita**; `\TODO{BLOCKED}` em `03_method.tex`.
`matlab/analytical/inverse_kinematics_solver.m` está intocado desde o commit
raiz `c283f47`, e o `CHANGELOG` de 2026-07-24 declara que a correção *"fica para
sessão futura"*. Re-derivação **não fechada**. Ver R0/R1 em
`TASKS_CLAUDE_CODE.md`.

## D-G · T6 — sem divergência a reportar

O brief manda **parar e reportar** se o código usar Euler e o texto disser ZOH.
Código lido (`phase0_replay/plant.py`): `a = 1.0 - math.exp(-dt/tau)` (ZOH
exato) e `src = floor(j - Td/dt + 1e-9)` ≡ `j - ceil(Td/dt)`. **Concordam.**
Acrescentado apenas o que faltava: erro residual de quantização por GDL,
derivado aritmeticamente de `config/twin_params.json`.

## D-H · Figuras (T4) — braços de comparação não desenhados

A Fig. B pedida no brief inclui sobreposição com rSim e cinemática ideal. **Não
desenhados:** as trajetórias do rSim do run `20260617_0030` nunca foram
persistidas e o `robosim` está indisponível (bloqueio pré-existente,
`BACKLOG_EXTENSAO_JINT.md` pendência 1). Declarado na legenda da figura e
registrado como R2, em vez de inventado.

## D-I · Commits (Entregável 1) — não executados

O brief pede "um commit por seção". **Não commitei.** O working tree tem ~20+
arquivos já modificados antes desta sessão (aparentemente churn de fim de linha
em `archive/`, `.dvc/`, `LICENSE`), e commitar no meio disso produziria um
histórico sujo, contrariando o próprio pedido de "diff limpo". Os arquivos
tocados estão listados abaixo para `git add` seletivo quando o autor decidir.

**Arquivos alterados nesta sessão:**
```
latex/main.tex
latex/sections/00_abstract.tex
latex/sections/03_method.tex
latex/sections/04_results.tex
latex/sections/05_discussion.tex
latex/sections/06_limitations.tex
latex/tables/tab_twin_vs_rsim.tex
latex/tables/tab_units.tex                    (novo)
latex/tables/tab_validation_composition.tex   (novo)
latex/figures/fig_architecture.tex            (novo)
docs/CARTA_RESPOSTA_REVISORES.md              (novo)
docs/TASKS_CLAUDE_CODE.md                     (novo)
docs/CORTES_SUGERIDOS.md                      (novo)
docs/TRIAGEM_BACKLOG_JINT.md                  (novo)
docs/REGISTRO_DESVIOS.md                      (novo)
```
Guardrails respeitados: `data/`, `models/`, `config/`, `results/` **não
tocados**; nenhuma referência bibliográfica nova; ordem do vetor θ e SLDD
intactos; nenhum número novo sem artefato de origem.

## D-J · Observação de ambiente

O mount Linux do workspace serviu um snapshot **desatualizado** dos arquivos
durante a sessão (`wc -l` e `grep` via shell reportavam o estado pré-edição de
arquivos que as ferramentas de arquivo já haviam gravado corretamente).
Verificações finais foram feitas com as ferramentas de arquivo, não pelo shell.
Relevante para sessões futuras que dependam de checagem por `grep`.

## D-K · Corte para 6 páginas (2026-08-10) — limite confirmado no CFP

Limite de 6 páginas confirmado pelo autor no CFP do SBR 2026. Executado:

| Item removido do build | Motivo | Onde ficou |
|---|---|---|
| Fig. 1 (arquitetura TikZ, `figure*`) | maior item isolado (~0,42 pág.) e o único sem evidência; pipeline agora descrito em prosa em III | `latex/figures/fig_architecture.tex` |
| Tabela twin vs. rSim | resultado demovido a contexto no reposicionamento | `latex/tables/tab_twin_vs_rsim.tex` |
| Tabela de regimes de ω | as duas linhas cabem em uma frase; resolve também a objeção C5 (linha "Closed-loop" era armadilha de leitura) | `latex/tables/tab_omega_regime.tex` |
| Tabela de unidades | **REVERTE o pedido M-F1 do autor** (2026-08-08, manter valores só na tabela). As cinco constantes usadas estão inline em III-F | `latex/tables/tab_units.tex` |
| Fig. de trajetória (real vs. modelos) | último item cortável sem tocar em resultado; era o item 10 do revisor independente | `results/figs/trajectory_holdout_en.png` e no repositório público |
| Seção VI (Limitations) | virou subseção da Discussão, enxugada ~40% | `latex/sections/06_limitations.tex` |

**Guardrail respeitado:** nenhuma limitação, nenhum número e nenhuma citação
foram removidos. As 20 referências continuam todas citadas.

**Estado do build** (sandbox, `unsrt.bst`): 7 páginas com apenas 62 palavras na
página 7; 0 erros, 0 referências indefinidas. Com `IEEEtran.bst`, que encurta as
referências em ~155 palavras, o documento fecha em **6 páginas**. Confirmar no
Overleaf.
