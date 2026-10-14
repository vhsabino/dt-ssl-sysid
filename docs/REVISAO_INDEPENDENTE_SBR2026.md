# Revisão independente — SBR/LARS 2026

**Artigo:** "A Behavioral Model for Reality-Gap Mitigation in Digital Twins of Omnidirectional Soccer Robots"
**Arquivo revisado:** `uploads/Artigo_SBR_2026___Digital_Twin (3).pdf` (7 páginas, A4, pdfTeX, 2026-08-09)
**Fontes consultados quando o PDF estava ambíguo:** `latex/main.tex`, `latex/sections/*.tex`, `latex/tables/*.tex`, `latex/figures/*.png`
**Papel do revisor:** revisor externo, sem acesso ao repositório de dados/artefatos do autor.
**Data da revisão:** 2026-08-09

---

## 0. Nota preliminar sobre o build revisado

O PDF entregue é um build quebrado, e isso vai além dos "??" e do erro de siunitx avisados. Concretamente:

- A Seção III-C termina literalmente no meio da frase — *"identification resamples every signal onto the uniform"* — e o texto salta direto para "IV. Results".
- Com isso, **desaparecem do PDF as subseções III-D (Identification), III-E (Dedicated open-loop yaw excitation), III-F (Geometric constants), III-G (Coordinate conventions) e III-H (Free-run replay and multi-horizon metric)**, além da Tabela de unidades e da Eq. (2) (definição de *fit*).
- Ou seja: **no PDF submetido a métrica central (`e_pos` re-ancorado), a regra de binning, o gate estatístico, o `N_min`, os horizontes e a definição de *fit* nunca são definidos** — todos os resultados da Seção IV citam construtos que o leitor nunca viu.

Revisei o conteúdo dessas subseções a partir de `sections/03_method.tex`, como instruído, e as considero **presentes e razoavelmente bem escritas**. Não penalizo o artigo por elas faltarem no PDF. Mas registro duas consequências que **são** do conteúdo, não do build:

1. **Orçamento de páginas.** O PDF de 7 páginas está incompleto. Reinserindo ~2 páginas de Método + `tab_units` (que é `\input` em `03_method.tex:206`), o build correto fica em **8 páginas ou mais** — os próprios comentários no fonte falam em "CORTE 2026-08-09 (9->8 pag.)". Contra um limite de **6 páginas** (ver §6.1), isso é um problema estrutural, não de formatação.
2. **`tab_validation_composition.tex` existe mas não é `\input` em lugar nenhum.** A tabela que tornaria auditável o buraco de validação rotacional (264/1/0) está órfã; o fato só aparece em prosa.

---

## 1. Resumo do artigo, nas minhas palavras

Consegui reconstruir a contribuição em **uma leitura**, com uma ressalva: a definição da métrica não estava no PDF, então tive de aceitá-la sob palavra até consultar o fonte.

O artigo modela um robô SSL omnidirecional de 4 rodas como **três canais SISO desacoplados de primeira ordem com tempo morto (FOPDT)** — um por grau de liberdade (`vx`, `vy`, `ω`) — mapeando comando de velocidade de corpo para velocidade de corpo atingida. Nove parâmetros no total. Os canais translacionais são identificados por minimização de erro de predição a partir de **logs de competição em malha fechada** (dados que as equipes já gravam), com hold-out por evento, e atingem ~87% de *fit*. O canal de yaw **falha** nesse regime; os autores diagnosticam por quê e o re-identificam numa **coleta dedicada em malha aberta** (escada de degraus de yaw com `vx=vy=0`), obtendo *fit* 71,1% e ganho ≈1,00 contra 1,3–1,35 do ajuste em malha fechada.

O diagnóstico é a parte mais interessante do artigo e é feito com cuidado: 94,3% das amostras de comando de yaw nos logs caem abaixo do limiar de atuação por roda, mas os autores **refutam a leitura ingênua** (não é que o atuador esteja desligado — a zona morta engaja em ~2% das amostras) e a substituem por **diluição**: em jogo, o comando de yaw contribui com mediana de 1,0% do setpoint por roda, então a rotação medida é dominada por perturbações que o comando não produziu, e sob realimentação essas perturbações são correlacionadas com o comando — o viés clássico de identificação em malha fechada.

A fidelidade é avaliada em **free-run** (sem teacher forcing), em janelas re-ancoradas à pose SE(2) verdadeira, com erro de posição mediano em horizontes de 0,1 a 1,5 s, contra dois comparadores: **cinemática ideal** e **rSim** (motor ODE do rSoccer, com parâmetros default). No bin translation-dominated (264 janelas densas, 49 independentes), em h_ref = 0,4 s: gêmeo 0,038 m, ideal 0,101 m, rSim 0,131 m; Wilcoxon pareado p = 4,4e-11, rank-biserial +0,922.

**Tese de fundo:** identificabilidade é propriedade dos dados, não do DOF. Mesma estrutura, mesma ferramenta, veredictos opostos conforme o regime de excitação — e o diagnóstico (fração da atuação atribuível a cada canal de comando) é computável dos próprios logs, antes de qualquer ajuste.

---

## 2. Avaliação por critério

| Critério | Nota | Justificativa curta |
|---|---|---|
| Originalidade | **3/5** | O achado de diluição/excitação é genuíno e bem instrumentado; a modelagem em si é livro-texto. |
| Solidez técnica | **3/5** | Modelo, discretização e diagnóstico de yaw são sólidos; a comparação central não está isolada. |
| Rigor experimental | **2/5** | Gate pré-registrado é louvável, mas a base empírica é ~74 s de movimento de **um** robô e o baseline principal nunca é especificado. |
| Clareza | **3/5** | Escrita boa em nível de frase; arquitetura de evidência confusa (três harnesses, dois grids de horizonte, Modos A/B indefinidos). |
| Relevância SBR/LARS | **5/5** | Encaixe direto em pelo menos 4 tópicos da chamada; problema real e reconhecível para a comunidade. |
| Reprodutibilidade | **3/5** | Determinismo bit-exato e pré-registro são exemplares; repositório não verificável e o baseline rSim não é descrito o bastante para reimplementar. |

### 2.1 Originalidade — 3/5
`G(s) = K·e^(−Td·s)/(τs+1)` por DOF é o modelo de processo mais convencional que existe (o próprio artigo cita Åström & Hägglund [12] para isso). A originalidade **não** está no modelo — está em (a) tentar identificá-lo de logs operacionais de competição e (b) quantificar, de dentro dos logs, **por que um dos DOFs não é identificável ali**. A parte (b) é boa e eu não conheço precedente direto no contexto SSL.

Mas a alegação de gap na Seção II-d — *"No prior work, to our knowledge, identifies a behavioral twin of an omnidirectional robot from closed-loop operational logs"* — é enfraquecida pelo próprio artigo: o canal de yaw acabou **não** sendo identificado de logs de malha fechada. O artigo entrega "dois de três DOFs de logs operacionais + um resultado negativo bem caracterizado". Isso é honesto, mas é menos do que o gap enunciado promete.

### 2.2 Solidez técnica — 3/5
Positivo: a discretização (Seção III-B) é especificada com um nível de detalhe que raramente vejo em artigo de conferência — coeficiente ZOH exato vs. Euler, teto vs. arredondamento no atraso, e o resíduo sub-amostral com análise de sensibilidade (±21%). A reconciliação contra um Simulink construído independentemente (≤6 mm, ≤9e-4 rad) é uma verificação de implementação genuína, não decorativa.

Negativo: ver §4(i). O núcleo do problema é que a diferença de 0,093 m contra o rSim **não é atribuída** a nada em particular. O artigo tenta uma ablação (o termo de atraso) e admite não conseguir isolar o resto.

### 2.3 Rigor experimental — 2/5
O que puxa a nota para baixo, em ordem:
- **Tamanho da evidência.** 49 janelas independentes × 1,5 s ≈ **73,5 segundos** de movimento pontuados. O artigo nunca declara isso em segundos, nem quantos eventos de hold-out geram essas 49 janelas.
- **Independência.** O teste de Wilcoxon trata as 49 janelas como amostras pareadas independentes. Janelas não sobrepostas do **mesmo evento** compartilham robô, superfície, sessão e controlador; o *n* efetivo é o número de eventos (aparentemente ~10, de `holdout_events.json`), não 49. Os `p` de 1e-13 são aritmeticamente corretos e epistemicamente enganosos.
- **`vx` tem um único evento de hold-out** (nota da Tabela I). Um número de generalização com n=1.
- **Um robô, uma superfície, e — para ω — uma única sessão.** O artigo reconhece isso nas Limitações, o que é correto, mas reconhecer não substitui.

### 2.4 Clareza — 3/5
Frase a frase, a escrita é acima da média para o SBR: precisa, sem inflação, com boa disciplina de qualificadores. O problema é estrutural — ver §4(ii), itens C4–C7. O leitor tem de rastrear três harnesses de avaliação diferentes, dois grids de horizonte ({0,1…1,5} s e {0,5…4} s), dois "Modos" (A/B) nunca definidos no Método, e duas linhas de "closed-loop" para ω que são ajustes diferentes.

### 2.5 Relevância SBR/LARS — 5/5
Ver §6.1. Encaixe forte. Um artigo sobre gap de realidade em SSL, com dados reais e um resultado negativo bem caracterizado, é exatamente o tipo de trabalho que o LARS/SBR deveria publicar.

### 2.6 Reprodutibilidade — 3/5
Pontos altos genuínos: pré-registro dos critérios de aceitação **antes** da estimação (Seção III-E no fonte), hold-out congelado, re-execução determinística ("reproduces all nine parameters to 0.0 absolute difference"), e a explicitação das duas convenções de discretização que uma replicação precisa acertar.

Pontos baixos: (a) o repositório anônimo é uma URL que eu, como revisor, não posso verificar, e a alegação *"with instructions to reproduce every number reported here"* é literalmente não auditável na submissão; (b) **não há uma palavra sobre disponibilidade dos dados** — os logs de competição e a coleta `rotate` são liberados, ou só o código?; (c) o rSim, que é o comparador do título dos resultados, não tem **nenhuma** descrição de configuração no artigo.

---

## 3. Pontos fortes que sustentam aceitação

Não são elogios genéricos; são coisas que a maioria dos artigos que reviso não faz.

1. **O resultado negativo é tratado como resultado, não escondido.** O canal de yaw falha em malha fechada, e o artigo dedica a Seção IV-D inteira a explicar por quê, com um teste de coerência interna raro: a Seção IV-D-b (*"The threshold does not suppress yaw — it buries it"*) **prevê o que a hipótese ingênua implicaria, verifica que não acontece, e troca a explicação**. Esse parágrafo é o melhor do artigo.
2. **Pré-registro de critérios de aceitação** (bounds físicos, fit ≥ 60%, gate SE(2)) antes da estimação, num contexto onde o sample é pequeno e a tentação de ajustar o critério ao resultado é máxima.
3. **Recusa explícita de reportar intervalo de confiança em `K_ω`** porque Ljung–Box rejeita brancura dos resíduos, com justificativa e com declaração de que a comparação usada é entre estimativas pontuais, não um teste formal. É o oposto do padrão do campo.
4. **Controle negativo (calibração conjunta bayesiana de 9 parâmetros)** que perde para o modelo per-DOF e é reportado assim, com `p = 0,040` "na direção errada". Muitos autores teriam simplesmente omitido.
5. **A ablação do termo de atraso** (aplicar o Td do gêmeo à saída do rSim) é o teste certo a fazer, e o resultado é reportado mesmo contrariando a leitura mais simples.
6. **Seção VI (Limitações)** é substantiva e antecipa boa parte das objeções óbvias, inclusive a mais incômoda (*"the zero-parameter ideal-kinematics baseline also outperforms rSim at the reference horizon, which indicates that a substantial share of rSim's deficit comes from the replay harness rather than from its physics"*).

---

## 4. Fraquezas

### (i) BLOQUEADORAS

**B1 — Limite de páginas.** O PDF submetido tem 7 páginas e está **incompleto**; o build corrigido fica em ≥8. O limite do LARS/SBR é **6 páginas em formato IEEE, incluindo tudo** (§6.1). Isso é desk-reject em muitas edições. Não é um detalhe de camera-ready: cortar 2–3 páginas exige decidir **qual claim sai**, e essa decisão muda o artigo.

**B2 — A comparação central (gêmeo vs. rSim) não isola nada, e o próprio artigo diz isso.** Três problemas empilhados:

- *O baseline nunca é especificado.* Em nenhum ponto do artigo — nem no Método completo do fonte — se diz como o rSim foi acionado: massa/atrito/parâmetros usados, timestep, se os comandos passam pelo controlador interno do rSim ou pela sua cinemática de rodas, como a pose inicial e a **velocidade** inicial são impostas. Um revisor não pode reimplementar, e portanto não pode avaliar, o comparador que dá título à Seção IV-C.
- *Assimetria de inicialização.* A Seção IV-C-b diz *"Without warm-up (Mode B, first 15 samples dropped for both plants) rSim's **rest-start penalty** widens the gap (+0.282 m at h_ref)"*. Isto é: **o rSim começa do repouso e o gêmeo não** — o gêmeo recebe uma condição inicial de velocidade derivada da visão (Seção III-C). Um warm-up de 15 amostras (0,25 s) muda o gap de +0,282 para +0,093 m, um **fator 3**. Quando um detalhe de harness domina o efeito nessa proporção, o número medido é predominantemente inicialização de estado, não fidelidade dinâmica. Isso é agudo no horizonte curto: em h = 0,1 s o gêmeo faz 0,0077 m e o rSim 0,0572 m — a 100 ms **nenhum** modelo de primeira ordem com τ ≈ 0,07–0,13 s produziu dinâmica suficiente para explicar 7×; o que se está medindo ali é quase inteiramente o estado inicial.
- *Comparação injusta declarada.* Planta ajustada a **este** robô vs. motor com parâmetros default. O artigo admite (Seção VI: *"it bounds what an untuned reference simulator delivers on this task rather than establishing a general dynamical advantage"*), mas o Abstract e a Conclusão não carregam a ressalva com o mesmo peso.

**B3 — O comparador honesto é a cinemática ideal, e ele é enterrado.** O baseline de **zero parâmetros**, rodando no **mesmo harness** e com a **mesma inicialização**, faz 0,101 m em h_ref contra 0,038 m do gêmeo (gap +0,063, efeito +0,736). O rSim, com harness diferente e inicialização diferente, faz 0,131 m — e **perde para a cinemática ideal**, fato que o artigo registra apenas nas Limitações. A Conclusão (Seção VII) afirma *"it beats the ODE-based rSim engine on translation-dominated hold-out windows at every horizon, with a gap that grows with horizon and effect sizes of +0.731 to +0.980 (GO verdict)"* — sem mencionar a cinemática ideal, sem mencionar que a ideal também bate o rSim, e sem mencionar que contra o comparador justo o ganho é 40% menor e o efeito cai de +0,92 para +0,74. **Isto é excesso de conclusão sobre a evidência por omissão seletiva.**

**B4 — Contradição visível sobre a ablação de atraso.** A legenda da Fig. 1 afirma: *"the Td ablation is **pending** (Sec. IV-C)"*. A Seção IV-C-a executa a ablação e reporta números (*"it widens it, from +0.091 m to +0.143 m at h_ref"*). A Seção VI afirma *"The matched-delay ablation **rules out** the transport-delay term as the source of the gap"*. Pendente, executada e conclusiva ao mesmo tempo. Um revisor cético lê isso como sinal de que a ablação não foi rodada no mesmo pipeline dos demais números, e vai pedir a proveniência.

**B5 — O título promete algo que o artigo não mede.** *"A Behavioral Model for **Reality-Gap Mitigation**"*. Mitigação do gap de realidade é uma alegação sobre transferência: uma política/controlador que degrada menos ao ir para o campo. O artigo mede erro de predição de trajetória em replay open-loop. Nenhuma política é treinada, nada é transferido, nenhum controlador é avaliado. O que o artigo demonstra é fidelidade preditiva de curto horizonte contra dois comparadores — o que já é uma contribuição, mas não é a do título.

### (ii) CORRIGÍVEIS antes da câmera-pronta

**C1 — Erro aritmético verificável na Seção III-B.** *"α_i is the exact ZOH coefficient 1 − e^(−Δt/τ_i) rather than an Euler step Δt/τ_i, **which at the identified time constants would differ by close to a fifth**"*. Com Δt = 1/60 e os τ da Tabela I: para τ = 0,072 → Euler 0,2315 vs. exato 0,2067 (**12,0%** relativo ao exato); τ = 0,127 → 0,1312 vs. 0,1230 (**6,7%**); τ = 0,083 → 0,2008 vs. 0,1819 (**10,4%**). O maior é ~12%, não ~20%. Corrigir para "cerca de um décimo" ou dar o número.

**C2 — `m = 4` amostras é inconsistente com a própria convenção do artigo.** A Seção IV-C-a aplica *"the twin's identified translational dead time to the rSim output as a pure shift of m = 4 samples (66.7 ms)"*. Pela regra de teto da Seção III-B: Td_vx = 0,069 s → ⌈4,14⌉ = **5** amostras; Td_vy = 0,056 s → ⌈3,36⌉ = 4. Então m=4 é o atraso de `vy`, não "o atraso translacional do gêmeo". Dizer qual canal, ou justificar a escolha.

**C3 — O mesmo número aparece com dois valores.** O gap em h_ref é **+0,093 m** (Seção IV-C e Tabela II: 0,1312 − 0,0382 = 0,0930) e **+0,091 m** (Seção IV-C-a, na ablação). O artigo explica em seguida (*"reproduces the Mode A baseline of Table II to within 2 mm"*), mas o leitor encontra o segundo número **antes** da explicação e sem etiqueta de que vem de outra corrida. Marcar explicitamente.

**C4 — O ganho de yaw em malha fechada tem quatro valores diferentes no artigo:** `1.35` (Seção IV-D, ajuste direto), `1.3–1.5` (Seção IV-D-b e Seção V-B, per-amplitude), `1.3–1.35` (Seção V-C), `1.307` (Tabela III). São grandezas diferentes (ajuste direto, faixa por amplitude, re-identificação restrita ao regime), mas o texto as usa quase intercambiavelmente. Fixar uma nomenclatura.

**C5 — A Tabela III é armadilha de leitura.** A linha "Closed-loop" traz `K=1.307, τ=0.0222, Td=0.1179`, que **não** é o ajuste `(1.35, 0.035, 0.106)` com fit 52,6% citado no primeiro parágrafo da Seção IV-D — é a re-identificação restrita ao regime, conforme a nota de rodapé †. O leitor médio vai emparelhar 1.307 com 52,6%. A legenda diz "closed-loop competition logs vs. dedicated open-loop", o que reforça o erro. Renomear a linha ("Closed-loop, regime-restricted") ou dar as duas linhas.

**C6 — "Mode A" e "Mode B" nunca são definidos no Método**, nem no fonte completo. A Tabela II define Mode A na legenda ("warm-up + rigid SE(2) re-anchor") e a Seção IV-C-b define Mode B de forma internamente ambígua: *"Without warm-up (Mode B, first 15 samples dropped for both plants)"* — "sem warm-up" e "15 amostras descartadas" parecem dizer coisas opostas. Dado que essa escolha move o resultado por um fator 3 (B2), ela precisa de um parágrafo próprio no Método.

**C7 — Dois grids de horizonte sem sinalização suficiente.** A Seção IV-A reporta *"roughly halving the median position error at 2.5 s"* — mas 2,5 s não existe no grid {0,1; 0,2; 0,4; 0,7; 1,0; 1,5} s. A explicação está na Seção III-H ("Horizon grid and anchor convention"), que **não aparece no PDF**. Mesmo no build correto, misturar dois harnesses no mesmo artigo pede uma frase de aviso no ponto de uso, não só na definição.

**C8 — A Fig. 2 está em PORTUGUÊS.** Título *"Identificacao ω (P1D, malha aberta, dataset rotate) -- medido vs simulado"*, legendas "medido"/"simulado (P1D)", subtítulos "(treino)", eixo *"t - inicio bruto do evento (s)"* — e sem acentos. Num artigo em inglês, isso é inaceitável. Além disso é uma figura MATLAB default de **6 painéis** colocada a `0.95\columnwidth`: numa coluna IEEE (~88 mm), rótulos de eixo que ocupam ~30 px numa imagem de 2380 px renderizam a cerca de **3 pt**. Ilegível impressa. Ou vira `figure*` com 2–3 painéis, ou vira painel único.

**C9 — Alegação central sem evidência mostrada.** *"A per-amplitude gain analysis shows a flat effective gain of ≈1.3–1.5 across the closed-loop command range, **with no dead-zone knee visible** in the body-frame yaw signal"* (Seção IV-D). Essa ausência de joelho é uma das duas âncoras do argumento de diluição, e não há figura. O ativo `figures/omega_gain_amplitude.png` existe no diretório e não é usado. Se não couber, ao menos dar a estatística (inclinação ajustada, CI) em vez de "no knee visible".

**C10 — Erro de heading é reportado seletivamente.** A Seção IV-C-c admite que *"against rSim, however, it [e_ang] is larger at long horizons — the position claim does not transfer to heading"*. Isso não aparece no Abstract nem na Conclusão. Um artigo cujo Abstract diz que o gêmeo bate o simulador deve dizer que **em orientação, em horizonte longo, ele perde**.

**C11 — Nunca se declara sobre quanto dado a alegação principal repousa.** "265 dense windows (49 independent)" com H_max = 1,5 s e stride ≥ H_max implica ~**73,5 s** de movimento pontuado. Declarar em segundos e em número de eventos de hold-out. E declarar a estrutura de correlação: quantas das 49 janelas vêm do mesmo evento.

**C12 — Referência [3] sem venue nem ano** ("Preprint"). Num artigo que usa [3] três vezes para sustentar a motivação (políticas de RL treinadas nesses ambientes), a citação precisa ser rastreável.

**C13 — `tab_validation_composition.tex` não é incluída** (verificado: nenhum `\input` no fonte). Se houver espaço, essa é a tabela mais útil que o artigo tem para a honestidade do escopo.

### (iii) Sugestões opcionais

- **S1 — Reposicionar o artigo em torno do achado de identificabilidade.** O resultado forte, defensável e novo é a Seção IV-D + Seção V-A. O resultado fraco e contestável é gêmeo-vs-rSim. Um artigo de 6 páginas cujo título e Abstract fossem a *dilution/excitation story*, com a comparação de fidelidade como validação de suporte contra a cinemática ideal, seria mais curto, mais honesto e mais difícil de rejeitar. Isso resolve B1, B2, B3 e B5 de uma vez.
- **S2** — Reportar `e_pos` normalizado pela distância percorrida na janela, além do absoluto. 0,038 m em h_ref significa coisas diferentes a 0,3 m/s e a 2,5 m/s.
- **S3** — Um bootstrap agrupado por **evento** (não por bloco dentro do evento) daria o intervalo que a estrutura dos dados realmente sustenta, e provavelmente mataria os `p` de 1e-13 em favor de algo defensável.
- **S4** — Comparar numericamente com o gêmeo Simscape white-box de [13] (150–240 mm de RMSE de trajetória em cenários de jogo). O artigo cita esse número na Seção II-b e depois reporta 38–123 mm sem jamais voltar a ele. O leitor vai fazer a conta sozinho; melhor os autores fazerem, com as ressalvas de cenário e métrica.
- **S5** — A escada de yaw usa {0,25; 0,5; 1; 2,5; 5} rad/s. Um único ponto adicional em ~0,75 rad/s fecharia o bracket 0,58–0,60 vs. (0,5; 1,0] e transformaria um intervalo em uma medida. É ~1 minuto de coleta.
- **S6** — A palavra "digital twin" carrega, na literatura de manufatura que o artigo cita ([4], [6], [10]), sincronização bidirecional com o ativo físico. Aqui não há sincronização em tempo de execução. O artigo é honesto ao dizer "behavioral (observational)"; valeria uma frase explicitando essa diferença de escopo já na Introdução.

---

## 5. As perguntas que eu faria como revisor

1. **Como o rSim é acionado?** Parâmetros (massa, inércia, atrito de roda, coeficientes de contato), timestep de integração, e se os comandos passam pelo controlador de rodas do rSim ou pela cinemática direta. Sem isso não é possível avaliar a alegação central.
2. **O rSim recebe velocidade inicial?** Se não, e o gêmeo recebe, então em h = 0,1 s vocês estão medindo estado inicial e não dinâmica. Qual é o gap em h_ref quando **ambos** partem do repouso E ambos recebem a mesma estimativa de velocidade inicial derivada da visão?
3. **Decomponham o gap de +0,093 m.** Quanto vem de (a) mismatch de velocidade inicial, (b) ganho estacionário, (c) constante de tempo, (d) atraso? A ablação de Td cobre só (d). Um teste direto: rodar o gêmeo com K=1, τ=0, Td=0 (= cinemática ideal) e com K identificado, τ=0, Td=0 — isolando ganho de dinâmica.
4. **Quantos eventos de hold-out geram as 49 janelas independentes?** E qual o resultado se o Wilcoxon for pareado **por evento** (mediana dentro do evento) em vez de por janela?
5. **A Fig. 1 diz que a ablação de Td está "pending"; a Seção IV-C reporta seus números.** Qual das duas está certa? A ablação foi executada no mesmo pipeline registrado que gerou a Tabela II?
6. **Sobre o *fit* de 71,1% do yaw:** olhando a Fig. 2, os eventos são degraus únicos de ~10 s. Nesses sinais, `‖y − ȳ‖` é dominado pelo transiente do degrau (≈0,5 s de 10,5 s) e por ruído de medição de amplitude enorme (no painel `rotate_01_05`, comando 1,0 rad/s, o ω medido oscila ±0,4 rad/s). Um *fit* nesse dado **não é comensurável** com o *fit* obtido em logs de competição ricos em variação. Em que sentido "87% vs. 71%" e o gate de 60% são a mesma escala? Por que o gate pré-registrado deveria valer em dois regimes de excitação diferentes?
7. **Ainda na Fig. 2:** o traço simulado (vermelho) parte de zero em t ≈ −0,5 s enquanto o medido está no patamar do degrau anterior, gerando um transiente artificial grande no início de cada segmento. Esse trecho entra no cálculo do *fit*? Se entra, ele infla o numerador; se não entra, digam onde o segmento começa.
8. **Ljung–Box rejeita brancura para os dois ajustes de yaw.** Vocês atribuem ao diferenciador suavizante. Isso é testável: rodar a identificação com a velocidade angular do encoder/odometria em vez da derivada da visão, ou com uma janela SG diferente, e verificar se a rejeição persiste. Fizeram?
9. **Por que os intervalos de confiança dos parâmetros translacionais também não são reportados?** A justificativa dada (Tabela I) é a não-brancura dos resíduos de **yaw**. `vx`/`vy` sofrem do mesmo diferenciador. Se a razão vale para um, vale para todos — e então nenhum dos nove parâmetros tem incerteza declarada no artigo.
10. **`vx` tem um único evento de hold-out.** Qual é a variância do fit de `vx` sob leave-one-event-out sobre os 46 eventos?
11. **Sobre o "negative control" bayesiano:** `p = 0,040` com gap +0,0041 m. Com o gate declarado (α = 0,05), esse resultado é *significativo na direção errada* — mas 4 mm num contexto onde o warm-up move 190 mm. Vocês o tratam como evidência de que logs de malha fechada não sustentam ajuste conjunto. Não é mais parcimonioso dizer que os dois modelos empatam?
12. **[13] reporta 150–240 mm de RMSE de trajetória para um gêmeo white-box do mesmo tipo de robô.** Vocês reportam 38–123 mm. Por que esses números não podem ser comparados? (Se puderem, é o resultado mais forte do artigo e está fora dele.)
13. **Disponibilidade dos dados:** os logs de competição e o dataset `rotate` são liberados junto com o código, ou só o código? "Instructions to reproduce every number" pressupõe os dois.
14. **As Tabelas I e III trazem `K_ω` com 4–5 dígitos significativos** (1.0016, 1.307, 0.0828) em cima de 4 eventos de treino de uma sessão, sem intervalos. Que precisão vocês realmente defendem?

---

## 6. Checagens específicas pedidas

### 6.1 CFP — o que consegui confirmar

**Não consegui acessar `https://www.natalnet.br/sbr2026/#cfp`.** O `web_fetch` retorna corpo vazio (página aparentemente renderizada por JS) em três tentativas (`/sbr2026/`, `/sbr2026/index.html`, `/sbr2026/index.php?page=call`), e o ambiente de shell não tem rede. A página oficial de CFP do LARS/SBR em `robotica.robocup.org.br/?page_id=1137` **está desatualizada**: o conteúdo servido em 2026-08 ainda é o texto de LARS/SBR 2019 (Rio Grande), embora a mesma URL seja linkada como "Call for Papers – LARS/SBR – Robótica 2026".

Confirmado (com o grau de certeza indicado):

| Item | Valor | Confiança |
|---|---|---|
| **Limite de páginas** | **6 páginas**, formato IEEE padrão, **incluindo** título, resumo, tabelas, figuras e referências | **Alta.** Texto idêntico nas chamadas de 2019, 2020, 2021, 2024 e 2025; nenhuma edição recente com limite diferente. Não confirmado *especificamente* para 2026. |
| **Formato** | IEEE conference, **A4** (templates `ras.papercept.net`, "set to A4") | Alta |
| **Idioma** | Inglês obrigatório | Alta |
| **Double-blind** | **Sim** — autores devem ocultar nomes, contato, agradecimentos e qualquer referência ao local da pesquisa | Alta (consistente de 2019 a 2025); não confirmado explicitamente para 2026 |
| **Submissão** | JEMS/SBC | Alta |
| **Proceedings** | IEEE Xplore + A&I | Alta |
| **Tópicos** | Lista de 36 tópicos | Alta |
| **Local 2026** | **João Pessoa/PB**, Centro de Convenções (não Natal — o site é hospedado pelo Natalnet/UFRN, mas o evento é em João Pessoa) | Alta |
| Extended version | Melhores artigos convidados para versão estendida no JINT | Média |

**Consequência direta:** o artigo, no build corrigido, **excede o limite** (ver B1). Se o limite de 2026 for de fato 6 páginas, isto precisa ser resolvido antes de qualquer discussão de mérito.

### 6.2 Aderência aos tópicos do CFP
Forte. Encaixa em pelo menos quatro dos 36 tópicos: **20 (Robot soccer)**, **14 (Robot modeling)**, **11 (Robot simulation and visualization tools)**, **33 (Mobile robot platforms)** — e tangencia 16 (Sensor-Motor control of Robots). Nenhuma objeção de escopo.

### 6.3 O Abstract corresponde ao conteúdo?
**Parcialmente.** Todos os números do Abstract são rastreáveis ao corpo e batem (87% ≈ 86,7/87,1; 71%; 1%; 0,038 / 0,131 / 0,101; efeito 0,92 = 0,922; horizontes 0,1–1,5 s). Bom.

Mas o Abstract:
- **omite** que a cinemática ideal (zero parâmetros) também bate o rSim, e que o comparador justo dá um ganho 40% menor;
- **omite** que em erro de heading o gêmeo perde para o rSim em horizonte longo (Seção IV-C-c);
- **omite** que 99,6% da população de validação é translacional e que a fidelidade rotacional é *não validada* — omissão relevante num Abstract que anuncia um gêmeo de três DOFs;
- diz *"untuned ODE-based league simulator"*, o que é honesto — crédito por isso.

Além disso o Abstract herda o problema do título: promete "reality-gap mitigation" e entrega erro de predição em replay.

### 6.4 Figuras e tabelas: necessárias e legíveis?

| Elemento | Necessária? | Legível? | Nota |
|---|---|---|---|
| Fig. 1 (pipeline TikZ, 2 colunas) | Sim | Sim | Boa. **Mas a legenda contradiz o texto** (B4: "Td ablation is pending") e repete o "94,3% abaixo do limiar" como razão da coleta dedicada — exatamente a leitura que a Seção IV-D-b passa uma página refutando. A legenda propaga o erro que o artigo corrige. |
| Fig. 2 (yaw, 6 painéis) | Sim (é o resultado central e o único traço medido-vs-simulado do artigo) | **Não** | Em **português**, sem acentos, estilo MATLAB default, 6 painéis em uma coluna → rótulos a ~3 pt. Ver C8. |
| Fig. 3 (twin vs. rSim) | Sim | Sim | Limpa, em inglês, tipografia adequada, CI de bootstrap visível. É a melhor figura do artigo. Redundante com a Tabela II em conteúdo, mas o painel de gap com CI justifica a duplicação. |
| Tabela I (parâmetros) | Sim | Sim | Nota de rodapé é honesta sobre a ausência de dispersão em `vx`. |
| Tabela II (twin vs rSim) | Parcialmente redundante com a Fig. 3 | Sim | Num artigo de 6 páginas, **uma das duas deveria sair**. Sugiro manter a Fig. 3 e cortar a tabela, movendo p/efeito para a legenda. |
| Tabela III (regimes de yaw) | Sim | Sim | Estrutura confusa (duas mini-tabelas empilhadas) e a linha "Closed-loop" é armadilha (C5). |
| Tabela de unidades | (ausente do PDF) | — | Presente no fonte; útil, mas é a primeira candidata a corte se o limite for 6 páginas. |

**O artigo não tem uma única figura de trajetória.** Um artigo cuja alegação é "erro de posição em free-run" nunca mostra uma trajetória — real vs. gêmeo vs. rSim vs. ideal — numa janela de hold-out. É a figura que eu mais quero ver e é a que não existe.

### 6.5 Referências: adequadas e atuais?
**Adequadas.** 20 entradas; boa mistura temporal — clássicos de identificação em malha fechada de 1977/1998/1999 ([16]–[18]), Ljung 1999 [19], Åström & Hägglund 1995 [12] — e trabalho recente pertinente: 2023 [9,11], 2024 [4,7,15], 2025 [5,6,8,13], 2026 [10]. Nove das 20 são de 2023 ou depois. Cobertura da literatura de gêmeos digitais de plataformas móveis, de simuladores SSL e de identificação em malha fechada é apropriada para o venue.

Ressalvas:
- **[3] não tem venue nem ano** ("Preprint") e é usada para sustentar a motivação.
- Falta literatura de **identificação de sistemas em malha fechada com métodos corrigidos** aplicada a robótica móvel — o artigo cita a teoria ([16]–[18]) e admite não ter tentado IV/two-stage/joint I-O (Seção VI), o que é honesto, mas nenhuma aplicação recente é citada.
- **Nenhum trabalho de SSL sobre modelagem de dinâmica de robô com dados de jogo além de [13], [14], [15].** Se existe, faltou; se não existe, vale afirmar.
- **Anonimização:** OK. Sem nomes, sem afiliação, sem agradecimentos, URL do repositório anonimizada (`anon-ssl-dt`). [13] e [14] são citados em terceira pessoa. Nenhuma violação detectável de double-blind.

### 6.6 Afirmações sem suporte no próprio PDF
Lista, em ordem de gravidade:

1. **"reality-gap mitigation"** (título) — nenhuma medida de transferência (B5).
2. **Configuração do rSim** — a alegação comparativa central repousa num sistema nunca descrito (B2).
3. **"no dead-zone knee visible in the body-frame yaw signal"** (Seção IV-D) — âncora do argumento de diluição, sem figura nem estatística (C9).
4. **"with instructions to reproduce every number reported here"** (Seção VII-a) — não auditável na submissão; sem declaração de disponibilidade dos dados.
5. **"the two agree to ≤ 6 mm... on a reference event"** (Seção III-B) — um evento, não mostrado, sem identificação de qual.
6. **"Those ranges are swept over nine plausible wheel-angle layouts... the conclusion is invariant to the choice"** (Seção IV-D-b) — os nove layouts não são listados nem a invariância é quantificada.
7. **"reproduces all nine parameters to 0.0 absolute difference"** (Seção IV-A) — determinismo bit-exato é plausível, mas "0.0 absolute difference" em nove floats merece dizer com que tolerância.
8. **"a residual initial-velocity mismatch also accumulates with horizon"** (Seção V-C) — nunca quantificado, e é exatamente o confundidor que decide B2.
9. **"which at the identified time constants would differ by close to a fifth"** (Seção III-B) — aritmeticamente errado por ~2× (C1).
10. **Legenda da Fig. 1: "the Td ablation is pending"** vs. Seção IV-C que a reporta (B4).

### 6.7 Limite de páginas
**Não.** 7 páginas no PDF submetido, e o PDF está incompleto — o build corrigido passa de 8. Limite: 6. Ver B1.

---

## 7. Recomendação final

### **WEAK REJECT**

Justificativa. Há um bom artigo aqui, mas não é o artigo que foi submetido. A contribuição defensável — *identificabilidade é propriedade do regime de excitação, e a diluição do comando de yaw é mensurável a partir dos próprios logs, antes de ajustar qualquer modelo* — é original o suficiente, bem instrumentada, e foi conduzida com um nível de disciplina metodológica (pré-registro, controle negativo, recusa de reportar CIs inválidos) que é raro no venue e que eu gostaria de premiar.

O que impede a aceitação nesta forma:

- o artigo **excede o limite de 6 páginas** de modo estrutural, não cosmético;
- o resultado que o título, o Abstract e a Conclusão colocam em primeiro plano — bater o rSim — é o **menos defensável** do artigo: baseline não especificado, inicialização assimétrica que move o efeito por um fator 3, e comparação declaradamente "ajustado vs. default", num cenário em que a cinemática ideal de zero parâmetros também vence o rSim;
- o resultado **bem construído** (yaw/excitação) está subordinado a ele.

Não é um reject forte: nada aqui é errado, inventado ou desonesto. Ao contrário — as Limitações do artigo já contêm a maior parte da minha crítica, escrita pelos próprios autores. O problema é que as conclusões não foram ajustadas às limitações que os autores reconhecem.

### O que moveria minha nota para cima

**Para *weak accept* (mudanças de reescrita, sem experimento novo):**
1. Cortar para 6 páginas, tirando gordura da comparação com o rSim e não do diagnóstico de yaw.
2. Reescrever título, Abstract e Conclusão em torno do achado de identificabilidade; **rebaixar a comparação com o rSim a uma linha de contexto** e promover a comparação contra a cinemática ideal (mesmo harness, mesma inicialização) a comparação primária, com o número honesto (+0,063 m, efeito +0,736).
3. Adicionar ao Abstract as três omissões: heading pior que o rSim em horizonte longo; 99,6% da validação é translacional; comparação rSim é fitted-vs-untuned.
4. Resolver B4 (ablação: pendente ou executada?), C1 (erro do "um quinto"), C2 (m=4 vs. m=5), C3, C4, C5, C6 (definir Modos A/B no Método).
5. Refazer a Fig. 2 em inglês e legível (C8).
6. Declarar quantos segundos e quantos eventos de hold-out sustentam a alegação (C11), e declarar disponibilidade dos dados.

**Para *accept* (exige trabalho novo, tudo barato):**
7. Especificar completamente a configuração do rSim, **e** rodar a comparação com inicialização de velocidade simétrica entre as plantas. Se o gap sobreviver, é um resultado de verdade e vale o destaque atual.
8. Decompor o gap em ganho / constante de tempo / atraso / velocidade inicial (pergunta 3). É um dia de trabalho e converte uma correlação numa explicação.
9. Bootstrap e Wilcoxon **agrupados por evento**, com o `n` efetivo declarado.
10. Uma figura de trajetória: real vs. gêmeo vs. ideal vs. rSim, numa janela de hold-out, em h = 1,5 s.
11. Fit de yaw reportado numa métrica comensurável entre regimes (ou uma justificativa explícita de por que 87% e 71% são comparáveis) — ver pergunta 6.

Itens 1–6 são uma semana. Se vierem, mudo para **weak accept** sem hesitar; com 7–8, para **accept**.

---

### Fontes de CFP consultadas
- [Call for Papers – LARS/SBR – Robótica 2026](https://robotica.robocup.org.br/?page_id=1137) (conteúdo servido = texto de 2019; limite de 6 páginas, double-blind, templates IEEE A4, JEMS, 36 tópicos)
- [LARS/SBR 2020 – call](https://natalnet.br/lars-sbr2020/call.html)
- [LARS/SBR 2021 – call](https://www.natalnet.br/lars-sbr2021/call.html)
- [SBR 2026 (Natalnet)](https://www.natalnet.br/sbr2026/) — **inacessível ao fetch (corpo vazio)**
- [SBR 2024](https://natalnet.br/sbr2024/), [SBR 2025](https://natalnet.br/sbr2025/)
