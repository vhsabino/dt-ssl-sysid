# Teste-reteste da triagem por título e resumo: resultado (11/10/2026)

Planilha preenchida às cegas em 11/10/2026 (`reteste_TA_2026-09-12.xlsx`, 45 de 45 decisões) comparada com o gabarito de 12/09 (`reteste_TA_2026-09-12_GABARITO_nao_abrir.csv`). A situação atual de cada registro divergente foi conferida no banco do Notion em 11/10. Números em `resultado_reteste_2026-10-11.json`; para refazer, `python analise_reteste.py . resultado_reteste_2026-10-11.json` nesta pasta (requer openpyxl).

## Números

| | Reteste: excluir | Reteste: aprovar | Total |
|---|---|---|---|
| Original: excluído (estrato A) | 24 | 1 | 25 |
| Original: aprovado (estrato B) | 6 | 14 | 20 |
| Total | 30 | 15 | 45 |

- Concordância simples: 84,4% (38 de 45; IC 95% de Wilson, 71,2% a 92,3%).
- Kappa de Cohen: 0,68 (IC 95% assintótico de 0,46 a 0,89; bootstrap estratificado, 20.000 reamostragens, de 0,44 a 0,86). PABAK 0,69.
- Estrato A, exclusões por EC1: 24 de 25 repetidas (96%; IC 95% de 80,5% a 99,3%), todas com o mesmo critério (EC1). Exclusão que virou aprovação: 1 em 25 (IC 95% de 0,7% a 19,5%).
- Estrato B, aprovações: 14 de 20 repetidas (70%; IC 95% de 48,1% a 85,5%). As 6 divergências foram todas para exclusão por EC1.
- Por estrato, o kappa não se aplica, porque a decisão original é a mesma em todo o estrato: a medida por estrato é a concordância simples, e o kappa vale para o total.

## Divergências e situação atual no banco

| Paper ID | Estrato | Original (jul e ago) | Reteste (11/10) | Situação no banco em 11/10 |
|---|---|---|---|---|
| SLR-2024-Jongmoon-4537 | A | excluído, EC1 | aprovar | Excluded Title/Abstract, EC1. Capítulo de livro de autor único (Springer, 2024); pelo título, visão geral de DRL, IA generativa, aprendizado federado e DT |
| SLR-2020-I-1931 | B | aprovado | excluir, EC1 | Excluded Full-Text, EC1 (passada 1) |
| SLR-2025-Febrian-2449 | B | aprovado | excluir, EC1 | Excluded Full-Text, EC1 (passada 1, RQ4) |
| SLR-2025-Lianzhao-3590 | B | aprovado | excluir, EC1 | Excluded Full-Text, EC1 (passada 1) |
| SLR-2026-Philippe-4238 | B | aprovado | excluir, EC1 | Excluded Full-Text, EC1 (RQ3, decidido em 09/10 sem o PDF) |
| SLR-2023-Grazioso-2365 | B | aprovado | excluir, EC1 | Included, RQ1 e RQ2, após o texto completo |
| SLR-2026-Xinmao-161 | B | aprovado | excluir, EC1 | Included, RQ3, após o texto completo |

## Leitura

1. O kappa de 0,68 passa o limiar de 0,6 do protocolo: a triagem por título e resumo fica como está, sem ampliar a amostra.
2. As exclusões se repetem (24 de 25, mesmo EC). A direção de risco, exclusão indevida, teve uma ocorrência, que precisa de adjudicação.
3. O reteste foi mais restritivo que a triagem original: as 6 divergências do estrato B foram para exclusão. É o efeito esperado da calibração das regras de EC1 nas leituras da RQ2 e da RQ3. Quatro desses registros saíram depois nas etapas seguintes, mas dois foram incluídos após o texto completo (Grazioso-2365 e Xinmao-161). Aplicado na triagem, o critério mais restritivo de hoje teria descartado dois estudos incluídos: a regra "na dúvida, avança" fez o seu papel e deve valer em qualquer triagem nova, inclusive a do snowballing.
4. Com 45 registros, o intervalo do kappa vai de moderado a quase perfeito, e uma exclusão indevida em 25 não distingue uma taxa de 1% de uma de 15%. O risco residual de exclusão indevida é tratado pelo snowballing (§3), não por ampliar o reteste.
5. Limitação: os 20 registros do estrato B já tinham sido revistos na passada 1 ou nas leituras de texto completo da RQ2 e da RQ3 antes do reteste, então esse estrato não estava cego. O estrato A, que testa a direção de risco, estava.

## Rascunho para o §8 do protocolo

Teste-reteste da triagem por título e resumo (11/10/2026). Como a triagem foi conduzida por um único pesquisador, a confiabilidade intra-avaliador foi verificada por teste-reteste, conforme previsto no §4. Uma amostra de 45 registros, gerada em 12/09/2026, foi rejulgada às cegas em 11/10/2026, de seis semanas a três meses depois da triagem original, feita em julho e agosto, sem consulta ao banco nem às decisões anteriores. O estrato A reuniu 25 registros excluídos por EC1, escolhidos por seleção sistemática pelo Paper ID, e testou a direção de maior risco, a exclusão indevida. O estrato B reuniu 20 registros aprovados para leitura integral, sorteados da fila de 442 em proporção às RQs. A concordância simples foi de 84,4% (38 de 45) e o kappa de Cohen foi de 0,68 (IC 95% de 0,46 a 0,89), acima do limiar de 0,6 fixado no protocolo, e a triagem foi mantida sem alterações. As exclusões se repetiram em 24 dos 25 registros do estrato A, todas pelo mesmo critério. A única divergência nesse estrato, SLR-2024-Jongmoon-4537, foi adjudicada em [data]: [mantida a exclusão por EC1, por se tratar de visão geral sem sistema robótico | registro reaberto e encaminhado à leitura integral]. No estrato B, as aprovações se repetiram em 14 dos 20 registros, e as seis divergências foram todas no sentido mais restritivo, com EC1 no reteste. Quatro desses registros foram excluídos nas etapas seguintes e dois foram incluídos após a leitura do texto completo (SLR-2023-Grazioso-2365 e SLR-2026-Xinmao-161). O resultado indica que o critério ficou mais restritivo ao longo do processo, efeito da calibração das regras de EC1 durante as leituras da RQ2 e da RQ3, e reforça a regra de interpretação liberal na triagem, já que o critério mais restritivo teria descartado dois estudos incluídos. Como limitações, os registros do estrato B já tinham sido revistos na passada 1 ou nas leituras de texto completo antes do reteste, o que compromete o cegamento desse estrato, e o tamanho da amostra deixa o intervalo de confiança do kappa amplo. O risco residual de exclusão indevida é tratado pelo snowballing previsto no §3.

Observação: o rascunho não cita referência externa. Cohen (1960), para o kappa, e Landis e Koch (1977), para as faixas de interpretação, não estão no `latex/refs/references.bib`; se forem citados no artigo, precisam entrar lá antes.
