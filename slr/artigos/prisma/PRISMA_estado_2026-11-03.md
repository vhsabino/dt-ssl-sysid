# Funil PRISMA: 03/11/2026

Conferido no banco do Notion em 03/11 (consulta SQL agregada, idêntica linha a linha à de 23/10) e na pasta `slr\artigos\` (260 PDFs, os mesmos): nenhuma mudança desde 23/10. A figura `fig_funil_prisma_2026-11-03.png` repete os números da atualização de 23/10 com a data nova; `contagens_prisma_2026-11-03.json` é idêntico em valores ao de 23/10.

Números: 8.635 identificados, 3.112 removidos antes da triagem, 5.523 triados, 5.075 excluídos, 448 aprovados; passada 1 com 113 aprovados e 158 excluídos; 290 buscados, 4 não recuperados, 286 de texto completo (196 avaliados, 90 em avaliação: 81 com PDF e 9 aguardando PDF), 104 excluídos no texto completo, 94 incluídos (92 das bases e 2 de outros métodos). Passada 2: 8 de 89 decididos (Mostafa-4396 incluído; 7 excluídos).

Documentos novos em `slr\`: `metodologia_slr_prisma_2026-11-03.md` (a metodologia inteira, para apresentar a outros alunos) e `cronograma_slr_2026-11-03.md` (cronograma revisado para a orientadora, com `artigos\prisma\fig_cronograma_slr_2026-11-03.png`, gerada por `fig_cronograma.py`).

Para refazer: `python deriva_contagens.py 2026-11-03`, `python prisma_funil_apresentacao.py contagens_prisma_2026-11-03.json`, `python prisma_funil.py contagens_prisma_2026-11-03.json`.
