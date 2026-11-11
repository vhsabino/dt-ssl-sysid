# Funil PRISMA: 23/10/2026, versão para apresentação

Arquivos desta rodada, em `slr\artigos\prisma\`: `fig_funil_prisma_2026-10-23.png` e `.pdf` (uma lâmina, 3:2, versão limpa), `fig_funil_prisma_2026-10-23_detalhado.png` e `.pdf` (acompanhamento, com pendências), `contagens_prisma_2026-10-23.json`, `sql_2026-10-23.json`, `p1_aprovados_estado_2026-10-23.json`, `incluidos_tc_2026-10-23.json`, `pdfs_locais_2026-10-23.txt`, `pdfs_invalidos_2026-10-23.txt`, `pdfs_faltantes_2026-10-23.csv` (igual à v4), `deriva_contagens.py`, `prisma_funil_apresentacao.py`, `prisma_funil.py`, `monta_v5.py`.

## O que mudou na figura

- O fluxo fecha de cima para baixo. A caixa de elegibilidade passou a ser "Relatórios de texto completo, n = 286" (os 290 buscados menos os 4 não recuperados), dividida em avaliados (196) e em avaliação (90). Os avaliados menos os 104 excluídos dão os 92 incluídos das bases, que com os 2 de outros métodos são os 94 da caixa de incluídos. Os 90 em avaliação aparecem na caixa de elegibilidade e, como lembrete, numa linha da caixa de incluídos; a soma 94 + 90 = 184 é o Included do Notion, dita só no rodapé.
- Saíram a caixa "O que falta para fechar o funil", as notas de rodapé das caixas, as listas de IDs e os avisos em laranja. Cada caixa tem título, n e no máximo duas linhas.
- A linha do teste-reteste entrou na caixa da triagem (concordância 84%, kappa 0,68), lida de `..\reteste\resultado_reteste_2026-10-11.json`.
- A versão detalhada continua disponível (`prisma_funil.py`, agora gravando `_detalhado`), com o mesmo fechamento novo.

## O que mudou no banco desde 10/10

Conferido no Notion em 23/10 (uma consulta SQL agregada e uma em modo rows) e na pasta (260 PDFs, os mesmos).

- Passada 2 começou: Mostafa-4396 foi confirmado com `SKIM 11/10: INCLUI | RQ1` (Status Read in Progress, Quality Score preenchido). É o primeiro registro que sai de "em análise" para "incluído" pelo prefixo SKIM; o script passou a tratar isso.
- Sete aprovados da passada 1 foram excluídos no texto completo: Ghandali-915 e Satyam-886 (EC3), Stepani-2511, Lin-2372, Maksim-1096, M-857 e T-338 (EC4). Nenhum deles estava na lista de PDFs faltantes, que continua com 12.
- Nenhum PDF novo.

## O funil agora

| Etapa | n |
|---|---|
| Identificados / removidos antes da triagem / triados / excluídos / aprovados | 8.635 / 3.112 / 5.523 / 5.075 / 448 |
| Passada 1 (RQ1 e RQ4, por resumo) | 271 → 113 aprovados, 158 excluídos |
| Buscados para o texto completo | 290 (177 + 113) |
| Não recuperados (EC6) | 4 |
| Texto completo | 286 = 196 avaliados + 90 em avaliação (81 com PDF, 9 aguardando PDF) |
| Excluídos no texto completo | 104 (EC1 78, EC4 10, EC3 8, EC2 5, EC5 3) |
| **Estudos incluídos** | **94** = 92 das bases + 2 de outros métodos; 86 primários e 8 revisões; RQ1 7, RQ2 23, RQ3 71 |
| Em avaliação (passada 2) | 90 (RQ1 84, RQ4 6; 14 revisões) |

No Notion: Included = 184 = 94 + 90.

## Como refazer

`python deriva_contagens.py 2026-10-23` e `python prisma_funil_apresentacao.py contagens_prisma_2026-10-23.json` (lâmina) ou `python prisma_funil.py contagens_prisma_2026-10-23.json` (detalhado). O `deriva_contagens.py` continua reproduzindo 10/10 (v3 e v4). Para o próximo funil: basta repetir a consulta SQL (coluna `skim` = Notes iniciando em "SKIM ") e atualizar `p1_aprovados_estado_<data>.json` com as decisões novas; incluídos confirmados recebem `"skim": "dd/mm"`.
