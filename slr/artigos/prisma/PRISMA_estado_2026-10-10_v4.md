# Funil PRISMA, PDFs faltantes e fila da passada 2: 10/10/2026, noite (atualização 4)

Arquivos desta rodada, em `slr\artigos\prisma\`: `fila_passada2_2026-10-10.html` e `.csv` (os 89 com PDF, em ordem de leitura), `pdfs_faltantes_2026-10-10_v4.html` (com o e-mail pronto para os 5 que valem pedir ao autor) e `.csv`, `fig_funil_prisma_2026-10-10_v4.png` e `.pdf`, `contagens_prisma_2026-10-10_v4.json`. As listas e figuras anteriores foram mantidas.

## O que mudou desde a atualização 3 (15h57)

Conferido no banco do Notion na noite de 10/10 (uma consulta SQL agregada e uma em modo rows pelos 21 da lista v3) e na pasta `slr\artigos\` (260 PDFs, os mesmos da v3).

- **Notion:** as 9 prováveis exclusões sem o PDF passaram a Excluded Full-Text, com os EC sugeridos: Jonathan-007 (EC5), Schrage-2388 (EC4), Alishba-4278 (EC3), Atul-650 (EC2), Giuseppe-3583, Ayan-4763, Bo-3503, Tim-4861 e Robel-4076 (EC1).
- **Pasta:** nenhum PDF novo.
- **Figura:** a nota dos decididos sem o PDF passa a 26 (14 da RQ3 em 09/10 e 12 da passada 1). Prévias de 2 páginas contam como sem PDF também nessa nota (Giuseppe-3583).

## O funil agora

| Etapa | n | Observação |
|---|---|---|
| Identificação e triagem | 8.635 / 3.112 / 5.523 / 5.075 / 448 | sem mudança |
| Passada 1 | 113 aprovados, 158 excluídos (EC1 156, EC4 1, EC2 1) | congelada |
| Relatórios buscados | 290 | 177 da RQ2 e RQ3 + 113 da passada 1 |
| Não recuperados | 4 | EC6: 2 antigos + Gershom-2485 e Freederia-473 |
| Aguardando PDF | 9 | todos aprovados na passada 1 |
| Com PDF e sem decisão | 89 | todos aprovados na passada 1: é a fila da passada 2 |
| Avaliados no texto completo | 188 | 91 incluídos das bases + 97 excluídos (EC1 78, EC3 6, EC2 5, EC4 5, EC5 3) |
| **Estudos incluídos** | **191 (98 em análise)** | 93 confirmados (85 primários e 8 revisões) + 98 aprovados na passada 1 (84 primários e 14 revisões) |

Por RQ (ocorrências): RQ1 98, RQ2 23, RQ3 71, RQ4 6.

## PDFs que faltam: 12

- **Vale ir atrás, até pedir ao autor (5):** Noah-2410, Mateo-856, Chen-4265, Zhenyao-4198 e Charles-404. A página traz, para cada um, o e-mail em inglês já preenchido (destinatário, assunto e texto), com um botão que abre o seu programa de e-mail. Falta só trocar `[Your full name]`.
- **Rota fácil; se não sair, EC6 (7):** J-828, Flavien-822, Zakaria-4587, Michele-4935, Nino-846, Cludio-3751 e Bentley-3518.

## Fila da passada 2: 89 registros, cerca de 15 h

Pré-julgamento para ordenar a leitura; a decisão é sua, registro por registro. Os sinais vêm do texto das três primeiras páginas de cada PDF.

| Grupo | n | min | O que é |
|---|---|---|---|
| 1. Decisão rápida | 11 | 5 | Idioma: Lin-2372 (chinês), Maksim-1096, T-338 e M-857 (russo), Stepani-2511 (dissertação em esloveno). Teses e dissertações: Jaqueline-3731, Hamidreza-031, Allamaa-2507. Formato: Ghandali-915 (resumo de 1 página), Satyam-886 (3 páginas no Zenodo), Hannes-919 (post de blog impresso). |
| 2. Preprint do arXiv | 6 | 10 | Xuda-797, Marcel-289, Jiarong-057, Ruopeng-455, Tianwei-597, Ziyang-467: conferir a versão publicada antes de ler. |
| 3. Núcleo da RQ1 | 33 | 15 | Robô móvel com modelo ou DT e dado real, mais os omnidirecionais e do SSL, que vêm primeiro (Mostafa-4396, Marvin-1071, Muhammad-3393, V-1914, Marvin-250, Hongjiu-749, Mahmoud-752, Shang-2393...). |
| 4. Revisões de terceiros | 19 | 5 | Régua 2 do guia: com robótica no escopo, Type = Survey; DT sem robótica, EC1. |
| 5. Demais candidatos | 15 | 10 | |
| 6. Dúvidas e EC1 da pré-triagem que você aprovou | 5 | 8 | |

Gustavo-995 está em português, o que o IC4 aceita. Seis registros do grupo 3 a 6 têm como PDF a versão arXiv de um trabalho publicado (o DOI do registro é o da versão publicada); servem para a leitura.

Marcação: `SKIM dd/mm: INCLUI | RQ1 | frase` ou `SKIM dd/mm: ECx | razão` antes da nota do agente. O prefixo é o que permite ao próximo funil separar os confirmados no texto completo dos que seguem em análise.

## Como refazer

`python deriva_contagens.py 2026-10-10_v4` lê `sql_2026-10-10_v4.json`, `p1_decididos_base.json`, `p1_aprovados_estado_2026-10-10_v4.json`, `pdfs_locais_2026-10-10_v4.txt`, `pdfs_invalidos_2026-10-10_v4.txt`, `incluidos_tc_2026-10-10_v4.json` e a lista v4, confere os fechamentos e grava `contagens_prisma_2026-10-10_v4.json`. `python prisma_funil.py contagens_prisma_2026-10-10_v4.json` gera a figura. Os mesmos scripts refazem os funis de 09/10, de 10/10 pela manhã e da v3.
