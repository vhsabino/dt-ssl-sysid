# Funil PRISMA da SLR 2026: estado em 02/10/2026

Figura: `fig_funil_prisma_2026-10-02.png` (e `.pdf` para o LaTeX), no mesmo estilo da figura de 11/09 (`reuniao_2026-09-11\fig1_funil_prisma.png`, que fica como está). Os números vêm de duas consultas ao banco do Notion feitas hoje e do log de busca do protocolo (§3). O script `deriva_contagens.py` refaz as contas e confere que cada caixa fecha com a anterior: os 5.565 registros do banco estão todos em alguma caixa, sem sobra.

## O funil hoje

| Etapa | n | Como foi contado |
|---|---|---|
| Identificados nas bases | 8.635 | log de busca do protocolo: 7 fontes × S1 a S5, buscas de 11 e 12/07 |
| Removidos antes da triagem | 3.112 | 3.071 na ingestão (log menos banco), 40 duplicatas por título (EC5), 1 registro vazio |
| Triados por título e resumo (rodada 1) | 5.523 | registros vindos das bases, menos os 40 EC5 |
| Excluídos na rodada 1 | 5.075 | EC1 5.068 (inclui 607 front-matter em lote), EC4 4, EC2 2, 1 sem critério (Youndo-914) |
| Aprovados na rodada 1 | 448 | 177 da RQ2 e RQ3 seguem ao texto completo; 271 da RQ1 e RQ4 passam pela passada 1 |
| Excluídos na passada 1, por resumo | 72 | EC1 71, EC4 1 |
| Pendentes na passada 1 | 141 | RQ1 113 (grupos C 55, D 48, E 10) e RQ4 28 |
| Relatórios buscados | 235 | 177 da RQ2 e RQ3 e 58 aprovados na passada 1 |
| Não recuperados | 2 | EC6 |
| Aguardando PDF | 65 | 18 da RQ3 (grupo F) e 47 aprovados na passada 1 |
| Com PDF e sem decisão | 15 | 4 da RQ3 e 11 aprovados na passada 1 |
| Avaliados no texto completo | 153 | 87 incluídos e 66 excluídos |
| Excluídos no texto completo | 66 | EC1 54, EC3 5, EC2 4, EC5 2, EC4 1 |
| Outros métodos | 2 | DROPO (snowballing backward, 12/07) e asRoBallet (entrada manual, 02/09), ambos incluídos |
| **Estudos incluídos** | **89** | 87 das bases e 2 de outros métodos; 8 são revisões de terceiros, então 81 estudos primários |

Por RQ: a RQ2 está fechada com 23 incluídos e 21 excluídos; a RQ3 tem 67 incluídos, 41 excluídos e 22 pendentes (4 com PDF, 18 sem); a RQ1 e a RQ4 estão na passada 1, e os 6 incluídos com etiqueta RQ1 vieram de remapeamento na RQ2 e na RQ3. Extração (§6) e DARE: 0 de 89.

## O que mudou desde o funil de 11/09

A identificação agora parte do log de busca (8.635 registros brutos) e não do total do banco, e as duplicatas saem antes da triagem, como o PRISMA 2020 pede. O "+1 registro" que estava em aberto em 11/09 é o asRoBallet (EXT-2026-Omniwheel-Mujoco), entrada manual de 02/09: a pendência está encerrada. Entraram a passada 1 (segunda rodada por resumo, só da RQ1 e da RQ4) e a separação entre buscados, recuperados e avaliados. Os incluídos passaram de 2 para 89.

## Cinco decisões suas antes de continuar (mudam a contagem)

1. **Os 58 aprovados na passada 1 estão como `Included`.** O protocolo (§4, convenção de 12/07) diz que Included é final e só vem depois do texto completo. 47 deles não têm PDF na pasta, e as suas duas anotações (Josifovska-1119, "quero ver como é definido um framework para digital twins"; Maksim-1096, "talvez indisponível") mostram que é aprovação para leitura, não inclusão. Por isso a figura os conta em "buscados". Proposta: voltar os 58 para `Identified` (filtro: RQ Mapping contém RQ1, Selection Stage = Included, Notes contém "PRE-TRIAGEM IA 27/09"; seleciona tudo e troca de uma vez) e eu acrescento `P1: aprovado` no início das Notes.
2. **Os 72 excluídos na passada 1 foram decididos por resumo, mas 70 estão como `Excluded Full-Text`.** Foi erro do meu guia v2, que manteve essa etapa depois de tirar o PDF da passada 1. Proposta: trocar os 70 para `Excluded Title/Abstract` (só Ghayth-5191 e Kuhl-2958 já estão assim). Daí em diante a regra fica simples e o banco se explica sozinho: a passada 1 exclui em Title/Abstract e aprova deixando Identified; só a passada 2 usa Included e Excluded Full-Text.
3. **Revisões de terceiros.** 11 registros estão com `Type = Survey` (8 incluídos e 3 aprovados na passada 1). O protocolo manda `Literature Review` e as trata como related-SLRs, fora da síntese primária. Também foi erro meu, no guia da RQ3. Proposta: trocar para Literature Review; no PRISMA elas aparecem em linha separada.
4. **asRoBallet (EXT) é preprint arXiv e está `Included`.** Pelo EC3 só entraria com versão publicada. Ou EC3 (segue citado na tese como referência da plataforma, fora do funil), ou fica com justificativa no §8.
5. **SLR-2021-Xia-2292 (RQ3)** está `Excluded Title/Abstract`, mas foi decidido no texto completo: trocar para `Excluded Full-Text`. E falta o EC do Youndo-914, sem critério desde julho.

Pela regra em vigor eu só escrevo em Notes. Se você autorizar, faço as trocas de Selection Stage e Type em lote e confiro por consulta agregada.

## O que falta para fechar o funil, na ordem

1. **Passada 1:** 141 registros (RQ1 113 nos grupos C, D e E; RQ4 28). Pelo orçamento do guia (3 min nos grupos C e D, 2 min no E), cerca de 6,5 h, duas tardes.
2. **PDFs:** 65 hoje. Dos 47 da passada 1, 11 abrem no navegador, 28 vão pelo CAFe e 8 não têm URL conhecida; somam-se os que a passada 1 ainda aprovar. Os 18 da RQ3 (grupo F) ficam para o fim, como você decidiu. EC6 pela regra dos dez minutos.
3. **Passada 2 (texto completo) da RQ1 e RQ4:** 58 hoje mais os aprovados dos 141. Na taxa de aprovação observada até agora (58 de 130), estimo 115 a 125 registros, perto de 22 h no ritmo da RQ3 (11 min por registro). Antes dela, o pré-skim por texto completo dos que tiverem PDF.
4. **Decisões pendentes no texto completo:** 4 da RQ3 (Jiahe-141, Viktor-092, Y-1807, Mohamed-414).
5. **Snowballing backward e forward** (§3 do protocolo) sobre os incluídos e as âncoras (Machado 2024, DROPO, rSoccer, Purwin e D'Andrea 2006), depois da passada 2. Os registros novos entram com Source `Snowballing` e Search String `Snowball-B` ou `Snowball-F`, e aparecem na coluna de outros métodos.
6. **Para o PRISMA e o §8:** teste-reteste da triagem (kappa); registrar que a Web of Science, complementar no protocolo, não foi buscada; conferir no log de ingestão a composição dos 3.071 removidos (DOI ou outro motivo); completar o log de busca (há duas linhas vazias no fim da tabela do §3).
7. **Depois do funil:** extração (§6) e DARE, hoje 0 de 89, e a figura final no formato PRISMA 2020.

## Passada 1 contra a pré-triagem (para o §8)

Dos 130 registros decididos: dos 48 EC1_CLARO do agente, você confirmou 41 e aprovou 7; dos 80 CANDIDATO, aprovou 50 e excluiu 30 (28 deles no grupo B, de confiança alta); o EC2 do agente (Jacob-781) você aprovou e o EC4 (Seongsig-787) você excluiu. As exclusões do agente se sustentam (41 de 48); os candidatos são lenientes (50 de 80), como a instrução pedia ("na dúvida, candidato"). Nenhum registro foi excluído pela IA: no PRISMA 2020, a caixa "marcados como inelegíveis por ferramentas de automação" é zero, e a assistência entra na descrição do método.

## Como refazer

`python deriva_contagens.py` lê `sql_2026-10-02.json`, `p1_decididos.json`, `pdfs_locais_2026-10-02.txt` e o CSV da pré-triagem, confere os fechamentos e grava `contagens_prisma_2026-10-02.json`. `python prisma_funil.py contagens_prisma_2026-10-02.json` gera a figura. Para uma data nova eu rodo as duas consultas no Notion, gero o JSON e a figura sai no mesmo formato.
