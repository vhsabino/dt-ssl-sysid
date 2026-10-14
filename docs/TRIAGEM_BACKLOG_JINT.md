# Triagem do BACKLOG_EXTENSAO_JINT.md

> Feita em 2026-08-07 (revisão maior, T8). Classificação:
> **(a)** cabe agora e responde diretamente a um revisor ·
> **(b)** pós-qualificação / extensão JINT · **(c)** descartar.
> **Default é (b)**; promoção para (a) exige justificativa explícita.
> Nada foi executado — esta é triagem, não implementação.

## Cortes de texto

| # | Item | Classe | Justificativa (uma linha) |
|---|---|---|---|
| A | Limitations 9→4 parágrafos, versão íntegra | **(b)** parcial → **(a)** | O sub-item "constantes cinemáticas (R/r 2,61 vs 2,699)" foi **promovido e já executado** nesta sessão como subseção *Geometric constants and units* (T5.3); o resto do parágrafo íntegro fica para a extensão. |
| B | bayesopt 9-param como subseção + discussão | **(b)** | Controle negativo já presente como parágrafo; expandir gasta página sem responder a nenhum bloqueador. |
| C | Figura de distribuição de bins | **(b)** | Substituída nesta sessão por `tab_validation_composition.tex`, que entrega a mesma informação auditável a ~1/3 do custo de página. |
| D | Discussão V-A e V-E íntegras | **(b)** | Versões longas não endereçam B1–B6; risco de reintroduzir o excesso de conclusão que B1 acusa. |
| E | Parágrafos de robustez completos (Modo B, twin×ideal, e_ang) | **(b)** parcial → **(a)** | O sub-item "twin × ideal" foi **promovido**: B5 exige declarar que a cinemática ideal bate o rSim, e isso já entrou na Seção VI. Tabelas completas ficam para JINT. |
| F | Related Work eixos (a)/(c) detalhados | **(b)** | O revisor considera a seção atual adequada; expandir é contraindicado com o orçamento estourado. |

## Figuras que não entraram

| Figura | Classe | Justificativa |
|---|---|---|
| Fit hold-out vx/vy (medido × simulado) | **(a) PROMOVIDA** | Responde diretamente a **S1** (o pedido de figura mais forte do revisor). Já compõe a Fig. B desta sessão. Artefato verificado, fits Python reproduzem MATLAB a ≤0,05 p.p. |
| Resposta ao degrau de ω | **(a) PROMOVIDA** | Mesma justificativa; é a evidência direta do resultado central do artigo e o leitor hoje nunca a vê. Compõe o painel direito da Fig. B. |
| Ganho × amplitude de ω | **(b)** com ressalva | **Não promovida, mas sinalizada:** é a evidência visual do paradoxo **B4** (ganho plano 1,3–1,5 sem joelho de zona morta). Incluí-la sem uma explicação para B4 torna a anomalia mais visível sem resolvê-la. Promover **junto** com a resposta a B4, nunca antes. |

## Pendências técnicas herdadas

| # | Item | Classe | Justificativa |
|---|---|---|---|
| 1 | Painel `e_ang` da Fig. twin×rSim com ω promovido | **(b) BLOQUEADO** | Responde a **C1/C11** (figura desatualizada) e seria (a), mas é **irrecuperável**: trajetórias do run `20260617_0030` nunca persistidas e `robosim` indisponível. Bloqueio pré-existente, não criado nesta sessão. Ver R2. |
| 2 | Validação rotacional contra distribuição rica em rotação | **(b)** | É o achado #9 do revisor e a limitação central, mas exige coleta nova — impossível para esta submissão. Já declarado como limitação e como trabalho futuro. |
| 3 | Cross-log / segundo dataset / multi-robô | **(b)** | Responde à pergunta 5 do revisor (variabilidade entre sessões); exige dados que não existem. |
| 4 | SLR completa (Kitchenham) | **(b)** | Fora de escopo para 6 páginas; a mini-revisão de 20 refs foi avaliada como adequada. |
| 5 | Grade de horizonte unificada | **(a) PROMOVIDA** | É o **C6** do revisor, listado por ele entre os "corrigíveis antes da submissão"; exige só re-executar uma campanha na grade da outra, sem dado novo. Registrado como **R8** em `TASKS_CLAUDE_CODE.md`. |

## Itens descartados — classe (c)

**Nenhum.** A regra do CFP registrada no próprio backlog é que nada se descarta;
não encontrei item cuja retenção custe mais do que informa.

## Itens novos criados nesta sessão (para o backlog)

| Item | Classe | Origem |
|---|---|---|
| Re-derivação da cinemática inversa (assimetria `√2` na linha ω) | **(a)** | Bloqueia a subseção de replicação (T5.4). Ver R0/R1. |
| Correção da entrada de CHANGELOG 2026-07-24 AÇÃO 2 (`R_efetivo = 3,3245` está errado) | **(a)** | Achado desta sessão; erro factual no registro. Ver R0. |
| Ablação rSim + atraso casado | **(a) BLOQUEADA** | Responde a B5/B6. Ver R2. |
| IC robusto para `K_ω` | **(a)** | Responde a B2 (contradição interna). Ver R5. |
| Resposta ao paradoxo ganho × zona morta | **(a)** | Responde a B4, o bloqueador sem resposta. Depende de R1. |
