# Pré-triagem por resumo da RQ1 e da RQ4: 271 registros classificados e 271 notas gravadas no Notion em 27/09/2026

## O que foi feito

A fila de RQ1 tinha 243 registros em `Identified` e a de RQ4, 28. Só 7 deles têm PDF na pasta `slr\artigos\`, então este pré-julgamento não leu texto completo: leu título, resumo, veículo, tipo de publicação e palavras-chave. Os resumos foram buscados pelo seu MATLAB a partir dos DOIs (OpenAlex em lotes de 50, depois Semantic Scholar e Crossref para os que faltaram, depois a página do próprio DOI para os que ainda faltavam). Resultado: 252 dos 271 registros com resumo (OpenAlex 162, página do DOI 77, Semantic Scholar 12, Crossref 1); 19 ficaram sem resumo em todas as fontes e foram classificados só pelo título e pelo veículo, como DUVIDA de confiança baixa, salvo domínio claramente fora da robótica.

Os 271 arquivos de texto foram distribuídos entre 8 agentes em paralelo, 34 registros cada, com as instruções de `INSTRUCOES_AGENTE_PRETRIAGEM.md` (nesta pasta): a RQ1 e a sua sub-questão, os critérios IC1 a IC4 e EC1 a EC6, as três regras EC1 do lote 1 mais a regra 4 da RQ3 (falta de RL não exclui), e uma árvore de decisão de 8 passos que começa pelo domínio. As instruções carregam a calibração observada nas RQ2 e RQ3: você rejeitou pouquíssimos INCLUI do agente e incluiu vários EC1 quando a contribuição era metodológica sem robô físico ou quando era artigo de contexto do grupo (RoboCup, SSL, VSSS). Por isso EC1_CLARO ficou reservado para domínio fora da robótica ou robótica sem nenhum DT, simulador, modelo identificado ou fidelidade em jogo; robô móvel com qualquer forma de modelo, simulador, DT, identificação, calibração ou dado real é CANDIDATO; o que não dá para decidir pelo resumo é DUVIDA.

O campo Notes dos 271 registros recebeu a nota com o prefixo `PRE-TRIAGEM IA 27/09:`. Em 8 delas acrescentei um sufixo `|| REVISÃO 27/09:` com a minha leitura de revisor. **Nada além de Notes foi tocado**: consulta agregada depois da escrita mostra 243 RQ1 e 28 RQ4, todos `Identified` e `Recommended Full Read`, nenhum Exclusion Criterion preenchido, RQ Mapping intacto. Quatro dos oito agentes escreveram sem acentos; as 136 notas afetadas foram restauradas por dois agentes de correção e conferidas uma a uma (o texto sem diacríticos é idêntico ao original).

## Formato da nota (dois separadores)

`PRE-TRIAGEM IA 27/09: [CANDIDATO | EC1_CLARO | DUVIDA | EC2 | EC4] | [plataforma ou domínio; o que o resumo promete sobre DT, identificação, dados ou RL] | [motivo da classe em uma frase; "EC3 a verificar" quando for tese, dissertação ou preprint]`

A classe é sugestão de passada 1, não decisão. As colunas `robo_movel`, `dt_ou_modelo`, `dado_real` e `rl` do CSV (sim, nao, incerto) são a resposta do agente às perguntas da árvore e servem para você filtrar.

## Pré-vereditos

| Classe | RQ1 | RQ4 | Total | O que significa |
|---|---|---|---|---|
| CANDIDATO | 135 | 8 | 143 | domínio robótico e algum modelo, simulador, DT, identificação ou dado real no resumo; 99 com robô móvel explícito, 66 desses com dado real; 18 surveys marcados para snowballing |
| DUVIDA | 58 | 12 | 70 | resumo truncado ou ausente (a maior parte), capítulo genérico de DT sem robô visível, metodológico sem robô, contexto RoboCup sem DT; 29 dos 38 capítulos de coletânea caíram aqui |
| EC1_CLARO | 48 | 8 | 56 | domínio fora (manufatura, logística, energia, CPS genérico, PIML e DT em geral), controle puro em robô móvel, manipulador fixo sem método transferível |
| EC2 | 1 | 0 | 1 | Jacob-781, modelo de maturidade (conferir se há avaliação empírica) |
| EC4 | 1 | 0 | 1 | Seongsig-787, resumo em coreano (conferir o idioma do texto completo) |

Confiança: alta 118, média 82, baixa 71 (a baixa é quase toda DUVIDA por falta de resumo). Por string: S4 e S5 concentram os candidatos (47 e 51); S1 tem 20 EC1 em 72, a maior taxa de fora de domínio. Tipo declarado pelo agente: artigo 155, survey 40, capítulo 38, preprint 17, tese 8, outro 13. Sinalizados "EC3 a verificar": 27 (15 candidatos da RQ1, 2 da RQ4). Com URL de PDF aberto conhecida (OpenAlex ou Semantic Scholar): 63, dos quais 45 entre CANDIDATO e DUVIDA.

Se a taxa da RQ3 se repetir (você confirmou 50 de 55 INCLUI decididos e incluiu 13 de 34 DUVIDA), a passada 2 terá algo entre 130 e 170 estudos. É mais do que o gatilho de 39 % do guia de duas passadas; a conta está no guia atualizado.

## A ordem de leitura está no CSV (coluna `grupo`)

O CSV `pretriagem_rq1_rq4_2026-09-27.csv` tem as 271 linhas na ordem sugerida para a passada 1, primeiro RQ1, depois RQ4, e traz o resumo inteiro na coluna `resumo` para você ler sem abrir o PDF (que na maioria dos casos não existe ainda).

- **A confirmar exclusão (58, 1 min cada)**: os EC1_CLARO, o EC2 e o EC4. Leia a nota e o título; abra o resumo só se discordar. Doze têm robô móvel explícito e ainda assim saíram EC1: cinco por controle puro ou simulação sem contraparte (regras 1 e 2 do lote 1: Noorulden-5311, Kim-2426, Mostafa-4074, Mi-1495, A-2146), três por DT do processo e não do robô (Pawe-877, Nikunjkumar-937, I-1931), três de contexto RoboCup sem DT (Febrian-2449, Andrei-2465, Joo-4052) e um metodológico só simulado (Freederia-473). Se a sua régua da RQ1 for "controle validado em robô real também interessa", os cinco primeiros voltam para candidato.
- **B candidato alta (79, 1,5 min cada)**: confirme e siga. Eles vão para a passada 2 de qualquer jeito; a passada 2 é que decide EC3, EC5 e o mérito.
- **C candidato média ou baixa (64, 3 min cada)**: aqui estão surveys gerais, manipuladores com método talvez transferível e DTs de ambiente. É onde a sua régua muda mais coisa.
- **D dúvida com resumo (54, 3 min cada)**: 29 capítulos Springer com resumo cortado, metodológicos sem robô, contexto RoboCup. Na dúvida, candidato; a passada 2 decide.
- **E dúvida sem resumo (16, 2 min cada)**: abra o link ou o DOI, leia o resumo na página e decida. Seis são teses ou registros incompletos.

Orçamento: cerca de 9,5 h, ou três tardes de 3,5 h (segunda 28, terça 29 e quarta 30/09). RQ4 vem no fim da ordem e tem 28 registros: 8 candidatos, 12 dúvidas (6 sem resumo), 8 EC1.

## O que precisa de você e o agente não resolve

1. **Régua para artigos de contexto do grupo sem DT** (Andrei-2465, firmware SSL da ITAndroids; Joo-4052, MCL na SSL; Rohman-2466 e Stefan-4287, MSL): o agente marcou EC1 ou DUVIDA. Na RQ2 você incluiu contexto do grupo; decida uma vez e aplique a todos, ou use o `CONTEXTO-RQ4` que já combinamos para a RQ4.
2. **Régua para survey de DT sem robótica** (15 surveys marcados EC1, 7 DUVIDA, 18 CANDIDATO): a regra 3 do lote 1 manda EC1; os 18 CANDIDATO são surveys com robótica ou sim-to-real no escopo e entram com `Type = Survey`.
3. **Metodológico sem robô físico** (Freederia-473, Anoop-078, Wang-1339, Poommitol-010): mesma régua que você fixou na RQ3. As notas de revisão dizem qual classe sairia com a régua da RQ2 e da RQ3.
4. **Seongsig-787**: só o resumo está em coreano; se o texto for inglês, é candidato forte (DT ROS 2 de robô móvel comparando movimento real e virtual).
5. **A-2146**: cinemática validada em protótipo real com erro de 2,2 %; IC1 fraco ou EC1 pela regra 2. Vale como caso-limite para escrever a régua.
6. **Jacob-781**: modelo de maturidade para integrar robôs móveis (Spot, Bittle) a DTs; conferir se há avaliação empírica antes de EC2.
7. **Os 27 sinalizados EC3** (8 teses, 17 preprints, 2 registros sem veículo): a busca de dez minutos por versão publicada fica para a passada 2, e só para os que sobreviverem à passada 1.
8. **PDFs para a passada 2**: já rodei pelo seu MATLAB a busca de PDF aberto (OpenAlex, Semantic Scholar, Unpaywall, arXiv) para os 213 candidatos e dúvidas e baixei o que o servidor entregou: **33 PDFs novos em `slr\artigos\`** (verificados pelo cabeçalho `%PDF`), listados em `pdf_status_candidatos_2026-09-27.csv` com status `baixado_27-09`. Outros 40 têm URL aberta mas o servidor bloqueia script (MDPI, ScienceDirect, ACM, Taylor & Francis, ou página do DOI): status `abrir_no_navegador`, um clique cada. Os 140 restantes (`cafe`) não têm versão aberta conhecida e vão pelo CAFe, só os que sobreviverem à passada 1.

## Limites conhecidos deste pré-julgamento

O agente leu só o resumo: não viu figuras, método nem resultados, e 77 resumos vieram da página do DOI, muitas vezes cortados (os com menos de 40 palavras foram mandados para DUVIDA por regra). Nenhum número foi conferido contra o texto completo porque não há texto completo; os números que aparecem nas notas vieram do resumo. A régua entre EC1_CLARO e CANDIDATO em robôs móveis sem DT depende da regra 2 do lote 1, que é sua. E, como nas rodadas anteriores, os agentes não julgam peer review nem duplicata: "EC3 a verificar" é aviso, não classe.

## Custo e repetição

Oito agentes de 34 registros, cada um lendo 34 arquivos curtos (título, metadados e resumo), mais dois agentes de restauração de acentos. Como não há extração de PDF, o custo por registro é uma fração do pré-skim por texto completo da RQ2 e da RQ3. O procedimento (busca de resumos por DOI no MATLAB, montagem dos .txt, instruções, agentes, validação e escrita só em Notes) está na skill `pre-skim-slr` e nesta pasta; para uma nova fila muda só a pergunta, a árvore e a calibração.

## Arquivos

- `pretriagem_rq1_rq4_2026-09-27.csv`: as 271 linhas na ordem de leitura, com grupo, classe, confiança, as quatro respostas da árvore, tipo, RQ sugerida, sinal de EC3, fonte e tamanho do resumo, tipo e veículo segundo o OpenAlex, URL de PDF aberto, DOI, link, página do Notion, a nota gravada, o alerta do agente, o resumo inteiro e duas colunas vazias (`p1_decisao`, `p1_obs`) para você registrar a passada 1 se preferir a planilha ao Notion.
- `INSTRUCOES_AGENTE_PRETRIAGEM.md`: as instruções dadas aos agentes.
- `pdf_status_candidatos_2026-09-27.csv`: os 213 candidatos e dúvidas com DOI, URL de PDF e status (`baixado_27-09`, `abrir_no_navegador`, `cafe`); `candidatos_pdf_2026-09-27.csv`, `oa_lookup.json`, `oa_lookup_log.txt` e `oa_download_log.txt` são o insumo e o registro do script.
- `pretriagem_rq1_rq4_dois.csv`, `openalex_batch_01..06.json`, `round2_s2_crossref.json`, `round3_landing.json`: os DOIs e as respostas brutas das fontes de resumo, para auditoria.
- `guia_skim_rq1_duas_passadas.md` (em `slr\artigos\`): como fazer a passada 1 com a nota pronta e o que muda no calendário.
