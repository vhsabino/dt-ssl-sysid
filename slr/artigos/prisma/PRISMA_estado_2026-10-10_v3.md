# Funil PRISMA e PDFs faltantes: 10/10/2026, fim da tarde (atualização 3)

Arquivos desta rodada, em `slr\artigos\prisma\`: `pdfs_faltantes_2026-10-10_v3.html` (lista com a análise, contatos e modelo de e-mail) e `.csv`, `verificacao_downloads_2026-10-10_v3.csv`, `fig_funil_prisma_2026-10-10_v3.png` e `.pdf`, `contagens_prisma_2026-10-10_v3.json`. As listas e figuras anteriores foram mantidas.

## O que mudou desde a lista das 13h38

Conferido no banco do Notion às 15h57 UTC (uma consulta SQL agregada e uma em modo rows pelos 87 da lista) e na pasta `slr\artigos\` (260 PDFs).

- **Pasta:** 5 PDFs novos conferem com o registro (Riei-2446, Wang-1339, Liu-1421, Li-2282, Wilson-782). S-2045 foi substituído e agora é o artigo certo. Albatati-1285 foi substituído pelo preprint do Preprints.org ("Not peer-reviewed version"); a versão publicada é a da ACM. O arquivo J-828 virou Haiwen-851. Bentley-3518, Cludio-3751 e Giuseppe-3583 continuam só com a prévia de 2 páginas.
- **Notion:** Cijyun-5223 e Haiwen-851 passaram a Excluded Full-Text (EC1). Os outros 81 da lista seguem Included.

## Regra nova do funil

A passada 1 ficou congelada como fechou (113 aprovados, 158 excluídos; arquivo `p1_decididos_base.json`). Decisões posteriores sobre os 113 aprovados não voltam para a triagem: EC6 vai para "não recuperados" (Gershom-2485, Freederia-473) e as demais vão para "excluídos no texto completo" (Haiwen-851, com PDF; Cijyun-5223, Onggo-2956 e Taemin-896, sem PDF). A figura informa quantas exclusões foram decididas sem o PDF: 17, sendo 14 da RQ3 em 09/10 e 3 da passada 1. Prévias de 2 páginas não contam como texto completo (`pdfs_invalidos_2026-10-10_v3.txt`).

Correção da nota anterior: dos 16 EC1 da RQ3 decididos em 09/10, 12 não têm PDF, e não 14. Somando os 2 EC4, são 14 decididos sem o PDF.

## O funil agora

| Etapa | n | Observação |
|---|---|---|
| Identificação e triagem | 8.635 / 3.112 / 5.523 / 5.075 / 448 | sem mudança |
| Passada 1 | 113 aprovados, 158 excluídos (EC1 156, EC4 1, EC2 1) | congelada |
| Relatórios buscados | 290 | 177 da RQ2 e RQ3 + 113 da passada 1 |
| Não recuperados | 4 | EC6: 2 antigos + Gershom-2485 e Freederia-473 |
| Aguardando PDF | 18 | todos aprovados na passada 1, 3 deles só com a prévia |
| Com PDF e sem decisão | 89 | todos aprovados na passada 1 |
| Avaliados no texto completo | 179 | 91 incluídos das bases + 88 excluídos (EC1 73, EC3 5, EC2 4, EC4 4, EC5 2) |
| **Estudos incluídos** | **200 (107 em análise)** | 93 confirmados (85 primários e 8 revisões) + 107 aprovados na passada 1 (92 primários e 15 revisões) |

Por RQ (ocorrências): RQ1 106, RQ2 23, RQ3 71, RQ4 7.

## PDFs que faltam: 21

São os 18 aprovados da passada 1 aguardando PDF e os 3 incluídos da RQ3 sem PDF. A página HTML traz, para cada um, o motivo, a versão livre quando existe e o contato publicado em página oficial. É pré-julgamento: a decisão é sua.

- **Vale ir atrás, até pedir ao autor (5):** Noah-2410 (modelo de robô Mecanum omnidirecional validado no robô, o mais próximo da tese), Mateo-856 (robô holonômico com gêmeo e protótipo em escala), Chen-4265 e Zhenyao-4198 (já incluídos na RQ3), Charles-404 (construção de gêmeo com fidelidade medida, robô com pernas). Nenhum tem versão livre.
- **Rota fácil; se não sair, EC6 (7):** J-828 (IEEE, pelo CAFe), Flavien-822 (depósito no HAL), Zakaria-4587 (incluído na RQ3, mas é visão geral: pelo protocolo, Literature Review), Michele-4935 (arXiv; provável EC1), Nino-846 (prova de conceito sem métricas; provável EC2), Cludio-3751 e Bentley-3518 (capítulos de livro-texto, só a prévia na pasta).
- **Prováveis exclusões sem o PDF (9):** Jonathan-007 (EC5: versão anterior do Robert-002, que você tem), Schrage-2388 (EC4: a revista publica só em alemão), Alishba-4278 (EC3: livro técnico da Apress), Atul-650 (EC2: capítulo de 2 páginas sem método nem dados), Giuseppe-3583 (capítulo introdutório de livro-texto), Ayan-4763, Bo-3503, Tim-4861 e Robel-4076 (EC1 pelo resumo). Para os EC1 sem leitura, a alternativa é EC6 se o PDF não aparecer.
- **Candidato a snowballing:** o artigo irmão do Bentley-3518 em acesso aberto (Gil, Oakes, Gomes, Frasheri e Larsen, SIMULATION, 2025, doi 10.1177/00375497241261406), que descreve o Desktop Robotti, réplica de bancada de um robô móvel de campo.

## Como refazer

`python deriva_contagens.py 2026-10-10_v3` lê `sql_2026-10-10_v3.json`, `p1_decididos_base.json`, `p1_aprovados_estado_2026-10-10_v3.json`, `pdfs_locais_2026-10-10_v3.txt`, `pdfs_invalidos_2026-10-10_v3.txt`, `incluidos_tc_2026-10-10_v3.json` e a lista v3, confere os fechamentos e grava `contagens_prisma_2026-10-10_v3.json`. `python prisma_funil.py contagens_prisma_2026-10-10_v3.json` gera a figura. O mesmo script refaz os funis de 09/10 e de 10/10 pela manhã com os arquivos daquelas datas.
