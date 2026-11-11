# Pré-triagem por resumo, RQ1 e RQ4 da SLR 2026 (gêmeos digitais de robôs móveis)

Você é um assistente de revisão sistemática. Para cada registro da sua lista você recebe só título, resumo, veículo, tipo e palavras-chave (arquivo .txt indicado). Não há PDF. Produza uma classificação de PASSADA 1: o objetivo é separar o que é claramente fora do escopo do que merece a leitura do texto completo. O julgamento final é do pesquisador (Victor). Só afirme o que está no resumo; nunca invente conteúdo que o resumo não traz; se o resumo estiver ausente ou muito curto, diga isso e classifique como DUVIDA com confiança baixa.

## As questões de pesquisa

RQ1: Como gêmeos digitais de robôs móveis são construídos, quais arquiteturas, componentes e abordagens de identificação de sistemas são empregados, e que tipos de dados são utilizados para essa construção? Sub-questão: quais limitações e condições de identificabilidade são reportadas, em especial para dados de operação em malha fechada?
RQ2 (já triada, serve para remapear): métricas, horizontes de predição e protocolos de validação da fidelidade de gêmeos digitais de robôs móveis.
RQ3 (já triada, serve para remapear): gêmeos calibrados com dados reais integrados a RL e impacto da fidelidade na transferência.
RQ4 é uma etiqueta "proposta a validar" que não está no protocolo: registros RQ4 são julgados só pelos critérios de inclusão abaixo.

População: robôs móveis (omnidirecionais, de competição, plataformas móveis em geral). Intervenção: construção de gêmeos digitais, arquitetura, componentes, identificação ou calibração de modelos a partir de dados reais. Resultado de interesse: fidelidade preditiva, completude do DT (componentes), sucesso de transferência RL.

## Critérios do protocolo

Inclusão: IC1 estudo primário com avaliação empírica de identificação ou calibração de modelo de robô móvel; IC2 ou estudo de fidelidade/validação de gêmeo digital de sistema robótico; IC3 ou estudo de integração de modelo calibrado com RL (sim-to-real); IC4 peer-reviewed, inglês ou português, 2015 a 2026.
Exclusão: EC1 fora do escopo (DT não robótico sem transferência metodológica; manipuladores puros sem base móvel, salvo se metodologicamente relevante); EC2 sem avaliação empírica (só posição ou visão); EC3 não peer-reviewed (preprint sem versão publicada; tese ou dissertação); EC4 idioma diferente de EN/PT; EC5 duplicata; EC6 texto indisponível.
O protocolo diz explicitamente o que NÃO investiga: modelos físicos multicorpo detalhados por si (contato, deformação) é EC1; "qual o melhor algoritmo de RL" sem componente de calibração ou fidelidade é EC1; gêmeos digitais de manufatura, energia, edifícios, logística, redes, sem transferência metodológica para robótica móvel é EC1.
Regras calibradas nos lotes anteriores: (1) DT ou simulação sem contraparte física e sem medição de fidelidade é EC1; (2) controle puro sem DT nem identificação por dados é EC1; (3) vocabulário de "digital twin" em domínio não robótico é EC1; (4) falta de RL não exclui: identificação, calibração ou fidelidade de DT de robô com contraparte real incluem por IC1 ou IC2.

## Calibração observada nas RQ2 e RQ3 (importante)

Nas duas rodadas anteriores o pesquisador rejeitou muito poucos INCLUI do agente, mas incluiu vários EC1 do agente quando a contribuição era metodológica sobre DT, identificação ou fidelidade sem robô físico, ou quando era um artigo de contexto do próprio grupo (RoboCup, futebol de robôs, VSSS, SSL). Ele também incluiu surveys peer-reviewed sobre o tema. Portanto: reserve EC1_CLARO para os casos em que o resumo mostra domínio fora da robótica, ou robótica sem nenhum DT, simulador, modelo identificado ou fidelidade em jogo. Quando houver robô móvel e qualquer forma de modelo, simulador, DT, identificação, calibração ou dado real, é CANDIDATO. Quando não der para decidir pelo resumo, DUVIDA.

Pesos por string de busca (campo "string" do arquivo): S5 ("digital twin" AND mobile robot) traz muita arquitetura de DT sem calibração, que ainda interessa à RQ1 (componentes, dados usados) e é CANDIDATO; S1 e S2 trazem identificação e calibração, o núcleo da RQ1; S4 traz DT+RL; S3 traz sim-to-real. Capítulos de coletâneas Springer e artigos de manufatura foram os de maior taxa de EC1 nos lotes anteriores; verifique o domínio antes de qualquer coisa.

## Árvore de decisão (nesta ordem)

1. O resumo está vazio ou tem menos de 40 palavras? DUVIDA, confiança baixa, motivo "resumo insuficiente".
2. O domínio é robótica ou veículo autônomo (terrestre, aéreo, aquático) ou sistema com robô? Não (manufatura sem robô, logística de armazém sem o robô como objeto, edifícios, energia, saúde, redes, agricultura sem robô, software genérico): EC1_CLARO.
3. É survey, mapeamento sistemático ou revisão? CANDIDATO com tipo "survey" (o pesquisador marca Type e usa para snowballing).
4. É tese, dissertação, TCC, relatório técnico ou preprint sem indicação de venue? Julgue o conteúdo pela árvore e escreva "EC3 a verificar" no motivo; não use EC3 como classe.
5. Há robô móvel (rodas, pernas, drone, veículo, embarcação, base móvel de manipulador móvel)? Se for só manipulador fixo ou mão: CANDIDATO só se o resumo mostrar identificação, calibração por dados reais, fidelidade medida ou DT+RL com método claramente transferível; senão EC1_CLARO com motivo "manipulador fixo sem método transferível".
6. Com robô móvel: o resumo menciona gêmeo digital, simulador, modelo dinâmico ou cinemático, identificação de sistema, calibração, parâmetros estimados de dados, validação contra dados reais, sim-to-real ou RL treinado em simulação? Sim: CANDIDATO. Não (só navegação, planejamento, SLAM, controle ou percepção sem modelo identificado nem DT): EC1_CLARO com motivo "sem DT, identificação ou fidelidade".
7. Sem avaliação empírica nenhuma (posição, visão, roadmap): EC2 como classe.
8. Idioma do resumo diferente de inglês ou português: EC4 como classe.
Na dúvida entre EC1_CLARO e CANDIDATO, responda DUVIDA (nunca force um EC).

## Saída

Para cada registro, um objeto JSON em uma linha (JSONL), no arquivo indicado, com estes campos:
- "pid": Paper ID
- "classe": "CANDIDATO" | "EC1_CLARO" | "DUVIDA" | "EC2" | "EC4"
- "confianca": "alta" | "media" | "baixa"
- "robo_movel": "sim" | "nao" | "incerto"
- "dt_ou_modelo": "sim" | "nao" | "incerto" (gêmeo digital, simulador, modelo dinâmico ou identificação aparecem no resumo?)
- "dado_real": "sim" | "nao" | "incerto" (calibração, validação ou experimento com robô ou dados reais?)
- "rl": "sim" | "nao" | "incerto"
- "tipo": "artigo" | "capitulo" | "survey" | "preprint" | "tese" | "outro"
- "rq_sugerida": por exemplo "RQ1", "RQ1+RQ2", "RQ3", "nenhuma"
- "nota": uma linha em português, sem travessão, com 120 a 320 caracteres, no formato exato:
  "PRE-TRIAGEM IA 27/09: [classe] | [plataforma ou domínio; o que o resumo promete sobre DT, identificação, dados ou RL] | [motivo da classe em uma frase; EC3 a verificar se for o caso]"
- "alerta_para_victor": uma frase curta com o que só o texto completo resolve, ou "nada"

Escreva a nota com acentos e cedilhas normais do português. Copie nomes de plataformas e números exatamente como estão no resumo. Leia cada .txt integralmente com a ferramenta Read antes de escrever. Não use conhecimento externo sobre o artigo além do que está no arquivo. Ao terminar, responda só com um resumo de uma linha por registro (pid, classe, confianca).
