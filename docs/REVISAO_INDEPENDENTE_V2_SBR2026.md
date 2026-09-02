# Revisão independente — SBR/LARS 2026 (Robótica 2026, João Pessoa)

**Manuscrito:** "What Competition Logs Can Identify: Excitation-Dependent Behavioral Modeling of an Omnidirectional Soccer Robot"
**Revisor:** independente, sem acesso a dados, código ou artefatos do autor. Revisão feita **apenas sobre o PDF compilado**.
**Data:** 2026-08-10. Esta é uma revisão NOVA; nada foi assumido de rodadas anteriores.

---

## 0. Procedimento de compilação (para registro)

Os fontes do mount vinham truncados (padding de `\0` e cortes secos). Recuperei o conteúdo real de
`main.tex`, `sections/{00..05,07}.tex` e `tables/tab_sysid_params.tex` do filesystem verdadeiro e reconstruí a árvore
antes de compilar. Substituí `\bibliographystyle{IEEEtran}` por `unsrt` (IEEEtran.bst não existe no sandbox) e criei
um stub de `siunitx`. Build limpo: **zero warnings de LaTeX, zero referências indefinidas, zero `??`, zero `\TODO{}`,
zero overfull hbox > 20 pt**. Arquivos efetivamente no build: abstract, intro, related, method, results, discussion
(com Limitations como subseção), conclusion, 1 tabela, 1 figura, 19 referências renderizadas
(o `.bib` tem 20 entradas; `katyara2024benchmarking` não é citada — invisível no PDF, mas contradiz o comentário
interno de `02_related_work.tex` que afirma que as 20 estão todas citadas).

**Contagem de páginas medida: 7 páginas.** A página 7 contém só a coluna esquerda, com texto até y≈455 de 841 pt
(≈47–55 % de uma coluna, ou ≈0,25 página de transbordo).

**Estimativa para o build real com `IEEEtran.bst`:** ainda **7 páginas**. Testei empiricamente recompilando o `.bbl`
com todos os prenomes reduzidos a iniciais (a economia dominante do `IEEEtran.bst`; o tamanho de fonte da
bibliografia vem da *classe*, não do `.bst`, e já é o real): o texto da p. 7 recuou de y≈455 para y≈401 — cerca de
6 linhas de coluna. Mesmo dando o benefício integral dos ~155 palavras/~30 % que o `IEEEtran.bst` economiza, sobram
**~20–30 linhas de coluna na página 7**. Conclusão: o artigo está **~0,2–0,3 página acima do limite** e não cabe em 6
páginas sem cortar conteúdo (≈250–400 palavras, ou um float, ou a seção V-B inteira).

---

## 1. Resumo do artigo (nas minhas palavras)

Reconstruí a contribuição em uma leitura — o artigo é claro sobre o que promete.

O trabalho modela a camada de planta de um gêmeo digital de um robô omnidirecional de 4 rodas da RoboCup SSL como
**três canais SISO desacoplados de primeira ordem com tempo morto (FOPDT)**, um por grau de liberdade (`vx`, `vy`, `ω`),
totalizando nove parâmetros. A pergunta central não é "qual o melhor modelo", e sim **o que é identificável a partir
dos logs de competição que as equipes já gravam** (comandos em body frame + pose de visão a ~60 Hz, em malha fechada).

Resposta em duas partes. (i) Os canais translacionais **identificam bem** desses logs: fit em hold-out 86,7 % (`vx`) e
87,1 % (`vy`). (ii) O canal de guinada **não identifica**: o ajuste direto dá K≈1,35 com fit 52,6 %, abaixo do gate de
60 %, e piora a posição em free-run. O artigo então diagnostica *por quê*, com um argumento que é o núcleo da
contribuição: a zona morta do firmware é **por roda e posterior à cinemática de comando**, e em jogo as rodas já giram
por causa da translação; portanto o comando de guinada não é *suprimido*, é **diluído** — carrega uma mediana de
**1,0 %** do setpoint por roda (p90 = 5,7 %). Uma coleta dedicada curta, em malha aberta e com `vx=vy=0` (escada de
±{0,25; 0,5; 1; 2,5; 5} rad/s), remove a diluição e identifica ω com K=1,0016 e fit 71,1 %.

A fidelidade é medida em **free-run** (janelas re-ancoradas em SE(2) em t₀, roladas até 1,5 s só com o fluxo de
comandos, sem teacher forcing), contra uma **cinemática ideal de zero parâmetros** no mesmo harness. Sobre 73,5 s de
movimento pontuado (49 janelas independentes, 10 eventos de hold-out), o modelo baixa a mediana do erro de posição de
0,101 m para 0,038 m em h=0,4 s, vencendo em 10 de 10 eventos. Uma ablação atribui a melhoria ao **atraso de primeira
ordem (τ)**, não ao tempo morto. O rSim (motor ODE do rSoccer, sem sintonia) é reportado só como contexto. Duas
ressalvas ficam abertas e são declaradas: o erro de heading é *pior* que o do rSim em horizontes longos, e 99,6 % das
janelas de validação são dominadas por translação, de modo que a fidelidade rotacional **não** é validada.

A "lição metodológica" proposta: antes de declarar um DOF não identificável de logs operacionais, meça a fração da
atuação que o comando daquele DOF carrega — é computável dos próprios logs, antes de qualquer ajuste.

---

## 2. Notas (1–5) com justificativa

| Critério | Nota | Justificativa curta |
|---|---|---|
| **Originalidade** | **3** | O modelo (FOPDT por DOF) é livro-texto e o artigo admite isso. A novidade real é o *diagnóstico de diluição de atuação* e a demonstração de inversão de veredito sob gate idêntico. Isso é genuíno e útil, mas modesto: é uma instância bem documentada de excitação persistente, e o contraste que a sustenta é confundido (ver 4.i-3). |
| **Solidez técnica** | **3** | Discretização, ZOH exato, quantização de atraso, reconciliação contra um Simulink independente: tudo bem-feito e verificável na leitura. Mas a decomposição gain/lag/delay é sequencial e dependente de ordem, o termo "placeholder" — referência central de dois resultados — nunca é definido, e o benefício da semeadura de velocidade inicial (que só as plantas dinâmicas conseguem usar) fica fora da decomposição. |
| **Rigor experimental** | **3** | Pontos altos raros: pré-registro dos critérios de ω *antes* da estimação, recusa explícita de IC para K_ω por não-brancura, controle negativo (bayesopt) reportado como não promovido, análise agrupada por evento. Pontos baixos: 73,5 s de validação, 10 eventos, 1 robô, 1 sessão, 1 split; `vx` com **um único evento de hold-out**; dois harnesses e duas grades de horizonte misturados; padrão estatístico inconsistente entre o resultado principal (por evento) e o controle negativo (por janela). |
| **Clareza** | **3** | A prosa é boa, densa e economicamente escrita. Mas: 7 páginas num limite de 6; a **única figura nunca é citada no texto**; o resultado principal não tem figura nem tabela; "placeholder" não definido; "events" e "splits" usados como sinônimos; §IV-D repete o mesmo número (+0,0489 m) duas vezes com descrições incompatíveis. |
| **Relevância p/ SBR/LARS** | **5** | Alvo exato do evento: RoboCup SSL, gêmeo digital, identificação, sim-to-real. Dialoga com trabalhos de LARS/SBR ([13], [14], [15]). O resultado negativo é acionável para qualquer equipe da liga. |
| **Reprodutibilidade** | **2** | A alegação é forte ("instructions to reproduce every number above", datasets incluídos) mas apoiada num **URL anonimizado que o revisor não pode verificar**. O artigo, sozinho, não permite reprodução: faltam o *stride* das janelas (do qual dependem os 265/49), ordem e janela do filtro Savitzky–Golay, o estimador concreto de erro de predição e sua inicialização, e a definição do "placeholder". "Re-rodar reproduz os nove parâmetros exatamente" é determinismo, não reprodutibilidade. |

---

## 3. Pontos fortes que sustentam aceitação

Nenhum destes é elogio genérico; são coisas que a maioria das submissões erra.

1. **O artigo resolve honestamente um paradoxo dos próprios dados.** §IV-D é o melhor trecho: a estatística de 94,3 %
   de amostras sub-limiar prediz duas coisas (ganho deflacionado, joelho de zona morta) que **não acontecem**; em vez
   de esconder, o artigo enuncia a predição falha e a resolve com a distinção "por roda, depois da cinemática" +
   diluição. Isso é raciocínio científico visível.
2. **Consistência interna verificável do argumento físico.** Checei a aritmética: 1,567/2,699 = 0,5806 e 1,567/2,61 =
   0,6004 → o intervalo declarado "0,58–0,60 rad/s" fecha; e o bracket empírico (0,5; 1,0] rad/s é coerente com a
   escada (0,5 rad/s não move, 1,0 move). A análise de sensibilidade 92,5 %→97,6 % mostra que a conclusão não depende
   do ponto escolhido. Isso é sólido.
3. **Recusa disciplinada de intervalos de confiança.** Não anexar IC a K_ω porque Ljung–Box rejeita brancura, e dizer
   isso explicitamente, é mais rigoroso do que o que a maioria dos artigos de ID faz.
4. **Pré-registro dos critérios de aceitação de ω antes da estimação**, com o gate de 60 % e limites físicos fixados
   *a priori*. Raro em robótica.
5. **Controle negativo reportado e não promovido** (calibração bayesiana conjunta de 9 parâmetros). Publicar o que
   *não* funcionou fortalece a tese de excitação.
6. **Tratamento correto da dependência intra-evento**: usar o evento como unidade de análise (n=10) e dizer
   explicitamente que o p por janela é menor mas não é o que se reporta.
7. **Auto-crítica do próprio comparador.** Mostrar que retirar o warm-up **triplica** o gap contra o rSim (+0,093 →
   +0,282 m) e concluir daí que o que separa é estado inicial, não física, é o tipo de coisa que um autor interessado
   em vencer esconderia.
8. **Métrica bem escolhida e bem defendida**: free-run sem re-âncora interna, com a justificativa explícita de que
   teacher forcing infla a fidelidade aparente.

---

## 4. Fraquezas

### (i) BLOQUEADORAS

**B1. O artigo tem 7 páginas; o limite é 6.**
Medido: 7 páginas com `unsrt`. Estimado com `IEEEtran.bst` real: ainda 7 (economia de ~6 linhas de coluna medida
empiricamente; mesmo no cenário otimista de ~155 palavras, sobram 20–30 linhas). Isso é violação formal e risco de
desk-reject no JEMS. Não é um detalhe de formatação: **cortar 0,25 página vai obrigar a decidir o que sai**, e as
escolhas óbvias (V-B "What the model actually buys", o parágrafo do rSim, a repetição de +0,0489 m em §IV-D) mudam o
texto que estou avaliando.

**B2. A única figura do artigo nunca é referenciada no texto.**
`\label{fig:fits}` existe; `\ref{fig:fits}` não aparece em nenhum arquivo do build (verifiquei por grep em
`main.tex`, `sections/`, `tables/`). A Fig. 1 flutua na coluna direita da p. 4 sem âncora. Violação de estilo IEEE e,
pior, o leitor não é levado à única evidência gráfica que existe.

**B3. O resultado principal do artigo não tem figura nem tabela.**
Toda a contribuição C3 — a comparação twin × cinemática ideal × rSim ao longo de seis horizontes — é entregue como
números em prosa corrida (§IV-C). A única tabela é a de parâmetros; a única figura é sobre ω, que é o resultado
*secundário*. Um leitor não consegue ver a curva erro×horizonte, nem a dispersão por evento, nem uma trajetória real
contra as duas plantas. Para um artigo cuja tese é "fidelidade observacional", isso é um buraco de apresentação.

**B4. A atribuição causal da melhoria ("é o lag, não o dead time") não está isolada.**
Três problemas somados:
- O texto diz "*Turning the three parameter groups on one at a time*", mas os números descrevem um caminho
  **cumulativo** (0,101 → 0,109 → 0,046 → 0,039), não três ablações independentes. Descrição e números discordam.
- Sendo cumulativo, o resultado é **dependente da ordem**. Ligar τ antes de Td naturalmente dá quase todo o crédito a
  τ. Nada no artigo mostra que a ordem inversa daria a mesma conclusão.
- "Nove décimos" só fecha se o denominador **exclui** a contribuição negativa do ganho: 0,063/(0,063+0,007) = 0,90,
  enquanto a melhoria líquida é 0,062 e o passo do lag sozinho é 0,063 (102 %). A convenção usada não é declarada.
- **Confundidor não tratado:** §IV-C diz que ambas as plantas "are seeded with the same measured body velocity". A
  cinemática ideal é *memoryless* (v = u), então essa semeadura não faz nada para ela; a planta FOPDT começa com o
  estado interno na velocidade real medida. O passo "adicionar o lag" é exatamente o passo que introduz **estado** — ou
  seja, o único passo que consegue consumir a condição inicial privilegiada. Parte da vitória, sobretudo em h=0,1–0,4 s,
  pode ser condição inicial e não dinâmica identificada. O artigo aplica esse escrutínio ao rSim (e muito bem) e não o
  aplica a si mesmo.

**B5. "The verdict inverts on an identical gate, with the data regime as the only difference" (§IV-D) é contradito
pela própria seção de Limitações.**
§V-C: "*The two yaw campaigns differ in loop topology, yaw-to-translation ratio and session at once*". Três fatores
mudam juntos; "the only difference" é falso como está escrito. A frase de §IV-D é a afirmação mais forte do artigo e
é a que menos se sustenta. Some-se a isso que **o "placeholder" — a referência contra a qual ambos os vereditos são
computados — nunca é definido no PDF** (aparece em §III-E e §IV-D como se o leitor soubesse o que é). Não dá para
avaliar uma inversão de veredito contra um baseline não especificado.

### (ii) CORRIGÍVEIS antes da câmera-pronta

**C1. Inconsistência numérica: 0,038 m vs 0,039 m.**
§IV-C (e o abstract, e a conclusão) dão 0,038 m para o modelo completo em h_ref. O parágrafo de ablação, três linhas
depois, diz que somar o dead time leva a 0,039 m — que é a *mesma quantidade*. Sem explicação. Ou é arredondamento
diferente, ou são populações/execuções diferentes; nos dois casos precisa ser dito.

**C2. Os três números do controle negativo (bayesopt) não reconciliam com o resultado principal.**
§IV-D-c: bayesopt bate o ideal em −0,098 m; perde para o per-DOF em +0,0041 m. §IV-C: per-DOF bate o ideal em
0,101→0,038 = 0,063 m (mediana) / +0,069 m (gap mediano por evento). Aritmeticamente, se bayesopt ganha 0,098 do
ideal e perde 0,004 para o per-DOF, o per-DOF deveria ganhar ~0,102 do ideal — não 0,063–0,069. Presumo que sejam
harness, grade de horizontes e estatística (pooled mean × median) diferentes, mas **o artigo põe esses números lado a
lado sem avisar**, e o leitor conclui que algo está errado. Ou reconcilie, ou marque explicitamente a
incomparabilidade.

**C3. Padrão estatístico inconsistente dentro do mesmo artigo.**
§IV-C abandona o teste por janela porque "*windows within an event are not independent*" — correto. Mas §IV-D e
§IV-D-c continuam reportando p por janela (3,8×10⁻⁹; 1,7×10⁻¹⁶; 7,6×10⁻¹⁰; 0,040) sem o mesmo tratamento. E a
conclusão "closed-loop logs do not sustain a joint fit that improves on per-DOF identification" é tirada de uma
diferença de **4 mm** com p=0,040 por janela — que pelo próprio gate do artigo (efeito ≥0,2, CI excluindo zero) muito
provavelmente não passaria. Isso é essencialmente um empate apresentado como achado.

**C4. O gate pré-especificado (§III-G-b) não é o gate usado no resultado principal.**
O método define GO/NO-GO com Wilcoxon + moving-block bootstrap sobre janelas não sobrepostas, N_min=10 janelas. O
resultado principal usa pareamento **por evento** (n=10 eventos, bootstrap sobre eventos). A troca é bem motivada,
mas o artigo não diz se foi decidida antes ou depois de ver os dados. Como o artigo se orgulha (com razão) do
pré-registro de ω, essa omissão chama atenção.

**C5. "Halves ... in all ten hold-out events" (Conclusão) é mais forte que a evidência.**
O que foi medido é: (a) a mediana agregada cai pela metade; (b) o modelo **vence** em 10/10 eventos. A conclusão junta
as duas em "halves ... in all ten hold-out events", que afirma redução ≥50 % em *cada* evento — não demonstrado. O
abstract, aliás, está correto ("every one of the ten hold-out events favors it"); é a conclusão que escorrega.

**C6. O erro de heading contra o rSim é uma limitação declarada sem nenhum número.**
§IV-C-c e o abstract afirmam que o e_ang do twin "*exceeds the simulator's at long horizons*". Os valores do twin
(0,013→0,090 rad) e do ideal (0,023→0,095 rad) são dados; os do rSim, não. O artigo pede ao leitor que aceite a
própria limitação sem evidência.

**C7. O fit de `vx` (86,7 %) vem de UM único evento de hold-out** (nota de rodapé da Tabela I). O abstract agrega isso
com `vy` em "roughly 87 percent hold-out fit", o que dá impressão de amostra maior. Além disso: §III-C diz que 10
eventos foram separados como hold-out, mas §IV-A/Tabela I usam 1 (`vx`) e 4 (`vy`). A relação entre o hold-out de
identificação e o hold-out de 10 eventos da avaliação de fidelidade nunca é explicada — e é importante, porque se
forem o mesmo conjunto, os 10 eventos da §IV-C incluem eventos usados para escolher os parâmetros de `vy`.
**Isto precisa ser esclarecido explicitamente**; do jeito que está, não consigo descartar vazamento.

**C8. "A practical restatement of persistent excitation" (§V-D) é imprecisa.**
Excitação persistente é uma propriedade *espectral* do sinal de entrada (ordem de PE, riqueza de frequências), não a
razão entre a amplitude de um comando e a atuação total. Um DOF pode carregar 1 % da atuação e ainda assim ser
perfeitamente identificável se o comando variar suficientemente e a medida for limpa. O artigo nunca reporta, para
ω, nada análogo à correlação cruzada de 0,99 que reporta para `vx`/`vy`: nem espectro, nem ordem de PE, nem
variância de `cmd_ω`, nem relação sinal-ruído da medida de ω. O diagnóstico proposto é interessante, mas a
justificativa teórica está mal colocada.

**C9. "The measured rotation is dominated by disturbances the command did not produce" (abstract) e "most of the
rotation ... was produced not by the command but by slip, contact and traction asymmetry" (§V-A) não são medidos.**
São inferências plausíveis a partir de 1 % de diluição, apresentadas em voz assertiva — no abstract, sem hedge
nenhum. Nada no artigo decompõe a guinada medida em parcela comandada e parcela de distúrbio.

**C10. Reprodutibilidade não verificável.** O URL `github.com/anon-ssl-dt/behavioral-twin-ssl` não pode ser conferido
por um revisor e a promessa é ampla (código + configs + hold-out congelado + **datasets** + instruções para reproduzir
*todos* os números). Independentemente do repositório existir, o **artigo** omite parâmetros necessários: *stride* das
janelas (265 densas / 49 independentes dependem dele), ordem/janela do Savitzky–Golay, o estimador PEM concreto e sua
inicialização/limites, e o "placeholder".

**C11. Sem escala de referência para 0,038 m / 0,101 m.** O leitor não sabe quanto o robô anda em 0,4 s nem qual é o
raio do robô (o raio só aparece implicitamente em R=0,0796 m). Um erro absoluto sem denominador não permite julgar se
a melhoria importa. Uma frase com a velocidade mediana das janelas de hold-out resolve.

**C12. Terminologia oscilante:** "46 events" (§III-C) × "46 splits" (§IV-D); "twin" × "model" × "per-DOF model" usados
alternadamente para a mesma planta. Em 6 páginas isso custa leitura.

**C13. §IV-D repete o mesmo resultado duas vezes**, com descrições incompatíveis do mesmo número: "pooled gap
+0,0489 m **at 4 s**" (1º parágrafo) e "(pooled +0,0489 m)" (penúltimo parágrafo). É pooled ou é em 4 s? E, num artigo
0,25 página acima do limite, uma dessas duas frases é o corte mais barato do texto.

**C14. Sem comparação quantitativa com [13]**, o gêmeo Simscape de robô SSL que o próprio Related Work cita com RMSE
de 150–240 mm. É o comparador mais óbvio da mesma liga e o artigo passa ao largo. Basta uma frase dizendo por que as
métricas não são comparáveis (janela re-ancorada × trajetória inteira).

**C15. Anonimização (double-blind): OK, com um risco leve.** Bloco de título anônimo, sem agradecimentos, sem
financiamento, URL anonimizado. Porém [13] e [14] são, quase certamente, trabalho prévio do mesmo grupo, citados em
terceira pessoa (correto) mas [13] é descrito em uma linha sem posicionamento — a combinação "robô SSL 4 rodas + CAD
próprio + firmware próprio + [13],[14],[15]" identifica o laboratório para qualquer pessoa da liga. Não é violação
formal; vale ao autor saber.

### (iii) OPCIONAIS

- O keyword "sim-to-real" está no Index Terms mas nenhuma transferência é feita. Trocar por "system identification /
  excitation design".
- C1 ("identification ... from closed-loop competition logs") promete o que C4 depois desmente para ω. Um qualificador
  em C1 ("for the translational DOFs") economizaria a tensão.
- "Re-running the pipeline ... reproduces all nine parameters exactly" é determinismo, não reprodutibilidade; ocupa
  uma linha e não sustenta nada. Candidato a corte.
- §V-B tem label `sec:discussion:rsim` mas não fala de rSim. Cosmético.
- A Fig. 1 é legível (3 painéis, eixos em inglês, legenda clara) — mas o modelo aparece essencialmente como uma reta
  no valor comandado. O painel de −1,0 rad/s mostra ruído de medida de ±0,4 rad/s (±40 %), o que é informativo e
  merecia uma frase: o fit de 65 % naquele evento é, em boa parte, teto de ruído.
- Faltou um baseline barato e óbvio: **extrapolação de velocidade constante** a partir da velocidade inicial medida.
  Ele também usa a semeadura de IC e por isso seria o comparador honesto para B4.

---

## 5. As perguntas difíceis que eu faria ao autor

1. **O que é o "placeholder"?** Ele é a referência de dois dos seus resultados centrais (+0,0489 m e −0,1138 m) e não
   está definido em lugar nenhum do PDF. Qual é o (K, τ, Td) dele e de onde ele veio?
2. **Se a cinemática ideal não tem estado, o que significa "seeded with the same measured body velocity"?** Quanto da
   vitória em h=0,1 e h=0,2 s desaparece se você semear a planta FOPDT com `v[0] = K·u[0]` em vez da velocidade real
   medida? Você já tem essa decomposição — por que ela não está no artigo?
3. **Inverta a ordem da ablação** (ideal → +dead time → +lag → +gain). "Nove décimos" continua valendo? Se sim,
   reporte as duas ordens; se não, a frase "the lag, not the dead time, carries the improvement" precisa virar
   "under this ordering".
4. Os 10 eventos de hold-out da §IV-C **são os mesmos** que os hold-outs de identificação de `vx` (1) e `vy` (4)? Se
   forem, a avaliação de fidelidade inclui eventos que participaram da seleção do modelo?
5. Um fit de 86,7 % em **um** evento de hold-out sustenta a afirmação "the translational channels identify directly
   from in-game logs"? Qual é a dispersão entre eventos para `vx`?
6. Reconcilie: ideal→per-DOF = 0,063 m; ideal→bayesopt = 0,098 m; bayesopt→per-DOF = +0,004 m. Esses três números não
   fecham. Em que harness/estatística cada um foi computado?
7. Sua tese é sobre **excitação**, mas você nunca mostra o espectro nem a ordem de PE do comando de guinada nos logs.
   Por que a "fração de atuação" é o diagnóstico certo, e não a variância/riqueza espectral de `cmd_ω` relativa ao
   ruído da medida de ω? Um DOF de 1 % da atuação com comando ricamente variado seria identificável.
8. Você afirma que a rotação medida é dominada por distúrbios. Isso foi **medido**? Qual é a fração da variância de
   `meas_ω` explicada por `cmd_ω` (defasado por Td) nos logs?
9. A campanha de ω dedicada é uma **escada de degraus constantes**. Nesse regime, um ajuste FOPDT é quase um
   estimador de ganho estático. Como você descarta que K_ω=1,00 seja um artefato de regime permanente, e não uma
   propriedade do canal em manobras de jogo?
10. Você reporta o gap contra o rSim e mostra que ele triplica sem warm-up. **Qual é o gap twin×ideal sob o Modo B?**
    Se o Modo B é o teste de robustez, ele deveria ser aplicado também à comparação primária.
11. Duas grades de horizonte e "two independently implemented harnesses" (§III-G-c). O que garante que os dois
    harnesses concordam? Existe algum ponto de horizonte comum onde ambos foram rodados?
12. O que exatamente está no repositório anônimo hoje, e os *datasets* de competição são redistribuíveis (direitos da
    liga/equipe)?
13. Como o modelo se compara a [13] (150–240 mm), e por que essa comparação não aparece?
14. `\ref{fig:fits}` não existe no texto. A Fig. 1 é evidência de qual afirmação, exatamente?

---

## 6. Checagens solicitadas

| Checagem | Resultado |
|---|---|
| **Cabe em 6 páginas?** | **Não.** 7 páginas medidas (`unsrt`); estimo **7 páginas** também com `IEEEtran.bst` real — transbordo de ~0,2–0,3 página. Precisa cortar ~250–400 palavras ou um float. |
| **Abstract corresponde ao conteúdo?** | **Sim, e é o melhor abstract do artigo.** Todos os números do abstract (87 %, 1 %, 71 %, 73,5 s, 0,038/0,101, 10/10, 99,6 %) aparecem no corpo com os mesmos valores. O abstract inclusive declara as três limitações principais — o que é incomum e bom. Duas ressalvas: (a) "the measured rotation is dominated by disturbances the command did not produce" é asseverado sem hedge e não é medido (C9); (b) "Over 73.5 seconds of scored motion, the model halves the median position error" mistura duas populações — os 73,5 s vêm das 49 janelas independentes, as medianas vêm das 264 densas. |
| **Consistência numérica (abstract / resultados / discussão / conclusão)** | Boa no geral; **três problemas**: (1) 0,038 m (§IV-C, abstract, conclusão) × **0,039 m** (§IV-C ablação) para a mesma quantidade; (2) os três números do bayesopt não fecham com o resultado principal (0,063 + 0,004 ≠ 0,098); (3) a conclusão diz "halves ... in all ten hold-out events" enquanto o medido é "vence em 10/10". Verifiquei e **batem**: 49×1,5 = 73,5 s; 264/265 = 99,62 %; 0,5¹⁰ = 9,77×10⁻⁴; 1,567/2,699 = 0,5806 e 1,567/2,61 = 0,6004; média(0,069; 0,056)×60 = 3,75 → teto 4 amostras = 66,7 ms; 0,063/(0,063+0,007) = 0,90. Também é consistente que 0,25 e 0,5 rad/s não engajem, dado o limiar 0,58–0,60. |
| **Figuras e tabelas necessárias e legíveis?** | **Insuficientes.** Uma figura e uma tabela no total. A Fig. 1 é legível (3 painéis, eixos e legenda em inglês, fontes adequadas em 0,82 coluna) mas **não é citada no texto**. A Tabela I é clara e a nota de rodapé é honesta. **Falta a figura/tabela do resultado principal** (erro×horizonte, twin × ideal × rSim; e/ou dispersão por evento). |
| **Referências adequadas?** | **Sim.** 19 referências renderizadas, todas pertinentes e bem distribuídas: clássicos de ID em malha fechada ([16]–[18]), Ljung [19], FOPDT [12], contexto SSL ([1],[2],[3],[13],[14],[15]), gêmeos digitais e ID grey-box ([4],[5],[6],[10]), robôs omni ([7],[8],[9]), sim-to-real offline [11]. Não vi referência inventada nem citação fora de contexto. `katyara2024benchmarking` está no `.bib` e não é citada (invisível no PDF). Ausência notável: nenhuma referência sobre *design de experimento / excitação ótima*, que é o assunto que o artigo diz estar reformulando. |
| **Afirmações sem suporte no PDF** | (a) e_ang do twin > rSim em horizontes longos — sem números do rSim; (b) "widens rather than closes the gap" (ablação de atraso no rSim) — sem número; (c) rotação medida dominada por distúrbio — não medido; (d) "the data regime as the only difference" — contradito por §V-C; (e) "instructions to reproduce every number above" — não verificável; (f) "improve every event-by-horizon cell (20/20 and 65/65)" — contra "the previous, slower parameters", que nunca são apresentados. |
| **Seções vazias / `??` / TODO visíveis** | **Nenhum.** Zero referências indefinidas, zero `??`, zero `\TODO{}`, zero seção vazia, zero warning de LaTeX, zero overfull hbox relevante. O build está limpo. |
| **Anonimização double-blind** | **Conforme.** Bloco de autor anônimo, sem afiliação, sem agradecimentos, sem financiamento, URL anonimizado, auto-citações em terceira pessoa. Risco residual apenas de inferência de laboratório (ver C15). |

---

## 7. Recomendação final

### **WEAK ACCEPT** — condicionada a B1 e B2; converte-se em **reject por questão formal** se as 6 páginas não forem cumpridas.

Justificativa. Este é um artigo honesto e bem executado sobre um problema real da liga, com um resultado negativo bem
diagnosticado que é mais útil para as equipes do que a maioria dos resultados positivos publicados no SBR/LARS. O
diagnóstico de diluição de atuação é uma contribuição de verdade, e a disciplina metodológica (pré-registro,
não-promoção do bayesopt, recusa de IC, análise por evento, auto-crítica do comparador rSim) está acima da média do
evento. O que me impede de recomendar accept é a combinação de: violação de tamanho, ausência de evidência gráfica
para a afirmação principal, uma atribuição causal dependente de ordem e confundida com condição inicial, e uma
afirmação de "única diferença" que a própria seção de limitações desmente.

### O que moveria minha nota para cima (em ordem de impacto)

1. **Caber em 6 páginas** — sem isso não há discussão.
2. **Uma figura do resultado principal**: mediana de e_pos × horizonte para twin / ideal / rSim, com dispersão por
   evento (dot plot dos 10 eventos). Isso resolve B3 e, de quebra, dá ao leitor a escala que falta em C11. Se for
   preciso escolher, prefiro essa figura à Fig. 1 atual.
3. **Citar a Fig. 1 no texto** (uma linha).
4. **Refazer a ablação de forma isolada e ordem-robusta**, incluindo um braço "IC medida × IC = K·u[0]" para separar a
   semeadura de velocidade inicial da dinâmica identificada. Se o lag continuar dominando, a afirmação fica muito mais
   forte do que está hoje. → **weak accept vira accept.**
5. **Reescrever "the data regime as the only difference"** para o que os dados sustentam ("the two campaigns differ in
   loop topology, excitation share and session; we cannot separate them") e **definir o placeholder** em uma frase.
6. **Reconciliar ou marcar como incomparáveis** os três números do bayesopt, e aplicar ao controle negativo o mesmo
   padrão estatístico por evento usado no resultado principal — ou rebaixá-lo de "achado" para "empate".
7. Esclarecer a relação entre o hold-out de identificação (1 e 4 eventos) e o hold-out de fidelidade (10 eventos), de
   forma a descartar vazamento explicitamente.
8. Corrigir 0,038 vs 0,039 e a frase "halves ... in all ten hold-out events".
9. Trocar "a practical restatement of persistent excitation" por uma formulação correta, e/ou acrescentar uma medida
   espectral/de correlação para `cmd_ω` análoga ao 0,99 reportado para `vx`/`vy`.

Com 1–5 feitos, eu subiria para **accept**. Com 1–9, para **accept** com entusiasmo, e o artigo passaria a ser um dos
melhores da trilha de RoboCup do evento.
