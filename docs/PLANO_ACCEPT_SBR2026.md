# Plano para *Accept* — SBR/LARS 2026

Derivado de `docs/REVISAO_INDEPENDENTE_SBR2026.md` (weak reject) e executado em
2026-08-10. O revisor listou 6 itens para *weak accept* e mais 5 para *accept*.

**Movimento central.** O revisor mostrou que o resultado em destaque — bater o
rSim — é o menos defensável do artigo, e que o resultado bem construído
(identificabilidade/diluição) estava subordinado a ele. Reposicionar resolve
**B1, B2, B3 e B5 de uma vez**, e o material do rSim que sai é justamente o que
financia o corte de páginas. Decisão do autor: aceito.

---

## 1. Estado dos itens do revisor

### Para *weak accept* (reescrita)

| # | Item | Status |
|---|---|---|
| 1 | Cortar para 6 páginas, tirando gordura do rSim e não do diagnóstico de yaw | **PARCIAL** — ver §3 |
| 2 | Reposicionar título/abstract/conclusão na identificabilidade; ideal vira comparador primário | **FEITO** |
| 3 | Abstract admite as três omissões (heading, 99,6% translacional, fitted-vs-untuned) | **FEITO** |
| 4 | Resolver B4, C1, C2, C3, C4, C5, C6 | **FEITO** |
| 5 | Refazer a Fig. 2 em inglês e legível | **FEITO** |
| 6 | Declarar segundos e eventos de hold-out; disponibilidade dos dados | **FEITO** (segundos/eventos); disponibilidade de dados **PENDENTE** |

### Para *accept* (trabalho novo)

| # | Item | Status |
|---|---|---|
| 7 | Especificar a configuração do rSim | **FEITO** (texto) — inicialização simétrica **NÃO** rodada |
| 8 | Decompor o gap em ganho / τ / atraso | **FEITO** |
| 9 | Wilcoxon e bootstrap agrupados por evento, com *n* efetivo | **FEITO** |
| 10 | Figura de trajetória real vs. modelos | **FEITO** |
| 11 | Fit de yaw em métrica comensurável entre regimes | **NÃO FEITO** — ver §4 |

---

## 2. O que foi implementado

### 2.1 Reposicionamento

- **Título** trocado para *"What Competition Logs Can Identify:
  Excitation-Dependent Behavioral Modeling of an Omnidirectional Soccer Robot"*.
  O anterior prometia *reality-gap mitigation*, que é alegação de transferência,
  e o artigo não treina nem transfere nenhuma política (B5).
  **Ação do autor: atualizar o registro preliminar no JEMS.**
- **Comparador primário** passa a ser a cinemática ideal: mesmo harness, mesma
  inicialização, mesmas janelas, então a única diferença entre as duas plantas é
  o modelo. O rSim vira um parágrafo de contexto que declara as duas assimetrias
  (default vs. ajustado; partida do repouso) e o fator 3 do warm-up.
- **Tabela III (twin vs. rSim) e Fig. 3 removidas.** Eram o aparato do resultado
  demovido. Economia ~33 linhas de coluna.

### 2.2 Análises novas (todas com artefato em `results/`)

**Decomposição do gap** (`gap_decomposition_20260809_2308.md`). Ligando os
grupos de parâmetros um a um, em `h_ref`:

| variante | e_pos (m) |
|---|---|
| ideal (K=1, τ=0, Td=0) | 0,1005 |
| + ganho K | 0,1093 |
| + constante de tempo τ | 0,0455 |
| modelo completo (+ atraso) | 0,0388 |

O ganho sozinho **piora**; o lag de primeira ordem responde por ~9/10 da
melhoria; o atraso pelo resto. Converte a correlação numa explicação e responde
à pergunta 3 do revisor.

**Estatística por evento** (`clustered_stats_20260809_2309.md`). Unidade de
análise = evento, não janela:

- 264 janelas densas, 49 não-sobrepostas → **73,5 s** de movimento pontuado,
  de **10 eventos**;
- twin vence em **10 de 10** eventos, rank-biserial **+1,000**;
- gap mediano **+0,069 m**, IC95% bootstrap por evento **[+0,038, +0,097]**;
- Wilcoxon pareado por evento **p = 9,8×10⁻⁴** — o menor valor atingível com
  n=10, e defensável, ao contrário do p=1e-13 por janela.

**Figura de trajetória** (`trajectory_holdout_en.png`). Medido vs. gêmeo vs.
ideal vs. rSim numa janela de hold-out. A janela é a de erro **mediano** em
1,5 s, não a melhor — declarado na legenda. Substitui a Fig. 3.

### 2.3 Correções pontuais

| Item | O que era | O que ficou |
|---|---|---|
| **C1** | *"differ by close to a fifth"* | 7–12%, valores exatos por DOF (12,1 / 6,7 / 10,4%) |
| **C2** | `m=4` sem justificar | declarado como teto da **média** de Td_vx e Td_vy |
| **C3** | gap com +0,093 e +0,091 | um número só; a re-execução não é mais citada como grandeza separada |
| **C5** | linha "Closed-loop" da Tabela V | renomeada "Closed-loop, regime-restricted" |
| **C6** | Modos A/B indefinidos | a subseção Baselines existia; havia uma **duplicata** que eu criei e removi |
| **C8** | Fig. 2 em português, 6 painéis | inglês, 3 painéis, legível |
| **B2** | rSim nunca especificado | timestep, frame de comando, wheel-speed desabilitado, substep e interpolação documentados |
| **B4** | Fig. 1 dizia ablação *pending* | legenda corrigida |
| **A6** | parágrafo "Gap" em II | removido, duplicava a Introdução |
| — | erro de siunitx `\SI{1/60}{s}` | corrigido; era a causa única dos 8 erros do Overleaf |

---

## 3. Páginas — o que falta

**Não verificável nesta sessão.** O mount Linux do ambiente serve cópias
truncadas dos `.tex` recém-editados e não expira; nenhum build confiável foi
possível após a rodada de edições. **Compilar no Overleaf e medir.**

Balanço estimado das mudanças:

| Mudança | Linhas de coluna |
|---|---|
| Tabela III removida | −14 |
| Fig. 3 removida | −19 |
| Parágrafo "Robustness and second baseline" absorvido | −8 |
| Parágrafo "Gap" (II) removido | −4 |
| Nota da Tabela II encurtada | −3 |
| Fig. de trajetória adicionada | +17 |
| Parágrafo de evidência/estatística por evento | +13 |
| Parágrafo de decomposição | +10 |
| Especificação do rSim | +7 |
| **Líquido** | **≈ −1** |

Ou seja: **o reposicionamento pagou pelas análises novas, mas não cortou
páginas.** Se o build fechar em 8, ainda faltam ~2 páginas para 6.

### Próximos cortes, na ordem (de `CORTES_PARA_6_PAGINAS.md`)

1. **A2** — Tabela I (unidades) → duas frases em III-F. ~10 linhas.
   *Conflito registrado:* a tabela foi reinserida por pedido explícito do autor
   em 2026-08-08 (M-F1). Reverter é decisão dele.
2. **A4** — detalhe da reconciliação com o Simulink. ~4 linhas.
3. **A7** — "Horizon grid" → nota de rodapé. ~5 linhas.
4. **B1** — Fig. 1 (arquitetura). ~49 linhas. **O maior item isolado.**
5. **B3** — Limitações em um parágrafo denso. ~12 linhas.
6. **B4** — "Coordinate conventions" → 4 linhas + ponteiro para o código. ~10.
7. **B5** — proveniência da razão de raios. ~9 linhas.
8. **B2** — comprimir a Introdução. ~22 linhas.

Somados: ~121 linhas ≈ 1,05 página. Com o líquido acima, isso leva a ~7
páginas. **Para 6 é preciso entrar na Faixa C**, e aí a decisão volta a ser de
conteúdo — a recomendação do plano de cortes continua valendo: a Rota A
(artigo sem figuras, todos os números preservados) é a única que fecha sem
destruir contribuição.

---

## 4. O que continua aberto

1. **Limite de páginas não confirmado para 2026.** O revisor deu 6 páginas com
   confiança alta (texto idêntico de 2019 a 2025) mas não conseguiu abrir o CFP
   de 2026. **Confirmar no JEMS antes de cortar mais.** Se forem 8, o artigo
   está essencialmente pronto.
2. **Inicialização simétrica no rSim** (item 7, segunda metade). O teste honesto
   é rodar as duas plantas partindo do repouso. Não rodado.
3. **Fit de yaw comensurável** (item 11). O revisor observa que 87% em logs de
   competição e 71% numa escada de degraus não estão na mesma escala, porque
   `‖y − ȳ‖` é dominado por coisas diferentes nos dois regimes. Precisa de uma
   métrica comum ou de uma justificativa explícita.
4. **Disponibilidade dos dados.** O texto libera código; não diz se os logs de
   competição e o dataset `rotate` também saem.
5. **R3** — recomputar a linha de malha fechada da Tabela V com o mesmo critério
   de hold-out. MATLAB R2026a com System Identification Toolbox está disponível.
6. **R1** — re-derivar `inverse_kinematics_solver.m` (assimetria √2). Não
   bloqueia o artigo.
7. **Referência [3]** sem venue nem ano (C12).
8. **Savitzky–Golay não é citado** em lugar nenhum do `.bib`.
