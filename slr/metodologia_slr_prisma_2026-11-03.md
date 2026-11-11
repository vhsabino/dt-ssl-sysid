# Revisão Sistemática da Literatura com funil PRISMA: como estou conduzindo a SLR do doutorado

Victor Araújo (CIn-UFPE) · material para alunos · estado da revisão em 03/11/2026

Este documento reúne, na ordem em que eu explicaria para alguém começando, a metodologia que estou usando na revisão sistemática da minha tese (gêmeos digitais de robôs móveis, com foco em robôs omnidirecionais da RoboCup Small Size League). Tudo o que está aqui tem uma fonte canônica: o protocolo e o plano de execução no Notion, o banco de registros no Notion e os arquivos da pasta `slr\` do repositório. Os números são os do banco em 03/11/2026.

## 1. A origem: as diretrizes de Kitchenham e Charters

A metodologia vem das diretrizes de revisão sistemática para engenharia de software de Kitchenham e Charters [1], escritas para trazer para a área a ideia de "prática baseada em evidência" da medicina. Uma revisão sistemática (SLR) é diferente de uma revisão narrativa em três pontos: ela parte de um protocolo escrito antes da busca, usa uma estratégia de busca que outra pessoa consegue repetir, e registra toda decisão de inclusão e exclusão com o critério que a motivou. O produto não é só um texto de related work: é uma trilha auditável que mostra de onde saiu cada estudo incluído e por que os outros ficaram de fora.

As diretrizes organizam a revisão em três fases:

1. **Planejamento:** justificar a necessidade da revisão, formular as questões de pesquisa e escrever o protocolo (estratégia de busca, critérios de seleção, avaliação de qualidade, formulário de extração, plano de síntese).
2. **Condução:** executar as buscas, selecionar os estudos, avaliar a qualidade, extrair os dados e sintetizar.
3. **Relato:** escrever a revisão e documentar os desvios do protocolo.

Dois pontos das diretrizes pesam muito no meu caso. O primeiro é que o protocolo pode ser refinado durante a fase piloto, desde que o refinamento seja registrado (§6.1.1): foi assim que as strings S4 e S5 entraram e a S2 foi revisada antes das buscas institucionais. O segundo é a mitigação para revisor único (§6.2.3): como a triagem é feita por uma pessoa, o protocolo prevê um teste-reteste em amostra, com cálculo de concordância, e a arbitragem da orientadora nos casos limítrofes. Toda a adaptação que fiz do procedimento (duas passadas, pré-julgamento assistido por IA) está registrada na seção 8 do protocolo como desvio justificado, que é o mecanismo que as diretrizes oferecem para isso.

## 2. O funil PRISMA genérico

PRISMA é um padrão de relato de revisões sistemáticas [2]. Enquanto Kitchenham diz como conduzir, o PRISMA diz como reportar, e a peça mais conhecida é o diagrama de fluxo, o "funil". A versão de 2020 tem quatro faixas:

| Faixa | O que entra | O que sai pelo lado |
|---|---|---|
| **Identificação** | registros devolvidos pelas bases (e, numa coluna paralela, registros vindos de outros métodos: snowballing, entrada manual) | registros removidos antes da triagem: duplicatas e registros inválidos |
| **Triagem** | registros triados por título e resumo | registros excluídos na triagem |
| **Elegibilidade** | relatórios buscados para leitura do texto completo; relatórios avaliados no texto completo | relatórios não recuperados; relatórios excluídos, com o motivo e a contagem por motivo |
| **Incluídos** | estudos incluídos na síntese | |

Três distinções importam na hora de contar. "Registro" é a linha que a base devolveu; "relatório" é o documento (o PDF); "estudo" é a pesquisa relatada, e um estudo pode ter mais de um relatório (um preprint e a versão publicada, por exemplo). Cada seta do funil fecha aritmeticamente: o que entra numa caixa é o que saiu da anterior menos o que saiu pelo lado. É essa aritmética que torna o funil verificável, e é por isso que, no meu caso, ele é gerado por script a partir do banco e não desenhado à mão.

## 3. As questões de pesquisa

A questão de pesquisa (RQ) é o que define o escopo: ela diz o que a revisão vai responder e, por consequência, o que fica de fora. Kitchenham recomenda estruturar as RQs com o PICOC (população, intervenção, comparação, resultado e contexto), porque cada faceta vira depois um bloco da string de busca. Também vale escrever o que não está sendo investigado: são essas perguntas que afiam os critérios de exclusão.

As minhas RQs (versão 2, refinada em 11/07/2026 com a orientadora) são:

- **RQ1.** Como gêmeos digitais de robôs móveis são construídos, quais arquiteturas, componentes e abordagens de identificação de sistemas são empregados, e que tipos de dados são utilizados para essa construção? Sub-questão, respondida pelo formulário de extração e não por string própria: quais limitações e condições de identificabilidade são reportadas, em especial para dados de operação em malha fechada?
- **RQ2.** Quais métricas, horizontes de predição e protocolos de validação são utilizados para quantificar a fidelidade de gêmeos digitais de robôs móveis?
- **RQ3.** Como gêmeos digitais calibrados a partir de dados reais são integrados a pipelines de treinamento por aprendizado por reforço, e qual o impacto da fidelidade do gêmeo na transferência de políticas?
- **RQ4 (proposta, ainda a validar com a orientadora):** o contexto da RoboCup e do futebol de robôs. Não está no protocolo; existe como marcação no banco e os 28 registros dela foram julgados pelos mesmos critérios das outras.

O PICOC que sustenta as RQs: população, robôs móveis (omnidirecionais, de competição e plataformas móveis em geral); intervenção, construção de gêmeos digitais e identificação ou calibração de modelos a partir de dados reais; comparação, abordagens caixa branca, cinza e preta, parâmetros nominais, gêmeos sem calibração empírica; resultado, fidelidade preditiva (métrica, horizonte e protocolo), completude do gêmeo e sucesso da transferência para RL; contexto, dados de operação (malha fechada, telemetria, competição) e experimentos dedicados de excitação.

E o que não está sendo investigado, com o critério que isso gera: como construir modelos físicos multicorpo detalhados (EC1); qual o melhor algoritmo de RL sem componente de calibração ou fidelidade (EC1); gêmeos digitais de manufatura, energia ou edifícios sem transferência metodológica para robótica móvel (EC1).

## 4. Das questões às palavras-chave e às strings

O método é o de Kitchenham: cada faceta do PICOC vira um bloco de termos ligados por OR, com sinônimos; os blocos são ligados por AND. A decisão mais importante que tomei aqui foi manter sinônimos de "gêmeo digital" ("virtual model", "simulation model", "behavioral model"), porque o termo é recente e muita literatura relevante de identificação para sim-to-real usa vocabulário de modelagem e simulação sem empregá-lo. O critério de validação das strings foi recuperar os artigos-âncora que eu já conhecia; os que não foram recuperados entraram por snowballing documentado.

| String | Cobre | Formulação |
|---|---|---|
| S1 | RQ1, RQ2 | ("digital twin" OR "virtual model" OR "simulation model" OR "behavioral model") AND ("system identification" OR "model calibration" OR "grey-box" OR "gray-box" OR "parameter identification") AND ("mobile robot" OR "omnidirectional robot" OR robot*) |
| S2 (v2) | a lacuna da tese | ("omnidirectional robot" OR "mobile robot" OR "RoboCup") AND ("model calibration" OR "parameter identification" OR "system identification") AND (log* OR telemetry OR "operational data" OR "field data" OR "closed-loop data" OR "real-world data") |
| S3 | RQ3 | ("sim-to-real" OR "reality gap" OR "domain randomization") AND ("system identification" OR calibrat*) AND ("reinforcement learning") |
| S4 | RQ3, RQ1 | ("digital twin" OR "virtual model" OR "simulation model") AND ("sim-to-real" OR "reality gap" OR "reinforcement learning") AND ("mobile robot" OR "omnidirectional robot" OR robot*) |
| S5 | RQ1 (arquitetura) | "digital twin" AND ("mobile robot" OR "omnidirectional robot") |

Duas histórias dessas strings valem ser contadas para quem está começando. A S2, na primeira versão, devolveu zero resultados no OpenAlex. Em vez de descartar a string, verifiquei cada par de blocos: plataforma com calibração devolvia 59, plataforma com telemetria 320, calibração com telemetria 553, e só a interseção tripla era vazia. Isso não é erro de string, é uma célula vazia na literatura, e virou a primeira evidência da lacuna que a tese preenche (calibração a partir de dados operacionais de robôs móveis). A versão 2 ampliou o vocabulário de dados ("field data", "closed-loop data", "real-world data") e acrescentou "system identification" ao bloco central; o resultado da v1 ficou preservado no log. A segunda história é a das strings S4 e S5, adicionadas em 11/07 depois da análise de cobertura do piloto: a S1 e a S3 exigiam vocabulário de identificação, e estudos de gêmeo com RL que não usam esse vocabulário escapavam das duas (daí a S4); estudos de arquitetura de gêmeos de robôs móveis sem calibração e sem RL escapavam de todas (daí a S5, de alta precisão, sem o terceiro bloco porque a população já é específica).

Filtros comuns a todas as execuções: 2015 a 2026 e, onde a base permite, inglês. Clássicos anteriores a 2015 entram por snowballing.

## 5. As plataformas de busca

O protocolo define quatro bases obrigatórias, IEEE Xplore, ACM Digital Library, Scopus e SpringerLink, e as complementares Web of Science e OpenAlex (reaproveitando, rotulado como fonte auxiliar, um mapeamento anterior feito com o Claude Science). Na execução entraram também as APIs abertas do Semantic Scholar e do arXiv. As buscas nas bases institucionais foram feitas em 11 e 12/07/2026; as das APIs abertas, em 12/07. A Web of Science ficou fora do log e isso é um item em aberto para a seção 8.

| Base | S1 | S2 | S3 | S4 | S5 | Total |
|---|---|---|---|---|---|---|
| SpringerLink | 677 | 184 | 344 | 1.000 | 355 | 2.560 |
| ACM DL | 538 | 101 | 199 | 1.132 | 201 | 2.171 |
| OpenAlex | 94 | 0 | 139 | 616 | 383 | 1.232 |
| Scopus | 81 | 14 | 80 | 509 | 350 | 1.034 |
| Semantic Scholar | 56 | 0 | 91 | 362 | 220 | 729 |
| IEEE Xplore | 58 | 4 | 68 | 406 | 186 | 722 |
| arXiv | 17 | 0 | 56 | 98 | 16 | 187 |
| **Total** | 1.521 | 303 | 977 | 4.123 | 1.711 | **8.635** |

Dois cuidados operacionais que aprendi nessa etapa. O ACM DL trunca a exportação em 1.000 registros: a S4 devolveu exatamente 1.000 na primeira exportação, o número redondo denunciou o teto, e a busca foi refeita em duas partes (1.132 reais); o arquivo truncado foi arquivado para auditoria. O SpringerLink busca em texto completo, com ranking que não é previsível em anais: dois artigos-âncora publicados na LNAI não vieram no export institucional, e isso foi registrado como limitação da própria base, não presumido. Cada execução tem no log do protocolo a base, a string, a data, os filtros e o número de retornados.

## 6. A integração com o Notion

O Notion é a única fonte de verdade da revisão. São três páginas: o protocolo (seções 1 a 9: contexto, RQs, estratégia de busca com log, critérios, avaliação de qualidade, formulário de extração, síntese, desvios e cronograma), o plano de execução (sprints e marcos) e o banco de registros, que é uma base de dados com 5.565 linhas, uma por registro.

As propriedades do banco que fazem o funil funcionar:

| Propriedade | Para que serve |
|---|---|
| Paper ID | identificador único no formato `SLR-ANO-PrimeiroAutor-NNNN`, igual ao nome do arquivo PDF; entradas de snowballing usam a série `SB-NNN` e entradas manuais, o prefixo `EXT` |
| Name, Authors, Year, DOI, Link | metadados do registro |
| Source (múltipla) e Search String | de onde o registro veio; um registro devolvido por várias bases tem todas marcadas |
| Selection Stage | o veredito do funil: `Identified`, `Excluded Title/Abstract`, `Excluded Full-Text`, `Included`, `Duplicate` |
| Status | o estágio de leitura, separado do veredito: `Not read`, `Recommended Full Read`, `Read in Progress`, `Finished` |
| Exclusion Criterion | EC1 a EC6, exatamente com os códigos do protocolo |
| RQ Mapping (múltipla) | RQ1 a RQ4; um estudo pode responder a mais de uma |
| Type, Keyword, Qualis | classificação; revisões de terceiros recebem marcação própria em Type (`Survey` na prática, `Literature Review` no protocolo; a unificação está pendente), alimentam o snowballing e não entram como estudos primários |
| Notes | a trilha de auditoria: justificativa da decisão e, antes dela, o pré-julgamento assistido |
| Quality Score, Data Extracted, Cite, BibTeX Key, Drive File | preenchidos só na fase de texto completo (DARE de 0 a 4, formulário de extração, citação) |

As convenções que mantêm o banco consistente, registradas no protocolo em 12/07: `Included` é final e só depois do texto completo; na triagem, o registro aprovado continua `Identified` com `Status = Recommended Full Read`; na dúvida, o registro avança; a decisão é sempre minha, registro por registro. A automação só escreve no campo `Notes`, e com prefixo que identifica a origem: `PRE-SKIM IA dd/mm:` (pré-julgamento por texto completo, usado nas RQ2 e RQ3), `PRE-TRIAGEM IA 27/09:` (pré-julgamento por resumo, usado na passada 1 da RQ1 e da RQ4) e `SKIM dd/mm:` (a minha decisão, escrita antes da nota do agente, sem apagar nada). Os prefixos permitem consultar o banco e separar o que já foi julgado do que não foi, e medir a concordância entre o pré-julgamento e a minha decisão, que vai para a seção 8.

A ingestão foi feita por script (`slr\scripts\slr_pipeline.py`): os exports de cada base foram unificados, deduplicados por DOI e por título normalizado e carregados no banco pela API do Notion, com o log de busca preservado. A exclusão em lote de 607 registros de front-matter de anais (capas, prefácios, índices) foi feita por padrão de título, mas só depois de eu revisar a lista inteira; a automação executou a marcação, a decisão foi minha. Depois disso, toda leitura do banco para contagem é feita por consulta SQL ao Notion e passa por um script (`deriva_contagens.py`) que confere o fechamento de cada caixa do funil antes de gerar a figura.

## 7. Como os artigos estão organizados

Os PDFs ficam fora do controle de versão, em `slr\artigos\`, um arquivo por registro com o nome exato do Paper ID (`SLR-2024-Wilson-782.pdf`). Hoje são 260 arquivos. A pasta `slr\pdfs\` guarda os clássicos e os artigos de contexto que não vieram das buscas (`EXT-...`). Os downloads foram organizados em lotes por RQ (lote 1 RQ2, lote 2 RQ3, lotes 3 e 4 RQ1 e RQ4), com um CSV por lote dizendo de onde baixar cada um.

Dentro de `slr\artigos\`:

- `guia_skim_rq2.md`, `guia_skim_rq3.md`, `guia_skim_rq1_duas_passadas.md`, `guia_passada2_rq1.md`: os guias de leitura de cada rodada, com a rotina cronometrada, a árvore de decisão, as réguas fixadas na primeira ocorrência e o modelo de nota para o Notion.
- `preskim\`: os pré-julgamentos assistidos (CSV por RQ, instruções dadas aos agentes, texto extraído dos PDFs) e, em `preskim\pretriagem\`, a pré-triagem por resumo dos 271 registros da RQ1 e da RQ4.
- `prisma\`: o funil. Para cada data: a consulta ao banco transcrita (`sql_<data>.json`), o estado congelado da passada 1, a lista de PDFs presentes, as contagens derivadas com os fechamentos conferidos (`contagens_prisma_<data>.json`), a figura (`fig_funil_prisma_<data>.png`) e uma nota de estado. Também a lista viva de PDFs que faltam, com a rota para obter cada um.
- `reteste\`: a amostra do teste-reteste da triagem, o gabarito (que só abri depois de preencher) e o resultado.
- `reuniao_2026-09-11\`: o relatório e as figuras da reunião com a orientadora.

A regra prática é que nenhum número da revisão vive só em texto: ele tem de ser derivável do banco do Notion ou de um arquivo dessa pasta.

## 8. O funil PRISMA adaptado ao meu contexto

![Funil PRISMA em 03/11/2026](artigos/prisma/fig_funil_prisma_2026-11-03.png)

| Etapa | n | Observação |
|---|---|---|
| Registros identificados nas bases | 8.635 | 7 bases, 5 strings, julho de 2026 |
| Removidos antes da triagem | 3.112 | 3.071 na deduplicação da ingestão, 40 duplicatas por título, 1 registro vazio |
| Triados por título e resumo | 5.523 | rodada 1, julho e agosto, um revisor; teste-reteste em 45: concordância 84%, kappa 0,68 |
| Excluídos na triagem | 5.075 | EC1 5.068, EC4 4, EC2 2, 1 sem critério |
| Aprovados para leitura | 448 | 177 das RQ2 e RQ3 direto ao texto completo; 271 da RQ1 e RQ4 em passada 1 por resumo |
| Excluídos na passada 1 | 158 | decisão por resumo, com pré-triagem assistida: EC1 156, EC2 1, EC4 1 |
| Buscados para o texto completo | 290 | 177 + 113 aprovados na passada 1 |
| Não recuperados | 4 | EC6 |
| Texto completo | 286 | 196 avaliados; 90 em avaliação (81 com PDF, 9 aguardando PDF) |
| Excluídos no texto completo | 104 | EC1 78, EC4 10, EC3 8, EC2 5, EC5 3 |
| **Estudos incluídos** | **94** | 92 das bases + 2 de outros métodos; 86 primários e 8 revisões; RQ1 7, RQ2 23, RQ3 71 |

O que mudou em relação ao funil genérico, e por quê:

1. **Duas rodadas de triagem.** A rodada 1 (título e resumo) cobriu os 5.523 registros. Para a RQ1 e a RQ4, que concentravam 271 dos 448 aprovados, não cabia uma leitura de texto completo de 10 minutos por registro no tempo que eu tinha; fiz uma passada 1 por resumo, com pré-triagem assistida por IA gravada nas Notes, e a passada 2 por texto completo só nos 113 que sobreviveram. No PRISMA, a passada 1 conta como triagem (decisão por resumo), por isso os 158 excluídos ali aparecem na faixa de triagem e não na de elegibilidade.
2. **Caixa "em avaliação".** Como a passada 2 está em andamento, a faixa de elegibilidade mostra os 286 relatórios de texto completo divididos em avaliados e em avaliação; assim o fluxo fecha de cima para baixo (196 avaliados menos 104 excluídos são os 92 incluídos das bases) e ninguém precisa somar o Included do Notion com o que ainda está em análise.
3. **Pré-julgamento assistido, decisão humana.** Agentes de IA leram o texto completo (RQ2 e RQ3) ou o resumo (RQ1 e RQ4) e escreveram um pré-veredito nas Notes; eu decidi cada registro. A concordância é medida e vai para a seção 8: na RQ2, 30 de 35 nos pré-vereditos não ambíguos; na RQ3, 65 de 71; na passada 1, 46 dos 56 marcados "exclusão clara" foram confirmados e 84 dos 143 "candidatos" foram aprovados.
4. **Teste-reteste.** Reavaliei às cegas 45 registros da triagem (25 excluídos e 20 aprovados) um mês e meio a três meses depois: concordância de 84% e kappa de Cohen de 0,68, acima do limiar de 0,6 do protocolo; a triagem foi mantida. As seis divergências no estrato dos aprovados foram todas no sentido mais restritivo, e duas delas eram estudos que acabei incluindo no texto completo, o que reforça a regra de avançar na dúvida.
5. **Decisões sem o PDF.** 26 exclusões de texto completo foram decididas pela página da editora ou pelo resumo (idioma, tipo de publicação, escopo claro); a versão detalhada do funil lista os IDs, para que isso fique auditável.
6. **Outros métodos.** Dois estudos entraram fora das strings: um por snowballing backward (DROPO, ausente de todas as bases) e um por entrada manual.

## 9. Estado atual e próximos passos

Em 03/11/2026: 94 estudos incluídos, 90 aprovados na passada 1 ainda em avaliação (a passada 2 decidiu 8 dos 89 com PDF: 1 confirmado, 7 excluídos), 12 PDFs faltando (5 que valem pedir ao autor, 7 por rota fácil ou EC6), extração e avaliação de qualidade ainda não iniciadas. O que falta, na ordem:

1. Terminar a passada 2 (81 registros com PDF, cerca de 14 horas) e decidir EC6 para o que não chegar.
2. Fechar a seleção: adjudicar a divergência do reteste, resolver os três registros com marcação pendente, calcular a concordância final da passada 2 e registrar tudo na seção 8 do protocolo.
3. Snowballing backward e forward sobre os incluídos e os artigos-âncora, com a mesma regra de triagem.
4. Sprint 3: formulário de extração e DARE para cada incluído.
5. Sprint 4: síntese narrativa por RQ, as quatro tabelas da seção 7 do protocolo, o funil final e o texto do capítulo.

O cronograma revisado, com datas, está em `slr\cronograma_slr_2026-11-03.md`.

## Referências

[1] KITCHENHAM, B.; CHARTERS, S. Guidelines for performing Systematic Literature Reviews in Software Engineering. Version 2.3. EBSE Technical Report EBSE-2007-01. Keele University and University of Durham, 2007.

[2] PAGE, M. J. et al. The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ, v. 372, n71, 2021.
