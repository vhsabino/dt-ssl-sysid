# Pré-skim assistido da RQ2: 42 estudos, notas gravadas no Notion em 14/09/2026

## O que foi feito

Os 42 PDFs da fila de RQ2 foram lidos por seis agentes em paralelo, um lote de sete cada, com as mesmas instruções (`INSTRUCOES_AGENTE_preskim.md`, nesta pasta), calibradas pelas suas duas notas manuais de 13/09 (Victor-4055 e Victor-849) usadas como exemplos. Cada agente devolveu, por estudo, um pré-veredito, a nota no seu formato, os números citados, um trecho de evidência literal e um alerta do que só o PDF resolve.

O campo Notes de cada um dos 42 registros foi atualizado com a nota, prefixada por `PRE-SKIM IA 14/09:` para você distinguir do seu próprio skim. **Nada além de Notes foi tocado**: Selection Stage continua `Identified`, Status continua `Recommended Full Read`, Exclusion Criterion segue vazio e RQ Mapping intacto. A decisão continua sendo sua, registro por registro. As duas notas `SKIM 13/09` que você escreveu não foram alteradas.

## Pré-vereditos (sugestão, não decisão)

| Pré-veredito | n | O que significa |
|---|---|---|
| INCLUI | 11 | mede fidelidade físico vs virtual com número e protocolo descrito |
| DUVIDA | 7 | falta peer review, escopo discutível, ou o texto extraído não bastou |
| EC3 | 2 | preprint sem versão publicada aparente |
| EC2 | 1 | sem avaliação empírica de fidelidade |
| EC1 | 21 | sem contraparte física medida, ou controle puro, ou domínio fora |

Se esse padrão se confirmar na sua leitura, a RQ2 termina com algo entre 11 e 20 incluídos, e o gatilho do plano de execução (menos de 15 incluídos na RQ2 aciona a string S6 dedicada mais snowballing) fica no limite. Vale acompanhar já na segunda-feira.

## Os sete estudos que valem seu tempo primeiro

Ordem sugerida para a segunda-feira, começando pelo mais próximo da tese:

1. **SLR-2025-Laura-024**, DT Mecanum em ROS-Gazebo. É o método mais próximo do seu no lote inteiro: identificação grey-box por motor (fit de 90 a 92 %) mais ARX MIMO para o corpo, 154 trajetórias, validação cruzada K-fold repetida, e compara o DT contra simulação pura. Candidato natural a baseline da RQ2.
2. **SLR-2025-Lukas-293**, RB-Kairos no Isaac Sim contra OptiTrack. Multi-métrica (RMSE, distância de Hausdorff, erro de meta), 5 cenários, 10 repetições, bootstrapping para intervalo de confiança. É o protocolo mais rigoroso do lote e serve direto como evidência para a nota D6 (Isaac Sim medido, não competindo com o seu harness).
3. **SLR-2024-Koji-3890**, pá-carregadeira em terreno deformável. Sim-to-real gap médio de 10 % com MAE normalizado e DTW, três operações reais replicadas em oito simuladores de fidelidade decrescente. O desenho é quase o do seu C2b; a pergunta é de escopo, máquina pesada conta como robô móvel na sua PICOC.
4. **SLR-2023-Shuang-030**, Ranger Mini. Erro de trajetória máximo e médio simulação vs real em três percursos, com identificação de inércia por mínimos quadrados.
5. **SLR-2026-Hongjiu-952** e **SLR-2024-Hongjiu-762**, do mesmo grupo. RMSE de erro síncrono virtual menos físico (0,061 m no de 2024); protocolo fraco, n igual a 1, mas a métrica é exatamente a sua.
6. **SLR-2020-A-1974**, Sim2Real Predictivity. Mede fidelidade por correlação de desempenho (SRCC), não por erro geométrico. É o contraponto conceitual mais interessante do lote para a sua discussão de o que conta como fidelidade.

## Cinco coisas que precisam de você e o agente não resolve

1. **SLR-2023-Grazioso-2365 tem o PDF errado na pasta.** O arquivo é o capítulo IFToMM Italy 2022 (doi 10.1007/978-3-031-10776-4_17), e o banco aponta para Robotica 2023 (doi 10.1017/S0263574723000966). O capítulo compara duas simulações entre si e diz que replicar dados do protótipo real é trabalho futuro; o artigo do banco promete validação. Baixar o correto por CAFe antes de julgar.
2. **Sete estudos podem cair em EC3.** Zhuo-2413 (SSRN, o texto declara que não passou por revisão), Ziqi-3365 e Anil-3371 (arXiv, DOI placeholder), Nazish-899 (arXiv), Sunny-046 (capítulo em arXiv), Lionti-2478 (tese) e Cristina-2495 (trabalho de graduação). Uma busca de dez minutos por versão publicada resolve cada um, e dois deles (Nazish e Sunny) teriam relevância alta se publicados.
3. **SLR-2020-Sangyoon-2395 é fronteira.** O agente marcou INCLUI pelo erro de 2 % na identificação do motor; eu discordo em parte, porque a contribuição do artigo é controle por modo deslizante e o resto do paper cai na regra 2. Registrei a divergência na própria nota. Sua régua decide.
4. **SLR-2021-Wouter-2391 idem.** Conferi o texto completo por busca: a Fig. 4 compara a FRF medida com a resposta esperada do modelo em diagrama de Bode, qualitativamente, sem métrica de erro. Se você contar FRF como identificação, vira RQ1; senão é EC1 pela regra 2.
5. **Doze estudos tiveram o texto cortado por tamanho** (marcados como `texto_parcial` no CSV): Cristina-2495, Lionti-2478, Zhuo-2413, Gerasimos-2411, Leonardo-2414, P-741, Valentina-3460, Wouter-2391, Koji-3890, Renjun-764, Minan-4060 e Mirosaw-4072. Nesses, o pré-veredito vale menos; os quatro primeiros são os que mais perderam conteúdo.

## Limites conhecidos deste pré-julgamento

O agente lê só o texto extraído por `pdftotext`: **tabelas e figuras se perdem**. Por isso quase toda nota traz um alerta do tipo "conferir a Tabela V no PDF". Onze estudos têm números de fidelidade que existem no artigo mas não no texto extraído. Tratar o pré-veredito como uma hipótese bem informada, não como triagem feita.

Rodei uma verificação automática: todo número que aparece nas notas foi procurado no texto de origem. Dezessete notas tiveram algum aviso, quase todos de formatação (grau, porcentagem colada, expoente corrompido pela extração). Nenhum número inventado foi encontrado, mas a verificação é por correspondência de texto, não semântica.

## Repetir nos outros lotes

O procedimento está em `INSTRUCOES_AGENTE_preskim.md`. Para a RQ3 (130 estudos, 112 PDFs em mãos) muda só a definição da pergunta e a árvore de decisão; a estrutura de saída, a verificação de números e a escrita no Notion são as mesmas. Custo observado: cerca de 250 mil tokens por agente de sete artigos, ou seja, uns 36 mil por estudo, e nada disso passa pelo contexto da nossa conversa. Para a RQ3 seriam cerca de 19 agentes.

## Arquivos

- `preskim_rq2_2026-09-14.csv`: as 42 linhas com pré-veredito, confiança, robô físico sim ou não, medição físico-virtual, RQ sugerida, tipo, se o texto foi cortado, a nota, o alerta, o trecho de evidência e o link da página no Notion. É por aqui que você acompanha enquanto lê.
- `INSTRUCOES_AGENTE_preskim.md`: as instruções dadas aos agentes, para reusar nos lotes seguintes.
