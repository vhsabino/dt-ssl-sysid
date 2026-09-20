# Revisão independente — SBR/LARS 2026 (Robótica 2026, João Pessoa)

**Artigo:** "A Behavioral Model for Reality-Gap Mitigation in Digital Twins of Omnidirectional Soccer Robots"
**Data da revisão:** 2026-08-10
**Revisor:** independente, sem acesso a dados, código ou artefatos do autor. Base: exclusivamente o PDF compilado a partir de `latex/`.
**Rodada:** revisão NOVA. Não li relatórios de rodadas anteriores; o artigo foi julgado como está.

---

## 0. Nota de procedimento (compilação)

Não havia PDF atualizado. Gerei um a partir de `latex/`.

O mount Linux entrega cópias corrompidas dos arquivos editados recentemente, de duas formas distintas — e as duas ocorreram:

- **Padding**: `01_introduction.tex` veio com ~1.8 kB de espaços no fim (tamanho em cache maior que o real). Conteúdo íntegro.
- **Truncamento**: `main.tex`, `00_abstract.tex`, `03_method.tex`, `04_results.tex`, `05_discussion.tex` e `tables/tab_omega_regime.tex` vieram **cortados no meio de uma frase**. Três deles passaram na checagem de chaves/ambientes balanceados mesmo truncados (o corte caiu num ponto balanceado), então a validação estrutural sozinha não bastou — foi preciso conferir o *tail* de cada arquivo.

Recuperei o conteúdo real dos seis arquivos com a ferramenta `Read` (filesystem verdadeiro) e reescrevi em `/tmp/rev`. **Nenhum texto foi inventado.** Build: `pdflatex → bibtex → pdflatex ×2`, com `siunitx` substituído por um stub de mesma largura tipográfica e `IEEEtran.bst` (indisponível no sandbox) substituído por `unsrt`.

Resultado: **0 referências indefinidas, 0 `??`, 0 `\TODO` renderizado, 0 overfull box acima de 10 pt.** O fonte compila limpo.

Confirmei que `06_limitations.tex` está fora do build (Limitações viraram §V-C) e que `tab_units`, `tab_validation_composition`, `tab_omega_regime`, `tab_twin_vs_rsim` e `fig_architecture` não são incluídos — nenhum deles é referenciado no texto, então não há referência pendurada.

---

## 1. Resumo do artigo nas minhas palavras

O artigo modela um robô SSL omnidirecional de 4 rodas como **três canais SISO desacoplados de primeira ordem com tempo morto (FOPDT)**, um por grau de liberdade (`vx`, `vy`, `ω`), totalizando nove parâmetros. A pergunta central é *metodológica*, não de modelagem: **quanto de um modelo comportamental dá para identificar a partir dos logs de competição que as equipes já gravam, e o que esses logs não conseguem sustentar?**

A resposta tem duas metades, e a assimetria entre elas é a contribuição:

- **Translação sim.** `vx` e `vy` são identificados diretamente dos logs de malha fechada, com fit hold-out de 86,7% e 87,1%.
- **Yaw não.** O mesmo estimador, a mesma estrutura, sobre os mesmos logs, dá ganho `K_ω ≈ 1,35`, fit 52,6% (abaixo do gate de 60%) e **piora** a posição em free-run. Uma coleta dedicada curta em malha aberta (escada de degraus de yaw com `vx=vy=0`) recupera `K_ω = 1,0016` e fit 71,1%.

O diagnóstico do *porquê* é a parte mais forte do artigo. Os autores mostram que o comando de yaw, durante o jogo, carrega **mediana de 1,0% do setpoint por roda** — as rodas já estão girando por causa da translação (setpoint translacional mediano 24,0 rad/s, 15× o clamp de 1,567 rad/s). Logo o yaw não está *desligado* pela zona morta (ela só engaja em ~2% das amostras); está **diluído**. Isso explica duas anomalias que a leitura ingênua da zona morta prevê e que não acontecem (nem o ganho deflaciona, nem aparece joelho de zona morta no sinal de corpo).

A avaliação de fidelidade é feita em **free-run**: janelas re-ancoradas em SE(2) no instante `t0`, roladas até 1,5 s dirigidas só pelo comando, sem teacher forcing. Contra uma baseline de **cinemática ideal** (zero parâmetros, mesmo harness, mesma inicialização), o modelo reduz o erro mediano de posição de 0,101 m para 0,039 m em `h_ref = 0,4 s`, ganhando em 10 de 10 eventos hold-out. Uma decomposição de Shapley sobre o fatorial 2³ de `{K, τ, Td}` atribui 55% ao `τ`, 43% ao `Td` e 2% ao ganho; um braço adicional mostra que o ganho só existe **em combinação com a velocidade inicial medida** (modelo do repouso: 0,114 m; só velocidade inicial extrapolada: 0,160 m; ambos piores que a ideal). Um controle negativo (calibração bayesiana conjunta de 9 parâmetros, 400 avaliações) empata com o grey-box por DOF.

**Reconstruí a contribuição em uma leitura?** Sim. O artigo é bem escrito e a tese é clara. Mas reconstruí a contribuição *apesar do título*, não por causa dele — ver objeção 3.

---

## 2. Notas (1–5)

| Critério | Nota | Justificativa curta |
|---|---|---|
| Originalidade | **3** | A estrutura FOPDT por DOF é livro-texto (o próprio artigo cita Åström & Hägglund [12]). O que é original é o *diagnóstico de identificabilidade por parcela de atuação* e a inversão de veredito sob tooling idêntico. É uma contribuição real, mas incremental e de escopo estreito. |
| Solidez técnica | **3** | A aritmética interna é impecável (verifiquei sete cadeias numéricas independentes — §6.3). Mas há uma possível fuga de informação não endereçada (filtro não-causal na condição inicial), uma afirmação de disjunção treino/teste que o próprio §IV-A parece contradizer, e nenhuma baseline competitiva. |
| Rigor experimental | **3** | Pré-registro, gate multi-horizonte, teste pareado + tamanho de efeito + bootstrap, controle negativo, honestidade sobre a mudança pós-hoc da unidade de análise — tudo isso é acima da média para SBR/LARS. Puxam a nota para baixo: n=1 evento hold-out para `vx`, n=6 eventos para `ω` numa sessão só, e uma baseline única que é um espantalho conhecido. |
| Clareza | **3** | A prosa é boa e densa. Mas o PDF tem **uma frase quebrada na Conclusão** e **duas contradições internas diretas** entre seções. Isso não é estilo, é defeito. |
| Relevância SBR/LARS | **5** | Encaixe perfeito: SSL, RoboCup, gêmeo digital, comunidade brasileira de robótica. É exatamente o tipo de trabalho que a LARS deve publicar. |
| Reprodutibilidade | **2** | O artigo promete "instructions to reproduce every number above" numa URL que **retorna HTTP 404** (verificado). Sem artefato, todas as alegações de determinismo bit-exato e de reconciliação com Simulink são não-verificáveis. |

---

## 3. Pontos fortes que sustentam aceitação

Sendo específico, porque estes pontos são genuínos e alguns são incomuns:

1. **A pergunta é a certa e é respondida com um número, não com uma opinião.** "Quanto da atuação por roda o comando deste DOF carrega?" é uma métrica computável dos logs *antes de qualquer ajuste*. O §V-D é explícito e correto ao dizer que isso **não** é uma reformulação de excitação persistente ("which is a spectral property of the input [19]") e ao notar que os dois diagnósticos são complementares e aqui concordam (1% de atuação, 56% de variância explicada). Essa honestidade conceitual é rara.

2. **A inversão de veredito sob tooling idêntico é um desenho experimental limpo.** Mesma estrutura P1D, mesmo estimador, mesmo gate SE(2), mesma população de avaliação, mesmo placeholder de referência — só a origem dos dados muda, e o veredito passa de `+0,0489 m (pior, p=3,8e-9)` para `−0,1138 m (melhor, p=1,7e-16)`. É a forma mais forte de sustentar a tese central.

3. **A ablação foi consertada na direção certa e contra o interesse dos autores.** Trocar a ablação cumulativa (dependente de ordem) pelo fatorial 2³ com Shapley **derrubou** a narrativa mais vendável ("o lag explica quase tudo") e a substituiu por "lag e tempo morto são comparáveis, 55% vs 43%". O texto ainda explica *por que* a leitura cumulativa dava 90% ao lag ("an artifact of ordering, since the two terms are partly redundant"). Isso é o oposto de p-hacking e merece ser dito.

4. **O braço de condição inicial é a análise que eu teria exigido, e já está lá.** O artigo poderia ter escondido que a vantagem depende de `v0`. Em vez disso mede: modelo do repouso 0,114 m (pior que a ideal), só `v0` extrapolado 0,160 m (pior ainda), combinação 0,039 m. E declara: "neither ingredient helps on its own". Note também que o canto `(K=1, τ=0, Td=0)` do fatorial **é** a cinemática ideal, então a decomposição de 0,062 m é internamente coerente.

5. **A mudança pós-hoc da unidade de análise é declarada, não escondida** (§III-G): "the per-event pairing ... was adopted later, in revision ... we flag the change rather than present it as pre-registered". E escolheram a versão *conservadora* (p=9,8e-4, o piso de n=10) em vez do p por janela, muito menor. Isso é exatamente o comportamento correto.

6. **O controle negativo é reportado honestamente como empate.** A calibração conjunta ganha em 7/10 eventos com p=0,042 — formalmente significativo — e os autores o chamam de empate porque a margem é 4 mm. Ler magnitude em vez de p é a leitura certa.

7. **A aritmética fecha.** Verifiquei independentemente: soma de Shapley (0,034+0,027+0,001=0,062, com 55/43/2%); piso do Wilcoxon (2⁻¹⁰=9,77e-4); 49×1,5=73,5 s; 264/265=99,62%; 24,0/1,567=15,3×; Euler/ZOH sobrestima 12,0%/6,7%/10,4% para τ=0,072/0,127/0,083; zona morta 1,567/2,699=0,5806 e 1,567/2,61=0,6004 (bate com "0,58–0,60"); spread 3,41% (bate com "~3,3%"); quantização de `Td` 4 vs 5 passos = −20% (bate com "±21%"). **Todos batem.** Isso é raro e deve constar da revisão.

8. **Contextualização física da métrica** (§IV-C): "the median commanded speed ... is ~1 m/s, so the reference horizon spans about 0.4 m of travel and the robot's contact diameter is 0.16 m". Poucos artigos dizem ao leitor se o erro reportado é grande ou pequeno. Este diz.

9. **A comparação com [13] (Simscape, 150–240 mm) é declarada não-comparável** — "We mention it only because the reader will otherwise make the comparison unaided". Correto e desarma uma comparação injusta antes que ela aconteça.

---

## 4. Fraquezas

### (i) BLOQUEADORAS

**B1. O artigo tem ~7,3 páginas de conteúdo num limite de 6. É desk-reject no JEMS.**
Medido no sandbox (`unsrt`): **8 páginas**. Corpo (Abstract → Conclusão) preenche integralmente as páginas 1–7; as referências ocupam 62 linhas tipografadas (~0,9 de uma coluna) na página 8. Estimativa para o build real com `IEEEtran.bst` (entradas ~30% mais curtas): referências caem para ~44 linhas (~0,6 coluna ≈ 0,3 página), o corpo **não muda**, então **8 páginas impressas, ~7,3 de conteúdo**. Detalhe em §6.1. Isto é ~1,3–1,5 página acima do limite, ou ~1.200–1.400 palavras (≈20% do corpo de 6.402 palavras).

**B2. A Conclusão tem uma frase quebrada, visível no PDF.**
Página 7, §VI, renderiza literalmente:

> "...and only in combination with the measured initial velocity. **characterizing why the** logs cannot support it: during play the yaw command carries a median 1% of the per-wheel actuation..."

A oração "Yaw needed a short dedicated open-loop campaign, after" foi engolida por uma linha de comentário LaTeX em `07_conclusion.tex:17` (o `%` da linha anterior continuou e absorveu a prosa). Efeito duplo: (a) frase começando em minúscula sem sujeito, no parágrafo de fecho do artigo; (b) **a Conclusão nunca chega a afirmar que o yaw exigiu a coleta dedicada** — o segundo dos dois resultados centrais desaparece do fecho. Um revisor que leia só abstract + conclusão sai sem o achado.

**B3. Contradição direta Resultados × Limitações sobre o erro de heading.**
- §IV-C: "the model's median `e_ang` is **the lowest of the three plants at every horizon**". A Tabela II confirma (h=1,50: modelo 0,090; ideal 0,095; rSim 0,094). A legenda da Tabela II também afirma "THE MODEL IS LOWEST IN BOTH QUANTITIES AT EVERY HORIZON".
- §V-C (Limitações): "**heading error exceeds rSim's at long horizons**, so the position claim does not transfer to heading."

As duas não podem ser verdadeiras. A Tabela II sustenta a primeira. A frase das Limitações é resíduo de uma versão anterior. Como está, o artigo se autoinvalida num ponto que um revisor checa.

**B4. Contradição direta Introdução (C3) × Resultados sobre a ablação.**
- Introdução, C3: "an ablation shows **the first-order lag, not the dead time**, carries the effect."
- §IV-C: "The lag and the dead time are therefore **comparable** contributors, **not one dominant and one marginal**" (55% vs 43%).
- Abstract: "attributes the improvement to the time constant and the dead time **in comparable parts**".

Ou seja: o abstract e os resultados concordam entre si, e a **declaração de contribuição da Introdução afirma o contrário do resultado do próprio artigo**. Pior: C3 é uma das quatro contribuições numeradas. Se um revisor ler só as contribuições, sai com a conclusão que o §IV-C explicitamente refuta.

**B5. A URL do artefato não existe (HTTP 404, verificado).**
§VI: "Code, configurations, the frozen hold-out list, both datasets and the pre-registration document with its commit timestamp are released at `https://github.com/anon-ssl-dt/behavioral-twin-ssl`, with instructions to reproduce every number above."
`curl` → **404**. Sem isso, ficam sem verificação: o determinismo bit-exato ("reproduces all nine parameters exactly", §IV-A), a reconciliação com o Simulink ("≤6 mm / ≤9e-4 rad", §III-B), o pré-registro do gate de ω, e a lista congelada de hold-out. O artigo faz da pré-registração um argumento central de rigor — e a evidência dela é justamente o que não está acessível.

### (ii) CORRIGÍVEIS antes da câmera-pronta

**C1. Possível vazamento de informação pelo filtro não-causal na condição inicial.**
Este é o meu maior receio *técnico*, e o artigo não o endereça em lugar nenhum.
§III-C: "Measured body velocity, **used only for identification and for the initial condition**, is obtained by **smoothing** the vision position with a low-order polynomial (**Savitzky–Golay**) filter, **differentiating it by central differences**".
Savitzky–Golay centrado e diferenças centrais são **não-causais**: `v(t0)` usa amostras de posição **posteriores** a `t0`. Como as janelas são ancoradas em `t0` e roladas para a frente, a semente `v0` do modelo pode conter informação de dentro da janela de avaliação. Isso colide frontalmente com a contribuição C2 — "no correction from measured data inside the window" — e é material porque o §IV-C demonstra que **toda** a vantagem depende de `v0` (do repouso o modelo faz 0,114 m, pior que a ideal). Em `h=0,1 s` o horizonte tem 6 amostras; uma janela SG centrada de comprimento comparável cobriria boa parte dele. O artigo nunca declara o comprimento nem a causalidade do filtro. **Correção:** declarar o comprimento da janela SG e ou (a) provar causalidade, ou (b) recomputar `v0` com estimador causal e reportar o delta. Os dados já existem.

**C2. A afirmação de disjunção treino/teste parece falsa como escrita.**
§IV-C: "**No event contributed to both parameter selection and fidelity scoring.**"
Mas §IV-A: "against the previous, slower parameters they **improve every event-by-horizon cell of the SE(2) gate (20/20 and 65/65)**" — isto é uma decisão de *promoção de modelo* (v2 sobre a versão anterior) tomada sobre os eventos de hold-out da identificação. E o próprio §IV-C diz que "the five that validated `vx` and `vy` **are a subset of them**" (dos 10 de fidelidade). Logo 5 dos 10 eventos de pontuação de fidelidade participaram de uma escolha de modelo. A frase como está é forte demais; o correto seria "nenhum evento entrou no *ajuste* dos parâmetros", que é outra coisa. **Correção:** reformular, ou re-particionar de modo que a afirmação seja literalmente verdadeira (há 46 eventos disponíveis).

**C3. Inconsistência numérica: 0,038 vs 0,039 m (o número-manchete).**
- Abstract: "0.038 against 0.101 metre"; §IV-C texto: "0.038 m against 0.101 m at `h_ref`".
- Tabela II (h=0,40): **0,039**; §IV-C ablação de CI: "Only the combination reaches **0.039** m"; §V-B: "the **39**–119 mm reported here".
São 3 ocorrências de 0,039 contra 2 de 0,038, para a mesma quantidade. Não é cosmético: a decomposição de Shapley soma 0,062 m, que é `0,101 − 0,039`, **não** `0,101 − 0,038 = 0,063`. Ou seja, o valor do abstract é aritmeticamente incompatível com a própria ablação do artigo.

**C4. Inconsistência numérica: rSim 0,129 vs 0,131 m em `h_ref`.**
Tabela II diz **0,129**; §IV-C texto diz "rSim reaches **0.131** m at `h_ref`". Consequência em cadeia: o gap declarado "+0,093 m" vem de `0,131 − 0,038`; pela Tabela II seria `0,129 − 0,039 = 0,090`. Provável mistura de duas campanhas (`eval_twin_vs_rsim_modeA` vs `epos_eang_three_models`), mas o PDF apresenta as duas como a mesma grandeza sem ressalva.

**C5. Dois valores diferentes para "o fit de ω em malha fechada", sem explicação no PDF.**
§IV-D reporta **52,6%** (ajuste direto em eventos de alta rotação) e, mais adiante, **44,8%** (re-ajuste com split event-wise e Eq. 2). A justificativa existe — mas só num comentário LaTeX ("a campanha original reportava 52,6%"), invisível ao revisor. No PDF, o leitor vê dois números para o que parece a mesma coisa. **Correção:** uma oração explicando que são duas campanhas com critérios de split diferentes, ambas abaixo do gate.

**C6. C3 da Introdução também sobreafirma "halves in all ten".**
"the model **halves** the median position error of the baseline **in all ten** hold-out events". O medido é: (a) vence em 10/10, e (b) reduz à metade *na mediana em `h_ref`*. A Fig. 2(b) mostra pares em que a razão claramente não é 2× (p.ex. ~0,053 → ~0,040). São duas afirmações distintas fundidas numa mais forte que ambas. (Curiosamente a Conclusão já traz a versão corrigida — "lowers ... in all ten hold-out events, halving it at the reference horizon" — mas a Introdução não.)

**C7. `vx` tem **um único** evento de hold-out.**
Rodapé da Tabela I: "`vy` ±0.8 p.p. over 4; ω 65.0/77.2 over 2; **`vx` has a single hold-out event**". O "86,7%" é, portanto, uma medida de n=1, reportada lado a lado com o 87,1% de `vy` (n=4) como se tivessem o mesmo peso, e o abstract funde os dois em "roughly 87 percent hold-out fit". Está declarado no rodapé — crédito por isso — mas merece uma oração no corpo, porque é a evidência de um dos dois canais que sustentam o resultado principal. Com 46 eventos disponíveis, um split mais generoso parece barato.

**C8. Citação [3] mal alocada e incompleta.**
§VI: "a robot-learning environment such as **Isaac Sim or MuJoCo [3]**". A ref. [3] é Machado et al., sobre planejamento por RL na SSL — não é fonte para Isaac Sim nem MuJoCo. Além disso [3] aparece na bibliografia como "**Preprint.**", sem ano, sem venue, sem arXiv ID: é a única entrada incompleta das 19.

**C9. `264` vs `265` janelas não-sobrepostas.**
§IV-B: "of **265** dense windows (**49** non-overlapping), **264** fall in the translation bin". §IV-C: "The scored population is **264** dense windows, **49** non-overlapping". As 49 não-sobrepostas foram contadas sobre 265; atribuí-las às 264 do bin de translação deveria dar ≤49. Como os 73,5 s (= 49×1,5) dependem disso, vale acertar.

**C10. O CI por evento não tem método declarado.**
§III-G descreve "a moving-block bootstrap (block ~`H_max`)", que é um método para lidar com correlação serial **entre janelas**. Mas §IV-C reporta "bootstrap CI **over events** [+0.038, +0.097] m" com n=10. Bootstrap de blocos móveis sobre 10 eventos independentes não faz sentido; presumivelmente foi bootstrap simples. Não está dito qual.

**C11. Figura 1 mostra 95% de regime permanente e ~5% do transiente.**
Cada painel cobre ~10 s de degrau constante; o transiente que codifica `τ_ω` e `Td_ω` ocupa os primeiros ~0,3 s. Consequência: o "fit hold-out 71,1%" é dominado por acertar o **patamar** (isto é, `K_ω`) — um modelo com `τ=0, Td=0` e o ganho certo obteria fit quase idêntico. Isso é benigno para a alegação principal do artigo (que é sobre `K_ω → 1,00`), mas significa que **`τ_ω` e `Td_ω` estão essencialmente não validados** por esta figura, e nunca são validados em posição depois (99,6% das janelas são translacionais). **Correção barata:** um inset com zoom nos primeiros 0,5 s de cada painel. Os dados já existem.

**C12. Nenhuma evidência de série temporal para o resultado-manchete.**
O único traço medido-vs-simulado do artigo (Fig. 1) é do canal **ω** — o canal que o artigo declara não validado em fidelidade. Para translação, que é a alegação central, o leitor recebe só medianas agregadas (Tab. II, Fig. 2). Para um artigo cuja tese é *fidelidade comportamental observacional*, faltar um único traço de trajetória translacional real vs. modelo é uma lacuna de evidência conspícua.

### (iii) Opcionais

- **O1.** §II tem ~330 palavras e nenhuma citação de projeto de experimento / análise de identificabilidade (Fisher, input design) — justamente a vizinhança do achado. A "parcela de atuação" é apresentada como diagnóstico novo sem ser posicionada contra medidas de SNR/identificabilidade existentes.
- **O2.** [2] (rSoccer) é citado por arXiv apesar de ter versão publicada em LARS 2021.
- **O3.** Fig. 2(b) mostra ~8 pares visualmente distinguíveis para 10 eventos (sobreposição). Um leve jitter horizontal resolveria.
- **O4.** §III-G usa duas grades de horizonte diferentes ({0,1…1,5 s} e {0,5…4 s}) em dois harnesses distintos. Está declarado e justificado ("reported on its native grid ... rather than recomputed") — aceitável, mas obriga o leitor a rastrear qual número veio de onde.

---

## 5. As perguntas difíceis que eu faria aos autores

1. **O filtro Savitzky–Golay que produz `v0` é causal?** Qual o comprimento da janela? Se for centrado, `v0` usa amostras posteriores a `t0` — dentro da janela de avaliação. Como toda a vantagem do modelo depende de `v0` (§IV-C: do repouso, 0,114 m, pior que a baseline), quanto do "0,039 vs 0,101" sobrevive a um estimador estritamente causal?

2. **Batendo cinemática instantânea, qual é a barra?** A baseline salta instantaneamente para a velocidade comandada — tem viés sistemático conhecido, e o modelo recebe `v0` medido que a baseline (memoryless) não pode usar. Vencê-la 10/10 é quase garantido. **Qual baseline competitiva existe no artigo?** O rSim está declaradamente não sintonizado e é reportado "as context". Então o artigo, na prática, não tem nenhum comparador ajustado. O que acontece contra um FOPDT com parâmetros nominais/de catálogo, ou contra um rSim com seus poucos parâmetros ajustados pelo mesmo procedimento?

3. **Como "No event contributed to both parameter selection and fidelity scoring" (§IV-C) se concilia com a promoção de v2 decidida sobre o gate SE(2) `20/20` e `65/65` (§IV-A), sabendo que esses 5 eventos são subconjunto dos 10 de fidelidade?**

4. **Por que `vx` tem um único evento de hold-out** quando o corpus tem 46 eventos? O 86,7% é robusto a um split diferente?

5. **A Tabela II diz que o modelo tem o menor `e_ang` em todos os horizontes; §V-C diz que ele excede o do rSim em horizontes longos. Qual das duas?** E se for a Tabela, por que o artigo mantém, como limitação declarada, uma afirmação que seus próprios dados refutam?

6. **O fit de 71,1% para ω mede `τ_ω` e `Td_ω`, ou só mede `K_ω`?** Num degrau de 10 s com transiente de 0,3 s, um modelo `(K=1, τ=0, Td=0)` atingiria que fit? Se for próximo de 71%, o gate pré-registrado de 60% não discrimina a dinâmica que vocês afirmam ter identificado.

7. **A inversão de veredito (§IV-D) é atribuída ao "excitation regime", mas o §V-C lista três diferenças simultâneas** entre as campanhas (topologia de malha, razão yaw/translação, sessão). O texto reconhece isso — então **o que exatamente a inversão isola?** A frase "so the inversion isolates the tooling, not a single causal factor" está correta, mas então a tese do título/abstract ("closed-loop logs cannot supply yaw") é uma inferência, não uma medida.

8. **O controle negativo empata em 0,042 m e o resultado principal é 0,039 m** (ambos em `h_ref`, unidades de análise diferentes: por evento vs. por janela). Um leitor pode concluir erroneamente que a calibração conjunta é pior. Podem reportar as duas na mesma unidade?

9. **Por que o gap por evento (+0,069 m) difere do gap por janela (0,062 m)?** Ambos aparecem sem reconciliação.

10. **O repositório está em 404.** Ele existirá no momento da revisão? Como o pré-registro pode ser auditado — que é o argumento de rigor mais forte do artigo — sem ele?

11. **"Reality-Gap Mitigation" no título: qual gap foi mitigado, e medido como?** Nenhuma política é treinada, nenhuma é transferida, nenhum controlador roda melhor. O artigo mede erro de predição em replay. (Ver objeção 3 do sumário.)

---

## 6. Checagens solicitadas

### 6.1 Cabe em 6 páginas? **Não.**

| | |
|---|---|
| **Medido no sandbox (`unsrt`)** | **8 páginas** |
| Corpo (Abstract → §VI Conclusão) | páginas 1–7, **ambas as colunas cheias até o fim da p. 7** |
| Referências (19 entradas, `unsrt`) | 62 linhas tipografadas ≈ 0,9 coluna, início no topo da p. 8 |
| **Estimativa para o build real (`IEEEtran.bst`)** | **8 páginas** (~7,3 de conteúdo) |

Raciocínio da estimativa: `IEEEtran.bst` abrevia prenomes a iniciais, usa "in Proc.", e comprime ~25–35%. As 62 linhas caem para ~44 (~0,6 coluna ≈ 0,3 página). **O corpo não muda** — e como a p. 7 já está cheia nas duas colunas, as referências continuam começando na p. 8. Melhor caso plausível: 7 páginas, se o corpo encolher marginalmente por diferenças de hifenização/`siunitx` reais; isso não é suficiente.

**Corte necessário:** ~1,3–1,5 página de conteúdo. Com 6.402 palavras de corpo em 7 páginas (≈915 palavras/página), isso é **~1.200–1.400 palavras (≈20% do corpo)**, mantendo as 2 figuras e 2 tabelas. Alternativa: cortar a Fig. 1 (0,70·col, ~0,3 página) e ~900 palavras.

Observação: os comentários no fonte mostram que o corte 9→6 já foi tentado e parou em ~7,3. As reduções restantes terão de vir de conteúdo, não de formatação.

### 6.2 O abstract corresponde ao conteúdo? **Sim, com uma exceção.**

O abstract é notavelmente fiel — inclusive declara as três limitações desconfortáveis (99,6% translacional, rSim não sintonizado, dependência da velocidade inicial). Duas notas:
- Usa **0,038** m, valor que conflita com a Tabela II (0,039) e com a própria decomposição de Shapley (§6.3).
- Diz "identified from the competition logs" no framing e depois "A short dedicated open-loop campaign restores the excitation" — coerente. Bom.

Ironia estrutural: **o abstract é mais preciso que a Introdução** (que carrega B4 e C6) e **mais completo que a Conclusão** (que perdeu o achado de yaw por causa de B2).

### 6.3 Consistência numérica (conferi a aritmética)

**Fecha corretamente** (verificado independentemente):

| Verificação | Resultado |
|---|---|
| Shapley: 0,034+0,027+0,001 | = 0,062 ✓; percentuais 54,8/43,5/1,6 → "55/43/2" ✓ |
| Gap `h_ref` = 0,101 − 0,039 | = 0,062 ✓ (consistente com a Tabela II) |
| Piso do Wilcoxon unilateral, n=10 | 2⁻¹⁰ = 9,766e-4 → "9.8×10⁻⁴, the smallest value attainable at n=10" ✓ |
| 49 janelas × 1,5 s | = 73,5 s ✓ (abstract, §IV-C e §VI concordam) |
| 264/265 | = 99,62% → "99,6%" ✓ |
| 24,0 / 1,567 | = 15,3× → "15×" ✓ |
| Euler/ZOH, τ = 0,072 / 0,127 / 0,083 | +12,0% / +6,7% / +10,4% → "7–12%" ✓ |
| Zona morta: 1,567/2,699 e 1,567/2,61 | 0,5806 e 0,6004 → "0,58–0,60 rad/s" ✓ |
| Spread 2,699 vs 2,61 | 3,41% → "~3,3%" ✓ |
| `Td` quantização, 4 vs 5 passos @60 Hz | −20,0% → "±21%" ✓ |
| Sensibilidade do limiar (92,5% → 94,3% → 97,6%) | monotônico e coerente ✓ |
| Cruzamento das baselines (Fig. 2a / Tab. II) | ideal 0,152 vs rSim 0,174 em 0,7 s; 0,217 vs 0,213 em 1,0 s → "cross near 1 s" ✓ |
| Média do fit de ω: (65,0+77,2)/2 | = 71,1 ✓ |
| Fig. 2(a) vs Tabela II | concordam em todos os pontos legíveis ✓ |

**Não fecha:**

| Discrepância | Onde |
|---|---|
| **0,038 vs 0,039 m** (`e_pos` do modelo em `h_ref`) | 0,038: Abstract, §IV-C texto. 0,039: Tab. II, §IV-C ablação, §V-B ("39–119 mm"). **0,038 é aritmeticamente incompatível com a decomposição de 0,062 m do próprio artigo.** |
| **0,129 vs 0,131 m** (`e_pos` do rSim em `h_ref`) | 0,129: Tab. II. 0,131: §IV-C. Propaga para o gap "+0,093 m" (Tab. II daria +0,090). |
| **52,6% vs 44,8%** (fit hold-out de ω em malha fechada) | §IV-D, ambos. A distinção existe mas só num comentário do fonte. |
| **+0,069 m vs 0,062 m** (gap modelo−ideal) | §IV-C: os dois, unidades de análise diferentes (evento vs. janela), nunca reconciliados. |
| **49 não-sobrepostas** atribuídas tanto a 265 quanto a 264 janelas | §IV-B vs §IV-C |
| **`e_ang`: modelo é o menor em todos os horizontes** (§IV-C + Tab. II) **vs. excede o do rSim em horizontes longos** (§V-C) | contradição lógica, não numérica — ver B3 |
| **Lag domina** (Intro C3) **vs. lag e dead time comparáveis** (Abstract + §IV-C) | contradição lógica — ver B4 |

### 6.4 Figuras e tabelas: necessárias, citadas, legíveis?

| Elemento | Citada? | Legível? | Necessária? |
|---|---|---|---|
| Fig. 1 (degrau de ω, 3 painéis, 0,70·col) | ✓ §IV-D | ✓ Inglês, fontes grandes em relação ao canvas, 441 dpi efetivo. Rótulos ficarão pequenos a 2,45 in de largura mas legíveis. | ✓ mas **mal enquadrada** (C11): 95% de regime permanente |
| Fig. 2 (resultado principal, `figure*`, 0,86·textwidth) | ✓ §IV-C | ✓ Excelente. Painéis (a)/(b) claros, legendas em inglês, marcadores distinguíveis em P&B (círculo/quadrado/triângulo + sólido/pontilhado/tracejado) | ✓ é a figura do artigo |
| Tab. I (parâmetros por DOF) | ✓ §IV-A | ✓ | ✓ |
| Tab. II (medianas `e_pos`/`e_ang` × horizonte) | ✓ §IV-C, §IV-C(d) | ✓ | ✓ |

Todos os 4 floats são citados no texto; nenhum float órfão; nenhum float empurrado para depois das referências (o `stfloats` + contadores ajustados funcionaram). Nenhuma figura está em português (defeito de versões anteriores, resolvido).

**Lacuna:** nenhum traço medido-vs-simulado para translação (C12).

### 6.5 Referências

19 entradas, todas citadas no texto, nenhuma citação indefinida. Cobertura adequada e bem escolhida para 6 páginas: gêmeos digitais de plataformas móveis [4,5,6], identificação de omnidirecionais [7,8,9], sim-to-real offline [11], contexto SSL [1,2,3,13,14,15], e os clássicos corretos de identificação em malha fechada [16,17,18] + Ljung [19] + Åström & Hägglund [12]. Não detectei nenhuma referência que pareça fabricada — todas têm venue, autores e páginas plausíveis e verificáveis.

Problemas: **[3] incompleta** ("Preprint.", sem ano/ID) e **mal alocada** em §VI (citada para Isaac Sim/MuJoCo). **[2]** citada por arXiv tendo versão de conferência.

Lacuna temática: nenhuma referência de projeto ótimo de experimento / análise de identificabilidade, que é a vizinhança direta do achado (O1).

### 6.6 Afirmações sem suporte no PDF

1. "reproduces all nine parameters exactly" (§IV-A) — determinismo bit-exato, sem artefato (404).
2. "the two agree to ≤6 mm in position and ≤9×10⁻⁴ rad in heading" (§III-B) — reconciliação com Simulink, **um evento de referência**, sem artefato.
3. "the acceptance criteria ... were committed **before** estimation" (§III-E) — pré-registro central para a credibilidade do resultado de ω, verificável só pelo repositório em 404.
4. "**No event** contributed to both parameter selection and fidelity scoring" (§IV-C) — aparentemente contradito pelo §IV-A (C2).
5. "**Reality-Gap Mitigation**" (título) — nenhuma medida de transferência no artigo.
6. "sweeping nine plausible layouts moves them by less than half a point" (§IV-D) — robustez geométrica, sem tabela nem apêndice.

### 6.7 Seções vazias, `??`, TODO

Nenhum. Verificado no texto extraído e no `.log`: **0 `??`, 0 `\TODO` renderizado, 0 referência/citação indefinida, 0 overfull box >10 pt.** Todas as seções têm conteúdo. O fonte está limpo — o problema é de volume e de consistência, não de acabamento LaTeX.

### 6.8 Anonimização double-blind

**Conforme, com um risco residual.**

- ✓ Bloco de autor: "Anonymous Author(s) / Affiliation withheld for double-blind review".
- ✓ Sem agradecimentos, sem financiamento, sem ORCID, sem nome de equipe.
- ✓ URL do repositório anonimizada (`anon-ssl-dt`) — mas **404** (B5).
- ⚠ **Risco residual, não violação:** as refs. [3], [13] e [14] são todas do mesmo grupo brasileiro de SSL, e [13] (Araújo & Barros, gêmeo Simscape de robô SSL) é discutida em §V-B como o trabalho mais próximo. Combinado com "an independently built Simulink model of **the same robot**" (§III-B) e com o acesso a firmware e CAD do robô, um revisor da área localiza o grupo com facilidade. Todas as citações estão em terceira pessoa, que é o que o double-blind exige — então **não é violação**. Vale apenas o alerta de que o anonimato é fino na prática.

---

## 7. Recomendação final

# **WEAK REJECT**

Não é um julgamento sobre a ciência, que é honesta e em vários pontos acima da média. É um julgamento sobre o **estado do manuscrito**: ele está ~2 páginas impressas acima de um limite rígido de 6 (risco de desk-reject antes de qualquer revisor), tem uma frase quebrada no parágrafo de fecho, duas contradições internas diretas em que uma seção refuta outra, e a URL do artefato que sustenta suas alegações de rigor retorna 404.

**Se todos os itens BLOQUEADORES forem corrigidos e o artigo couber em 6 páginas, minha nota sobe para ACCEPT** (não weak accept): o diagnóstico de identificabilidade por parcela de atuação, a inversão de veredito sob tooling idêntico, e a ablação Shapley que contraria a narrativa mais vendável dos próprios autores compõem uma contribuição sólida e bem executada para a LARS.

### O que moveria minha nota para cima, em ordem de impacto

1. **Caber em 6 páginas** (B1) — sem isso, nada mais importa.
2. **Consertar a frase quebrada da Conclusão** (B2) e **as duas contradições** `e_ang` (B3) e ablação/C3 (B4). Trinta minutos de trabalho; hoje custam credibilidade desproporcional.
3. **Publicar o repositório anonimizado** (B5). Converte seis alegações não-verificáveis em verificadas e é o argumento mais barato de rigor disponível.
4. **Endereçar a causalidade do filtro de `v0`** (C1) — declarar o comprimento da janela SG, e recomputar com estimador causal se ela for centrada. É o único defeito que poderia, em princípio, invalidar o resultado principal.
5. **Reformular a alegação de disjunção treino/teste** (C2) e **dar mais eventos de hold-out ao `vx`** (C7).
6. **Adicionar uma baseline competitiva** — mesmo que seja apenas o canto `(K=1, τ=nominal, Td=nominal)` do fatorial que vocês já rodaram, ou um rSim com seus poucos parâmetros ajustados. Hoje o artigo vence um espantalho e um simulador que ele mesmo declara não sintonizado.
7. **Unificar 0,038/0,039 e 0,129/0,131** (C3, C4) e explicar 52,6% vs 44,8% (C5).
8. **Zoom no transiente da Fig. 1** (C11) e, se sobrar espaço, um traço translacional medido-vs-modelo (C12).

---

## 8. PERGUNTA EXTRA — o que ainda separa este artigo de um "strong accept"?

Separo em três blocos, do mais barato ao mais caro.

### Bloco A — Higiene. Só reescrita. Nenhum dado novo, nenhuma análise nova.
*Impede um accept limpo hoje; é trabalho de horas, não de semanas.*

| Item | O que fazer |
|---|---|
| B1 | Cortar ~1.200–1.400 palavras. |
| B2 | Restaurar a oração engolida pelo `%` em `07_conclusion.tex:17`. |
| B3 | Deletar "heading error exceeds rSim's at long horizons" de §V-C (a Tab. II a refuta). |
| B4 | Reescrever C3 da Introdução para "lag e dead time em partes comparáveis". |
| C6 | C3: trocar "halves in all ten" por "wins in all ten; halves at `h_ref`". |
| C3, C4, C5, C9, C10 | Unificar 0,038/0,039 e 0,129/0,131; explicar 52,6% vs 44,8%; acertar 264/265; nomear o método do CI por evento. |
| C8 | Completar [3]; mover a citação de Isaac/MuJoCo. |
| B5 | Publicar o repositório (o conteúdo, segundo o próprio artigo, já existe). |

### Bloco B — Substância. **Alcançável só com reanálise dos dados que já existem.**
*Este é o bloco decisivo: é o que separa "accept" de "strong accept", e nada dele exige voltar ao robô.*

1. **Fechar a questão do vazamento (C1).** Recomputar `v0` com um estimador estritamente causal e republicar a Tabela II e a Fig. 2. Se o resultado sobreviver — provavelmente sobrevive, dado que o gap em `h=1,5 s` é 0,172 m —, isso **fortalece** o artigo mais do que qualquer outra análise possível, porque remove a única objeção capaz de derrubá-lo. Dados: já existem.
2. **Uma baseline que não seja espantalho.** O fatorial 2³ já contém `(K=1, τ=0, Td=0)` = cinemática ideal; basta reportar também um FOPDT de parâmetros nominais/catálogo como comparador, e/ou ajustar os poucos parâmetros do rSim com o mesmo procedimento para converter "fitted-vs-untuned" em "fitted-vs-fitted". Dados e ferramentas: já existem. **Este é o item de maior retorno científico da lista inteira.**
3. **Tornar a disjunção treino/teste literalmente verdadeira (C2, C7).** Re-particionar os 46 eventos para que os eventos de fidelidade não tenham participado de nenhuma decisão de promoção, e dar a `vx` mais de um evento de hold-out. Dados: já existem.
4. **Quantificar quanto do fit de 71,1% de ω é `K` e quanto é `τ`/`Td` (C11).** Reportar o fit de um modelo `(K=1,0016, τ=0, Td=0)` na mesma escada. Se for próximo de 71%, dizer isso — é uma limitação honesta que fortalece o artigo. Dados: já existem.
5. **Um traço translacional medido-vs-modelo (C12).** O painel foi cortado por espaço, não por falta de dado.
6. **Reconciliar as duas unidades de análise** (+0,069 por evento vs 0,062 por janela) numa frase.

Se o Bloco B for feito, o artigo passa de "modelo bate baseline trivial" para "modelo bate comparador ajustado, sem vazamento, com split limpo" — e aí a contribuição de identificabilidade fica apoiada num resultado de fidelidade que resiste a interrogatório. **É isso que produz um strong accept.**

### Bloco C — Exige coleta de dados nova. **Não é alcançável para esta submissão.**
*E, na minha leitura, não é necessário para um strong accept em 6 páginas — desde que o artigo pare de prometê-lo no título.*

1. **Validar fidelidade rotacional.** 99,6% das janelas de hold-out são translacionais e o bin de rotação tem `N_indep = 0`. Nenhuma reanálise cria janelas ricas em rotação num corpus que não as tem. Exige logs de competição (ou coleta) com distribuição rica em rotação.
2. **Isolar topologia de malha de diluição e de sessão.** O próprio §V-C diz o que falta: "an open-loop arm with translation superimposed, which we did not collect". Enquanto isso não existir, "closed-loop logs cannot identify yaw" continua sendo uma inferência bem argumentada, não uma medida controlada.
3. **Qualquer alegação de *reality-gap mitigation*.** Exige treinar uma política no gêmeo e transferi-la para o robô: robô, campo e tempo fora de competição. **Este é o item que decide o título.**
4. **Replicação cross-robô / cross-superfície.** Tudo vem de um robô, uma superfície, um split.
5. **Varredura fina de amplitude perto da zona morta de yaw** (para transformar o intervalo 0,58–0,60 rad/s em estimativa pontual) e **eventos suficientes para intervalos de parâmetro com resíduos brancos em ω**.

### A recomendação concreta que decorre disso

O Bloco C é caro e o Bloco B é barato — e é o Bloco B que move a nota. Portanto:

> **Faça A + B, e mude o título.** "Reality-Gap Mitigation" promete o Bloco C, que o artigo não entrega e não pretende entregar nesta submissão. Um título que nomeie o que foi medido — identificabilidade dependente de excitação, e fidelidade preditiva por DOF em replay — remove a maior objeção de sobreafirmação sem custar uma linha de resultado. A alternativa registrada no fonte ("*When Competition Logs Are Not Enough: Excitation-Dependent Identifiability in a Per-DOF Digital Twin of an Omnidirectional Soccer Robot*") descreve o artigo que efetivamente existe, e é um artigo melhor do que o título atual sugere.

Vale dizer com clareza, porque o oposto costuma ser o caso: **este artigo é mais honesto do que precisa ser.** Ele declara que 99,6% da validação é translacional, que o rSim não está sintonizado, que a unidade de análise mudou pós-hoc, que a vantagem depende da velocidade inicial, e que a inversão de veredito não isola um fator causal único. Um artigo com essa disciplina merece que os defeitos acima sejam tratados como o que são — reparáveis — e não como sintomas de fragilidade científica. Mas eles precisam ser reparados antes da submissão, porque hoje um deles (o limite de páginas) impede que qualquer revisor chegue ao mérito.
