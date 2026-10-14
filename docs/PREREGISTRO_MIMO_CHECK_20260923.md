# Pré-registro: checagem MIMO (acoplamento entre canais) nos logs de competição

*Escrito em 23/09/2026, antes de qualquer execução sobre dados reais. Módulo:
`src/dtssl/analysis/coupled_mimo_check.py` (`dtssl analysis run coupled_mimo_check`); testes sem
dataset em `tests/test_coupled_mimo_check.py`. A única execução feita até aqui foi um ensaio de
software sobre um conjunto sintético gerado na nuvem (nenhum número do robô). Qualquer mudança
depois de ver números reais vira uma re-registração (v2) com esta versão mantida, como no C1b.*

## 1. Pergunta

O revisor R2 do SBR/LARS 2026 pediu identificação conjunta ou acoplada (MIMO) e o R1 apontou que os
três canais desacoplados ignoram o acoplamento. O C1b (07/09) mostrou in silico que o ganho de yaw
inflado em malha fechada (K = 1,378 no ajuste de competição, contra 1,0016 na coleta dedicada) é
reproduzido por um gerador físico com acoplamento translação para guinada e desaparece quando a
translação é zerada. Três perguntas, na ordem de importância:

1. **M1 (primária).** Acrescentar termos cruzados de comando ao mesmo modelo de primeira ordem,
   com o mesmo estimador e os mesmos dados, melhora o que o modelo reproduz no hold-out?
2. **M2 (mecanismo).** Dar ao canal de yaw os comandos de translação como entradas reduz o ganho
   direto de yaw estimado em malha fechada, como o mecanismo do C1b prevê?
3. **M3 (uso).** O modelo acoplado reduz o erro de posição em free-run no harness do artigo, nas
   mesmas janelas de todos os outros números?

## 2. Dados

- Os 46 eventos de competição dos rótulos `front_to_back`, `side_to_side`, `shoot_to_goal` e
  `square` do dataset `2026-05-18_19-2-15`. Hold-out = os 10 eventos congelados de
  `config/holdout_events.json`; treino = os outros 36. A coleta dedicada de rotação (`rotate`) não
  entra no ajuste primário.
- Pré-processamento idêntico ao da identificação do artigo (`common.legacy_uy_series`): grade
  uniforme de 1/60 s, comando interpolado linearmente, velocidade de corpo medida pela pose da visão
  (Savitzky-Golay 7/2, diferenças centrais, rotação mundo para corpo, posições de mm para m). Os três
  DOFs de um evento compartilham a grade.

## 3. Modelo e braços

Por saída `i` (vx, vy, w), na convenção de alinhamento da planta do artigo (`AnalyticFOPDTPlant`: o
comando aplicado no passo k-1 produz a velocidade no passo k):

    y_i[0] = y_i medido na primeira amostra
    y_i[k] = A_i y_i[k-1] + soma_j B_ij u_j[k-1-M_ij]      (u = 0 antes do início do evento)

- **diagonal**: `B_ij = 0` para `i != j`. É exatamente a estrutura FOPDT por DOF
  (`A = exp(-dt/tau)`, `B_ii = K (1 - A)`), re-estimada nos mesmos 36 eventos.
- **acoplado**: `B` completo (3 x 3), um polo por saída.
- **promoted**: o θ oficial de `config/twin_params.json` na mesma grade (âncora dos números
  publicados; não é re-estimado).

Atrasos do ajuste primário: fixos nos atrasos da planta promovida, `M_ij = ceil(Td_i/dt)` = 5, 4 e 6
amostras para as linhas vx, vy e w, iguais para as três entradas de cada linha.

## 4. Estimador

Erro de saída (o erro de simulação que a Eq. (2) do artigo pontua), por mínimos quadrados
separáveis: para um polo `A` fixo, a saída simulada é linear na linha de `B`, então `B` sai de
mínimos quadrados; `A` é uma busca escalar em `tau` (grade log-espaçada de 121 pontos entre 5 ms e 1 s,
depois Brent limitado em `log tau` entre os vizinhos do melhor ponto da grade). Determinístico. O
mesmo estimador ajusta os dois braços.

Diferenças em relação ao esboço do §B3 do `PLANO_CAMERA_READY_SBR2026.md`, fixadas aqui antes de
rodar, com o motivo:

1. Erro de saída em vez de erro de equação (ARX): o erro de equação usa a velocidade medida como
   regressor, e o ruído colorido pelo diferenciador (o mesmo que faz o Ljung-Box rejeitar) enviesa o
   polo; a Eq. (2) pontua simulação, não predição de um passo.
2. Alinhamento da planta em vez do legado: o modelo ajustado é exatamente o que o harness roda (M3),
   sem conversão de atraso.
3. Critério de acoplamento adimensional (razão de contribuição, §5) em vez da razão entre ganhos
   estáticos cruzado e direto, que mistura unidades (rad/s por m/s contra adimensional).
4. Fit agregado do hold-out como métrica primária em vez da média do fit por evento: um evento em
   que o DOF quase não é excitado tem denominador pequeno e domina a média. A média por evento é
   reportada ao lado.

Secundário (atrasos por par): os atrasos de cada linha buscados exaustivamente em 0 a 10 amostras
(0 a 0,167 s) para cada entrada usada (o atraso do braço diagonal buscado do mesmo jeito), depois
Brent no polo. O atraso de um termo com contribuição desprezível não é interpretável e não é lido.

## 5. Métricas

- **Fit agregado do hold-out** por DOF: `100 (1 - ||y - ŷ|| / ||y - ȳ_e||)` sobre as amostras
  concatenadas dos 10 eventos, com `ȳ_e` a média de cada evento.
- **Razão de contribuição cruzada** da saída `i` no braço acoplado: RMS da soma dos termos cruzados
  (`B_ij` vezes a resposta de cada entrada `j != i`) dividido pelo RMS do termo direto, nos eventos
  de hold-out. Reportada também por entrada.
- **Ganhos estáticos** `G_ij = B_ij / (1 - A_i)` dos dois braços.
- **Bootstrap** por eventos de treino (200 réplicas, seed 42, atrasos mantidos nos valores da
  amostra completa): intervalos percentis de 95 % para `G_ww` dos dois braços, para o ganho de fit
  por DOF e para as razões de contribuição.
- **Harness** (M3): o free-run do artigo (janelas re-ancoradas em SE(2), stride 15, H_max 90,
  horizontes de `config/metrics.json`, bin translacional), com a planta
  `CoupledFirstOrderPlant` para os braços diagonal e acoplado e a `AnalyticFOPDTPlant` para o
  promoted; medianas por evento de `e_pos` em h_ref = 0,4 s. Sanidade: o promoted reproduz 0,0421 m.

## 6. Hipóteses e regras de decisão

**M1 (primária).** O acoplamento "importa" se, em algum DOF, o braço acoplado ganhar pelo menos
3 p.p. de fit agregado do hold-out sobre o diagonal **e**, no mesmo DOF, a razão de contribuição
cruzada for pelo menos 0,10. Caso contrário, "não importa no envelope destes logs".

**M2 (mecanismo).** Referência `K_ref` = 1,0016 (o `K_w` promovido, da coleta dedicada em malha
aberta). Premissa: o `G_ww` do braço diagonal fica pelo menos 10 % acima de `K_ref` (a inflação de
malha fechada reaparece com este estimador e este conjunto de treino). Se a premissa falhar, M2 é
"não testável" e isso é reportado. Com a premissa, M2 é corroborada se o braço acoplado remover pelo
menos metade do excesso, `|G_ww acoplado - K_ref| <= 0,5 |G_ww diagonal - K_ref|`, e falsificada
caso contrário. Sensibilidade reportada, sem decisão: o mesmo teste com o treino restrito aos
eventos de `shoot_to_goal` (o único rótulo de jogo).

**M3 (uso).** O acoplado melhora o harness se vencer o diagonal em pelo menos 8 dos 10 eventos,
com Wilcoxon unilateral pareado p < 0,05 e rank-biserial >= 0,5 (o gate por evento do C2b).
Também são reportados acoplado contra promoted e diagonal contra promoted.

**Controles in silico** (mesmo pipeline, logs sintéticos gerados a partir dos comandos registrados,
sem ruído, como a célula idealizada do C1b; a referência de yaw de cada controle é o próprio
estimador diagonal na resposta do gerador aos seis eventos de rotação dedicada em regime linear,
`rotate_01_05` a `rotate_01_10`):

- **C- (`control=fopdt`, gêmeo promovido, sem acoplamento):** previsão: M1 "não importa" e `G_ww`
  dos dois braços a no máximo 5 % do K_w verdadeiro. Se C- falhar, o pipeline inventa acoplamento e
  M1 e M2 do dado real não são interpretáveis; isso é reportado e nada vai para o artigo.
- **C+ (`control=mujoco-rollers-delay`, rota b do MuJoCo sem sintonia, com o atraso identificado):**
  previsão: a premissa de M2 reaparece e o braço acoplado remove pelo menos metade do excesso. Se a
  premissa reaparecer e o acoplado não remover o excesso, um termo cruzado linear não captura o
  mecanismo físico da rota b, e uma falha de M2 no dado real passa a ser lida assim, não como
  refutação do mecanismo.

Limitação declarada: termos cruzados lineares capturam só a parte do acoplamento que é linear no
comando de translação; um efeito simétrico em sinal (proporcional a |v|, por exemplo) aparece como
variância não explicada, não como ganho cruzado.

## 7. Execução (Victor, no PC, depois de aprovar este documento)

Na ordem, na mesma sessão:

```powershell
py -3 -m dtssl.cli analysis run coupled_mimo_check --kw control=fopdt n_boot=0 pair_delays=false
py -3 -m dtssl.cli analysis run coupled_mimo_check
py -3 -m dtssl.cli analysis run coupled_mimo_check --kw control=mujoco-rollers-delay n_boot=0 pair_delays=false
```

Tempo estimado: o ensaio de software na nuvem (36 eventos de treino sintéticos, 20 réplicas de
bootstrap, atrasos por par e harness) levou 54 s; com 200 réplicas, cerca de 5 a 6 minutos para a
execução primária; os controles, 1 a 3 minutos cada (o C+ depende do MuJoCo). Artefatos:
`results/coupled_mimo_check_<stamp>.{md,json,csv}` e
`results/coupled_mimo_check_control-<gerador>_<stamp>.{md,json,csv}`. Depois: uma entrada no
`results/CHANGELOG.md` com os três artefatos e os vereditos, e o commit dos artefatos.

## 8. Frases para o artigo (camera-ready se o D1 permitir; senão, a extensão)

- M1 "importa": *"A coupled first-order model with cross-command terms, fitted with the same estimator
  on the same training events, raises the pooled hold-out fit of [DOF] by [x] p.p., with cross terms
  carrying [y] of the direct term's RMS; coupling is measurable in these logs and is taken up by the
  coupled identification of the extension."*
- M1 "não importa": *"A coupled first-order model with cross-command terms, fitted with the same
  estimator on the same training events, changes the pooled hold-out fit by less than [x] p.p. on
  every DOF, and its cross terms stay below [y] of the direct term's RMS; within the envelope of these
  logs the decoupled structure loses nothing measurable, and aggressive mixed motion is where a
  coupled model would have to be tested."*
- M2 corroborada (frase adicional): *"Given the translational commands as inputs, the direct yaw gain
  fitted on the closed-loop logs falls from [a] to [b], against [c] from the dedicated collection,
  which is the translation-induced bias the in-silico check predicts."*

## 9. O que não muda

O θ oficial, `config/*.json`, `data/`, `models/` e os artefatos existentes em `results/`. Nenhum
parâmetro é promovido por esta checagem; ela produz evidência para o texto, não um modelo novo.
