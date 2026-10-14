# Revisão editorial — inversão narrativa de ω (2026-07-24)

Sessão de **redação**, não de dado: nenhum experimento foi rodado, nenhum
número novo foi gerado. Todo número citado nos `.tex` abaixo vem de um
artefato listado na leitura obrigatória desta sessão (ver CLAUDE.md /
instrução da tarefa). Arquivos editados: `latex/sections/03_method.tex`,
`latex/sections/04_results.tex`, `latex/sections/05_discussion.tex`,
`latex/sections/06_limitations.tex`, `latex/tables/tab_sysid_params.tex`
(tabela existente, atualizada) e `latex/tables/tab_omega_regime.tex` (tabela
nova). Nenhum outro arquivo `.tex` foi tocado.

---

## 1. `\todocite` pendentes (agrupados por tema — insumo para a triagem da SLR)

Só existem 2 marcadores no repositório inteiro, ambos introduzidos nesta
sessão em `05_discussion.tex` (grep confirmado em toda `latex/`):

### Tema A — Identificação de sistemas em malha fechada
- **Local:** `05_discussion.tex`, §"Correlation bias as the mechanism" —
  `\todocite{closed-loop system identification / lack of persistency of
  excitation under feedback control}`.
- **O que precisa:** referência clássica/de survey sobre viés de
  identificação em malha fechada / persistência de excitação sob
  realimentação (ex.: Ljung, Forssell & Ljung, ou survey de closed-loop
  system ID). Sustenta a leitura de "viés de correlação comando↔perturbação"
  como fenômeno conhecido, não uma explicação ad-hoc desta sessão.

### Tema B — Prática de coleta de dados no RoboCup SSL
- **Local:** `05_discussion.tex`, §"A methodological lesson beyond this
  robot" — `\todocite{RoboCup SSL logging practice / general scarcity of
  dedicated system-identification data collection in robot soccer}`.
- **O que precisa:** algo que sustente a afirmação "equipes de RoboCup têm
  logs de competição abundantes e poucos experimentos dedicados de
  identificação" — TDPs/ETDPs da liga, ou survey de sim-to-real em RoboCup.
  Sem isso a frase deve ser suavizada para uma observação sem citação
  (menos forte) no lugar de uma afirmação de literatura.

**Nota:** as seções `00_abstract`, `01_introduction`, `02_related_work` e
`07_conclusion` **não foram tocadas** (restrição explícita da tarefa), mas
contêm comentários `% TODO` que dependem da SLR — não são `\todocite` no
sentido estrito, então não entram nesta lista, mas ver §3 abaixo (são
inconsistentes com a inversão narrativa e vão precisar de edição numa sessão
futura, fora do escopo desta).

---

## 2. `[A VERIFICAR]` remanescentes

**Apenas 1 marcador restou no arquivo** (`04_results.tex`, parágrafo "Heading
error") — a tarefa mencionava "2 `[A VERIFICAR]`" a resolver a partir de
`results/window_errors_20260619_000422.csv`, mas ao inspecionar o arquivo
antes de editar encontrei **apenas 1 ocorrência** no `.tex`, e a premissa da
tarefa sobre a fonte está **incorreta**: verifiquei o CSV citado e ele **não
tem coluna de `e_ang`** (só `e_pos_twin_{1.0,1.5}s_m`, `e_pos_grsim_*`,
`gap_*` — nenhuma medida angular, e só 2 horizontes, não a grade completa
usada na figura). Também verifiquei
`results/eval_twin_vs_rsim_modeA_20260617_0030.md` (fonte da Tabela 2): só
tem `e_pos`, nenhuma coluna `e_ang`. Grep por `e_ang|eang` em todo
`results/*.csv` não retornou nenhum arquivo. A curva de `e_ang` existe
**só como dado de pixel dentro dos `.svg`/`.png`** das figuras
(`rsim_twin_all_20260617_0030.{png,svg}`), não como número tabulado.

**Conclusão:** não resolvido — não é possível resolver sem re-rodar o
`eval_twin_vs_rsim` com uma tabela de erro que exporte `e_ang` (fora do
escopo "não recompute" desta sessão). Deixei o marcador no `.tex` com uma
nota explicando exatamente o que foi checado e por que continua em aberto,
para a próxima sessão não repetir a mesma checagem.

---

## 3. Decisões editoriais tomadas

1. **Narrativa invertida nas 4 seções editadas.** `04_results.tex` e
   `05_discussion.tex` agora contam: tentativa em malha fechada (reprovada,
   mantida como contraste) → coleta dedicada em malha aberta (aprovada,
   PROMOVIDA) → mecanismo (zona morta elétrica por roda, 94,3% dos comandos
   mascarados) → viés de correlação como explicação do K≈1,3 antigo. `Contribution
   C4`, o abstract e o future-work da conclusão **ainda dizem o oposto**
   ("ω não é identificável", "coleta dedicada = trabalho futuro") — ver §4,
   isso é uma inconsistência real entre seções até a próxima sessão editar
   `00_abstract`/`01_introduction`/`07_conclusion`.

2. **Tabela nova `tab_omega_regime.tex`** (malha fechada vs malha aberta:
   K, τ, Td, fit hold-out, Δmediana/p do gate) — criada em vez de inserida
   inline em `04_results.tex`, para seguir a convenção já usada no arquivo
   (`\input{tables/...}`).

3. **`tab_sysid_params.tex` atualizada** — linha de ω deixa de dizer
   "--- (placeholder)" e passa a reportar K=1,002/τ=0,083/Td=0,089/fit
   71,1%, todos de `results/identificacao_omega_20260724.md`.

4. **Grade de horizonte / âncora (desvio D5): NÃO unificada por
   recomputação** (proibida nesta sessão). Decisão registrada em
   `03_method.tex` §"Horizon grid and anchor convention": a âncora $\SEtwo$
   (pose completa) já era comum às duas campanhas e permanece única; a
   *grade de horizonte* continua sendo **duas** (harness Python
   `{0,1;0,2;0,4;0,7;1,0;1,5}` s para translação/rSim, harness MATLAB
   `{0,5;1;2;2,5;4}` s reusado para o gate de ω) porque unificá-las exigiria
   re-rodar uma das duas campanhas. Isso é declarado explicitamente no texto
   (não escondido), com a razão (D5, reuso de ferramenta já existente da
   campanha por-DOF anterior).

5. **Determinismo + sensibilidade de Td** registrados em `04_results.tex`
   (parágrafo "Interpretation: correlation bias, not plant gain") e citados
   como suporte de robustez, não como novo resultado — vêm de
   `results/reidentificacao_20260724.md`, sessão anterior a esta.

6. **Seção de bins** (`sec:results:bins`) reescrita para não atribuir mais o
   veredito INDETERMINADO de misto/rotação ao placeholder de ω (que não
   existe mais) — agora atribuído corretamente a escassez de população no
   hold-out (0 janelas mistas, 1 rotação-dominada de 265), confirmada por
   `results/phase0_metrics_report_20260724_1729.md` (re-rodado pós-promoção,
   mesma distribuição 264/1/0).

7. **Anonimização mantida**: não usei "RobôCIn"/"UFPE"/nome do robô
   versionado; citei o firmware genericamente como "the robot firmware" (não
   `ssl-embedded`); não citei quem mediu o CAD; não incluí data literal de
   deadline no texto do paper (só nesta nota interna). Checklist A1–A12 não
   violado pelas 4 seções editadas, até onde posso verificar sem rodar uma
   varredura full-text dedicada.

8. **Limitações**: as 6 pedidas na tarefa foram incluídas integralmente
   (amostra pequena de ω, robô único/sessão única, bins sem veredito por
   escassez real, constante do firmware 2,61 vs CAD 2,699 ~3,3%, constante
   0,3 rad/s sem proveniência, Ljung-Box informativo não-gate) **e** as
   limitações pré-existentes no stub anterior foram preservadas (fairness do
   baseline rSim, escopo de um único dataset, avaliação in-distribution,
   grade de tempo irregular, ambiente do rSim) — nada foi descartado, só
   substituído o que a inversão tornou obsoleto.

---

## 4. O que falta para submeter

**Bloqueador de caminho crítico (pré-existente, não mudou nesta sessão):**
Related Work (`02_related_work.tex`) continua bloqueada pela SLR — `bib`
vazio, checkpoint da triagem em 03/08.

**Inconsistências introduzidas por esta sessão que uma próxima sessão
PRECISA resolver** (fora do escopo desta, que só podia tocar
03/04/05/06):
- `01_introduction.tex`, Contribution C4: ainda diz "non-identifiability of
  yaw ... from closed-loop data" como o achado central — precisa virar
  algo como "C4: a characterization of yaw identifiability as a function of
  excitation regime, resolved via a dedicated open-loop collection."
- `00_abstract.tex` (stub, ainda não escrito): a instrução interna do stub
  ainda diz "omega is NOT identifiable ... reported as a placeholder" — essa
  instrução em si está desatualizada e vai produzir um abstract errado se
  seguida ao pé da letra.
- `07_conclusion.tex` (stub): recap diz "Yaw is characterized as
  non-identifiable ... (a finding)" e lista "dedicated pure-rotation data
  collection to identify omega" em **future work** — isso já foi feito
  (é o resultado desta sessão), precisa sair do future work e entrar no
  recap.
- **Título do paper** (`main.tex`): "... from Closed-Loop Competition Logs
  ..." não reflete mais que ω vem de uma coleta dedicada em malha aberta.
  Decisão de título não foi tomada aqui (fora do escopo dos arquivos
  autorizados) — sinalizar para a próxima sessão.

**Achado colateral desta revisão (registrado, não corrigido — exigiria
re-rodar):** a Fig. 2 (`twin_vs_rsim_all_modeA.png`, painel direito `e_ang`) e
sua tabela associada (`eval_twin_vs_rsim_modeA_20260617_0030.md`) foram
geradas **antes** da promoção de ω (17/06, com o placeholder K=1/τ=0,1/Td=0)
— diferente de $\epos$ (que não é sensível a ω em janelas
translação-dominadas), $\eang$ **é** diretamente função do modelo de ω, então
esse painel específico não reflete o ω promovido. Isso NÃO invalida o
resultado central da Fig. 2 (que é $\epos$), mas é uma inconsistência
material entre a Tabela 1 (ω promovido) e a Fig. 2 (ω placeholder) que uma
sessão futura deveria resolver re-rodando `eval_twin_vs_rsim` com o θ
promovido — sinalizado no texto (`04_results.tex`, legenda da Fig. 2), não
escondido, mas não corrigido aqui (fora do escopo "não recompute").

**Ainda pendente, não resolvido nesta sessão:**
- O `[A VERIFICAR]` de medianas de `e_ang` por horizonte (§2) — precisa de
  uma fonte numérica que hoje não existe no repo, ou aceitar não citar
  números de `e_ang`.
- Related Work / SLR (bloqueador de caminho crítico, ver acima).
- Revisão de double-blind final (checklist A1–A12) sobre o documento
  completo, não só as 4 seções tocadas.
- Verificação de que o PDF cabe em 6 páginas IEEE após todas as seções
  estarem escritas.
