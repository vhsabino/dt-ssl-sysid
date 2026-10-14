# Pré-registro: baseline física sintonizada (C3 / WP3), rota b do MuJoCo calibrada no treino

*Escrito em 14/10/2026, antes de qualquer execução sobre dados reais. Módulo:
`src/dtssl/analysis/tuned_physics_baseline.py` (`dtssl analysis run tuned_physics_baseline`); testes sem
dataset em `tests/test_tuned_physics_baseline.py`. A única execução feita até aqui foi um ensaio de software
com comandos PRBS sintéticos gerados pela própria rota b (`_to_delete\c3_smoke`), sem nenhum número do robô.
O item C3 continua congelado: este documento e o código existem para que a execução, quando a orientadora e o
Victor decidirem, seja um comando. Qualquer mudança depois de ver números reais vira uma re-registração (v2)
com esta versão mantida, como no C1b.*

## 1. Pergunta

Os revisores do SBR/LARS 2026 e a leitura do C2a deixam uma objeção aberta: o gêmeo comportamental vence
motores de física que ninguém sintonizou (rSim, grSim, ER-Force e a rota b do MuJoCo). A pergunta é se a
física da liga, uma vez calibrada nos mesmos eventos de treino que identificaram o gêmeo, alcança ou supera o
gêmeo nas mesmas janelas e com a mesma métrica. Três leituras são possíveis e as três estão escritas aqui.

## 2. Dados

- Treino: os eventos de competição dos rótulos `front_to_back`, `side_to_side`, `shoot_to_goal` e `square`
  do dataset `2026-05-18_19-2-15` que não estão em `config/holdout_events.json`, filtrados pelo mesmo
  critério de movimento do harness (deslocamento mínimo 0,1 m). Com o filtro, 36 eventos (os mesmos da
  checagem MIMO). A coleta dedicada de rotação não entra.
- Hold-out: os 10 eventos congelados de `config/holdout_events.json`, nunca vistos pela sintonia.
- Janelas: o harness do artigo sem alteração (janelas re-ancoradas em SE(2), stride 15, H_max 90, horizontes
  de `config/metrics.json`, bin translacional, velocidade inicial da série do loader).

## 3. Modelo sintonizado e braços

A planta é `mujoco-rollers-delay` do C2a: rota b do MuJoCo (chassi livre, 4 rodas omni com 12 roletes livres
cada, servo de velocidade por roda) com o atraso de transporte por DOF do θ oficial aplicado ao comando. O
atraso é propriedade do rádio e do firmware, não do contato, e a rota b sem sintonia com esse atraso é a
melhor física do C2a (0,0477 m); sintonizar sem ele daria à física uma desvantagem que não é dela.

Cinco parâmetros, todos com significado físico e faixas fechadas antes de rodar (escala logarítmica):

| parâmetro | o que é | faixa | untuned |
|---|---|---|---|
| `mu` | atrito de deslizamento efetivo roleta-piso (piso e roletes recebem o mesmo valor; a regra do máximo do MuJoCo devolve exatamente `mu`) | [0,4, 1,6] | 1,0 |
| `impratio` | razão de impedância do cone de atrito do solver (rigidez ao escorregamento) | [1, 30] | 10 |
| `kv_wheel` | ganho do laço de velocidade da roda (N m s/rad), a constante de tempo do acionamento | [0,02, 0,5] | 0,1 |
| `wheel_torque_max` | limite de torque na roda (N m), o limite de aceleração | [0,3, 3,0] | 1,5 |
| `gear_ratio` | relação da caixa, isto é, a inércia do rotor refletida N² J_rotor | [1,5, 8] | 4,0 |

O ponto untuned reproduz a planta do C2a bit a bit (piso 0,9 contra roleta 1,0 dá efetivo 1,0; o braço
sintonizado põe os dois em `mu`); isso é testado. Nada mais muda: número de roletes, passo do solver,
geometria do CAD, zona morta e massa ficam como estão.

Braços pontuados no hold-out: **gêmeo** (`fopdt`, θ oficial), **untuned** (rota b + atraso, parâmetros de
fábrica) e **sintonizado** (rota b + atraso, parâmetros do incumbente da otimização).

## 4. Objetivo e otimizador

- Objetivo J(x): mediana por janela de e_pos em h_ref = 0,4 s nas janelas translacionais dos eventos de
  treino, pelo harness do artigo. Só treino; o hold-out nunca entra na otimização.
- Otimizador: otimização bayesiana no cubo unitário dos cinco parâmetros em escala log; processo gaussiano
  (Matern 5/2 com uma escala por dimensão, ruído branco, scikit-learn), aquisição por melhoria esperada
  (margem 0,01 desvios-padrão), maximizada sobre 4096 candidatos Sobol e refinada por L-BFGS-B a partir dos
  cinco melhores. Desenho inicial: 16 pontos Sobol embaralhados, o primeiro substituído pelo ponto untuned.
  Depois, 44 passos de melhoria esperada. Orçamento fixo: 60 avaliações. Semente 42 em tudo; a execução é
  determinística.
- Custo estimado no PC: cerca de 56 s por avaliação (36 eventos, ~950 janelas, rota b a ~1500 passos/s no
  ensaio), 60 avaliações em cerca de 1 h, mais 1 min de pontuação no hold-out e 10 min do controle.
- Incumbente: a avaliação de menor J. Nenhum parâmetro é promovido a `config/`; o incumbente fica só no
  artefato.

## 5. Métricas

- Hold-out: e_pos mediano por janela por horizonte (bin translacional) e por evento em h_ref para os três
  braços; e_ang reportado ao lado; sanidade: a mediana por evento do gêmeo tem de reproduzir 0,0421 m.
- Ganhos: treino (untuned → sintonizado no objetivo) e hold-out (untuned → sintonizado na mediana por janela
  em h_ref).
- Faixa quase-ótima de cada parâmetro: os pontos avaliados com J a menos de 2 % do melhor; a faixa (em escala
  unitária e em valores físicos) diz o que os logs identificam da física de contato; faixa acima de metade do
  intervalo = parâmetro não identificado pelos logs.

## 6. Hipóteses e regras de decisão

**T1 (primária).** Gate por evento do C2b nas duas direções, nas medianas por evento em h_ref do hold-out:
um braço "vence" o outro se ganha em pelo menos 8 dos 10 eventos, com Wilcoxon unilateral pareado p < 0,05 e
rank-biserial ≥ 0,5. Três leituras:
- *gêmeo*: o gêmeo vence o sintonizado. A mensagem do artigo não muda: a física da liga, mesmo calibrada nos
  mesmos dados, não alcança o modelo comportamental identificado dos logs.
- *empate*: nenhum dos dois passa o gate. A mensagem passa a ser que o comportamental entrega a mesma
  fidelidade por uma fração do custo e sem parâmetros de contato.
- *sintonizado*: o sintonizado vence o gêmeo. O artigo relata, a discussão muda de tom, e o gêmeo passa a ser
  defendido pelo custo e pela identificabilidade, não pela fidelidade.

**T2 (ganho da sintonia).** No hold-out, mediana por janela em h_ref: a sintonia "comprou" algo se o
sintonizado fica pelo menos 20 % abaixo do untuned (0,0477 m no C2a). Abaixo disso, os parâmetros de fábrica
já estavam perto do que os logs permitem ajustar.

**T3 (sobreajuste).** O ganho relativo no hold-out tem de manter pelo menos metade do ganho relativo no
treino. Se não mantém, a sintonia sobreajustou os 36 eventos e T1 é lido com essa ressalva.

**V (validade).** O incumbente reavaliado reproduz o seu J (determinismo, tolerância 1e-6 m) e no máximo um
parâmetro fica a menos de 2 % de um limite da faixa. Dois ou mais parâmetros no limite = faixas apertadas
demais; o resultado é reportado e a re-registração v2 alarga as faixas antes de qualquer leitura.

**Controle in silico (`control=rollers`).** O mesmo pipeline sobre logs sintéticos gerados pela própria rota b
em parâmetros conhecidos (`mu` 0,7, `impratio` 5, `kv_wheel` 0,2, `wheel_torque_max` 1,0, `gear_ratio` 3,0)
a partir dos comandos dos primeiros 6 eventos de treino (rodízio pelos rótulos), pontuado em 3 outros
eventos sintéticos, com o mesmo orçamento (16 + 44). Previsão: o sintonizado reduz e_pos para no máximo 20 %
do untuned (o gerador está na classe do modelo; o ótimo é quase zero). Se o controle falhar, o otimizador com
este orçamento não recupera nem um gerador da própria classe, e uma leitura *gêmeo* em T1 não pode ser
atribuída aos limites da física: fica "com este orçamento", e a v2 decide se aumenta o orçamento.

Limitação declarada: o que se sintoniza é o contato e o acionamento (cinco graus); massa, geometria, roletes
e o passo do solver ficam fixos. Um resultado *gêmeo* não diz que nenhuma física alcança o gêmeo, diz que
esta rota b, com estes cinco parâmetros e este orçamento, não alcança.

## 7. Execução (depois da decisão da orientadora, na ordem, na mesma sessão)

```powershell
py -3 -m dtssl.cli analysis run tuned_physics_baseline --kw control=rollers
py -3 -m dtssl.cli analysis run tuned_physics_baseline
```

Artefatos: `results/tuned_physics_baseline_control-rollers_<stamp>.{md,json,csv}` e
`results/tuned_physics_baseline_<stamp>.{md,json,csv}` (o `.csv` é a história das 60 avaliações). Depois:
uma entrada no `results/CHANGELOG.md` com os dois artefatos e os vereditos, e o commit dos artefatos.

## 8. Frases para o artigo (uma por leitura de T1)

- *gêmeo*: *"Calibrating the physics engine's contact and drive parameters on the same training events by
  Bayesian optimisation ([n] evaluations) lowers its hold-out error from [a] to [b] m, and the behavioral twin
  still wins [k] of 10 events (p = [p]); within the envelope of these logs the tuned physics does not reach the
  identified behavioral plant."*
- *empate*: *"Once its contact and drive parameters are calibrated on the training events, the physics engine
  matches the behavioral twin on the hold-out ([a] against [b] m, [k] of 10 events); the behavioral plant
  delivers the same fidelity without contact parameters and at a fraction of the cost."*
- *sintonizado*: *"The calibrated physics engine beats the behavioral twin on the hold-out ([a] against [b] m,
  [k] of 10 events, p = [p]); the case for the behavioral plant rests on cost and identifiability, not on
  fidelity."*

## 9. O que não muda

O θ oficial, `config/*.json`, `data/`, `models/` e os artefatos existentes em `results/`. Nenhum parâmetro é
promovido; a checagem produz evidência para o texto, não um modelo novo.
