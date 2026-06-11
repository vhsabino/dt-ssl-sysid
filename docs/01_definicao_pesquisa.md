# 01 — Definição Formal da Pesquisa (Gate G1: validar com orientador até 17/06)

## Problema
Simuladores SSL (ex.: grSim, com modelo omni simplificado e ODE) não reproduzem a resposta dinâmica real do robô; políticas e estratégias validadas em simulação degradam no campo (*reality gap*).

## Lacuna
[PREENCHER após SLR — hipótese atual:] identificação de gêmeos digitais de robôs omnidirecionais a partir de **logs de competição em malha fechada** (sem experimentos dedicados de excitação) é pouco explorada; abordagens existentes assumem dados de excitação persistente em malha aberta ou modelos físicos detalhados.

## Tese (1 frase — o claim que você defende)
> Um modelo grey-box de 1ª ordem com atraso de transporte, identificado por DOF via otimização bayesiana sobre logs de competição, é suficiente para atingir fidelidade observacional comportamental [≥ X% de redução de RMSE multi-horizonte vs. cinemática ideal] em um robô SSL omnidirecional.

## Questões de Pesquisa
- **QP1:** Quanto o grey-box calibrado (bayesopt) reduz o erro de predição de trajetória vs. cinemática ideal e vs. procest, em múltiplos horizontes?
- **QP2:** Os 9 parâmetros (em particular Td) são identificáveis a partir de logs de competição em malha fechada? Sob quais condições de excitação?
- **QP3:** Qual a contribuição relativa de cada DOF (vx, vy, ω) para o erro do gêmeo?

## Hipóteses
- **H1:** θ_bayesopt reduz RMSE de posição em ≥ [X]% vs. ideal em todos os horizontes testados.
- **H2:** Td é o parâmetro de menor identificabilidade em malha fechada; fixá-lo por correlação cruzada não degrada o RMSE em mais de [Y]%.
- **H3:** ω domina o erro angular acumulado; identificação dedicada de ω melhora [métrica] em [Z]%.

## Objetivos
**Geral:** desenvolver e validar metodologia de identificação grey-box por DOF para gêmeo digital comportamental de robô SSL a partir de logs de competição.
**Específicos:** (1) pipeline de extração/segmentação de logs; (2) identificação por DOF com baselines; (3) calibração por BO com custo multi-horizonte; (4) análise de identificabilidade/excitação; (5) validação contra trajetórias reais e benchmark explícito vs. grSim.

## Escopo
**Dentro:** fidelidade comportamental (entrada de comando → pose); 3 DOF desacoplados; dados de competição 2025; MATLAB/Simulink + SLDD.
**Fora (pós-qualificação):** RL / sim-to-real; acoplamento entre DOF; modelo físico detalhado de roda/derrapagem; coleta dedicada.

## Contribuições esperadas
C1: metodologia de identificação a partir de logs de malha fechada; C2: gêmeo digital SSL aberto e reprodutível; C3: caracterização de identificabilidade (especialmente Td) nesse regime de dados.

## Riscos → mitigação
R1 excitação insuficiente → fixar Td, multi-experimento `iddata`, reportar limitação. R2 tempo → cortar ablations, mapping em vez de SLR no artigo. R3 inflação de escopo (vertente RL) → gate explícito na qualificação.
