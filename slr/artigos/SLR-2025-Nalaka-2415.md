# Resumo do Artigo: Universal Omni-Wheeled Mobile Robot Navigation Using Deep Reinforcement Learning

> **Aviso:** O acesso direto ao arquivo PDF completo no site da ASME está bloqueado para sistemas automatizados (devido a restrições de servidor/paywall). No entanto, consegui recuperar os metadados oficiais e o resumo completo do artigo solicitado, que estruturei neste documento Markdown para você.

## Informações do Artigo

* **Autores:** Nalaka Amarasiri, Raju Gottumukkala, Alan Barhorst
* **Conferência:** ASME 2025 International Mechanical Engineering Congress and Exposition (IMECE 2025)
* **Local/Sessão:** 08-11-02: Mobile Robots and Unmanned Ground Vehicles II (Vancouver, British Columbia, Canada)
* **Número do Paper:** IMECE2025-166906
* **Identificador de Volume:** V005T08A048
* **DOI:** [https://doi.org/10.1115/IMECE2025-166906](https://doi.org/10.1115/IMECE2025-166906)

---

## Resumo (Abstract)

Robôs Móveis Omnidirecionais Universais (UOWMR - *Universal Omni-wheeled Mobile Robots*) oferecem melhor manobrabilidade em ambientes não estruturados e complexos e são capazes de realizar navegações eficientes em espaços apertados. No entanto, utilizar as propriedades mencionadas acima e navegar nesses ambientes utilizando métodos convencionais de planejamento de rotas é desafiador devido a incertezas e dificuldades de modelagem.

A **Aprendizagem por Reforço (RL)** é uma abordagem promissora para o planejamento de caminhos, especialmente em ambientes não estruturados onde os robôs precisam evitar obstáculos. Contudo, os trabalhos relacionados à aplicação de RL em robôs omnidirecionais são limitados por conta de seu espaço de ação de alta dimensão, restrições não holonômicas e dinâmica e cinemática complexas.

Neste trabalho, introduzimos um sistema de robô móvel omnidirecional que navega de qualquer ponto inicial no espaço de trabalho para um ponto alvo fixo aprendendo comportamentos e, ao mesmo tempo, evitando colisões utilizando um planejador de caminhos baseado em RL. O modelo de UOWMR que utilizamos aqui foi desenvolvido em nosso trabalho anterior [1]. O modelo é capaz de manobrar em qualquer trajeto com curvas suaves ou acentuadas enquanto gira em torno de seu eixo vertical.

No treinamento dos agentes de RL, empregamos uma estratégia de aprendizado curricular, na qual aumentamos progressivamente a complexidade do ambiente (de ambiente sem obstáculos para obstáculos estáticos e depois dinâmicos) para treinar uma política de navegação robusta e adaptativa. Além disso, ajustamos e testamos sistematicamente duas funções de recompensa contínuas de RL:
1. Uma baseada na diferença entre o ângulo de direção (heading angle) e o ângulo de condução (driving angle).
2. Outra baseada na distância entre a localização atual e o objetivo.

O objetivo foi identificar a melhor função de recompensa que resultasse no caminho mais curto e com a melhor esquiva de obstáculos.

O modelo UOWMR foi treinado e testado com diversos algoritmos *on-policy* (Advanced Actor-Critic (A2C) e Proximal Policy Optimization (PPO)) e *off-policy* (Deep Deterministic Policy Gradient (DDPG), Soft Actor-Critic (SAC) e Twin Delayed Deep Deterministic Policy Gradient (TD3)) para investigar agentes de RL adequados. Além disso, os hiperparâmetros (Taxa de Aprendizado, Arquitetura da Rede Neural (NN)) foram ajustados sistematicamente por meio de uma série de experimentos para identificar a configuração ideal que gerasse os melhores resultados de desempenho na navegação pelos obstáculos.

Como mencionado, o treinamento começou em um ambiente livre de obstáculos, com obstáculos estáticos sendo adicionados gradualmente para o aprendizado de políticas de comportamento adequadas. Assim que o agente aprendia com sucesso essas políticas, vários obstáculos dinâmicos eram inseridos. 

Após identificar o melhor algoritmo de RL e hiperparâmetros para o UOWMR, utilizamos o mesmo procedimento para identificar e treinar um agente RL em um modelo clássico de Robô com Tração Diferencial nas Rodas (DWDR). Os resultados dos agentes de RL treinados e as funções de recompensa dos modelos UOWMR e DWDR foram comparados usando a recompensa cumulativa média, a perda média (average loss) e a distância percorrida durante a navegação.

A comparação demonstra que o modelo UOWMR apresentado e o seu agente RL treinado obtiveram resultados superiores em manobrabilidade em ambientes não estruturados complexos quando comparados ao modelo e agente DWDR.
