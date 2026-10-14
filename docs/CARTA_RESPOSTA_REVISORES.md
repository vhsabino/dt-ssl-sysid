# Carta-resposta — revisão especialista de 2026-07-31

**Artigo:** agora intitulado *"A Behavioral Digital Twin for Reality-Gap
Mitigation in Omnidirectional Soccer Robots: Identifiability Follows the
Excitation Regime, Not the Degree of Freedom"*
**Recomendação recebida:** Borderline, inclinado a *weak accept*, condicional a B1–B6 e C1–C5.
**Data desta resposta:** 2026-08-07.

> Convenção: **[FEITO]** = alterado no `.tex` nesta sessão · **[PENDENTE]** =
> exige execução, registrado em `docs/TASKS_CLAUDE_CODE.md` · **[RECUSADO]** =
> discordamos, com justificativa.

---

# Parte A — Relatório do revisor (`docs/REVISAO_ESPECIALISTA_20260731.md`)

## A.1 Bloqueadores

### B1 — Confundimento malha aberta/fechada × amplitude × sessão; "correlation bias" no abstract
**[FEITO — aceito integralmente.]** O revisor está certo, e a objeção é a mais
séria do relatório. O abstract foi **reescrito** e a atribuição causal a viés de
correlação foi **removida dele**. O abstract agora carrega o mecanismo que o
artigo de fato quantifica — o limiar de atuação por roda e os 94,3% de amostras
sub-limiar —, que é a explicação por amplitude, não por realimentação.

A Seção VI já declarava o contraste como não-single-factor; essa declaração
permanece e agora é **consistente com o abstract**, o que antes não era o caso.
Nota interna: o revisor observa que a própria análise de zona morta do artigo
sustenta melhor a explicação de amplitude — concordamos, e a mudança de abstract
reflete exatamente isso.

### B2 — Contradição entre rejeição de brancura (Ljung–Box) e o IC de `K_ω`
**[PENDENTE — R5.]** Aceito. Um IC assintótico de PEM pressupõe resíduos
brancos; o artigo declara que o Ljung–Box rejeita brancura para **os dois**
ajustes de yaw e ainda assim usa `±0.0024` para sustentar a afirmação mais forte
do texto. Duas saídas, ambas aceitáveis: IC por bootstrap de eventos, ou
rebaixamento a descritivo. **Não corrigimos por redação nesta sessão** porque a
escolha honesta exige o número, não uma reformulação — registrado como R5.

### B3 — Métodos de identificação em malha fechada nunca tentados
**[PENDENTE — R10 · parcialmente FEITO.]** A distinção do revisor é correta e
decisiva: demonstramos que *um estimador sabidamente enviesado nessa condição*
falha, não que o dado seja não-informativo. A Seção VI já reconhecia isso; o
abstract reescrito **não** afirma mais não-identificabilidade em termos
causais. A tentativa efetiva (IV / two-stage / joint I/O) é R10, extensão.

### B4 — Paradoxo: 94,3% sub-limiar, mas ganho inflado e sem joelho de zona morta
**[PENDENTE — sem correção nesta sessão.]** Este é, na nossa leitura, o ponto
mais forte do relatório e **não temos resposta redacional para ele**. O revisor
identifica corretamente que os dois argumentos do artigo (excitação insuficiente
e viés de correlação) são usados de forma intercambiável quando na verdade fazem
predições opostas sobre o ganho aparente. Reconhecemos a objeção como aberta.
Registramos: qualquer resposta exige olhar de onde vem a rotação medida em malha
fechada (arrasto, escorregamento, acoplamento de rodas, correção de heading via
IK) — o que depende de R1, já que a cadeia de IK está com defeito confirmado.

### B5 — Comparação com rSim próxima de tautológica; a cinemática ideal bate o rSim
**[FEITO.]** Aceito. Três mudanças: (i) o abstract agora qualifica o simulador
como **"untuned"**; (ii) a Seção VI passou a declarar explicitamente que **a
cinemática ideal — zero parâmetros — também supera o rSim** ao horizonte de
referência, e que isso indica que parte substancial do déficit vem do *harness*
de replay e não da física; (iii) o resultado translacional é declarado como
**limite superior** da vantagem do gêmeo. Era aritmética já contida no artigo
(0,038 + 0,063 ⇒ ideal ≈ 0,101 m < rSim 0,131 m) e omiti-la seria indefensável.

### B6 — "Gap cresce com o horizonte ⇒ vantagem dinâmica" é logicamente inválido
**[FEITO parcialmente · PENDENTE R2.]** O revisor está certo: erro de velocidade
inicial produz erro de posição que cresce linearmente em `h`, exatamente o padrão
observado, logo o argumento não discrimina as hipóteses. A Seção V já havia sido
enfraquecida em 2026-07-31; agora a Seção VI acrescenta que a **ablação de atraso
casado**, desenhada para limitar a parcela do gap atribuível ao termo de atraso,
**não foi executada**, e que por isso essa parcela é desconhecida. A ablação está
na tabela com `\TODO` e registrada como R2 — que hoje é **bloqueada** por um
problema pré-existente (trajetórias do rSim nunca persistidas, `robosim`
indisponível).

## A.2 Corrigíveis

| # | Item | Status |
|---|---|---|
| **C1** | Fig. 1 em português, com `[TODOS]` no título, desatualizada | **[PARCIAL]** O painel `e_pos` já havia sido refeito em inglês em 2026-07-31 (`twin_vs_rsim_epos_en.png`, medianas transcritas verbatim, nada recomputado). O painel `e_ang` **não é regenerável**: as trajetórias do run `20260617_0030` nunca foram persistidas e o `robosim` está indisponível. Registrado como R2/pendência 1 do backlog. |
| **C2** | Ilegível em largura de coluna | **[FEITO]** As duas figuras novas desta sessão (Fig. A arquitetura, Fig. B fits) usam `figure*` em largura dupla. |
| **C3** | Inconsistência numérica de `e_ang` (0,090 vs ≈0,103) | **[PENDENTE]** Não corrigimos porque não sabemos qual lado está certo sem re-executar — e **harmonizar silenciosamente seria pior**. Ver "Achados" abaixo. |
| **C4** | Cherry-picking na comparação de heading | **[PENDENTE]** Basta uma frase reconhecendo o cruzamento com o rSim; depende de C3 estar resolvido para não citar número errado. |
| **C5** | Tabela III: linhas pontuadas por critérios diferentes | **[PENDENTE — R3]** Aceito integralmente; é a objeção mais barata de eliminar. |
| **C6** | Duas grades de horizonte | **[PENDENTE — R8]** |
| **C7** | "hold-out fit" nunca definido | **[PENDENTE — R7]** Deliberadamente não escrito de memória: a fórmula deve sair do código. |
| **C8** | Tabela I sem incerteza | **[PENDENTE — R6]** |
| **C9** | Sensibilidade dos 94,3% ao bracket (0,5; 1,0] | **[PENDENTE — R4]** |
| **C10** | Sem declaração de disponibilidade; pré-registro sem artefato | **[PENDENTE — R11]** Concordamos que, sem timestamp verificável, "pre-registered" é retórica. |
| **C11** | Referências fracas ([3] preprint sem venue, [13] manuscrito) | **[PENDENTE]** Substituir ou marcar. Guardrail do projeto: só citar de `slr/incluidos.bib`. |
| **C12** | "high-fidelity Simulink model" não descrito | **[PENDENTE]** Descrever em uma frase ou remover a menção. |
| **C13** | Risco de desanonimização | **[CIENTE]** Não acionável sem mudar baseline; a figura em português (principal pista) já foi refeita. |

## A.3 Sugestões

- **S1** (falta figura medido × simulado) — **[FEITO]**. É a razão de a Fig. B ser
  a sobreposição medido/simulado dos três canais e não mais um gráfico de erro
  por horizonte. Ver justificativa em "Escolha da Fig. B" abaixo.
- **S2** (histograma de comando de yaw com o limiar) — **[PENDENTE]**, depende de R4.
- **S3** ("digital twin" para um simulador offline sem acoplamento bidirecional)
  — **[CIENTE]**. O texto já usa "behavioral (observational)"; o título novo
  mantém "digital twin" por decisão do autor.
- **S4** ("identifiability" sem análise de identificabilidade formal) —
  **[CIENTE]**, procede. Único diagnóstico dessa família hoje é `ρ(τ,Td) = −0,47`.
- **S5** (rSim com sintonia mínima como terceiro braço) — **[PENDENTE]**, blindaria C3 contra B5.
- **S6** (comprimir o bloco de determinismo bit-exato) — **[FEITO]** como candidato
  de corte em `docs/CORTES_SUGERIDOS.md`, item 4.
- **S7** (bootstrap por cluster de evento) — **[PENDENTE — R9]**.

---

# Parte B — Pauta do orientador (brief de revisão maior, T5.1–T5.4)

> Esta parte responde aos quatro itens do brief. **Três deles partem de
> premissas que não se confirmam** no relatório do revisor ou no repositório.
> Registrado aqui porque o brief pede recusas fundamentadas.

### T5.1 — "Rejeitar a sugestão de gerar dataset sintético no Simulink"
**Premissa incorreta.** O revisor **nunca fez essa sugestão**. As únicas três
menções a Simulink no relatório (linhas 53, 128, 185) são todas o item **C12**,
que pede o oposto: *descrever ou remover* a menção ao "high-fidelity Simulink
model" usado como padrão de reconciliação, porque o leitor não sabe o que é.

**O que foi feito mesmo assim:** o argumento de mérito é bom e independe de quem
o levantou, então foi redigido na Discussão (parágrafo *"Why not synthesize the
missing rotation set"*) — validar o grey-box contra um modelo de alta fidelidade
mede concordância entre modelos, não fidelidade observacional; a alternativa
metodologicamente correta é dado real de um regime que excite o GDL. Está
enquadrado como **decisão de projeto**, não como refutação a um revisor, porque
não houve o que refutar. A tabela de composição do conjunto de validação
(264/1/0) pedida no mesmo item **foi criada** (`tab_validation_composition.tex`).

### T5.2 — Ablação "rSim + atraso de transporte casado"
**Aceito e executado na parte redacional.** Linha na tabela com `\TODO`,
parágrafo em Resultados, script especificado em R2, e — porque a ablação está
**bloqueada** por artefato ausente — o parágrafo de ameaça à validade já foi
escrito na Seção VI, conforme o próprio brief determina ("nunca omitir").
Observação: o revisor não pediu esta ablação por este nome; ela responde de fato
a **B5/B6**, que são objeções reais e mais amplas.

### T5.3 — Constantes geométricas e os "3,3%"
**[FEITO]** — nova subseção *"Geometric constants and units"* + tabela de
unidades SI (`tab_units.tex`), com CAD (`R = 79,601 mm`, `r = 29,492 mm`,
`R/r = 2,6991`), a constante depreciada `3,3208` com o motivo da refutação (a
premissa física `R = 0,088 m`, não seu uso no firmware), as três fontes
independentes de confirmação e a auditoria de impacto nulo (`use_se2 = false`,
logo `R` não entra em `e_pos`; afeta só a classificação de bins, que reproduz
`264/1/0`).

**Mas a hipótese do brief sobre os "3,3%" está errada.** O brief pede que se
verifique se os "3,3%" citados pelo revisor são má-leitura do `3,3208`
depreciado. **Não são.** O revisor escreve (§3, Pontos fortes, item 2):

> *"reporta a divergência de **3,3% entre CAD e firmware** sem escolher um
> lado"*

Isto é `(2,6991 − 2,61)/2,6991 = 3,3%`, uma quantidade real, já presente na
Seção VI do artigo, e o revisor a cita **como elogio à honestidade**, não como
crítica. Não há nada a corrigir na carta-resposta a esse respeito. Acrescento
que o revisor **também não levantou** risco de erro de ordem de grandeza nem
pediu tabela de unidades — a busca por "unidade", "ordem de grandeza",
"milímetro" no relatório não retorna nada. A tabela de unidades foi criada assim
mesmo: é barata e não custa página relevante.

### T5.4 — Coordenadas e cinemática inversa
**[BLOQUEADO — confirmado, conforme o brief instruiu verificar.]** A subseção
**não foi escrita**; está marcada `\TODO{BLOCKED}` em `03_method.tex`.
Ver R1 e R0 em `docs/TASKS_CLAUDE_CODE.md`. Resumo em "Achados" abaixo.
Observação de escopo: este item **não aparece** no relatório do revisor — é
pauta interna, e correta.

---

# Achados desta sessão que ninguém pediu

1. **`results/CHANGELOG.md` (2026-07-24, AÇÃO 2) contém um erro factual.** Afirma
   que a `K_inv` teria `R_efetivo = 3,3245`, "a 0,11% da constante deprecated", e
   conclui que a matriz foi construída sobre a geometria deprecated. Verificação
   direta mostra `1/soma(linha ω) = 2,699070934`, idêntico ao `R/r` do CAD em
   **10 algarismos**. O diagnóstico registrado está invertido: o agregado está
   *certo*; o que está errado é a *distribuição* entre rodas (fator `√2` exato).
   Ver R0. **Não corrigi o CHANGELOG** — guardrail de não reescrever histórico;
   requer entrada nova e decisão do autor.

2. **A assimetria da `K_inv` é `√2`, não `cos(45°)`.** O brief e o CHANGELOG a
   descrevem como "assimetria cos(45°)". `cos(45°) = 0,70711` é a razão
   *menor/maior*; a razão maior/menor é `√2 = 1,41421`. Mesmo fenômeno, mas vale
   fixar o valor-alvo da correção: linha ω uniforme com
   `c = r/(4R) = 0,09262446451677743` — que é **exatamente** a média dos quatro
   elementos atuais (a `1,8e-10`).

3. **T6 (discretização) não tinha divergência a reportar.** O brief manda parar
   se o código usar Euler e o texto disser ZOH. Li `phase0_replay/plant.py`:
   `a = 1.0 - math.exp(-dt/self.tau[i])` (ZOH exato) e
   `src = floor(j - Td/dt + 1e-9)` (equivalente a `j - ceil(Td/dt)`). **Código e
   texto concordam.** O que faltava era o erro residual de quantização, agora
   explicitado por GDL (`+14,3 / +10,2 / +11,1 ms`), o que também explica de onde
   vem o "±21%" do teste de robustez já reportado.

4. **A maior parte de T2, T3 e T6 já estava feita.** O artigo de 2026-07-31 já
   incorporava ω em todas as seções, já tinha 9 parâmetros na Tabela I, já tinha
   a subseção de regime de excitação e já documentava a discretização. O rascunho
   de abstract fornecido no brief **reintroduzia** a contradição que o próprio
   brief mandava corrigir ("identified from in-game competition logs rather than
   from dedicated excitation experiments"). Foi reescrito, não copiado.

---

# Escolha da Fig. B (justificativa em duas linhas, conforme o brief)

Escolhida a **opção (i)**, sobreposição medido × simulado: a opção (ii)
(distribuição pareada do erro por horizonte com tamanho de efeito) já é
exatamente o conteúdo da Fig. 1 e da Tabela II, e duplicá-la em 6 páginas não
compra nada. A opção (i) atende ao pedido de figura mais forte do revisor (S1) —
o leitor hoje nunca vê uma resposta medida contra simulada, nem para o resultado
positivo de translação nem para o resultado central de yaw — e usa dois artefatos
já gerados e verificados no repositório. **Ressalva:** os braços rSim e
cinemática ideal pedidos no brief **não foram desenhados** porque não são
recuperáveis (trajetórias do rSim nunca persistidas); isso está dito na legenda
e registrado em R2, em vez de inventado.
