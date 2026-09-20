# Plano derivado da revisão V2 — executado em 2026-08-10

Fonte: `docs/REVISAO_INDEPENDENTE_V2_SBR2026.md` (**weak accept**, condicionada a
B1 e B2). O revisor listou nove itens em "o que moveria minha nota para cima";
com 1–5 ele sobe para **accept**, com 1–9 "accept com entusiasmo".

Instrução do autor nesta rodada: **não reduzir páginas por enquanto** — priorizar
conteúdo. O artigo passou de 6 para **7 páginas**, o que é esperado: foram
adicionados uma `figure*` e uma tabela que o revisor cobrava.

---

## 1. Itens do revisor — estado

| # | Item | Estado |
|---|---|---|
| 1 | Caber em 6 páginas | **ADIADO** por decisão do autor. Hoje 7 páginas. |
| 2 | Figura do resultado principal (e_pos × horizonte + dot plot por evento) | **FEITO** — Fig. 2, `main_result_en.png` |
| 3 | Citar a Fig. 1 no texto | **FEITO** na rodada anterior |
| 4 | Ablação isolada e ordem-robusta + braço de condição inicial | **FEITO** — e **mudou a conclusão** |
| 5 | Reescrever "the data regime as the only difference" e definir o placeholder | **FEITO** na rodada anterior |
| 6 | Reconciliar/marcar os números do bayesopt | **FEITO** (marcados incomparáveis) |
| 7 | Esclarecer hold-out de identificação × de fidelidade (vazamento) | **FEITO** — verificado e declarado |
| 8 | Corrigir 0,038 vs 0,039 e "halves in all ten events" | **FEITO** na rodada anterior |
| 9 | Trocar "practical restatement of persistent excitation" + medida espectral para ω | **FEITO** — com número novo |

---

## 2. O que as análises novas mudaram no artigo

### 2.1 A ablação ordem-robusta refutou a afirmação anterior

O artigo dizia que **o lag carrega a melhoria e o dead time é correção menor**.
Isso vinha de uma ablação cumulativa que ligava τ antes de Td — exatamente o
artefato de ordem que o revisor previu. O fatorial completo $2^3$ com atribuição
de Shapley (média sobre todas as ordens) diz outra coisa:

| grupo | contribuição | fração |
|---|---|---|
| constante de tempo τ | +0,034 m | **55%** |
| tempo morto Td | +0,027 m | **43%** |
| ganho K | +0,001 m | 2% |

**τ e Td são contribuintes comparáveis**, não um dominante e um marginal. O
texto foi corrigido e agora declara a redundância parcial entre os dois termos.
Artefato: `results/ablation_orderfree_20260810_1021.md`.

### 2.2 O braço de condição inicial (o item que vale *accept*)

O revisor apontou que a cinemática ideal é *memoryless*, então a semeadura de
velocidade inicial só beneficia a planta dinâmica — e que "adicionar o lag" é
justamente o passo que cria estado capaz de consumi-la. Medido:

| planta | condição inicial | e_pos em h_ref |
|---|---|---|
| cinemática ideal | irrelevante (sem estado) | 0,101 m |
| **extrapolação de velocidade constante** | usa **só** a IC, ignora comandos | **0,160 m** |
| FOPDT completo | parte do repouso, como o rSim | 0,114 m |
| FOPDT completo | IC medida | **0,039 m** |

Resultado honesto e mais interessante do que o anterior: **é efeito conjunto**.
A IC sozinha é pior que a ideal; a dinâmica sem IC também não bate a ideal; só a
combinação chega a 0,039 m. O artigo agora declara isso e argumenta que a
velocidade medida é parte da interface do modelo (um gêmeo rodando junto ao robô
tem essa estimativa), não informação privilegiada.

### 2.3 Diagnóstico de excitação para ω (fecha C8, C9, Q7, Q8)

O revisor observou, com razão, que "fração da atuação" não é excitação
persistente, que é propriedade espectral, e que o artigo nunca deu para ω nada
análogo ao 0,99 de vx/vy. Medido nos logs, com o comando alinhado pelo Td:

| DOF | corr(cmd, meas) | R² |
|---|---|---|
| vx | 0,979 | **0,959** |
| vy | 0,968 | **0,936** |
| ω  | 0,746 | **0,557** |

O comando de yaw explica **56%** da variância da rotação medida, contra 94–96%
na translação. Isso substitui a afirmação não medida ("dominated by
disturbances") por um número, e a frase sobre excitação persistente foi
reescrita para dizer que os dois diagnósticos são complementares.
Artefato: `results/excitation_per_dof_20260810_1022.md`.

### 2.4 Não há vazamento — verificado

O hold-out de fidelidade (10 eventos, `config/holdout_events.json`) **contém**
o hold-out de identificação (5 eventos), e os outros 5 são `shoot_to_goal`, que
não entrou em nenhum dos dois ajustes (vx veio de `front_to_back`, vy de
`side_to_side`). Nenhum evento participou de seleção de parâmetro e de
pontuação de fidelidade ao mesmo tempo. Declarado no texto.

### 2.5 O artigo se autoacusava sem base (C6)

O texto afirmava que o `e_ang` do modelo **excede** o do rSim em horizontes
longos, e o revisor cobrou o número do rSim, que nunca era dado. Ao medi-lo:

| h (s) | modelo | ideal | rSim |
|---|---|---|---|
| 0,10 | **0,013** | 0,023 | 0,026 |
| 0,40 | **0,044** | 0,067 | 0,064 |
| 1,50 | **0,090** | 0,095 | 0,094 |

O modelo é **o menor dos três em todos os horizontes**. A afirmação anterior era
falsa e foi corrigida para o que os dados mostram: a vantagem existe mas
*encolhe* com o horizonte, o que é coerente com o yaw ser o canal que os logs
não constrangem. Artefato: `results/epos_eang_three_models_20260810_1022.md`.

---

## 3. Figuras

**Fig. 2 (nova, `figure*`)** — resolve B3, que era a ausência de qualquer
figura ou tabela para o resultado principal. Painel (a): e_pos × horizonte para
modelo, ideal e rSim. Painel (b): os 10 eventos de hold-out pareados em h_ref.
Arquivo: `latex/figures/main_result_en.png`, gerador `scripts/fig_main_result.py`.

**Tabela nova (`tab_three_models.tex`)** — e_pos e e_ang das três plantas nos
seis horizontes. Dá ao leitor os números que sustentam a figura e fecha C6.

**Diagrama-especificação** — `results/figs/SPEC_main_result.png`. Não é a figura
do artigo: é o contrato visual dela, com seis marcadores numerados explicando o
que cada elemento precisa conter e por quê. Para ajustar, basta dizer o número
do marcador.

---

## 4. Título

Devolvido à forma pedida: *"A Behavioral Model for Reality-Gap Mitigation in
Digital Twins of Omnidirectional Soccer Robots"*.

**Risco registrado, apontado em duas revisões independentes:** o artigo não mede
transferência — nenhuma política é treinada, nada é transferido — então
"reality-gap mitigation" promete mais do que a evidência entrega. Mitigado no
abstract e na conclusão, que declaram o escopo como fidelidade preditiva em
replay. Se um revisor atacar por aqui, a defesa é o escopo declarado, não o
título.

---

## 5. Aberto

1. **Páginas: 7, limite 6.** Adiado por decisão do autor. O plano de cortes
   continua em `docs/CORTES_PARA_6_PAGINAS.md`; note que ele foi escrito antes
   desta rodada e a Fig. 2 e a nova tabela são agora os maiores flutuantes.
   Os candidatos naturais passam a ser a Fig. 1 (degrau de ω) e a compressão
   da Seção IV-C.
2. **Padrão estatístico do controle negativo** (C3 da V2): o bayesopt continua
   reportado por janela, não por evento. Marcado como incomparável, não
   recomputado.
3. **Gate pré-registrado × gate usado** (C4 da V2): o método define o gate por
   janela e o resultado principal usa pareamento por evento. A troca é
   defensável mas o artigo não diz se foi decidida antes ou depois de ver os
   dados.
4. **URL anonimizado é placeholder.** Trocar antes de submeter.
5. `katyara2024benchmarking` está no `.bib` e não é citada.
6. **R3** (recomputar a linha closed-loop com o mesmo critério de hold-out) e
   **R1** (assimetria √2 na cinemática inversa) seguem pendentes; nenhum dos
   dois bloqueia o artigo.
