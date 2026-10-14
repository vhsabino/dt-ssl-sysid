# CORTES_SUGERIDOS.md — candidatos ordenados por custo/benefício

> Criado em 2026-08-07 (revisão maior). **Nada foi cortado nesta sessão.**
> Conforme o brief (T7), esta é uma lista de candidatos para decisão do autor.
> Ultrapassar as 6 páginas por causa das figuras está autorizado.

## Situação de página

Adições desta sessão que **crescem** o artigo:

| Item | Tipo | Custo estimado |
|---|---|---|
| Fig. A — arquitetura (TikZ) | `figure*` largura dupla | ~0,33 pág. |
| Fig. B — medido × simulado (2 painéis) | `figure*` largura dupla | ~0,33 pág. |
| Tabela de unidades | 1 coluna, 12 linhas | ~0,18 pág. |
| Tabela de composição da validação | 1 coluna, 6 linhas | ~0,12 pág. |
| Subseção *Geometric constants and units* | texto | ~0,22 pág. |
| Parágrafo *Dead-time quantization* | texto | ~0,12 pág. |
| Parágrafo *Delay ablation* + linha na Tab. II | texto+tabela | ~0,10 pág. |
| Parágrafo *Why not synthesize…* (Discussão) | texto | ~0,09 pág. |
| Ampliação da Seção VI (B5/B6) | texto | ~0,10 pág. |
| **Total** | | **≈ 1,6 pág.** |

Partindo de 6 páginas fechadas, o artigo hoje está em **≈ 7,6 páginas**.
Se o alvo continuar sendo 6, é preciso recuperar ~1,6 pág.; se o venue aceitar 8,
**não corte nada**.

---

## Candidatos, do melhor para o pior custo/benefício

### 1. Bloco de determinismo bit-exato — ~14 linhas · ganho ~0,12 pág.
**Onde:** `04_results.tex`, três menções (Sec. III, IV-A, IV-D).
**O que se perde:** nada de substantivo. O revisor (S6) diz explicitamente que
isso *"pode ser comprimido a uma frase"* e (Reprodutibilidade, 2,5/5) que
enfatizá-lo três vezes enquanto não se libera código *"dá a impressão de
substituição retórica"*. **Cortar aqui melhora a nota, não só a página.**
**Recomendação: CORTAR. É o único item da lista com benefício líquido positivo.**

### 2. Parágrafo "Negative control: joint calibration" (bayesopt) — ~18 linhas · ganho ~0,16 pág.
**Onde:** `04_results.tex`, final.
**O que se perde:** um resultado negativo que o revisor **elogia
nominalmente** (§3, item 2, "honestidade metodológica"). Já está condensado de
uma subseção para um parágrafo (corte B de 2026-07-31); o conteúdo íntegro está
em `BACKLOG_EXTENSAO_JINT.md` item B.
**Recomendação: cortar só em último caso.** Remove um ponto forte reconhecido.

### 3. Detalhamento do pipeline de ETL — ~10 linhas · ganho ~0,09 pág.
**Onde:** `03_method.tex`, `\subsection{Data and pre-processing}`.
**O que se perde:** grade nativa irregular, resample, Savitzky–Golay, contagem de
eventos. **Atenção:** o revisor já reclama (Reprodutibilidade) que faltam
*ordem e janela do Savitzky–Golay, método de reamostragem*. Cortar aqui **piora**
uma nota já em 2,5/5, e a Fig. A agora carrega o pipeline visualmente — mas
figura não substitui hiperparâmetro.
**Recomendação: NÃO CORTAR.** Na verdade este bloco deveria *crescer*.

### 4. Related Work comprimido para parágrafo denso — 68 → ~30 linhas · ganho ~0,33 pág.
**Onde:** `02_related_work.tex` (5 parágrafos temáticos + Gap).
**O que se perde:** a estrutura por eixos (A–E) e a especificidade por trabalho.
O revisor classifica a seção como *"enxuto mas pertinente e atual… bem feito
para 6 páginas"* — ou seja, hoje é um ativo. Comprimir para um único parágrafo
denso preserva as citações mas dissolve o "Gap" explícito, que é o que sustenta
a alegação de originalidade (nota 3,5/5, já puxada para baixo).
**Recomendação: cortar no máximo os eixos (a) e (c) para uma frase cada
(~15 linhas, ~0,13 pág.), preservando o parágrafo "Gap" intacto.** O conteúdo
detalhado já está reservado em `BACKLOG_EXTENSAO_JINT.md` item F.

### 5. Redundância entre Métodos e Resultados — ~12 linhas dispersas · ganho ~0,10 pág.
**Onde:** a definição do gate estatístico aparece em `03_method.tex`
(*Statistical gate*) e é reafirmada em `04_results.tex` ao narrar o veredicto GO.
**O que se perde:** pouco; o leitor pode voltar à Seção III. Risco: o revisor
considera o protocolo *"a melhor parte do artigo"* — comprimir demais a
descrição do gate atinge justamente o que sustenta a nota de rigor (3,0/5).
**Recomendação: cortar a reafirmação em Resultados, preservar Métodos.**

### 6. Parágrafo de robustez Modo B — ~9 linhas · ganho ~0,08 pág.
**O que se perde:** a demonstração de que o Modo A é a escolha **conservadora**.
Dado que B5 acusa a comparação com rSim de ser tautológica, remover a evidência
de que escolhemos o cenário menos favorável a nós **enfraquece a defesa**.
**Recomendação: NÃO CORTAR.**

---

## Item do brief que não se aplica

> *"resultados de RL além da figura das três dinâmicas (esta permanece; o
> restante já está fora de escopo para a qualificação)"*

**Não há conteúdo de RL no artigo, e não há figura de três dinâmicas.** Busca em
`latex/sections/`: as únicas ocorrências de "reinforcement" são citações de
contexto a `martins2021rsoccer` e `machado2025planning` na Introdução e no
Related Work (uma frase cada, ambas necessárias para posicionar o trabalho), e um
comentário em `07_conclusion.tex` registrando que **nenhum RL é prometido como
contribuição**. O material de RL está em `docs/INVENTARIO_RL_2026-07-24.md`, fora
do paper. **Nada a cortar.**

---

## Recomendação final

Se for preciso voltar a 6 páginas, a sequência de menor dano é
**1 → 5 → 4 (parcial)**, que recupera ≈ 0,35 pág. Isso **não é suficiente** para
absorver as 1,6 pág. adicionadas. Conclusão honesta: **as duas figuras novas não
cabem em 6 páginas junto com o resto.** As opções reais são (a) submeter em 7–8
páginas se o venue permitir, (b) mover a Fig. B para a extensão JINT e manter só
a Fig. A (economiza 0,33 pág.), ou (c) manter as duas figuras e cortar
Related Work de forma agressiva, ao custo direto da nota de originalidade.
Recomendo (a); em segundo lugar (b), porque a Fig. A é a que carrega a
contribuição visualmente e a Fig. B, embora seja o pedido mais forte do revisor,
está incompleta enquanto os braços rSim/ideal não forem recuperáveis.
