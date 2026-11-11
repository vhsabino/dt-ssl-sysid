# Guia de skim em duas passadas (RQ1, 243 na fila; RQ4, 28) · versão 2, 27/09/2026, com a pré-triagem por resumo

Por que: com 3,5 a 4 h por dia útil, a fila de 271 registros não cabe em uma passada de 10 min. A passada 1 concentra o tempo nos candidatos reais; a passada 2 lê texto completo só deles. O que muda nesta versão: cada registro já tem uma nota `PRE-TRIAGEM IA 27/09:` no Notion com classe sugerida (CANDIDATO, DUVIDA, EC1_CLARO, EC2, EC4), e o CSV `slr\artigos\preskim\pretriagem\pretriagem_rq1_rq4_2026-09-27.csv` traz o resumo inteiro de 252 registros, na ordem de leitura. A decisão continua sendo sua, registro por registro; a nota é um pré-julgamento, como nas RQ2 e RQ3. Registrar no §8 do protocolo como refinamento de procedimento (Kitchenham §5.1), com a data em que começou, a taxa de candidatos observada e a concordância com a pré-triagem.

**RQ1:** *Como gêmeos digitais de robôs móveis são construídos, quais arquiteturas, componentes e abordagens de identificação de sistemas são empregados, e que tipos de dados são utilizados para essa construção?* Sub-questão: limitações e condições de identificabilidade reportadas, em especial para dados de operação em malha fechada.

## 1. Passada 1 com a nota pronta (9,5 h no total, três tardes)

Siga a ordem do CSV (coluna `ordem`; a coluna `grupo` diz o ritmo). Leia a nota, o título e, quando precisar, o resumo na coluna `resumo`. Não abra PDF na passada 1.

| Grupo | n | Tempo | O que fazer |
|---|---|---|---|
| A confirmar exclusão | 58 | 1 min | EC1_CLARO, EC2 e EC4 do agente. Confirme pelo título e pela nota. Discordou: leia o resumo e marque candidato. Doze têm robô móvel explícito e saíram EC1 por controle puro, DT do processo ou contexto RoboCup; é onde a sua régua pode discordar. |
| B candidato alta | 79 | 1,5 min | Confirme e siga. Vão para a passada 2 de qualquer jeito. |
| C candidato média ou baixa | 64 | 3 min | Surveys gerais, manipuladores com método talvez transferível, DTs de ambiente. Leia o resumo. |
| D dúvida com resumo | 54 | 3 min | Capítulos com resumo cortado, metodológicos sem robô, contexto RoboCup. Na dúvida, candidato. |
| E dúvida sem resumo | 16 | 2 min | Abra o link ou o DOI, leia o resumo na página, decida. |

Três perguntas, na ordem, as mesmas da versão 1:

1. Há robô móvel físico (ou plataforma móvel real) no trabalho? Não, claramente: EC1.
2. O domínio é robótica móvel (ou transfere método para ela)? Não: EC1 (regra 3 do lote 1: vocabulário de DT em domínio não robótico).
3. Há pelo menos um destes: modelo, DT ou simulador do robô identificado ou calibrado a partir de dados; medição de fidelidade físico e virtual; DT integrado a RL com transferência? Não, claramente: EC1. Sim ou dúvida: CANDIDATO.

Regra de ouro da passada 1: só excluir quando a resposta é clara. Dúvida vira candidato; a passada 2 decide. EC3 (tese, preprint) e EC5 (duplicata) não se decidem na passada 1: o CSV sinaliza 27 "EC3 a verificar" e a busca por versão publicada fica para a passada 2, só para os que sobreviverem.

Cinco réguas para fixar na primeira ocorrência e anotar no §8 (as notas de revisão `|| REVISÃO 27/09:` apontam os casos):

1. Controle validado em robô real sem DT nem identificação (Noorulden-5311, Kim-2426, Mostafa-4074, A-2146): EC1 pela regra 2 ou IC1 fraco?
2. Survey de DT sem robótica (15 marcados EC1, 7 DUVIDA): EC1 pela regra 3; survey com robótica ou sim-to-real no escopo (18 CANDIDATO): INCLUI com `Type = Survey`.
3. Metodológico sem robô físico (Freederia-473, Anoop-078, Wang-1339, Poommitol-010): a mesma régua da RQ3.
4. Artigo de contexto do grupo sem DT (Andrei-2465, Joo-4052, Rohman-2466, Stefan-4287): EC1 com Notes `CONTEXTO`, como combinado para a RQ4, ou INCLUI como na RQ2.
5. DT do ambiente e não do robô (Nikunjkumar-937, Rens-2541, Pawe-877, Batool-655): interessa à RQ1 pelos componentes e dados, ou EC1?

## 2. Registro da passada 1 no Notion (30 s por registro)

Escreva a sua linha antes da nota do agente, sem apagar nada, para as consultas por prefixo separarem o que já passou (`P1 `) do que ainda não passou (`PRE-TRIAGEM IA`):

```
P1 dd/mm: EC1 | [motivo em poucas palavras]
PRE-TRIAGEM IA 27/09: ... (mantida)
```
```
P1 dd/mm: candidato
PRE-TRIAGEM IA 27/09: ... (mantida)
```

- **EC1 (ou EC2, EC4) na passada 1:** Selection Stage `Excluded Full-Text`, Exclusion Criterion preenchido, RQ Mapping limpo.
- **Candidato:** só a linha `P1 dd/mm: candidato` em Notes; Selection Stage continua `Identified`.
- Se preferir a planilha, use as colunas `p1_decisao` e `p1_obs` do CSV e me mande o arquivo ao fim de cada dia; eu gravo no Notion e conto.

Ao fim de cada tarde, anote quantos registros passaram e quantos minutos gastou por grupo: é o dado que fecha o calendário da passada 2.

## 3. Entre as passadas: PDFs e pré-skim (um dia, quinta 01/10)

Terminada a passada 1, a lista de candidatos define os downloads. 45 candidatos e dúvidas já têm URL de PDF aberto na coluna `oa_pdf` do CSV e podem ser baixados por script pelo seu MATLAB; o restante vai pelo CAFe, na ordem dos lotes 3 e 4 (`lote3_rq1_downloads.csv`, `lote4_rq4_downloads.csv`, cruzados com a lista de candidatos). Com os PDFs na pasta, rodo o pré-skim por texto completo dos candidatos no mesmo procedimento da RQ3 (pergunta e árvore da RQ1: arquitetura e componentes do DT, abordagem de identificação, tipo de dado, identificabilidade e malha fechada), com o formato de nota `PRE-SKIM IA dd/mm:` e os campos do formulário de extração que dependem da RQ1.

## 4. Passada 2 (6 a 10 min, guia da RQ3): só os candidatos com PDF

Rotina, árvore de decisão e template de Notes de `guia_skim_rq3.md`, com a régua da RQ1: arquitetura e componentes do DT reportados, abordagem de identificação (caixa branca, cinza, preta; bancada dedicada ou dados operacionais), tipo de dado usado, e o que o estudo diz sobre identificabilidade em malha fechada (quase nunca aparece; é o buraco que a tese ocupa). Incluídos recebem Selection Stage `Included`, `SKIM dd/mm: ...` antes da nota do agente e RQ Mapping ajustado (RQ1+RQ2 ou RQ1+RQ3 quando couber). Sem PDF em dez minutos de busca: EC6, como na RQ3.

## 5. Calendário e gatilho

- Segunda 28 a quarta 30/09: passada 1 (grupos A e B na segunda, C e D na terça, D e E mais a RQ4 na quarta).
- Quinta 01/10: downloads e pré-skim dos candidatos; você pode começar a passada 2 pelos 7 registros da RQ1 que já têm PDF.
- Sexta 02/10 em diante: passada 2 na ordem do CSV novo (âncoras, surveys, demais candidatos, dúvidas), 18 a 20 registros por tarde, que foi o seu ritmo na RQ3 com nota pronta.
- Sábado 03/10 de manhã: teste-reteste da T/A (45 registros, planilha `slr\artigos\reteste\`), às cegas, antes de a passada 2 contaminar a memória dos registros.
- Gatilho, quarta 30/09 à noite: contar os candidatos. Até 130, a passada 2 fecha em 7 tardes (até sexta 09/10). Entre 130 e 170, fecha em 9 tardes (até terça 13/10). Acima de 170, a régua da passada 1 está frouxa demais ou a fila é mesmo grande; aí a decisão vai à orientadora com três opções: estender, amostragem estratificada por ano e string na RQ1, ou passada 2 só nos candidatos com robô móvel explícito (99 dos 143 CANDIDATO) e o resto por resumo.
- A data nova do M3 combinada com a orientadora entra aqui como a restrição que escolhe entre as três opções.
- RQ4 (28): passada 1 na quarta 30/09, julgada pelos IC1 a IC3; o que falhar mas for contexto relevante recebe EC1 e Notes `CONTEXTO-RQ4`, recuperável se a orientadora formalizar a RQ4.

## 6. Controle de qualidade

- Concordância com a pré-triagem: ao fim da passada 1, eu calculo a matriz agente x você a partir do Notion (RQ2: 30 de 35; RQ3: 65 de 71 nos pré-vereditos não ambíguos, com 4 das 6 discordâncias por EC3 e EC5, que o agente não julga). A RQ1 é a primeira rodada por resumo; se a concordância nos EC1_CLARO for alta, a taxa vira argumento para o §8 de que a passada 1 assistida não muda a seleção.
- Registro no §8 do protocolo: pré-triagem por resumo assistida por IA (fontes dos resumos, cobertura de 252 em 271, classes, decisão humana em todos os registros, concordância), pré-skim por texto completo nos candidatos, as réguas acima, EC5 e EC6 aplicados.
