# Guia da passada 2 (RQ1 e RQ4): 89 registros com PDF · 11/10/2026

Consolida o que estava espalhado em dois guias, já adaptado à RQ1: `guia_skim_rq1_duas_passadas.md` (§1, réguas; §4, passada 2) e `guia_skim_rq3.md` (§1, rotina; §2, árvore; §4, registro). A diferença em relação à RQ3: aqui não há pré-skim por texto completo, só a nota da pré-triagem por resumo (`PRE-TRIAGEM IA 27/09`). Por isso os primeiros minutos vão para o PDF, não para conferir a nota. A ordem de leitura e os links estão em `prisma\fila_passada2_2026-10-10.html` (abra pelo PC para os links de PDF funcionarem).

**RQ1:** *Como gêmeos digitais de robôs móveis são construídos, quais arquiteturas, componentes e abordagens de identificação de sistemas são empregados, e que tipos de dados são utilizados para essa construção?* Sub-questão: limitações e condições de identificabilidade reportadas, em especial para dados de operação em malha fechada.

## 1. Rotina por artigo

| Min | O que fazer | O que decidir |
|---|---|---|
| 0 a 1 | Ler na fila a nota da pré-triagem, o alerta e o sinal em laranja | O que o resumo prometia e o que conferir |
| 1 a 2 | Abrir o PDF: é o registro certo, em inglês ou português, artigo revisado por pares? | EC3, EC4 ou EC6 antes de ler o conteúdo |
| 2 a 8 | Resumo, figura do sistema, método e resultados | Robô móvel físico? Modelo ou DT identificado ou calibrado com dados? Fidelidade medida? RL com transferência? |
| 8 a 10 | Veredito e registro no Notion (no núcleo, até 15 min no total) | Selection Stage, Exclusion Criterion, RQ Mapping, Notes |

Procurou 3 minutos e não achou: trate como ausente. Na dúvida entre incluir e excluir, inclua; a avaliação de qualidade da Sprint 3 elimina os fracos. O reteste de 11/10 mostrou que o seu critério atual está mais restritivo que o da triagem: aplicado lá, teria tirado dois estudos que você incluiu no texto completo.

## 2. Árvore de decisão, na ordem

1. **Arquivo e idioma.** Texto em outro idioma que não inglês ou português: **EC4**. PDF de outro trabalho ou só a prévia: resolva em 10 min; sem arquivo, **EC6**.
2. **Tipo de publicação.** Tese, dissertação, preprint ou relatório: 10 min de busca por versão publicada (Google Scholar, DOI, página do autor). Publicado: troque o DOI e siga a árvore. Não publicado: **EC3**, com a anotação "candidato a snowballing se publicar".
3. **Domínio.** Não é robótica nem transfere método para robôs móveis: **EC1** (vocabulário de DT em domínio não robótico).
4. **Avaliação empírica.** Só posição, visão ou conceito: **EC2**.
5. **Contribuição para a RQ1.** Há pelo menos um destes, com contraparte real: modelo, DT ou simulador do robô identificado ou calibrado a partir de dados (IC1); fidelidade entre físico e virtual medida (IC2); modelo calibrado integrado a RL com transferência medida (IC3)? Sim: **INCLUI**, com RQ Mapping RQ1, mais RQ2 se mede fidelidade e RQ3 se há RL. Não: **EC1**. Simulação sem contraparte física e sem medição de fidelidade é EC1 (regra 1); controle puro sem DT nem identificação por dados é EC1 (regra 2).
6. **Plataforma não móvel** (braço, drone, AUV, humanoide): o EC1 do protocolo exclui manipulador sem base móvel "salvo se metodologicamente relevante". Inclua se o mecanismo de identificação ou calibração for transferível a robôs com rodas, como na RQ2 e na RQ3.
7. **Revisão de terceiros.** Com robótica ou sim-to-real no escopo: **INCLUI** com `Type = Survey` (alimenta o snowballing, não a síntese). DT sem robótica: **EC1**.
8. **Duplicata ou versão anterior** de estudo já incluído: **EC5** na versão mais fraca.

Registros da RQ4 (6 na fila): julgados pelos IC1 a IC3. O que falhar mas for contexto relevante recebe EC1 e Notes `CONTEXTO-RQ4`.

## 3. Réguas da RQ1: decida na primeira ocorrência e anote para o §8

Se já decidiu alguma na passada 1, mantenha.

1. Controle validado em robô real sem DT nem identificação: EC1 pela regra 2 ou IC1 fraco?
2. Survey de DT sem robótica: EC1; survey com robótica no escopo: INCLUI com `Type = Survey`.
3. Metodológico sem robô físico (na fila: Wang-1339): a régua da RQ2 e da RQ3 foi INCLUI com relevância média.
4. Artigo de contexto do grupo sem DT (na fila: Joo-4052): EC1 com Notes `CONTEXTO`, ou INCLUI como na RQ2.
5. DT do ambiente e não do robô: interessa à RQ1 pelos componentes e dados, ou EC1?

## 4. Registro no Notion (1 min)

Escreva a sua linha antes da nota do agente, sem apagar nada:

```
SKIM dd/mm: INCLUI | RQ1 (ou RQ1+RQ2, RQ1+RQ3) | arquitetura e componentes; identificação (caixa branca, cinza ou preta; bancada ou dados de operação); tipo de dado; identificabilidade em malha fechada, se houver
PRE-TRIAGEM IA 27/09: ... (mantida)
```
```
SKIM dd/mm: EC1 (ou EC2, EC3, EC4, EC5, EC6) | razão em uma frase
PRE-TRIAGEM IA 27/09: ... (mantida)
```

- **Inclui:** Selection Stage continua `Included` (já está); RQ Mapping ajustado; `Type = Survey` nas revisões.
- **Exclui:** Selection Stage `Excluded Full-Text` e Exclusion Criterion preenchido.
- O prefixo `SKIM` é obrigatório nos incluídos: é ele que tira o registro de "em análise" no funil.

## 5. Ordem e ritmo

Siga os grupos da fila: 1, decisão rápida (11 registros, 5 min); 2, preprints (6, 10 min); 3, núcleo e omnidirecionais (33, 15 min); 4, revisões (19, 5 min); 5, demais candidatos (15, 10 min); 6, dúvidas (5, 8 min). Cerca de 15 h, de quatro a cinco tardes de 3,5 h. Anote os minutos gastos por grupo (coluna `minutos_gastos` do CSV da fila).

Terminada a passada 2: eu calculo a concordância entre a pré-triagem e as suas decisões (para o §8) e atualizo o funil; depois vem o snowballing (§3), com a mesma regra de que na dúvida o registro avança.
