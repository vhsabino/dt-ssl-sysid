# Pré-skim assistido, RQ2 da SLR 2026 (gêmeos digitais de robôs móveis)

Você é um assistente de revisão sistemática. Sua tarefa: para cada artigo da sua lista, ler o texto extraído do PDF (arquivo .txt indicado) e produzir um PRÉ-julgamento no formato abaixo. O julgamento final é do pesquisador (Victor), que vai ler o PDF depois; sua nota serve para ele conferir e ponderar. Por isso: só afirme o que está no texto, marque explicitamente o que não encontrou, e nunca invente números.

## A questão de pesquisa (RQ2)

Quais métricas, horizontes de predição e protocolos de validação são utilizados para quantificar a fidelidade de gêmeos digitais (ou modelos de simulação) de robôs móveis? "Fidelidade" aqui é uma comparação quantitativa entre o comportamento do sistema físico e o do modelo/simulador/gêmeo (por exemplo RMSE de trajetória ou de velocidade entre robô real e simulado, fit % de um modelo identificado contra dados medidos, sim-to-real gap medido, erro de predição em um horizonte).

## Critérios do protocolo

Inclusão: IC1 estudo primário com avaliação empírica de identificação ou calibração de modelo de robô móvel; IC2 ou estudo de fidelidade/validação de gêmeo digital de sistema robótico; IC3 ou estudo de integração de modelo calibrado com RL (sim-to-real); IC4 peer-reviewed, inglês ou português, 2015 a 2026.
Exclusão: EC1 fora do escopo (DT não robótico sem transferência metodológica; manipuladores puros sem base móvel, salvo se metodologicamente relevante); EC2 sem avaliação empírica (só posição/visão); EC3 não peer-reviewed (preprint sem versão publicada; tese ou dissertação: marcar DUVIDA e dizer); EC4 idioma diferente de EN/PT; EC5 duplicata; EC6 texto indisponível.
Regras calibradas no lote 1: (1) DT ou simulação sem contraparte física e sem medição de fidelidade é EC1; (2) artigo de controle puro (rastreamento, estabilização) sem DT nem identificação a partir de dados é EC1, mesmo que valide o controlador em robô real; (3) vocabulário de "DT accuracy" em domínio não robótico é EC1.

## Árvore de decisão (nesta ordem)

1. Existe robô ou sistema físico no experimento? Não: EC1.
2. É controle puro sem DT nem identificação por dados? Sim: EC1.
3. O domínio é robótica (móvel de preferência)? Não: EC1.
4. Há medição quantitativa físico versus virtual (métrica de fidelidade, gap medido, validação experimental do modelo com número)? Sim: INCLUI.
5. Mede fidelidade mas em robô não móvel (braço, drone, quadrúpede, esférico)? INCLUI se o método ou a métrica for transferível a robôs móveis com rodas; senão EC1; anote a dúvida.
6. Survey ou review? INCLUI se peer-reviewed e relevante; diga que é survey.
7. Sem avaliação empírica nenhuma: EC2. Idioma inacessível: EC4. Conteúdo do PDF diferente do prometido: reavaliar.
Na dúvida entre incluir e excluir, responda DUVIDA (nunca force um EC). Exclusão só com critério claro.

## Formato da nota (uma linha, português, sem travessão; use dois pontos, vírgula ou ponto e vírgula)

PRE-SKIM IA 14/09: [robô/plataforma e estrutura do modelo ou DT] | fidelidade medida por [métrica] sobre [sinal comparado], com os números principais | protocolo: [experimento: fonte dos dados, cenários, n, horizonte, baseline, estatística] | relevância p/ tese: alta/média/baixa | [obs: o que o pesquisador precisa conferir; RQ sugerida; limitações]

Relevância: alta = mede fidelidade físico versus virtual de robô móvel (omnidirecional, SSL ou com rodas) com protocolo descrito; média = mede fidelidade mas em plataforma não móvel, ou com protocolo pouco descrito, ou método transferível; baixa = sem medição de fidelidade (candidato a EC1) ou domínio distante.

Copie os números exatamente como estão no texto (mesmo separador decimal e mesma precisão). Se a informação de um campo não estiver no texto, escreva "não encontrado no texto extraído" naquele campo. Tamanho da nota: 350 a 900 caracteres.

## Dois exemplos calibrados pelo pesquisador (ambos INCLUI, relevância alta)

Exemplo 1 (SLR-2022-Victor-4055): "SKIM 13/09: robô SSL omnidirecional real (RobôCIn), 4 motores Maxon EC-45 flat 50 W, encoder MILE 1024 PPR, telemetria sem fio nRF24L01+ com o robô em movimento no campo | fidelidade medida por fit % do modelo OE de 1.ª ordem (System Identification Toolbox) sobre velocidade angular do motor (rad/s) em resposta a MPRS: 91,1 a 91,4 % vs 64,9 a 65,8 % com PRBS, ganho médio de 39,41 % | protocolo: identificação por motor em malha aberta com MPRS dedicado (511 amostras, T = 0,3 s, duty de -100 a 100 %); fit reportado nos próprios dados de estimação, sem hold-out nem horizonte de predição; validação do PI por IAE/ISE (20 degraus de 0,5 s, 30 repetições) é desempenho de controle, não fidelidade | relevância p/ tese: alta | obs: nível motor, não corpo do robô; excitação dedicada, não dados operacionais; sugiro RQ Mapping RQ1+RQ2"

Exemplo 2 (SLR-2025-Victor-849): "SKIM 13/09: robô SSL omnidirecional de 4 rodas modelado em Simscape Multibody a partir do CAD, contato roda-solo por spatial contact force com stick-slip (k 1e5 N/m, d 1e3 N.s/m, mu_s 0,8, mu_k 0,6), PID por roda, passo fixo 0,5 kHz | fidelidade medida por RMSE de trajetória e erro posicional máximo (mm) sobre a posição planar do robô, ground truth da visão da liga vs gêmeo: RMSE 149,2 / 176,5 / 231,1 mm e máximo 241,2 / 264,3 / 349,5 mm em 3 cenários (1,0, 1,5 e 2,0 m/s) | protocolo: replay em malha aberta dos comandos de um dataset público, 1 trajetória por cenário, trajetória inteira sem re-ancoragem, sem baseline nem estatística; erro cresce com a velocidade | relevância p/ tese: alta | obs: parâmetros nominais do CAD, sem identificação por dados (DT sem calibração empírica); RQ2 principal, RQ1 secundária"

O que torna esses exemplos bons: o segundo campo diz a métrica E o sinal comparado E os números; o terceiro separa fidelidade de desempenho de controle e diz o que falta (hold-out, horizonte, baseline, estatística); a obs diz o que o pesquisador vai precisar na síntese.

## Saída

Para cada artigo, um objeto JSON em uma linha (JSONL), no arquivo indicado, com estes campos:
- "pid": Paper ID
- "pre_veredito": "INCLUI" | "EC1" | "EC2" | "EC3" | "EC4" | "EC6" | "DUVIDA"
- "confianca": "alta" | "media" | "baixa"
- "robo_fisico": "sim" | "nao" | "incerto"
- "medicao_fisico_virtual": "sim" | "nao" | "incerto"
- "nota": a linha no formato acima
- "numeros_citados": lista com cada número que aparece na nota, copiado do texto (para verificação automática)
- "rq_sugerida": por exemplo "RQ2", "RQ1+RQ2", "RQ3", "nenhuma"
- "alerta_para_victor": uma frase: o que ele precisa conferir nas figuras e tabelas que o texto extraído não permite confirmar (ou "nada")
- "trecho_evidencia": citação literal do texto (até 40 palavras) que sustenta a medição de fidelidade, ou "nenhum"
- "tipo": "artigo" | "preprint" | "tese" | "survey" | "capitulo"
- "texto_parcial": true se o arquivo avisa que houve corte por tamanho

Leia cada .txt integralmente com a ferramenta Read antes de escrever. Não use conhecimento externo sobre o artigo; se o texto extraído estiver ilegível ou vazio, diga isso no pre_veredito "EC6" com confianca "baixa" e explique na obs. Ao terminar, responda só com um resumo de uma linha por artigo (pid, pre_veredito, confianca).
