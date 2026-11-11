# Pré-skim assistido da RQ3: 111 estudos lidos, 109 notas gravadas no Notion em 19/09/2026

## O que foi feito

Dos 129 registros da fila de RQ3, 111 tinham PDF na pasta `slr\artigos\` (110 PDFs mais o resumo `.md` de Nalaka-2415). O texto de cada um foi extraído com `pdftotext`, cortado em 7.000 palavras quando necessário (38 estudos ficaram parciais, marcados na coluna `texto_parcial` do CSV) e distribuído entre 14 agentes em paralelo, oito artigos por agente, com as mesmas instruções (`INSTRUCOES_AGENTE_preskim_rq3.md`, nesta pasta). As instruções foram calibradas com dois exemplos escritos por mim no formato novo, DROPO (Tiboni-SB001) e VSSS-RL (Hansenclever-2407), e carregam a lição da RQ2: nos cinco casos em que o agente disse EC1 e você incluiu, a contribuição era metodológica sem robô físico; por isso na RQ3 esses casos viram DUVIDA, não EC1.

O campo Notes de 109 registros recebeu a nota com o prefixo `PRE-SKIM IA 19/09:`. Em 22 delas acrescentei um sufixo `|| REVISÃO 19/09:` com a minha leitura de revisor, onde discordo do agente ou onde a decisão depende de uma régua sua. **Nada além de Notes foi tocado**: Selection Stage continua `Identified`, Status continua `Recommended Full Read`, Exclusion Criterion segue vazio e RQ Mapping intacto, conferido por consulta agregada depois da escrita. Duas notas suas foram preservadas sem alteração e o pré-skim delas está só no CSV: EXT-2026-Omniwheel-Mujoco (sua entrada manual de 02/09) e SLR-2023-Tiboni-SB001 (o âncora). Os 18 registros sem PDF ficaram com Notes vazio e aparecem no CSV como `SEM PDF`.

## Formato da nota (cinco campos, seis separadores contando a revisão)

`PRE-SKIM IA 19/09: [robô/plataforma; simulador ou DT; calibração com dados reais] | integração DT+RL: [mecanismo com o valor do formulário de extração; algoritmo] | transferência medida por [métrica] sobre [tarefa]: [números sim vs real] | fidelidade -> transferência: [efeito isolado com número, ou "não isolado", ou "não encontrado"] | relevância p/ tese: alta/média/baixa | [obs]`

O segundo e o quarto campos são os dois campos do formulário de extração que dependem da RQ3 (mecanismo de integração e impacto da fidelidade na transferência). Quando você confirmar uma nota, a extração da Sprint 3 já está meio feita.

## Pré-vereditos (sugestão, não decisão)

| Pré-veredito | n | O que significa |
|---|---|---|
| INCLUI | 60 | RL ou aprendizado de política em simulador ou DT com contraparte real (52 têm robô físico e transferência medida; 32 calibram o simulador com dados reais; 24 variam a fidelidade e medem o efeito) |
| DUVIDA | 35 | 12 são metodológicos sobre DT+RL sem robô físico; 17 não têm RL e servem à RQ1 ou RQ2 (remapear); 6 têm texto insuficiente ou peer review incerto |
| EC1 | 12 | domínio fora (trânsito, ponte, job shop, suspensão, SciML), survey de ML geral, ou RL sim-to-sim sem DT nem dado real |
| EC2 | 4 | sem avaliação empírica (conceituais, whitepaper) |
| SEM PDF | 18 | não julgados |

Confiança do agente: 70 alta, 31 média, 10 baixa. Mecanismo mais frequente entre os INCLUI: substituição de dinâmica (23), DR informada por dados (14), adaptação de domínio (8), fine-tuning no real (3), residual (2). Relevância alta em 36 notas.

Se o padrão se confirmar, a RQ3 fecha com 60 a 80 incluídos, muito acima do gatilho S6. O que muda em relação à RQ2 é a natureza das dúvidas: aqui a maior parte é "serve à SLR, mas não à RQ3 como está escrita". A regra do guia é clara: falta de RL não é critério de exclusão, IC1 e IC2 bastam; a decisão nesses casos é INCLUI com RQ Mapping alterado, não EC.

## A ordem de leitura está no CSV (coluna `grupo_leitura`)

- **A âncora (22)**: robô móvel ou veículo real, RL e transferência medida. Comece por Tobias-220 (Cozmo com DT calibrado por dados reais, o caso mais literal da RQ3), Masanori-4201 (DR calibrada por medição real de sensor, cinco robôs com rodas), C-1839 (gap sim2real medido em três graus de DR, relação não monotônica), Viktor-092 (SysID mais DR informada, atraso do atuador decide a transferência), Taner-465 (três níveis de fidelidade, Python, Gazebo, real, com números), J-1786 (prior físico mais GP residual em RC car), Weitao-142 (compensação de ação aprendida com dados reais) e Aarush-1090 (robô de baixíssimo custo, drift do encoder medido). Mateus-2445 é a plataforma da tese e tem leitura obrigatória. Os dois Hansenclever têm os mesmos números: decida qual fica e marque EC5 no outro.
- **B survey (5)**: W-1800, Erica-2406, Rajesh-226, Ziqian-1066 e Hao-4214 alimentam o snowballing; marque `Type = Survey`.
- **C inclui (33)**: braços, mãos, drones, humanoides e AUV com mecanismo transferível. Aqui a sua régua sobre "método transferível a robô com rodas" decide; os agentes anotaram a dúvida em cada obs.
- **D dúvida (35)**: os 17 "remapear" primeiro (Arango-2328, Mengmeng-419, Manuel-242, S-1918, A-1906, A-2110, Shijie-3560, Xilun-847, Asher-471, Sunny-053, Jo-421, Cavalcanti-1399 e afins), depois os metodológicos sem robô.
- **E exclusão (16)**: confirmação rápida, três minutos cada. Três merecem um olhar a mais e estão sinalizados na revisão: A-208 (RL direto no hardware, 950 horas de robô, contraste útil na discussão), A-2074 (trânsito, mas é o desenho experimental de dois simuladores com gap medido que a RQ3 mais precisa) e Ying-426 (regra 1, mas com atrito medido experimentalmente).
- **F sem PDF (18)**: baixar por CAFe antes de julgar, ou EC6 pela regra dos dez minutos.

## O que precisa de você e o agente não resolve

1. **SLR-2022-Hao-4214 (Nature Machine Intelligence, review exatamente sobre a RQ3)**: o PDF na pasta tem uma página e está corrompido. Baixar de novo antes de julgar.
2. **SLR-2026-Oliver-3504**: o PDF é o livro inteiro (416 páginas). Reextraí o capítulo Sim2Rob (páginas 331 a 342 do livro) e escrevi a nota eu mesmo; o pré-veredito é INCLUI com relevância média (Franka, PPO, 93% em sim e 85% no real).
3. **25 estudos podem cair em EC3** (preprints arXiv, TechRxiv, bioRxiv, Research Square, Preprints.org, Zenodo, um TCC e um relatório de curso), listados na coluna `tipo`. Dez minutos de busca por versão publicada resolvem cada um; treze deles têm relevância alta (Rae-091, Hansenclever-2407, Gabrael-2528, Jack-323, Jaume-3372, Luis-125, Lszl-546, Sahar-3370, Jad-424, Jiahe-141, Satoshi-140, Vishnu-146 e a entrada manual asRoBallet).
4. **Duplicata provável**: Hansenclever-2409 (resumo de workshop 2019) e Hansenclever-2407 (arXiv 2020) trazem os mesmos números.
5. **Dois estudos com extração corrompida ou só resumo**: Wenshuai-090 (troca sistemática de caracteres no PDF) e Nalaka-2415 (só o resumo, paywall ASME). Os pré-vereditos valem pouco; julgue pelo PDF.
6. **Régua sobre "aprendizado de política sem RL"**: Lszl-546 (CNN supervisionada), Jack-323 (imitação do MPC), Jad-424 (imitation learning com flow matching), Maximilian-1025 (otimização bayesiana de MPPI) e Narges-806 (imitation learning) foram marcados INCLUI ou DUVIDA porque calibram e transferem uma política aprendida, mas não por RL. A RQ3 diz RL. Decida uma vez e aplique a todos.
7. **Régua sobre plataforma não móvel**: cerca de 30 dos 60 INCLUI são braços, mãos, drones, humanoides, AUV ou ASV, não robôs com rodas. Na RQ2 você incluiu métodos transferíveis; se mantiver a régua, quase todos ficam.

## Limites conhecidos deste pré-julgamento

O agente lê só o texto extraído por `pdftotext`: **tabelas e figuras se perdem**, e 38 textos foram cortados por tamanho. Quase toda nota traz o alerta do que só o PDF resolve. A verificação automática procurou cada número das notas no texto de origem; as únicas divergências são de formatação (números separados por vírgula em listas, "8, 192" no original, um dígito de OCR sinalizado na própria nota). Nenhum número inventado foi encontrado, mas a verificação é por correspondência de texto, não semântica. Dois agentes escreveram sem acentos; corrigi as 16 notas à mão antes de gravar, e sete delas ficaram entre 1.000 e 1.100 caracteres.

## Custo e repetição

Custo observado: 16 agentes (14 mais duas relançadas por limite de sessão), cerca de 270 mil tokens por agente de oito artigos, ou 34 mil por estudo, fora do contexto da nossa conversa. Para a RQ1 (251 estudos, 233 com PDF esperado) seriam cerca de 30 agentes e 8 milhões de tokens. O procedimento e as instruções estão nesta pasta e na skill `pre-skim-slr`; muda só a pergunta, a árvore de decisão e os dois exemplos calibrados.

## Arquivos

- `preskim_rq3_2026-09-19.csv`: as 129 linhas, com grupo de leitura, pré-veredito, confiança, relevância, os cinco campos binários (robô físico, RL em simulador, calibração com dados reais, transferência real medida, fidelidade variada), mecanismo, RQ sugerida, tipo, se o texto foi cortado, a revisão, a nota, o alerta, o trecho de evidência literal, DOI e o link da página no Notion. Ordenado na ordem de leitura sugerida.
- `INSTRUCOES_AGENTE_preskim_rq3.md`: as instruções dadas aos agentes.
- `guia_skim_rq3.md` (em `slr\artigos\`): como julgar cada registro com a nota pronta.
