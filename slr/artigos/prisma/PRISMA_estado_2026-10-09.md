# Funil PRISMA e status da SLR 2026: 09/10/2026

Figura: `fig_funil_prisma_2026-10-09.png` (e `.pdf` para o LaTeX), no mesmo formato da de 02/10. Lista de PDFs: `pdfs_faltantes_2026-10-09.csv` e a mesma lista com links clicáveis em `pdfs_faltantes_2026-10-09.html`. Os números vêm de duas consultas ao banco do Notion feitas hoje e do log de busca do protocolo (§3). O `deriva_contagens.py` confere que cada caixa fecha com a anterior e que a lista de PDFs tem exatamente os registros que o funil diz estarem sem PDF.

## O funil hoje

| Etapa | n | Como foi contado |
|---|---|---|
| Identificados nas bases | 8.635 | log de busca do protocolo: 7 fontes × S1 a S5, 11 e 12/07 |
| Removidos antes da triagem | 3.112 | 3.071 na ingestão (log menos banco), 40 duplicatas por título (EC5), 1 registro vazio |
| Triados por título e resumo (rodada 1) | 5.523 | |
| Excluídos na rodada 1 | 5.075 | EC1 5.068, EC4 4, EC2 2, 1 sem critério (Youndo-914) |
| Aprovados na rodada 1 | 448 | 177 da RQ2 e RQ3 foram direto ao texto completo; 271 da RQ1 e RQ4 passaram pela passada 1 |
| Passada 1, excluídos | 157 | EC1 156, EC4 1 |
| Passada 1, aprovados | 113 | RQ1 105, RQ4 8 |
| Passada 1, sem decisão | 1 | Feng-1317 |
| Relatórios buscados | 290 | 177 e os 113 aprovados na passada 1 |
| Não recuperados | 2 | EC6 |
| Aguardando PDF | 101 | 17 da RQ3 (grupo F) e 84 aprovados na passada 1 |
| Com PDF e sem decisão | 34 | 5 da RQ3 e 29 aprovados na passada 1 |
| Avaliados no texto completo | 153 | 87 incluídos e 66 excluídos (EC1 54, EC3 5, EC2 4, EC5 2, EC4 1) |
| Outros métodos | 2 | DROPO (snowballing) e asRoBallet (entrada manual), ambos incluídos |
| **Estudos incluídos** | **202 (113 em análise)** | 89 confirmados no texto completo (81 primários e 8 revisões de terceiros) + 113 aprovados na passada 1 aguardando texto completo (98 primários e 15 revisões) |

## Os 202 incluídos (113 em análise)

Conferido direto no banco do Notion em 09/10, ao fim do dia: 202 registros com Selection Stage = Included, 113 deles com a nota da pré-triagem de 27/09, 23 com Type = Survey. Os mesmos números das consultas da manhã. A pedido seu, a caixa "Estudos incluídos" da figura mostra os 202, separados em dois grupos:

| Grupo | n | Como foi decidido |
|---|---|---|
| Confirmados | 89 | leitura do texto completo (RQ2, RQ3 e os 6 com etiqueta RQ1 remapeados); 87 das bases e 2 de outros métodos |
| Em análise | 113 | passada 1, pelo título e resumo (RQ1 105, RQ4 8); 84 ainda sem PDF e 29 com PDF sem leitura; viram definitivos na passada 2 |

Dos 202, 23 têm Type = Survey (8 confirmadas, 15 em análise). Pelo protocolo são revisões de terceiros, related-SLRs, e não estudos primários; os primários são 81 confirmados e 98 em análise. No PRISMA 2020 final, os 113 precisam ter passado pela caixa "avaliados para elegibilidade" para contar como incluídos; a figura de hoje é um retrato intermediário e diz isso no próprio campo.

Por RQ: a RQ2 está fechada (23 incluídos, 21 excluídos). A RQ3 tem 67 incluídos, 41 excluídos e 22 pendentes (4 com PDF e pré-skim, 18 do grupo F). A RQ1 saiu da passada 1 com 105 aprovados, 137 excluídos e 1 sem decisão, e ainda não tem decisão de texto completo; os 6 incluídos com etiqueta RQ1 vieram de remapeamento na RQ2 e na RQ3. A RQ4 saiu da passada 1 com 8 aprovados e 20 excluídos.

## O que mudou desde 02/10

A passada 1 fechou: foram de 130 para 270 decisões, com 113 aprovados e 157 excluídos. Hoje eu procurei versão aberta dos 106 registros sem PDF que têm DOI (OpenAlex e Semantic Scholar, pelo seu MATLAB) e baixei mais 9 para `slr\artigos\`: Joo-4052, Junfeng-4633, Franciszek-063, M-857, U-276 (RQ3) e quatro pela versão arXiv do artigo publicado (Adam-3455, Xu-1336, Zhou-1274, Wang-1664). M-857 é de periódico russo: confira o idioma antes de ler.

As marcações que propus em 02/10 seguem como estavam: os aprovados da passada 1 estão como `Included` (coerente com a figura, que os mostra em análise) e os excluídos como `Excluded Full-Text`. Isso não bloqueia nada agora, porque o funil separa os dois grupos pela nota da pré-triagem. Precisa ser resolvido antes da extração, quando Included passa a significar incluído de fato. Apareceu um caso novo: Haiwen-851 está `Included` com EC1 preenchido.

## Passada 1 contra a pré-triagem (para o §8)

Dos 270 decididos: dos 56 EC1_CLARO do agente, você confirmou 46 e aprovou 10; dos 143 CANDIDATO, aprovou 84 e excluiu 59; das 69 DUVIDA decididas, aprovou 18 e excluiu 51; o EC2 do agente (Jacob-781) você aprovou e o EC4 (Seongsig-787) você excluiu. As exclusões do agente se sustentam (46 de 56); os candidatos foram lenientes (84 de 143), como a instrução pedia. Nenhum registro foi excluído pela IA: no PRISMA 2020 a caixa de exclusão por ferramenta de automação é zero, e a assistência entra na descrição do método.

## PDFs que faltam: 101

| Como obter | n | O que fazer |
|---|---|---|
| Conferir antes de baixar | 13 | 6 de periódicos nacionais (China, Coreia, Rússia, Ucrânia): se o texto não for em inglês ou português, é EC4 e não precisa baixar. 7 teses, Zenodo e blog: dez minutos no Scholar atrás da versão publicada; sem ela, EC3 |
| Aberto, no navegador | 13 | acesso aberto, mas o servidor recusa download por script (MDPI, ScienceDirect, T&F, IOP, preprints.org) ou o PDF está na página do DOI |
| CAFe | 74 | Springer 37, IEEE 27, ASME 4, ACM 2, CRC 2, De Gruyter 1, Elsevier 1; agrupados por editora para fazer em uma sessão cada |
| Sem DOI nem link | 1 | Onggo-2956: buscar pelo título |

Salve como `<Paper ID>.pdf` em `slr\artigos\`. Se não quiser renomear, jogue tudo em `slr\artigos\_entrada\` com o nome que vier: eu leio o DOI de cada PDF, renomeio e atualizo a lista.

## O que falta na SLR, na ordem

1. **PDFs:** 101, pela lista. Estimativa: 1,5 h para os 13 de conferir, 15 min para os 13 abertos, cerca de 3 h para os 74 do CAFe.
2. **Pré-skim por texto completo** (meu lado, com agentes): 34 já têm PDF; o resto à medida que os PDFs chegarem. No custo observado na RQ3, cerca de 34 mil tokens por estudo, uns 4,6 milhões para os 135. Só começo com o seu ok.
3. **Passada 2 (texto completo):** 113 aprovados na passada 1 e 22 pendentes da RQ3, mais Feng-1317 se você aprovar. No ritmo da RQ3 com nota pronta (11 min por registro), cerca de 25 h, sete tardes de 3,5 h.
4. **Decisões soltas:** Feng-1317 (passada 1), EC do Youndo-914, EC3 do asRoBallet, Haiwen-851 (Included com EC1), e a marcação de 02/10 (exclusões da passada 1 para Excluded Title/Abstract, Type Survey para Literature Review em 23 registros, Xia-2292 para Excluded Full-Text). Se você autorizar, eu faço as trocas em lote.
5. **EC3:** 13 aprovados com suspeita de preprint, tese ou texto não revisado (7 na lista de PDFs, 6 já na pasta: Ghandali-915, Tianwei-597, Ruopeng-455, Jiarong-057, Xuda-797, Marcel-289). Resolve-se na passada 2, buscando a versão publicada.
6. **Snowballing backward e forward** (§3 do protocolo) sobre os incluídos finais e as âncoras, depois da passada 2, com o mesmo pipeline (MATLAB, OpenAlex, pré-triagem por resumo, decisão sua). O volume só dá para estimar com o número de incluídos.
7. **Teste-reteste:** 45 registros às cegas e kappa de Cohen; cerca de 1 h; pendente desde 19/09.
8. **§8 do protocolo:** regras EC1 do skim, duas passadas, pré-skim e pré-triagem assistidos por IA com as concordâncias (RQ2 30 de 35, RQ3 65 de 71, passada 1 acima), as réguas da RQ3 e da RQ1, EC5 e EC6 aplicados, Web of Science não buscada, composição dos 3.071 removidos na ingestão, duas linhas vazias do log de busca.
9. **Sprint 3:** extração (formulário do §6) e DARE de todos os incluídos; hoje 0 de 89.
10. **Sprint 4:** as quatro tabelas do §7, síntese por RQ, PRISMA final no formato 2020, §8 e §9.
11. **Com a orientadora:** RQ4 (os 8 aprovados dependem disso), texto final das RQs e a data nova do M3.

Pelo seu lado, os itens 1, 3, 4 e 7 somam cerca de 31 h, perto de nove tardes de 3,5 h, antes do snowballing e da extração.

## Como refazer

`python deriva_contagens.py 2026-10-09` lê `sql_2026-10-09.json`, `p1_decididos_2026-10-09.json`, `pdfs_locais_2026-10-09.txt`, `rq3_grupoF_18.json`, a lista de PDFs e o CSV da pré-triagem, confere os fechamentos (inclusive `notion_included_total` = incluídos por texto completo + aprovados na passada 1 = 202) e grava `contagens_prisma_2026-10-09.json`. `python prisma_funil.py contagens_prisma_2026-10-09.json` gera a figura. O mesmo script refaz o funil de 02/10 com os arquivos daquela data. Para uma data nova, eu rodo as consultas no Notion e listo a pasta.
