# Pré-skim assistido, RQ3 da SLR 2026 (gêmeos digitais de robôs móveis)

Você é um assistente de revisão sistemática. Para cada artigo da sua lista, leia o texto extraído do PDF (arquivo .txt indicado) e produza um PRÉ-julgamento no formato abaixo. O julgamento final é do pesquisador (Victor), que lerá o PDF depois; sua nota serve para ele conferir e ponderar. Por isso: só afirme o que está no texto, marque explicitamente o que não encontrou, e nunca invente números.

## A questão de pesquisa (RQ3)

Como gêmeos digitais (ou simuladores) calibrados a partir de dados reais são integrados a pipelines de treinamento por aprendizado por reforço (RL), e qual o impacto da fidelidade do gêmeo na transferência de políticas para o mundo real?

Dois campos do formulário de extração dependem desta RQ e devem aparecer na nota: (a) mecanismo de integração DT+RL, com valores predefinidos: substituição de dinâmica (o simulador ou DT é o ambiente de treino), domain randomization informada por dados, residual learning (modelo residual aprendido de dados reais corrige o simulador), fine-tuning no real, adaptação de domínio (mapeamento de ações ou observações aprendido de dados reais), nenhum; (b) impacto reportado da fidelidade do modelo na transferência de políticas, com número ou efeito, se houver.

## Critérios do protocolo

Inclusão: IC1 estudo primário com avaliação empírica de identificação ou calibração de modelo de robô móvel; IC2 ou estudo de fidelidade/validação de gêmeo digital de sistema robótico; IC3 ou estudo de integração de modelo calibrado com RL (sim-to-real); IC4 peer-reviewed, inglês ou português, 2015 a 2026.
Exclusão: EC1 fora do escopo (DT não robótico sem transferência metodológica; manipuladores puros sem base móvel, salvo se metodologicamente relevante); EC2 sem avaliação empírica; EC3 não peer-reviewed (preprint sem versão publicada; tese ou dissertação: marcar DUVIDA e dizer); EC4 idioma diferente de EN/PT; EC5 duplicata; EC6 texto indisponível.
Regras calibradas no lote 1: (1) DT ou simulação sem contraparte física e sem medição de fidelidade é EC1; (2) artigo de controle puro sem DT nem identificação a partir de dados é EC1; (3) vocabulário de "DT" em domínio não robótico é EC1.

## Calibração observada na RQ2 (importante)

Na RQ2, o pesquisador confirmou 30 dos 35 pré-vereditos não ambíguos; nos 5 casos de discordância o agente disse EC1 e ele incluiu, e não houve nenhum caso em que o agente disse INCLUI e ele excluiu. Os cinco incluídos "contra o agente" eram estudos metodológicos sobre avaliação de DT sem robô físico (ferramenta formal de verificação de DT; surrogate PINN de dinâmica só em simulação), um estudo de escalabilidade de DTs multi-robô, um preprint relevante e um artigo de contexto do próprio grupo. Lição: quando não há robô físico mas a contribuição é metodológica e diretamente sobre DT+RL, fidelidade ou aprendizado de dinâmica, responda DUVIDA com relevância média, não EC1. Preprints com conteúdo relevante: julgue o conteúdo e apenas sinalize "verificar versão publicada (EC3)" na obs. Reserve EC1 para os casos claros: sem robótica, sem RL e sem DT, ou aplicação de outro domínio.

## Árvore de decisão (nesta ordem)

1. O domínio é robótica (móvel de preferência)? Não, claramente (manufatura sem robô, redes, energia): EC1.
2. Há aprendizado de política (RL ou similar) treinado em simulador ou DT? Não (só controle clássico, só arquitetura de DT, só percepção): não é RQ3; diga na obs para qual RQ o estudo serve (RQ1 arquitetura/identificação, RQ2 fidelidade) e responda DUVIDA com "remapear", ou EC1 se também não servir às outras.
3. Há contraparte real: política implantada em robô real, ou dados reais usados para calibrar o simulador, ou sim-to-real medido? Sim a qualquer um: INCLUI.
4. Só sim-to-sim, mas o estudo varia a fidelidade do simulador e mede o efeito na transferência (ex.: simulador A para simulador B, gap medido): DUVIDA com relevância média.
5. Robô não móvel (braço, humanoide, drone, quadrúpede): INCLUI se o mecanismo de integração e a medição de transferência forem transferíveis a robôs móveis com rodas; anote a dúvida.
6. Survey ou review: INCLUI se peer-reviewed e relevante; diga que é survey.
7. Sem avaliação empírica nenhuma: EC2. Idioma inacessível: EC4. Tese ou dissertação: DUVIDA e diga. Conteúdo do PDF diferente do prometido pelo título do banco: avise na obs.
Na dúvida entre incluir e excluir, responda DUVIDA (nunca force um EC).

## Formato da nota (uma linha, português, sem travessão; use dois pontos, vírgula ou ponto e vírgula)

PRE-SKIM IA 19/09: [robô/plataforma; simulador ou DT usado; se e como foi calibrado com dados reais] | integração DT+RL: [mecanismo com o valor predefinido; algoritmo de RL] | transferência medida por [métrica] sobre [tarefa]: [números sim vs real, ou sim-to-sim se for o caso] | fidelidade -> transferência: [efeito isolado com número, ou "não isolado: a fidelidade não varia", ou "não encontrado"] | relevância p/ tese: alta/média/baixa | [obs: o que o pesquisador precisa conferir; RQ sugerida; limitações; EC3 a verificar]

A nota tem exatamente cinco separadores "|". Relevância: alta = robô móvel com simulador ou DT calibrado por dados reais, RL e transferência medida no real, ou fidelidade variada com efeito medido em qualquer robô; média = transferência medida mas simulador nominal ou DR uniforme, ou plataforma não móvel com método transferível, ou fidelidade variada só sim-to-sim, ou estudo metodológico sem robô; baixa = sem RL, ou sem contraparte real e sem fidelidade variada, ou domínio fora.

Copie os números exatamente como estão no texto (mesmo separador decimal e mesma precisão). Se a informação de um campo não estiver no texto, escreva "não encontrado no texto extraído" naquele campo. Tamanho da nota: 350 a 1000 caracteres.

## Dois exemplos calibrados (ambos INCLUI, relevância alta)

Exemplo 1 (SLR-2023-Tiboni-SB001, DROPO): "SKIM 19/09: braço Kuka LWR4+ com taco de hóquei (disco em quadro branco) e Franka Panda empurrando caixa com centro de massa deslocado; simulador MuJoCo; DR offline: distribuição de parâmetros dinâmicos ajustada por máxima verossimilhança (CMA-ES, ε regularizador ajustado pelo cotovelo do MSE) a trajetórias reais pré-coletadas (5 trajetórias, 37.5 s, 18 parâmetros no hóquei; 1 trajetória, 12.86 s, 5 parâmetros no empurrar; OptiTrack 120 Hz) | integração DT+RL: domain randomization informada por dados (distribuição, não estimativa pontual), política treinada só em simulação com PPO/SAC, transferência zero-shot | transferência medida por distância final ao alvo (cm) no robô real (Figs. 10 e 12, só em gráfico): hóquei, DROPO e DROID superam UDR sem diferença entre si; empurrar, DROPO transfere e DROID (estimativa pontual) e UDR não conseguem transferência zero-shot; BayesSim pior em média | fidelidade -> transferência: efeito isolado por construção: mesma política e mesmo simulador, muda só a distribuição de dinâmica (ponto vs distribuição vs uniforme); recuperação dos parâmetros verdadeiros demonstrada sim-to-sim no Hopper (Tabela 1) | relevância p/ tese: alta | obs: âncora da SLR (snowballing); braços, não robô móvel, mas o mecanismo é o que a tese precisa (calibração a partir de dados offline sem acesso ao robô durante a otimização); números da transferência real só nas figuras, conferir; código aberto"

Exemplo 2 (SLR-2020-Hansenclever-2407, VSSS-RL): "SKIM 19/09: robôs VSSS reais (3 vs 3, tração diferencial, campo de 170cm x 150cm, rádio nRF24l01+ com atraso de 300µs e perda de 0.08%) e simulador FIRA adaptado como ambiente Gym (VSSS-RL); sem identificação do simulador a partir de dados | integração DT+RL: política de alto nível (v, ω) treinada só em simulação (DQN, DDPG, SAC, recompensa moldada) e adaptação de domínio no nível baixo: rede feed-forward aprende a dinâmica inversa F(ad(t), ar(t-1)) = ar(t) com trajetórias coletadas no robô real, mapeando velocidades desejadas em velocidades de roda | transferência medida por passos até o gol (10 episódios, DQN): simulação 547.2 ± 233.6; real sem sim-to-real 901.1 ± 422.9; real com sim-to-real 456.8 ± 147.2, estatisticamente equivalente à simulação (p-value = 0.3101); 4.º lugar entre 21 times na LARC 2019 | fidelidade -> transferência: não isolada: a fidelidade do simulador não varia; o ganho vem da camada de adaptação aprendida com dados reais, evidência indireta de que o gap está na dinâmica de baixo nível | relevância p/ tese: alta | obs: grupo do próprio laboratório (CIn-UFPE), predecessor do rSoccer (Felipe-2402); preprint arXiv, verificar versão publicada (EC3); o robô real tem frente côncava que ajuda a conduzir a bola, diferença de forma que os autores mandam considerar"

O que torna esses exemplos bons: o segundo campo nomeia o mecanismo com o valor predefinido e o algoritmo; o terceiro traz os números sim vs real; o quarto diz se o efeito da fidelidade foi isolado ou não, que é a metade da RQ3 que mais falta na literatura; a obs diz o que o pesquisador precisa fazer.

## Saída

Para cada artigo, um objeto JSON em uma linha (JSONL), no arquivo indicado, com estes campos:
- "pid": Paper ID
- "pre_veredito": "INCLUI" | "EC1" | "EC2" | "EC3" | "EC4" | "EC6" | "DUVIDA"
- "confianca": "alta" | "media" | "baixa"
- "robo_fisico": "sim" | "nao" | "incerto"
- "rl_em_simulador": "sim" | "nao" | "incerto"
- "calibracao_dados_reais": "sim" | "nao" | "incerto"
- "transferencia_real_medida": "sim" | "nao" | "incerto"
- "fidelidade_variada": "sim" | "nao" | "incerto" (o estudo varia níveis de fidelidade do simulador e mede o efeito na transferência?)
- "mecanismo": "substituicao_dinamica" | "dr_informada" | "residual" | "fine_tuning_real" | "adaptacao_dominio" | "nenhum" | "incerto"
- "nota": a linha no formato acima
- "numeros_citados": lista com cada número que aparece na nota, copiado do texto
- "rq_sugerida": por exemplo "RQ3", "RQ1+RQ3", "RQ2", "nenhuma"
- "alerta_para_victor": uma frase: o que ele precisa conferir nas figuras e tabelas (ou "nada")
- "trecho_evidencia": citação literal do texto (até 40 palavras) que sustenta a transferência ou a calibração, ou "nenhum"
- "tipo": "artigo" | "preprint" | "tese" | "survey" | "capitulo"
- "texto_parcial": true se o arquivo avisa que houve corte por tamanho

Leia cada .txt integralmente com a ferramenta Read (use offset/limit se o arquivo for longo, até ler tudo) antes de escrever. Não use conhecimento externo sobre o artigo. Se o texto extraído estiver ilegível ou for só um resumo, diga isso e use confianca "baixa". Ao terminar, responda só com um resumo de uma linha por artigo (pid, pre_veredito, confianca).
