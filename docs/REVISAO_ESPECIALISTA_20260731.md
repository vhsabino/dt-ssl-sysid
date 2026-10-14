# Revisão especialista simulada — SBR/LARS 2026

**Artigo:** "Excitation Regime, Not the Degree of Freedom: Identifiability in Grey-Box Digital Twinning of an Omnidirectional Soccer Robot"
**Arquivo revisado:** `latex/paper_sbr2026_20260731.pdf` (6 páginas, IEEE A4 duas colunas, double-blind)
**Data da revisão:** 2026-07-31
**Papel adotado:** revisor externo, sem acesso ao repositório, aos `.tex` ou a qualquer material interno. Todas as críticas abaixo se referem **exclusivamente ao que está no PDF**.
**Escopo:** 1 figura (Fig. 1), 3 tabelas (I, II, III), 20 referências, 7 seções.

---

## 1. Resumo do artigo nas minhas próprias palavras

Os autores constroem um "gêmeo digital comportamental" de um robô omnidirecional de 4 rodas da RoboCup Small Size League (SSL). O modelo é deliberadamente simples: três canais SISO desacoplados (um por grau de liberdade — vx, vy, ω), cada um um primeiro-ordem-com-atraso (FOPDT/P1D) `G_i(s) = K_i·e^(−Td_i·s)/(τ_i·s+1)`, totalizando nove parâmetros. A velocidade de corpo resultante é rotacionada pelo heading corrente e integrada por trapézio para obter pose.

A pergunta de pesquisa não é "esse modelo funciona?", e sim **"esse modelo pode ser identificado a partir dos logs de competição que as equipes já gravam?"** — logs de malha fechada, ~60 Hz, comandos de corpo + pose de visão, nunca projetados para excitar a planta.

A resposta que o artigo defende é bipartida:

1. **Translação: sim.** vx e vy identificam bem dos logs de competição (fit hold-out 86,7% / 87,1%). Sob um protocolo de avaliação em *free run* (sem teacher forcing), com janelas re-ancoradas em SE(2), múltiplos horizontes (0,1–1,5 s), estratificação por fração rotacional e um "portão" estatístico (Wilcoxon pareado em janelas não-sobrepostas + bootstrap de blocos móveis + tamanho de efeito), o gêmeo bate o rSim (motor ODE do rSoccer) em todas as janelas dominadas por translação, com efeito muito grande (rank-biserial +0,73 a +0,98) e gap que **cresce** com o horizonte.
2. **Yaw: não — mas o culpado é o dado, não o GDL.** O mesmo P1D ajustado ao ω em logs de malha fechada reprova em todos os critérios (fit 52,6% < 60%, resíduos não brancos, e no portão SE(2) fica *pior* que um placeholder sem dinâmica). O mesmo P1D ajustado a uma coleta dedicada de malha aberta (escada de amplitudes ±1, ±2,5, ±5 rad/s, 6 eventos no regime linear, 4 treino / 2 hold-out) aprova em todos os critérios pré-registrados, com `K_ω = 1,0016` (CI [0,9993, 1,0040]). Como mecanismo, os autores oferecem: (a) viés de correlação de malha fechada inflando `K_ω` para ~1,3–1,35; (b) uma zona morta elétrica por roda, reconvertida para 0,58–0,60 rad/s no yaw de corpo, abaixo da qual caem **94,3%** das amostras de comando de yaw dos logs.

A tese-síntese, que dá título ao artigo: *"identifiability claims drawn from operational logs are claims about excitation, not about the robot"*.

**Teste de clareza: PASSA.** Consegui reconstruir a contribuição sem ambiguidade em uma leitura. O artigo é bem estruturado, honesto sobre suas limitações (Seção VI é acima da média para o venue) e a mensagem central é nítida. Isso é um ponto forte real, não uma cortesia.

---

## 2. Avaliação por critério (1–5)

### Originalidade — **3,5/5**
O modelo é o mais clássico possível (FOPDT é livro-texto, ref. [12]) e o fenômeno invocado — viés de identificação em malha fechada — é conhecido desde 1977 ([17]–[19], corretamente citados). A originalidade **não** está no método, e o artigo é honesto quanto a isso. Está no *enquadramento empírico*: a demonstração controlada, na mesma plataforma e mesma estrutura de modelo, de que dois regimes de excitação produzem veredictos opostos, com um mecanismo físico quantificado (limiar de atuação) explicando a diferença. Isso é útil e não vi feito exatamente assim para SSL. Mas é uma re-demonstração cuidadosa de um princípio conhecido, não um princípio novo — e o artigo por vezes escreve como se fosse a segunda coisa ("The methodological lesson travels beyond this robot"). Nota puxada para baixo por isso.

### Solidez técnica — **2,5/5**
É aqui que o artigo é mais frágil, e por três razões independentes (detalhadas em §4-i):
- O contraste central **confunde três variáveis simultaneamente**: malha aberta vs. fechada, faixa de amplitude (≤0,6 rad/s vs. 1–5 rad/s) e sessão/superfície. A conclusão causal privilegiada ("correlation bias") é apenas uma das três explicações compatíveis com a evidência — e a *própria* análise de zona morta do artigo sustenta melhor a explicação de amplitude.
- Os autores diagnosticam viés de malha fechada e concluem "não identificável", **sem jamais tentar os métodos padrão que existem exatamente para isso** (variáveis instrumentais, two-stage, identificação conjunta entrada-saída, projeção). Citam [17]–[19] pelo perigo e ignoram o remédio.
- Contradição interna entre o teste de brancura e o intervalo de confiança: a Seção VI-d declara que *"the Ljung–Box test rejects residual whiteness for **both** yaw fits"*, e ainda assim a Seção IV-D usa um CI assintótico de largura 0,005 sobre `K_ω` para afirmar que o ganho é "statistically indistinguishable from unity" e que o CI "excludes 1.3". Com resíduos comprovadamente coloridos e n = 4 eventos de treino, esse CI não é confiável, e ele sustenta a afirmação mais forte do artigo.

O que salva a nota de cair abaixo disso: a discretização é explicitada corretamente (ZOH exato, quantização inteira do atraso), há teste de robustez ±21% em Td, há reconciliação numérica do integrador, e a estrutura do modelo é adequada ao propósito declarado (fidelidade observacional).

### Rigor experimental — **3/5**
Bipolar. O protocolo de avaliação (Seção III-F) é genuinamente bom: free run explícito (com justificativa correta de por que teacher forcing infla fidelidade), estratificação por regime de movimento, distinção entre janelas densas (curvas) e não-sobrepostas (inferência), bootstrap de blocos para dependência serial, gate com quatro condições conjuntas e um estado `INDETERMINATE` honesto. **Poucos artigos deste venue chegam perto disso.**

Ao mesmo tempo:
- A evidência que sustenta a *tese do título* é n = 6 eventos, 4 treino / 2 hold-out, **uma sessão, um robô, uma superfície**. Um `fit` hold-out de 71,1% é a média de dois números (65,0% e 77,2%), e 65,0% está a 5 pontos do gate de 60%.
- Nenhuma incerteza é reportada na Tabela I. Nove parâmetros, zero barras de erro (exceto `K_ω`, no corpo do texto).
- Duas grades de horizonte diferentes coexistem no artigo ({0,1…1,5 s} para fidelidade; {0,5…4 s} para os portões por GDL), e os autores declaram explicitamente que **não recomputaram** ("Each result is reported on its native grid... rather than recomputed"). Honesto, mas revela um artigo montado sobre campanhas heterogêneas anteriores em vez de um estudo desenhado de uma vez.
- O painel direito da Fig. 1 é admitidamente **obsoleto** — gerado com o placeholder de ω, "not re-run with the identified ω". Um revisor não deveria estar olhando para uma figura que os autores sabem estar desatualizada em relação à Tabela I.

### Clareza — **3,5/5**
Escrita boa, inglês competente, estrutura lógica, contribuições C1–C4 enumeradas e efetivamente entregues. Terminologia consistente na maior parte. A Seção VI é modelo de honestidade.

Descontos: (a) **a única figura do artigo está em português** ("RMSE posicao", "erro heading", "horizonte h (s)", "e_pos mediana (m)") e com um rótulo interno de pipeline vazando no título (`[TODOS]`); (b) essa figura é ilegível na largura de uma coluna — os rótulos de eixo ficam em ~4 pt efetivos; (c) "hold-out fit" é o critério central de aceitação e **nunca é definido** (NRMSE? `fit` do `compare` do MATLAB? sobre qual sinal?); (d) o "high-fidelity Simulink model" aparece uma única vez (Seção III-B) como referência de reconciliação e nunca é descrito nem justificado — o leitor não sabe o que é nem por que concordar com ele significa algo.

### Relevância para a comunidade — **4/5**
Alta e bem posicionada para SBR/LARS. SSL é comunidade forte no venue, o problema (reality gap, validação de software em simulação) é real e reconhecível, o dado usado é o dado que todas as equipes já têm, e a "lição" é acionável: pare de concluir não-identificabilidade a partir de logs de jogo. O contraste com rSim/grSim toca diretamente as ferramentas que a comunidade usa. Único desconto: o gêmeo entregue só tem fidelidade *validada* em janelas onde o robô quase não gira — exatamente o regime menos interessante para quem treina políticas de motion planning.

### Reprodutibilidade — **2,5/5**
O artigo *fala* muito em reprodutibilidade e entrega pouco do que importa:
- **Nenhuma declaração de disponibilidade de código ou dados.** Nenhum link anonimizado (perfeitamente possível sob double-blind), nenhum DOI, nenhum repositório.
- O "pré-registro" é uma afirmação sem artefato: *"the acceptance criteria... were fixed and committed before estimation"*. Committed onde? Sem hash, sem timestamp verificável, é uma promessa, não um mecanismo.
- Hiperparâmetros de pré-processamento ausentes: ordem e janela do Savitzky–Golay, método de reamostragem, definição do `fit`, como o "seed 42" particiona os eventos, quantos eventos compõem as 49 janelas independentes.
- "Bit-for-bit determinism under re-execution" é enfatizado **três vezes** (III/IV-A/IV-D). Determinismo com mesma semente, mesmos dados e mesma versão de toolbox não é reprodutibilidade — é ausência de não-determinismo. Gastar três menções nisso enquanto não se libera código dá a impressão de substituição retórica.
- Reconhecido no próprio artigo: "reproducing the rSim comparison requires a documented Linux/ODE environment" — e essa documentação não é fornecida.

**Média ponderada informal: ~3,2/5.**

---

## 3. Pontos fortes (o que sustenta aceitação)

1. **O protocolo de avaliação é a melhor parte do artigo e é generalizável.** Free run sem re-ancoragem interna, múltiplos horizontes, janelas re-ancoradas em SE(2), estratificação por fração rotacional, separação entre janelas densas (curva) e não-sobrepostas (inferência), bootstrap de blocos, tamanho de efeito e um gate com condição de monotonicidade. A justificativa contra teacher forcing ("would measure single-step noise and inflate apparent fidelity") é exatamente o argumento certo e é raro vê-lo explicitado.
2. **Honestidade metodológica acima da média do venue.** O artigo reporta um resultado negativo (calibração conjunta por Bayesian optimization não promovida, Seção V-C, "negative control"), reporta o veredicto `INDETERMINATE` nos bins sem população, reporta a divergência de 3,3% entre CAD e firmware sem escolher um lado, reporta a proveniência perdida de uma constante herdada (0,3 rad/s), e a Seção VI antecipa quase todas as objeções óbvias. Isso constrói confiança.
3. **A inversão de sinal do veredicto no mesmo portão é uma evidência forte e bem apresentada.** Tabela III (fechada: +0,0489 m pior, p=3,8e−9; aberta: −0,1138 m melhor, p=1,7e−16), avaliada na *mesma* população `shoot_to_goal`, é o núcleo empírico do artigo e está bem construída.
4. **A ponte para o mecanismo físico é o diferencial.** Não parar em "o fit foi ruim" e ir até o firmware, à zona morta por roda, à razão geométrica roda/contato e daí à fração de 94,3% de amostras sub-limiar é o que transforma uma anedota de ajuste em um argumento. Reportar 0,58–0,60 rad/s como intervalo, "never a point estimate", é a decisão correta.
5. **Consistência do gap com o horizonte** (Tabela II: +0,050 → +0,170 m de 0,1 a 1,5 s) e efeitos de magnitude tal que a conclusão translacional não depende de sutileza estatística.
6. Related work enxuto mas pertinente e atual (a maioria 2023–2026), com um "Gap" explícito ao final da Seção II. Bem feito para 6 páginas.

---

## 4. Fraquezas

### (i) BLOQUEADORAS — comprometem a aceitação como está

**B1. O contraste malha-aberta × malha-fechada é confundido com amplitude, e a explicação causal preferida é a menos apoiada pelos próprios dados do artigo.**
Os dois regimes diferem em pelo menos três dimensões simultâneas: topologia de laço (aberto/fechado), **faixa de amplitude de comando** (aberto: 1–5 rad/s; fechado: 94,3% abaixo de 0,6 rad/s) e sessão/superfície/data de coleta. O artigo atribui a diferença a *correlation bias* (Seções IV-D-b e V-B), mas a sua própria Seção IV-D-a documenta uma **não-linearidade dependente de amplitude** (zona morta por roda) que explicaria a discrepância sem invocar realimentação alguma. Não há nenhum experimento que separe as duas explicações: faltam (a) uma coleta de malha aberta em baixa amplitude no regime de operação real, e (b) um trecho de malha fechada com yaw persistentemente alto. Enquanto isso, o título do artigo — "Excitation Regime, Not the Degree of Freedom" — na verdade é compatível com ambas as leituras, mas o **abstract** e a Seção V-B comprometem-se com a leitura causal específica ("refuting the inflated closed-loop estimate as correlation bias"), que a evidência não isola. Isso é excesso de conclusão sobre a evidência apresentada, e está no abstract.

**B2. Contradição interna entre a rejeição de brancura e o intervalo de confiança de `K_ω`.**
Seção VI-d: *"The Ljung–Box test rejects residual whiteness for both yaw fits"*. Seção IV-D: `K_ω = 1,0016 (95% CI [0,9993, 1,0040])`, usado para afirmar unidade e para "refutar" 1,3. Um CI assintótico de PEM pressupõe resíduos brancos (ou correção explícita); com resíduos coloridos por construção (o próprio artigo atribui isso ao filtro Savitzky–Golay), com n = 4 eventos de treino e dados reamostrados, uma largura de CI de ±0,0024 é implausível e não pode carregar o peso argumentativo que carrega. A afirmação "statistically indistinguishable from unity" precisa ou de um CI robusto/bootstrap por evento, ou de rebaixamento para descritivo.

**B3. Os métodos padrão para identificação em malha fechada nunca são tentados, e a conclusão de não-identificabilidade é enunciada mesmo assim.**
O artigo cita corretamente [17]–[19] para estabelecer que PEM direto é enviesado sob realimentação — e então usa PEM direto, observa o viés, e conclui que *os logs* não suportam o GDL. A objeção óbvia e, a meu ver, decisiva: existem métodos projetados para exatamente essa situação (variáveis instrumentais, abordagem two-stage/projeção, métodos joint input-output, identificação com conhecimento do controlador). Não tentá-los, nem discutir por que seriam inaplicáveis aqui (por exemplo, porque o "controlador" inclui decisão tática humana e não é parametrizável), deixa a conclusão C4 vulnerável: o que foi demonstrado é que *um estimador específico, sabidamente enviesado nessa condição*, falha — não que o dado seja não-informativo. A frase *"The closed-loop dataset simply does not excite the rotational mode enough to identify it"* é mais forte do que o experimento suporta; a evidência de excitação insuficiente (94,3% sub-limiar) é boa, mas ela é um argumento **separado** do argumento de viés de correlação, e o artigo os usa de forma intercambiável.

**B4. Paradoxo não reconhecido entre a zona morta e o ganho inflado.**
Se 94,3% das amostras de comando de yaw estão abaixo do limiar de atuação — isto é, comando presente, movimento ausente — então um ajuste comando→velocidade sobre esses dados deveria **deflacionar** o ganho aparente, não inflá-lo para 1,3–1,5. O artigo reporta, e não explica, exatamente essa anomalia: *"a flat effective gain of ≈ 1.3–1.5 across the closed-loop command range, with **no dead-zone knee visible** in the body-frame yaw signal"*. A ausência do joelho é um dado que **contraria** a hipótese de zona morta dominante no sinal de corpo, e é apresentada em uma subordinada, sem discussão. Ou (a) a rotação observada em malha fechada vem de outra fonte que não o comando de yaw (arrasto, escorregamento, acoplamento das rodas, correção de heading via cinemática inversa) — o que reabriria a interpretação inteira; ou (b) o limiar por roda não se traduz como o artigo supõe para o corpo. Um revisor cético vai parar exatamente aqui, e o artigo não dá resposta.

**B5. A comparação com rSim, como montada, é próxima de tautológica — e o baseline ideal expõe isso.**
O gêmeo tem nove parâmetros ajustados a *este* robô, com dados *deste* robô; o rSim roda "at default parameters" e nunca foi sintonizado para este robô. Os autores reconhecem isso em uma linha na Seção VI-d ("a re-tuned engine could narrow the gap"), mas C3 é anunciada no abstract e na conclusão como um resultado de fidelidade, sem essa qualificação. Pior para o argumento: pelos próprios números do artigo, no horizonte de referência o gêmeo está em 0,038 m, o gap contra o rSim é +0,093 m (rSim ≈ 0,131 m) e o gap contra a **cinemática ideal** é +0,063 m — logo a cinemática ideal está em ≈ 0,101 m e **bate o rSim**. Um baseline de zero parâmetros, sem dinâmica nenhuma, supera o motor ODE da liga. A leitura mais parcimoniosa disso não é "nosso gêmeo captura dinâmica"; é "o harness de replay do rSim está penalizado" (partida do repouso, sem setter de velocidade, motion control desabilitado, parâmetros default). C3 mede em boa medida o handicap do harness, não a fidelidade relativa.

**B6. O argumento "gap cresce com o horizonte ⇒ vantagem dinâmica, não de condição inicial" (Seção V-C) é logicamente inválido.**
Um erro de **velocidade inicial** — que é exatamente a assimetria admitida, já que o gêmeo é semeado com a velocidade de corpo real e o rSim "provides no velocity setter at reset" — produz erro de posição que cresce **linearmente com o horizonte**. O padrão observado (gap monotonicamente crescente) é, portanto, precisamente a assinatura esperada de um erro de CI, e não discrimina entre as duas hipóteses. O Modo A (warm-up de 15 amostras + re-âncora rígida) mitiga, mas não elimina, e o Modo B (sem warm-up) agrava deliberadamente. Como está, a inferência mais forte da discussão apoia-se em um argumento que não separa as alternativas.

### (ii) CORRIGÍVEIS antes da submissão (esforço baixo a médio, alto retorno)

**C1. A Figura 1 — única figura do artigo — está em português e desatualizada.**
Rótulos: "RMSE posicao", "erro heading", "horizonte h (s)", "e_pos mediana (m)", "e_ang mediana (rad)", e o título com um marcador interno de pipeline: `twin vs rSim (ODE replay) [TODOS] (N=265, indep=49)`. Em um artigo IEEE em inglês isso é falha de acabamento imediatamente visível. Além disso: a legenda admite que o painel direito foi gerado **com o placeholder de yaw**, antes de ω ser identificado, e "not re-run with the identified ω" — ou seja, a figura não corresponde à Tabela I. Refazer ambos os painéis em inglês, com o modelo final, é barato e obrigatório. O rótulo `[TODOS]` também conflita com a legenda, que diz "translation-dominated population".

**C2. A Figura 1 é ilegível na largura de coluna.** Dois painéis lado a lado em ~8,5 cm ⇒ fontes de eixo em torno de 4 pt. Ou use largura dupla (`figure*`), ou separe em duas figuras, ou aumente a fonte e remova o título redundante (a legenda já diz tudo).

**C3. Inconsistência numérica entre texto e figura no erro de heading.** Seção IV-C-b afirma que a mediana de `e_ang` do gêmeo *"grows from 0.013 to 0.090 rad over h = 0.1–1.5 s"*. Na Fig. 1 (painel direito), a curva do gêmeo termina em ≈ 0,103 rad em 1,5 s, e 0,090–0,091 é o valor em h = 1,0 s. Ou o texto cita o horizonte errado, ou as duas curvas vêm de execuções diferentes — nos dois casos, um revisor perde confiança nos números.

**C4. Cherry-picking visível na comparação de heading.** O texto compara `e_ang` do gêmeo **apenas contra a cinemática ideal** ("below it at every horizon"), enquanto a figura ao lado mostra o gêmeo **acima do rSim** em h = 1,0 e 1,5 s. Um leitor atento vê imediatamente que a comparação favorável foi a escolhida para o texto e a desfavorável ficou muda no gráfico. Basta uma frase reconhecendo o cruzamento; omiti-lo custa muito mais caro do que admiti-lo.

**C5. A Tabela III afirma "SAME ... IDENTIFICATION TOOLING; ONLY THE EXCITATION REGIME DIFFERS" e a própria nota de rodapé desmente.** O rodapé diz que a linha de malha fechada "was scored by the earlier regime-split criterion (fit 31.9% high-amplitude / −11.2% low-amplitude), not a single hold-out number", e a coluna de fit traz "n/a†". Se os dois casos foram avaliados por critérios diferentes, a alegação de comparação controlada — que é o coração do artigo — fica danificada. Recomputar a linha de malha fechada com o mesmo critério de hold-out é provavelmente barato e removeria a objeção mais fácil de fazer contra o artigo.

**C6. Duas grades de horizonte não reconciliadas.** Seção III-F-c admite que os portões por GDL usam h ∈ {0,5, 1, 2, 2,5, 4} s e a fidelidade usa h ∈ {0,1 … 1,5} s, "rather than recomputed". Para o leitor, o resultado é que o veredicto do yaw (pooled em até 4 s) e o veredicto de translação (até 1,5 s) não são comparáveis, e a impressão é de artigo montado a partir de campanhas antigas. Unificar, ou justificar tecnicamente por que 4 s é necessário para o yaw.

**C7. Definir "hold-out fit".** É o critério de aceitação que aparece em todas as três tabelas e no gate pré-registrado de 60%, e nunca é definido. Uma linha basta (fórmula NRMSE, sinal sobre o qual é calculado, se por evento ou concatenado).

**C8. Tabela I sem incerteza.** Nove parâmetros, nenhum intervalo. Acrescentar CI (ou desvio entre eventos) para os seis parâmetros translacionais, ao menos.

**C9. Sensibilidade de 94,3% ao limiar.** O número é derivado de um limiar geométrico (0,58–0,60 rad/s) cujo bracket empírico é (0,5; 1,0] rad/s — muito mais largo. Como 94,3% é a estatística mais citada do artigo (está no abstract, no título conceitual e na conclusão), é indispensável reportar a fração também em 0,5 e em 1,0 rad/s. Se a fração cair muito no extremo superior, o argumento enfraquece; se não cair, é evidência gratuita a favor.

**C10. Declaração de disponibilidade + artefato de pré-registro.** Um link anonimizado (Anonymous GitHub, OSF anonymous view) para código, parâmetros e critérios com timestamp resolveria de uma vez os problemas de reprodutibilidade e de credibilidade do pré-registro. Sem isso, "pre-registered" é retórica.

**C11. Referências fracas.** [3] "Preprint" sem venue nem ano; [13] "Book chapter manuscript, 2024" — não revisado por pares e usado para sustentar a afirmação de benchmarking de sim2real. Substituir ou marcar explicitamente.

**C12. Descrever ou remover o "high-fidelity Simulink model".** Aparece uma vez (III-B) como padrão de reconciliação (≤ 6 mm / ≤ 9e−4 rad). O leitor não sabe o que é, se foi validado contra o robô real, nem por que a concordância com ele é informativa. Como está, é uma auto-referência a um artefato invisível.

**C13. Risco (menor) de desanonimização.** O cluster [2], [3], [14], [15] aponta para um mesmo grupo, o baseline escolhido é o simulador desse mesmo grupo, e a figura está em português. Formalmente o artigo está anonimizado; na prática, um revisor da área identifica os autores em segundos. Não é motivo de rejeição, mas vale saber.

### (iii) SUGESTÕES de melhoria (não obrigatórias para esta submissão)

- **S1.** Falta uma figura de identificação. O leitor nunca vê uma resposta medida vs. simulada — nem para vx/vy (o resultado positivo), nem para a escada de malha aberta do ω (o resultado central). Um painel com degrau/resposta e resíduos valeria mais do que metade das p-values reportadas.
- **S2.** Falta o histograma da distribuição de comando de yaw com o limiar 0,58–0,60 rad/s sobreposto. É a evidência que sustenta os 94,3% e ela é hoje puramente numérica.
- **S3.** O termo "digital twin" é usado para um simulador FOPDT offline sem acoplamento bidirecional nem sincronização de estado com o robô físico. A comunidade de DT vai contestar. Os autores já usam "behavioral (observational)" — vale ancorar isso explicitamente contra alguma definição de fidelidade citada, ou assumir "behavioral model/plant" e reservar "twin" para o enquadramento.
- **S4.** "Identifiability" no título, mas não há análise de identificabilidade no sentido técnico (informação de Fisher, perfil de verossimilhança, covariância de parâmetros, identificabilidade prática). O único diagnóstico dessa família é ρ(τ, Td) = −0,47 para o ajuste de malha aberta. Ou incluir um diagnóstico mínimo, ou considerar "estimability"/"informativity of the data" no título.
- **S5.** Considerar o rSim com pelo menos uma sintonia mínima e documentada (limites de aceleração/atrito) como terceiro braço. Custa pouco e blinda C3 contra a objeção B5.
- **S6.** O bloco de determinismo bit-exato pode ser comprimido a uma frase; o espaço liberado cobre S1 ou S2.
- **S7.** Independência estatística: as 49 janelas "independentes" vêm de 10 eventos de hold-out. O bootstrap de blocos trata correlação serial *dentro* do segmento, mas não o agrupamento por evento (mesma superfície, mesma bateria, mesma trajetória). p = 1,6e−13 é precisão espúria; um bootstrap por *evento* (cluster) daria um número defensável. Não muda o veredicto — o efeito é enorme —, mas muda a credibilidade.

---

## 5. As perguntas difíceis que eu faria como revisor cético

1. **(Confundimento — a pergunta central)** Os dois conjuntos de dados diferem em topologia de laço, **faixa de amplitude** e sessão. Vocês atribuem a diferença ao viés de correlação de malha fechada. Que evidência **isola** essa causa da explicação de amplitude que vocês mesmos documentam (zona morta + 94,3% sub-limiar)? Concretamente: qual seria `K_ω` em uma coleta de **malha aberta a baixa amplitude** dentro da faixa de operação real? Sem esse braço, "correlation bias" é uma preferência interpretativa, não um achado.
2. **(Paradoxo do ganho)** Se 94,3% dos comandos de yaw estão abaixo do limiar de atuação, o ajuste comando→velocidade deveria produzir ganho **menor** que 1, não 1,3–1,5. Vocês inclusive reportam que **não há joelho de zona morta visível** no sinal de yaw de corpo. Como as duas coisas coexistem? De onde vem a rotação medida em malha fechada, se não do comando de yaw acima do limiar?
3. **(Remédio não tentado)** Vocês citam Gustavsson–Ljung–Söderström, Van den Hof e Forssell–Ljung para estabelecer o perigo, e então usam PEM direto — o método que esses trabalhos advertem não usar. Por que não variáveis instrumentais, two-stage, ou joint input-output? Sem isso, o que foi demonstrado é a falha de um estimador enviesado, não a não-informatividade do dado. A conclusão C4 sobrevive a essa distinção?
4. **(CI vs. brancura)** A Seção VI-d diz que o Ljung–Box rejeita brancura para **os dois** ajustes de yaw. A Seção IV-D usa um CI de ±0,0024 sobre `K_ω` para declarar unidade. Como esse CI foi calculado, e por que ele é válido com resíduos comprovadamente coloridos, 4 eventos de treino e derivada Savitzky–Golay no pré-processamento?
5. **(Tamanho de amostra)** A tese do título repousa sobre 6 eventos, 4 treino / 2 hold-out, uma sessão, um robô, uma superfície, sem varredura entre 0,5 e 1,0 rad/s. O fit hold-out de 71,1% é a média de 65,0% e 77,2% — um deles a 5 pontos do gate. Qual é a variabilidade esperada entre sessões? Com n = 2 no hold-out, o que exatamente o "gate de 60%" está protegendo?
6. **(Justiça da comparação)** O gêmeo tem 9 parâmetros ajustados a este robô; o rSim roda com parâmetros default e nunca foi sintonizado. Em que sentido C3 é um resultado de *fidelidade* e não um resultado de *ajuste vs. não-ajuste*? Qual seria o gap contra um rSim com uma sintonia mínima e honesta (aceleração máxima, atrito)?
7. **(O baseline ideal desmonta o argumento?)** Pelos números de vocês, a cinemática ideal fica em ≈ 0,101 m no horizonte de referência e o rSim em 0,131 m — um modelo de zero parâmetros **bate** o motor ODE da liga. Isso não indica que a maior parte do déficit do rSim vem do harness de replay (partida do repouso, sem setter de velocidade, motion control desabilitado) e não da física? Se sim, quanto de C3 sobra?
8. **(Crescimento do gap)** Vocês argumentam que o gap crescer com o horizonte é "the signature of a dynamical advantage rather than a favorable initial condition". Mas um erro de **velocidade** inicial gera erro de posição que cresce linearmente em h — exatamente o padrão observado — e vocês admitem que só o gêmeo é semeado com a velocidade real. Como esse argumento discrimina as duas hipóteses?
9. **(Métrica × achado)** A métrica primária é posicional ("epos is the claim of this paper"), o hold-out é 264/265 dominado por translação, e o achado central é sobre **yaw**. O gêmeo nunca é validado no regime em que o parâmetro que vocês tanto trabalharam para recuperar importa. Que valor prático tem o `K_ω` identificado, se a fidelidade rotacional segue explicitamente "unverified"? E por que não avaliar `e_ang` na própria coleta de malha aberta, onde há rotação de sobra?
10. **(Escopo da lição)** De um único robô, uma sessão e um GDL, vocês derivam uma norma metodológica geral ("claims about excitation, not about the system"). Que parte disso é evidência e que parte é o princípio de excitação persistente já conhecido desde Ljung [20]? O que exatamente o artigo adiciona ao que [20] já implica?
11. **(Ferramenta obsoleta)** O painel de heading da Fig. 1 foi gerado com o placeholder de ω e não foi refeito com o modelo identificado. Por que o leitor deve confiar que a distribuição de janelas, o gate e as demais curvas não carregam outras defasagens do mesmo tipo? (A Seção IV-B diz que a classificação de bins foi re-executada — mas então por que não a figura?)
12. **(Pré-registro)** "Fixed and committed before estimation" — committed onde, e verificável como? Sob double-blind é possível dar um link anônimo com timestamp. Sem artefato, o que distingue esse pré-registro de uma afirmação retrospectiva?
13. **(Consistência do harness)** Por que duas grades de horizonte, com resultados "reported on its native grid, rather than recomputed"? Recomputar em uma grade única parece barato. O que impede?
14. **(Limiar)** Os 94,3% derivam de um limiar geométrico de 0,58–0,60 rad/s cujo bracket empírico é (0,5; 1,0]. Qual é a fração em 1,0 rad/s? Se ela cair para, digamos, 80%, o argumento muda de tom?
15. **(Generalização)** SSL tem robôs de várias equipes, com firmwares e rodas diferentes. A lição é sobre *este* firmware (limiar por roda **depois** da cinemática inversa) ou sobre logs de competição em geral? Se um firmware aplicasse a zona morta no frame de corpo, a conclusão inteira se inverteria — vocês inclusive dizem isso ("not a body-frame Hammerstein dead-zone that a closed-loop fit could absorb"). Quão contingente é a lição?

---

## 6. Checagens adicionais solicitadas

**Aderência aos tópicos da chamada:** o artigo **não declara explicitamente** aderência a tópicos da chamada do SBR/LARS (o que é normal no formato IEEE e geralmente não é exigido no PDF). A aderência temática, contudo, é evidente e forte: robótica móvel, identificação de sistemas, simulação, sim-to-real, RoboCup. Sem problema.

**Abstract × conteúdo:** corresponde, com duas ressalvas de calibragem. (a) *"refuting the inflated closed-loop estimate as correlation bias"* compromete-se, já no abstract, com a interpretação causal que o experimento não isola (ver B1) — o corpo é mais cauteloso ("The reading we favor is..."), o abstract não. (b) *"the twin outperforms the simulator on translation-dominated windows with a large, statistically gated effect"* omite que o simulador não foi ressintonizado e que a cinemática ideal — baseline trivial — também bate esse simulador. O abstract está mais forte do que a Seção VI permite.

**Figuras e tabelas — legibilidade e necessidade:**
- **Fig. 1:** necessária, mas **em português, com marcador de pipeline `[TODOS]` no título, ilegível na largura de coluna e admitidamente desatualizada** no painel direito. Pior artefato do artigo.
- **Tabela I:** necessária, legível. Falta incerteza.
- **Tabela II:** necessária, legível, bem construída (mediana, gap, p, efeito, N).
- **Tabela III:** necessária e é o coração do argumento, mas a nota de rodapé revela critérios de pontuação diferentes entre as duas linhas, o que enfraquece justamente a alegação de "same tooling" do título da tabela.
- **Ausentes e sentidas:** resposta medida × simulada (vx/vy e escada de ω), histograma de comando de yaw com o limiar.

**Referências:** 20 itens, adequadas em tema e razoavelmente atuais (2023–2026 na maioria dos itens aplicados; clássicos corretos para malha fechada e FOPDT). Fraquezas: [3] "Preprint" sem venue nem ano; [13] "Book chapter manuscript, 2024" (não revisado). Ausência notável: nenhuma referência a **métodos** de identificação em malha fechada (IV, two-stage, joint I/O) — só às advertências —, o que é coerente com a lacuna B3. Também não há referência de identificação de sistemas específica de SSL além do trabalho Simscape [14].

**Afirmações sem suporte no PDF (lista):**
- "correlation bias, not plant gain" — mecanismo não isolado (B1).
- `K_ω` "statistically indistinguishable from unity" — CI de validade duvidosa dado Ljung–Box (B2).
- "The closed-loop dataset simply does not excite the rotational mode enough to identify it" — só um estimador foi testado (B3).
- "the signature of a dynamical advantage rather than a favorable initial condition" — não discrimina (B6).
- "a higher-fidelity behavioral plant for the robot simulation and visualization tools on which robot soccer development relies" (Introdução) — fidelidade superior demonstrada **apenas** em janelas dominadas por translação, contra um simulador não sintonizado; rotação explicitamente não validada.
- "agrees to ≤ 6 mm ... against the high-fidelity Simulink model" — o padrão de comparação não é descrito nem validado (C12).

---

## 7. Recomendação final

### **BORDERLINE** (inclinado a *weak accept*, condicional)

**Justificativa.** O artigo tem duas virtudes que eu levo a sério: um protocolo de avaliação de fidelidade genuinamente bem pensado e reutilizável, e um grau de honestidade metodológica (resultado negativo reportado, veredictos `INDETERMINATE`, discrepâncias de constantes admitidas, Seção VI extensa) que é raro e que eu quero recompensar. A pergunta é relevante para a comunidade do SBR/LARS, o dado usado é o dado que as equipes realmente têm, e o resultado negativo sobre yaw é mais interessante do que o resultado positivo sobre translação.

Contra a aceitação pesam três coisas, em ordem de gravidade: (1) a explicação causal que dá título e abstract ao artigo — viés de correlação de malha fechada — **não está isolada** da explicação alternativa de amplitude/zona morta que o próprio artigo documenta, e há um paradoxo não resolvido (94,3% sub-limiar mas ganho inflado e sem joelho de zona morta) bem no centro do argumento; (2) conclui-se não-identificabilidade sem tentar nenhum dos métodos padrão de identificação em malha fechada, o que torna a conclusão um enunciado sobre o estimador escolhido, não sobre o dado; (3) a comparação com o rSim, que sustenta C3, é entre um modelo ajustado e um simulador não ajustado, e o próprio baseline de cinemática ideal do artigo (zero parâmetros, batendo o rSim) sugere que boa parte do gap é handicap de harness.

A isso soma-se um problema de acabamento que, sozinho, não rejeita, mas corrói a confiança: **a única figura do artigo está em português, com rótulo interno de pipeline visível, ilegível no tamanho impresso, e explicitamente desatualizada em relação à Tabela I** — junto com duas grades de horizonte não reconciliadas e duas linhas de tabela pontuadas por critérios diferentes. O conjunto dá a impressão de um artigo montado sobre campanhas heterogêneas, o que é injusto com a qualidade real do protocolo.

**O que moveria minha nota para *weak accept* sem novos experimentos** (tudo redacional ou de re-execução barata): refazer a Fig. 1 em inglês, com o modelo final, em largura dupla (C1–C2); corrigir a inconsistência numérica de `e_ang` e reconhecer o cruzamento com o rSim (C3–C4); recomputar a linha de malha fechada da Tabela III com o mesmo critério da linha de malha aberta (C5); **rebaixar explicitamente "correlation bias" de conclusão para hipótese preferida, no abstract e na conclusão**, listando amplitude/zona morta como explicação concorrente não excluída (B1); adicionar um parágrafo reconhecendo que métodos de ID em malha fechada não foram tentados e por quê (B3); qualificar C3 com "against an untuned default rSim" e mencionar que a cinemática ideal também supera o rSim (B5); substituir o CI de `K_ω` por um intervalo robusto ou rebaixá-lo a descritivo (B2); reportar a sensibilidade dos 94,3% ao bracket (0,5; 1,0] (C9); definir "hold-out fit" (C7); incluir link anonimizado de código/dados (C10).

**O que moveria para *accept*:** adicionalmente, ou (a) um braço de malha aberta em baixa amplitude que separe regime de laço de faixa de amplitude, ou (b) uma tentativa de identificação de ω por variáveis instrumentais / two-stage sobre os mesmos logs de competição — qualquer um dos dois converteria a peça central de "interpretação favorecida" em "achado demonstrado".

**Não recomendo rejeição**: as falhas são de excesso de conclusão e de acabamento, não de execução fraudulenta ou de erro fatal; a base experimental existe, o protocolo é sólido, e as correções mais importantes são de escrita.

---

### Notas resumidas

| Critério | Nota |
|---|---|
| Originalidade | 3,5 / 5 |
| Solidez técnica | 2,5 / 5 |
| Rigor experimental | 3,0 / 5 |
| Clareza | 3,5 / 5 |
| Relevância | 4,0 / 5 |
| Reprodutibilidade | 2,5 / 5 |
| **Recomendação** | **Borderline (inclinado a weak accept, condicional às correções B1–B6 e C1–C5)** |
