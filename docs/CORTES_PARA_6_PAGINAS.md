# Plano de cortes para 6 páginas (SBR/LARS 2026)

Documento de **planejamento**. Nada aqui foi executado. O artigo no repositório
está em **8 páginas** (build limpo: 0 erros, 0 referências indefinidas, 0 TODO).

---

## 0. Como ler os números deste documento

Medidas tiradas do build atual (`latex/main.pdf`, A4, IEEEtran conference):

| Grandeza | Valor medido |
|---|---|
| Altura útil de uma coluna | ~658 pt |
| Entrelinha do corpo (9 pt) | ~11,4 pt |
| Linhas de coluna por página | ~116 (2 colunas x ~58) |
| Palavras por linha de coluna | ~8,2 |
| **Custo de 1 página** | **~116 linhas de coluna ~ 950 palavras** |

**Orçamento para sair de 8 para 6 páginas: ~232 linhas de coluna (~1.900 palavras
equivalentes).** Isso é aproximadamente **30 % do texto renderizado**.

Ocupação atual por seção (linhas de coluna, inclui legendas e tabelas embutidas):

| Bloco | Linhas | Fração da vaga |
|---|---:|---:|
| Título + autores + abstract + keywords | ~34 | 3,7 % |
| I. Introduction | ~82 | 8,8 % |
| II. Related Work | ~39 | 4,2 % |
| III. Method | ~261 | 28,1 % |
| IV. Results | ~259 | 27,9 % |
| V. Discussion | ~66 | 7,1 % |
| VI. Limitations | ~50 | 5,4 % |
| VII. Conclusion | ~40 | 4,3 % |
| References (19 entradas) | ~63 | 6,8 % |
| **Total** | **~894** | |

Custo individual dos flutuantes (medido no PDF, inclui legenda e separação):

| Flutuante | Custo em linhas de coluna |
|---|---:|
| Fig. 1 (arquitetura, `figure*`, ocupa 2 colunas x ~276 pt) | **~49** |
| Fig. 2 (degrau de omega, 0,95 col.) | ~19 |
| Fig. 3 (twin vs. rSim, 0,95 col.) | ~19 |
| Tabela I (unit contract, 8 linhas) | ~14 |
| Tabela II (parâmetros por DOF + nota de rodapé de 6 linhas) | ~15 |
| Tabela III (twin vs. rSim por horizonte, 6 linhas) | ~14 |
| Tabela IV (regime de omega, legenda longa + nota) | ~26 |
| **Soma dos flutuantes** | **~156 (17 % do artigo)** |

**Consequência aritmética, antes de qualquer discussão editorial:** os flutuantes
somam 156 linhas e o orçamento de corte é 232. Não existe caminho para 6 páginas
que preserve as 3 figuras e as 4 tabelas do build. Chegar a 6 páginas exige
abrir mão de material visual **e** comprimir prosa em ~25 %.

---

## 1. Ordem recomendada (do mais barato ao mais caro)

### Faixa A — indolor (redundância pura; nenhum conteúdo sai do artigo)

Total da faixa: **~50 linhas (~0,43 página)**.

| # | Bloco afetado | Economia | O que exatamente se perde |
|---|---|---:|---|
| A1 | **Fig. 3** (`04_results.tex`, `twin_vs_rsim_epos_en.png`) | ~19 | Nada de informação: a Tabela III já dá mediana do gêmeo, mediana do rSim, gap, `p` e effect size nos **mesmos 6 horizontes** que a figura plota. Perde-se só o impacto visual do gap crescente. Corte de melhor relação custo/benefício do artigo. |
| A2 | **Tabela I** (`tab_units.tex`) -> 2 frases em III-F | ~10 líquidas | Nada: os 8 valores (R, r, os três R/r, dt, 1,567 rad/s, 0,581–0,600 rad/s) migram para uma frase corrida em "Geometric constants". **Atenção: a tabela foi reinserida por decisão explícita do autor em 2026-08-08 (M-F1)** — reverter isso é decisão dele, não editorial. |
| A3 | **Nota de rodapé da Tabela II** (dispersão por evento) -> prosa de IV-A | ~3 líquidas | Nada: `65,0/77,2` e `+-0,8 p.p.` cabem em meia frase em IV-A, que já cita o fit 71,1 %. |
| A4 | III-B, frase de reconciliação com o Simulink | ~4 | Nada de resultado: os dois números (<= 6 mm, <= 9e-4 rad) ficam; sai a explicação de como o modelo Simulink é construído por dentro (blocos contínuos, cadeia de rodas). |
| A5 | III-I, descrição dos modos A/B | ~5 | Nada: mantém `L_w=15`, re-âncora rígida, descarte de 15 amostras; sai a justificativa repetida de por que rSim precisa de warm-up (já dita uma vez). |
| A6 | II, parágrafo "Gap" | ~4 | Nada: é a mesma lacuna já enunciada no fim do 3º parágrafo da Introdução ("remains little explored"). |
| A7 | III-H, parágrafo "Horizon grid and anchor convention" -> nota de rodapé | ~5 | Nada: a grade `{0,5;1;2;2,5;4} s` e a ressalva de que cada resultado é reportado na grade nativa continuam, em corpo menor. |

### Faixa B — perda leve (perde-se fluidez, contexto ou autossuficiência de replicação; nenhum resultado sai)

Total da faixa: **~124 linhas (~1,07 página)**. Somado à Faixa A: ~174 linhas (~1,5 página).

| # | Bloco afetado | Economia | O que exatamente se perde |
|---|---|---:|---|
| B1 | **Fig. 1** (arquitetura, `fig_architecture.tex`) | **~49** | O único mapa do pipeline. O leitor passa a montar mentalmente a distinção caminho sólido (logs de competição) vs. tracejado (coleta dedicada de rotação) a partir do texto de III. É o maior item isolado do artigo — e o mais caro em legibilidade por linha economizada. |
| B2 | I. Introduction, compressão de 82 -> ~60 linhas | ~22 | Perde-se o desenvolvimento da definição de digital twin e das duas premissas caras (descrição física detalhada / campanha dedicada). As 4 contribuições e todas as citações ficam. Risco: a Introdução fica assertiva demais e perde o enquadramento de reality gap pedido na revisão maior (T1). |
| B3 | VI. Limitations -> um parágrafo denso único | ~12 | Nenhuma limitação sai (guardrail). Perde-se a separação "Data and identification" / "Evaluation and scope", o que torna a seção mais difícil de auditar por um revisor. |
| B4 | III-G "Coordinate conventions" -> 4 linhas + ponteiro para o código | ~10 | Perde-se a autossuficiência de replicação: as equações de integração no frame do campo e a garantia explícita de que nenhuma cinemática de roda entra no gêmeo. Essa subseção existe por pedido de revisor (tarefa #8). |
| B5 | III-F, parágrafo de proveniência da razão de raios | ~9 | Perde-se a triangulação por três fontes independentes (CAD, telemetria de firmware, resposta medida) que defende a troca da constante no meio do projeto. O intervalo 0,58–0,60 rad/s e o spread de 3,3 % ficam (estão em IV-D e nas Limitações). |
| B6 | VII, parágrafo "Future work" -> 4 linhas | ~6 | Perde-se o detalhamento das duas direções (Isaac Sim / MuJoCo; braço open-loop com translação superposta). Mantém a citação `machado2025planning`. |
| B7 | II. Related Work, compressão adicional | ~9 | Nenhuma citação sai (guardrail); perde-se a caracterização do que cada trabalho faz, virando lista de rótulos. Seção já foi comprimida antes — o retorno por linha aqui é baixo. |
| B8 | V-C "Where the twin beats rSim" -> 2 frases dentro de IV-C | ~4 | Perde-se a separação entre resultado e interpretação. A leitura (atraso + lag capturam o curto horizonte) e a ressalva permanecem. |
| B9 | IV-C, parágrafo "Robustness and second baseline" -> 1 frase | ~3 | Nada de número: `+0,282 m`, `p=4,4e-14`, `+0,987`, `+0,063 m`, `p=8,5e-7`, `+0,736` ficam, entre parênteses. |

**Fim da Faixa B: ~6,5 páginas. Ainda faltam ~58 linhas.**

### Faixa C — custa contribuição (só com decisão consciente do autor)

| # | Bloco afetado | Economia | O que exatamente se perde |
|---|---|---:|---|
| C1 | **Fig. 2** (degrau de omega medido vs. simulado) | ~19 | A **única** evidência visual de ajuste do artigo, em qualquer canal. Foi incluída justamente porque um revisor apontou (S1) que o leitor nunca vê medido vs. simulado. Remover reabre essa objeção. |
| C2 | **Tabela IV** (regime de omega) -> 2 frases em IV-D | ~18 líquidas | O contraste lado a lado malha fechada vs. open-loop dedicada, que é a forma mais direta do achado central. Os números sobrevivem em prosa (1,307/1,0016; +0,0489 m vs. -0,1138 m; `p` de ambos), mas a comparação deixa de ser legível de relance. Também some a nota de rodapé que explica por que a linha de malha fechada não tem hold-out fit único — ponto de ataque previsível de revisor. |
| C3 | IV-E "Negative control: joint calibration" | ~9 | O controle negativo do bayesopt de 9 parâmetros. Sem ele, a pergunta "por que não calibrar os 9 juntos?" fica sem resposta no artigo, e o argumento de que a lição é de **excitação** (e não de estrutura de modelo) perde seu segundo apoio empírico. |
| C4 | **Tabela III** -> 2 horizontes em prosa | ~11 líquidas | Se A1 já removeu a Fig. 3, aqui a evidência quantitativa do resultado principal (C3 do artigo) fica reduzida a dois horizontes citados no texto. **Não combinar C4 com A1** sem aceitar que o resultado principal deixa de ser auditável ponto a ponto. |
| C5 | IV-C, parágrafo "Does the delay term explain the gap?" | ~13 | **Destrutivo.** É a resposta à objeção mais forte e mais provável contra o resultado principal ("o gêmeo só ganha porque tem termo de atraso e o rSim não"). Foi produzido especificamente para fechar essa lacuna. Não cortar. |
| C6 | III-C, Eq. 2 (definição de hold-out fit) | ~8 | **Destrutivo.** Sem ela, "fit 86,7 % / 87,1 % / 71,1 %" vira número não verificável e o gate de 60 % perde definição. Foi adicionado por pedido de revisor (C7). Não cortar. |
| C7 | IV-D, análise de diluição por roda + sensibilidade ao bracket | ~20 | **Destrutivo.** É o mecanismo que explica o achado central e resolve o paradoxo (94,3 % sub-limiar mas ganho inflado e sem joelho). Remover deixa o artigo com uma estatística sem explicação. Não cortar. |

---

## 2. Duas rotas fechadas até 6 páginas

### Rota A — "preserva os resultados, sacrifica o visual" (recomendada)

Faixa A completa (50) + Faixa B completa (124) + C1 (19) + C2 (18) = **~211 linhas**.
Faltam ~21 linhas: obtidas comprimindo IV-B (bins) e V-A/V-B em mais ~20 %.

Resultado: **artigo sem nenhuma figura**, com Tabelas II e III, todos os números,
todas as citações e todas as limitações. É defensável para um artigo de 6 páginas
de conferência, e é o cenário em que nenhuma **contribuição** é removida — só
material de apresentação.

Risco declarado: o artigo perde a Fig. 2, que atendia a um pedido explícito de
revisor. Registrar o desvio em `docs/REGISTRO_DESVIOS.md` e manter o painel em
`results/figs/` para a extensão JINT.

### Rota B — "preserva as figuras, sacrifica resultados de apoio"

Manter Fig. 1 e Fig. 2 obriga a tirar as ~68 linhas equivalentes de outro lugar:
A1 + A2..A7 (50) + B2..B9 (75) + C2 (18) + C3 (9) + C4 (11) + compressão de IV-B
(~8) + fusão V-A/V-B (~10) = ~181. Ainda faltam ~51 linhas, que só existem em
C5/C6/C7.

**Conclusão: a Rota B não fecha sem destruir uma contribuição.** Se as figuras
forem inegociáveis, a resposta honesta é que o artigo não cabe em 6 páginas na
forma atual — teria de virar um artigo sobre **um** dos dois resultados
(fidelidade translacional vs. identificabilidade de yaw), não sobre os dois.

---

## 3. Observações operacionais

1. **Não cortar citações.** As 19 referências ocupam ~63 linhas (~0,55 página),
   mas remover qualquer uma viola o guardrail do projeto e enfraquece a Related
   Work, que já está no mínimo.
2. **O build de sandbox é pessimista.** Ele usa `unsrt` (nomes por extenso)
   porque `IEEEtran.bst` não está disponível no ambiente Linux; o `IEEEtran.bst`
   real produz entradas mais curtas (iniciais). A folga real na página 8 é maior
   do que a medida aqui.
3. **Ordem de execução.** Executar sempre da Faixa A para a C, recompilando a
   cada 2–3 itens. Vários itens interagem via flutuantes: remover a Fig. 1
   (`figure*`) muda o empacotamento de floats de todas as páginas seguintes e
   pode render mais (ou menos) do que o estimado.
4. **Não combinar A1 com C4** (ver nota em C4).
5. **Cuidado de ambiente:** o mount Linux serve cópias truncadas de arquivos
   editados há pouco (tamanho em cache). Depois de editar, esperar e conferir
   que cada `.tex` termina onde deveria antes de compilar.
