# Lista de PDFs e funil PRISMA: 10/10/2026

Atualização depois das decisões que você gravou no Notion em 09/10 à noite. Arquivos desta rodada, todos em `slr\artigos\prisma\`: `pdfs_faltantes_2026-10-10.csv` e `.html` (lista com links), `fig_funil_prisma_2026-10-10.png` e `.pdf`, `contagens_prisma_2026-10-10.json`. A nota de 09/10 continua valendo para o que não mudou (passada 1 contra pré-triagem, estimativas, ordem do que falta).

## O que mudou no banco desde 09/10

Conferido por consulta ao Notion em 10/10 (uma consulta SQL agregada e cinco em modo rows) e pela listagem da pasta `slr\artigos\` (196 PDFs; nenhum novo desde 09/10, só Jiahe-141 foi salvo de novo).

- Os 23 registros que estavam sem decisão foram decididos, nenhum Identified sobrou:
  - Feng-1317 (passada 1): Excluded Full-Text, EC2. A passada 1 fechou: 113 aprovados, 158 excluídos.
  - RQ3, os 22 pendentes: 4 incluídos (Jiahe-141, Zakaria-4587, Chen-4265, Zhenyao-4198), 16 EC1 (Nguyen-5290, Miao-4755, Yunfeng-4680, Mengyuan-4264, Philippe-4238, Jhonattan-485, Qi-436, Arkapravo-420, Anhtu-408, U-276, Diego-264, T-259, Saleh-234, Y-1807, Mohamed-414, Viktor-092) e 2 EC4 (Kim-2321, Miao-2272).
- Haiwen-851 segue Included com EC1 preenchido; Youndo-914 segue sem critério; Cite marcado em 1 registro.

Um ponto para você decidir: 14 dos 16 excluídos da RQ3 por EC1 e os 2 por EC4 não têm PDF na pasta. Como estão marcados Excluded Full-Text, a figura os conta na caixa "Excluídos no texto completo" (84). Se a decisão foi pelo resumo ou pela página do artigo, eles pertencem à triagem, não à elegibilidade; me diga e eu movo os 16 para a caixa de triagem na próxima versão.

## Funil em 10/10

| Etapa | n | Observação |
|---|---|---|
| Identificados, removidos, triados, excluídos na rodada 1, aprovados | 8.635 / 3.112 / 5.523 / 5.075 / 448 | sem mudança |
| Passada 1 | 113 aprovados, 158 excluídos (EC1 156, EC4 1, EC2 1) | fechada |
| Relatórios buscados | 290 | 177 da RQ2 e RQ3 + 113 da passada 1 |
| Não recuperados | 2 | EC6 |
| Aguardando PDF | 84 | todos da passada 1 |
| Com PDF e sem decisão | 29 | todos da passada 1 |
| Avaliados no texto completo | 175 | 91 incluídos das bases + 84 excluídos (EC1 70, EC3 5, EC2 4, EC4 3, EC5 2) |
| **Estudos incluídos** | **206 (113 em análise)** | 93 confirmados (91 das bases + 2 de outros métodos; 85 primários e 8 revisões) + 113 em análise (98 primários e 15 revisões) |

Por RQ (ocorrências): RQ1 111, RQ2 23, RQ3 71, RQ4 8. A RQ2 e a RQ3 estão fechadas; a RQ1 e a RQ4 esperam a passada 2.

## PDFs que faltam: 87

Saíram da lista os 14 do grupo F da RQ3 que você excluiu sem PDF. Entraram, à parte, os 3 que você incluiu na RQ3 sem ter o PDF na pasta (Zakaria-4587, Chen-4265, Zhenyao-4198, todos Springer, pelo CAFe): não entram em "aguardando PDF" porque já estão decididos, mas precisam do arquivo para a extração. A busca de versão aberta (OpenAlex e Semantic Scholar) é a de 09/10; não repeti.

| Como obter | n | O que fazer |
|---|---|---|
| Conferir antes de baixar | 11 | 4 de periódicos nacionais (Lin-2372, Maksim-1096, Taemin-896, Nazarenko-501): se o texto não for em inglês ou português, é EC4. 7 teses, Zenodo e blog (Allamaa-2507, Stepani-2511, Gershom-2485, Hannes-919, Freederia-473, Satyam-886, Hamidreza-031): sem versão publicada, EC3 |
| Aberto, no navegador | 13 | 6 em que o servidor recusa script e 7 com o PDF na página do DOI |
| CAFe | 62 | Springer 29 (3 deles são os incluídos da RQ3), IEEE 26, ACM 2, ASME 2, CRC 1, De Gruyter 1, Elsevier 1 |
| Sem DOI nem link | 1 | Onggo-2956: buscar pelo título |

Salve como `<Paper ID>.pdf` em `slr\artigos\`, ou jogue tudo em `slr\artigos\_entrada\` com o nome que vier, que eu renomeio pelo DOI. Estimativa: cerca de 4 h (1 h para os 11 de conferir, 15 min para os 13 abertos, 2,5 h para os 62 do CAFe).

## O que falta, resumido

1. PDFs: 87, pela lista.
2. Passada 2 (texto completo): 113 aprovados na passada 1, 29 já com PDF. Pré-skim por texto completo só com o seu ok (cerca de 34 mil tokens por estudo).
3. Decisões soltas: EC do Youndo-914, EC3 do asRoBallet, Haiwen-851 (Included com EC1), Type Survey para Literature Review nos 23, os 16 da RQ3 acima (triagem ou elegibilidade), e a marcação dos excluídos da passada 1 (estão como Excluded Full-Text).
4. EC3: 13 aprovados com suspeita de preprint, tese ou não revisado (7 na lista de PDFs, 6 já na pasta).
5. Snowballing backward e forward, teste-reteste, §8, Sprint 3 (extração e DARE, 0 de 206) e Sprint 4, como na nota de 09/10.
6. Com a orientadora: RQ4, texto final das RQs e data do M3.

## Como refazer

`python deriva_contagens.py 2026-10-10` (lê `sql_2026-10-10.json`, `p1_decididos_2026-10-10.json`, `pdfs_locais_2026-10-10.txt`, `incluidos_tc_2026-10-10.json` e a lista de PDFs; sem arquivo de grupo F porque não há mais Identified) e `python prisma_funil.py contagens_prisma_2026-10-10.json`. A lista sai de `gera_lista_pdfs_10.py` e `gera_html_pdfs_10.py`; `monta_sql_10.py` documenta a consulta agregada transcrita e confere os fechamentos (5.565 em cada corte).
