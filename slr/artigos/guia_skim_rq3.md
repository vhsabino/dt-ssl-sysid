# Guia de Skim da RQ3 (129 registros, 111 com pré-skim) · Sprint 2

**Objetivo do skim:** decidir INCLUI ou EXCLUI cada registro, com a nota de pré-skim já gravada no Notion, em 6 a 8 minutos por artigo, e deixar o registro pronto para a extração da Sprint 3. Não é leitura profunda: é conferir o que o agente afirmou, decidir e registrar.

**RQ3:** *Como gêmeos digitais (ou simuladores) calibrados a partir de dados reais são integrados a pipelines de treinamento por RL, e qual o impacto da fidelidade do gêmeo na transferência de políticas para o mundo real?*

A diferença para a RQ2: lá a pergunta era "mede fidelidade?"; aqui são duas perguntas encadeadas, "há política aprendida em simulador ou DT com contraparte real?" e "o efeito da fidelidade foi isolado?". A segunda quase nunca é respondida, e é exatamente o buraco que a tese ocupa. Por isso o quarto campo da nota (fidelidade -> transferência) merece a sua atenção mesmo quando o veredito já está claro.

## 1. Rotina por artigo (6 a 8 min, cronometrado)

| Min | O que fazer | O que decidir |
|-----|-------------|---------------|
| 0 a 1 | Ler a nota `PRE-SKIM IA 19/09` no Notion, do primeiro campo até a obs e a revisão | O agente achou robô físico, RL em simulador, calibração por dados reais, transferência medida? |
| 1 a 4 | Abrir o PDF e ir direto ao que o alerta manda conferir (a tabela ou figura citada) | Os números da nota batem? O que o texto extraído perdeu muda o veredito? |
| 4 a 6 | Percorrer método e resultados só se a nota disser "não encontrado" ou "texto cortado" | Existe o que faltou (transferência real, calibração, algoritmo)? |
| 6 a 8 | Veredito e registro no Notion | Selection Stage, Exclusion Criterion, RQ Mapping, Notes |

Regra de ouro: **a nota diz "não encontrado no texto extraído" e você não acha em 3 minutos no PDF: trate como ausente.** A nota diz "não isolado: a fidelidade não varia": não gaste tempo procurando o contrário, esse é o achado esperado em 3 de cada 4 estudos.

Orçamento por grupo (coluna `grupo_leitura` do CSV): âncoras e surveys 8 min, demais INCLUI 6 min, DUVIDA 8 min, exclusões 3 min, sem PDF 2 min (decidir se baixa ou EC6). Total estimado: 12 a 13 horas, três dias e meio a 3,5 h por dia.

## 2. Árvore de decisão (na ordem)

1. **O domínio é robótica?** Não (trânsito, ponte, job shop, suspensão de veículo, SciML genérico, survey de ML geral): **EC1** pela regra 3 do lote 1.
2. **Há avaliação empírica?** Não (artigo conceitual, de posição, whitepaper): **EC2**.
3. **Há política aprendida (RL ou similar) treinada em simulador ou DT?** Não, mas há identificação, calibração ou medição de fidelidade de DT de robô com contraparte real: **INCLUI por IC1 ou IC2 e altere o RQ Mapping** (RQ1 ou RQ2). A falta de RL não é critério de exclusão; o protocolo inclui por qualquer IC. É o caso de 17 dúvidas do lote. Não há nada disso: **EC1** pela regra 2.
4. **Há contraparte real?** Política implantada em robô real, ou dados reais usados para calibrar o simulador, ou gap sim-to-real medido: **INCLUI**.
5. **Só sim-to-sim, mas varia a fidelidade e mede o efeito** (Antoine-236, H-2058, Algirdas-320, Ng-4196, Luca-4679): **INCLUI se você aceitar sim-to-sim como evidência sobre fidelidade -> transferência**; senão EC1 pela regra 1. Decida uma vez, na primeira ocorrência, e anote a régua no §8.
6. **Metodológico sobre DT+RL sem robô físico** (Andrej-363, Laukaitis-2258, Johannes-569, Sara-1062, Mohamed-414, Nat-532): mesma régua que você usou na RQ2, onde incluiu os cinco casos assim. Se mantiver, INCLUI com relevância média.
7. **Plataforma não móvel** (braço, mão, drone, humanoide, AUV, ASV): INCLUI se o mecanismo de integração e a medição de transferência forem transferíveis a robôs com rodas. Os agentes anotaram a dúvida em cada obs; cerca de 30 dos 60 INCLUI estão aqui.
8. **Survey ou review:** INCLUI se peer-reviewed; `Type = Survey`. Alimenta snowballing, não a síntese primária.
9. **Preprint, TCC ou relatório sem versão publicada:** dez minutos de busca (Google Scholar, DOI, página do autor). Publicado: substitua o DOI e siga a árvore. Não publicado: **EC3**, mesmo que relevante; anote "candidato a snowballing se publicar".
10. **Duplicata** (Hansenclever-2407 e 2409): fica a versão mais completa, **EC5** na outra.
11. **Conteúdo do PDF diferente do registro** (Oliver-3504 é o livro inteiro; Hao-4214 tem uma página corrompida): resolver o arquivo antes de julgar; sem arquivo em dez minutos, **EC6**.

Na dúvida entre incluir e excluir: **inclua**. A Sprint 3 elimina os fracos com a avaliação de qualidade.

## 3. Cinco réguas para fixar antes de começar

Decida cada uma na primeira ocorrência e registre no §8 do protocolo; depois é só aplicar.

1. Política aprendida sem RL (supervisionado, imitação, otimização bayesiana de controlador): conta para a RQ3 ou remapeia para RQ1? Afeta Lszl-546, Jack-323, Jad-424, Narges-806, Maximilian-1025.
2. Sim-to-sim com fidelidade variada: evidência válida para "fidelidade -> transferência" ou EC1? Afeta os cinco do item 5 acima.
3. Metodológico sem robô físico: INCLUI média (régua da RQ2) ou EC1? Afeta seis dúvidas.
4. Plataforma não móvel com mecanismo transferível: INCLUI (régua da RQ2) ou EC1? Afeta cerca de 30 estudos.
5. Preprint relevante sem versão publicada: EC3 estrito ou "na dúvida, inclua"? Afeta 25 estudos, treze de relevância alta.

## 4. Registro no Notion (por artigo, 1 min)

Escreva a sua linha **antes** da nota do agente, sem apagar nada. Assim as consultas por prefixo separam o que já foi julgado (`SKIM `) do que ainda não foi (`PRE-SKIM IA`), e a discordância agente x você fica auditável para o §8.

```
SKIM dd/mm: INCLUI | RQ3 (ou RQ1+RQ3, RQ2) | [uma frase: o que confirmou ou o que muda em relação ao pré-skim]
PRE-SKIM IA 19/09: ... (mantida)
```
```
SKIM dd/mm: EC1 (ou EC2, EC3, EC5, EC6) | [uma frase com a razão]
PRE-SKIM IA 19/09: ... (mantida)
```

- **INCLUI:** Selection Stage → `Included`; Status continua `Recommended Full Read`; RQ Mapping ajustado se remapear; `Type = Survey` quando for survey.
- **EXCLUI:** Selection Stage → `Excluded Full-Text`; Exclusion Criterion → ECx; RQ Mapping limpo.
- **Sem PDF:** não julgue; deixe `Identified` e use o CSV `lote2_faltantes_20260912.csv` mais os 18 desta fila para a rodada de download. EC6 só depois de tentar.

Quando a sua nota confirmar o mecanismo e o efeito da fidelidade, a extração da Sprint 3 já tem os dois campos que dependem da RQ3 preenchidos.

## 5. Ordem de leitura e cadência

Siga a ordem do CSV `preskim_rq3_2026-09-19.csv`: A âncoras (22) para calibrar a régua no que é mais próximo da tese, B surveys (5), C demais INCLUI (33), D dúvidas (35), E exclusões (16), F sem PDF (18).

Plano a 3,5 h por dia: segunda 21/09, grupos A e B (27, um pouco mais lentos); terça 22/09, grupo C (33); quarta 23/09, grupo D (35); quinta 24/09 de manhã, grupos E e F (34, rápidos). Ao fim de cada dia, anote quantos minutos por artigo você gastou de fato, separando INCLUI de DUVIDA: esse número é o que decide o replanejamento da RQ1 com a orientadora.

## 6. Controle de qualidade

- **Concordância com o pré-skim:** ao terminar, eu calculo a matriz agente x você a partir do Notion (na RQ2 foram 30 de 35 concordâncias nos casos não ambíguos, e zero INCLUI do agente rejeitado). Se a RQ3 mantiver o padrão, a RQ1 pode usar o pré-skim como primeira passada com segurança.
- **Teste-reteste:** a amostra de 45 continua valendo; as 6 de RQ3 do estrato B devem ser rejulgadas sem olhar a nota nem a decisão anterior.
- **Registro no §8 do protocolo:** assistência de IA na fase de texto completo (pré-julgamento gravado em Notes, decisão humana em todos os registros, estatística de concordância), as cinco réguas acima e os EC5 e EC6 aplicados.

## 7. O que vem depois

Terminada a RQ3, a fila é RQ1 (251 registros) e RQ4 (28). Para a RQ1 o pré-skim custa cerca de 30 agentes e um dia de processamento meu; para valer a pena, você precisa me dar dois números ao fim da RQ3: minutos reais por artigo INCLUI e por artigo DUVIDA com a nota pronta. Com eles fecho o plano da RQ1 em duas passadas (guia `guia_skim_rq1_duas_passadas.md`) e a proposta de replanejamento para a orientadora.
