# Revisão maior — rodada 2 (2026-08-07)

Entrada: `Artigo_SBR_2026___Digital_Twin (2).pdf` (10 páginas) + o relatório
`docs/REVISAO_ESPECIALISTA_20260731.md` (borderline / weak accept).
Objetivo declarado: levar o artigo a *strong accept*.

---

## 1. Defeitos fatais encontrados no PDF entregue

| # | Defeito | Gravidade | Status |
|---|---|---|---|
| F1 | **Tabela II compilada de versão ANTIGA**: mostrava ω como `fixed placeholder` (K=1.000, τ=0.100, Td=0.000, fit "—") e a legenda dizia *"closed-loop yaw not identifiable"* — contradizendo o abstract, a Seção IV-A e a Tabela V do mesmo PDF | **Rejeição imediata** | RESOLVIDO (o repo já tinha a versão certa; era dessincronia Overleaf↔repo) |
| F2 | 10 páginas | Desk-reject | RESOLVIDO → 8–9 |
| F3 | Subseção III-G *"Coordinate conventions and replication"* **vazia** no PDF (só o título) | Grave | RESOLVIDO — subseção escrita de verdade |
| F4 | Dois `[TODO: ablation]` **visíveis** no PDF (Tabela IV e §IV-C) | Grave | RESOLVIDO — linha removida, ameaça à validade fica na Seção VI |
| F5 | Tabela IV **estourando a coluna**: expoentes de $p$ cortados ("1.6×10−") e a coluna `effect` inteira ausente | Grave | RESOLVIDO — `tabcolsep` + notação compacta |
| F6 | Figs. 2 e 3 em **duas páginas órfãs depois das referências** | Grave | RESOLVIDO — `stfloats` + parâmetros de float + `[!t]` |
| F7 | Título sem o subtítulo acordado | Médio | Era dessincronia; repo está correto |

> **Causa-raiz de F1 e F7:** o PDF não foi compilado a partir de `latex/` do
> repositório. Antes de submeter, **re-sincronize o Overleaf a partir do repo**.

---

## 2. O achado da rodada: o paradoxo B4 está resolvido

O revisor classificou B4 como o ponto onde *"um revisor cético vai parar
exatamente aqui"*: se 94,3% dos comandos de yaw estão abaixo do limiar de
atuação, o ganho ajustado deveria **deflacionar**, não inflar para 1,3–1,5 — e
não há joelho de zona morta no yaw de corpo.

**Hipótese testada.** A zona morta é elétrica, **por roda**, aplicada *depois*
da cinemática de comando. O limiar de corpo 0,58–0,60 rad/s só vale sob
**rotação pura** (o regime do dataset `rotate`, com vx=vy=0). Em jogo há
translação simultânea: as rodas já giram muito acima do clamp e o comando de
yaw não é zerado.

**Resultado** (`scripts/analyze_omega_excitation.py`, 37 437 amostras, 46 eventos):

| Grandeza | Valor |
|---|---|
| Validação do pipeline: fração < 0,600 rad/s (pooled / `shoot_to_goal`) | **94,33% / 77,26%** — reproduz os 94,3%/77,3% do artefato de 24/07 |
| Setpoint translacional por roda (RMS, mediana) entre as amostras sub-limiar | **23,98 rad/s** = **15,3×** o clamp de 1,567 rad/s |
| Amostras sub-limiar com ≥1 roda acionada | **97,3%–97,8%** (invariante a 9 conjuntos de ângulos) |
| Amostras com as 4 rodas clampadas | **2,2%–2,7%** |
| Termo de yaw como fração do setpoint de roda | mediana **1,0%**, p90 **5,7%** |

**Interpretação.** Os 94,3% **não** medem atuador inativo; medem **diluição**:
o que as rodas são mandadas fazer é 99% translação. Isso dissolve as duas
anomalias — nada é zerado (logo o ganho não deflaciona) e a zona morta engaja
em ~2% das amostras (logo não deve haver joelho) — e identifica o que o
estimador de malha fechada está medindo: com o yaw a 1% da atuação, a rotação
medida é dominada por perturbações que o comando não produziu, e sob
realimentação o controlador reage justamente a elas.

**Efeito colateral valioso:** isso **enfraquece o bloqueador B1**. A explicação
concorrente "amplitude/zona morta" deixa de ser concorrente — a zona morta é
mostrada não engajar. Resta diluição + realimentação, que são o mesmo
mecanismo, não dois rivais.

**Bônus (C9).** A estatística é robusta ao bracket: 92,5% em 0,5 rad/s → 97,6%
em 1,0 rad/s (72,8% → 87,9% em `shoot_to_goal`). O revisor previu que, se não
caísse, seria "evidência gratuita a favor". Não cai.

Artefatos: `results/omega_excitation_analysis_20260807_133917.json`,
`results/omega_threshold_sensitivity_20260807_133917.csv`.

---

## 3. Segundo achado: T5.4 estava bloqueado por engano

`phase0_replay/plant.py` foi lido linha a linha. A cadeia do gêmeo é
`comando → atraso → lag ZOH → ganho → rotação → integração trapezoidal`.
**Nenhuma cinemática de roda participa de qualquer resultado do artigo.**

Logo a assimetria √2 de `inverse_kinematics_solver.m` — real, e ainda a
corrigir (R1) — **não contamina o artigo**. A subseção de convenções de
coordenadas pôde ser escrita e fechada. Também corrigi a Fig. 1, cujo bloco
dizia "Inverse kinematics / SE(2) composition" (herdado do brief): o correto é
rotação corpo→campo e integração SE(2).

---

## 4. Respostas fechadas nesta rodada

| Item do revisor | O que foi feito |
|---|---|
| **B1** (correlation bias sobre-concluído) | Abstract já suavizado na rodada 1; agora a Introdução (C4), o título de §V-B, a Conclusão e §V-A também foram alinhados. §V-B passou a *"What the inflated closed-loop gain is measuring"*. A análise de diluição remove a explicação concorrente. |
| **B2** (IC de K_ω vs Ljung–Box) | IC **removido**. O artigo agora diz explicitamente por quê e passa a comparar pontos-estimativa (1,00 vs 1,3–1,5), sem teste formal. |
| **B3** (estimadores closed-loop não tentados) | "*simply does not excite*" substituído por afirmação de diluição quantificada; limitação mantida. |
| **B4** (paradoxo) | **RESOLVIDO** — §2 acima. |
| **B5** (rSim não sintonizado; ideal bate rSim) | Já na rodada 1; mantido, e o abstract diz "untuned". |
| **B6** (gap cresce ⇒ vantagem dinâmica) | Ablação removida do corpo; ameaça à validade explícita na Seção VI. |
| **C1/C2** (figura em PT, ilegível) | Painel `e_pos` já em inglês; figuras novas em largura adequada. |
| **C5** (Tabela V com critérios diferentes) | **Ainda aberto** — R3. É a objeção mais barata que sobra. |
| **C7** (definir *hold-out fit*) | **FECHADO** — Eq. (2) com a fórmula NRMSE do `compare`, sinal, por evento e média; lida de `automation/identify_trans_dof.m`. |
| **C8** (Tabela sem incerteza) | Dispersão entre eventos de hold-out na nota da tabela; IC de parâmetro explicitamente não reportado, com justificativa. |
| **C9** (sensibilidade dos 94,3%) | **FECHADO** — §2 acima. |
| **C10** (disponibilidade) | Parágrafo *Availability* escrito. **Falta o autor inserir o link anonimizado.** |
| **S1** (falta figura medido×simulado) | Fig. 2 = degrau de ω medido vs simulado. |
| **S6** (determinismo bit-exato 3×) | Reduzido a uma menção. |
| **Reprodutibilidade** | Savitzky–Golay (janela 7, ordem 2), partição por `rng(42)`, `Δt=1/60`, fórmula do fit — todos agora no artigo. |

---

## 5. Estado do build

`pdflatex` × 3 + BibTeX, em cópia isolada:
**0 erros, 0 citações indefinidas, 0 referências indefinidas, 0 `\TODO` visível,
0 overfull > 10 pt.**

Páginas: **9 com `unsrt.bst`** (a p.9 tem só 93 palavras — cauda das
referências). `IEEEtran.bst` não existe no sandbox e é sensivelmente mais
compacto (iniciais + `\footnotesize`), então o build real deve fechar em **8**.
**Ação do autor: confirmar no Overleaf com `IEEEtran.bst`.** Se sobrar uma
página, o próximo corte de menor dano é a Fig. 2 (≈0,3 pág.) ou o parágrafo
*Negative control*.

---

## 6. O que continua aberto

1. **R0** — corrigir a entrada de `results/CHANGELOG.md` (24/07, AÇÃO 2): a
   afirmação `R_efetivo = 3,3245` está errada; o valor verificado é
   **2,699070934** (= CAD em 10 algarismos).
2. **R1** — re-derivar `inverse_kinematics_solver.m` (linha ω uniforme
   `c = 0,09262446`). Já **não bloqueia o artigo**.
3. **R2** — ablação rSim + atraso casado (bloqueada: trajetórias não
   persistidas + `robosim` indisponível).
4. **R3 / C5** — recomputar a linha de malha fechada da Tabela V com o mesmo
   critério de hold-out. **Maior retorno por esforço entre os itens restantes.**
5. **C10** — inserir o link anonimizado de código/dados.
6. **B3 / R10** — estimadores closed-loop-aware (IV, two-stage). Extensão JINT.

---

## Linha para `results/CHANGELOG.md` (append)

```
- 2026-08-07 | REVISAO MAIOR RODADA 2 (artigo) | seed 42 | NENHUM modelo re-treinado; data/ e models/ intocados; results/ apenas ARTEFATOS NOVOS. ANALISE: scripts/analyze_omega_excitation.py (NOVO) resolve o bloqueador B4 da revisao de 31/07 -- a zona morta por roda NAO engaja em competicao (97.3-97.8% das amostras sub-limiar tem >=1 roda acima do clamp de 1.567 rad/s; apenas 2.2-2.7% com as 4 clampadas; setpoint translacional RMS mediano 23.98 rad/s = 15.3x o clamp), logo os 94.3% medem DILUICAO (yaw = 1.0% mediano do setpoint de roda), nao inatividade; conclusao invariante a 9 conjuntos de angulos de roda (angulos nao documentados em config/robot_geometry.json). VALIDACAO: reproduz 94.33% pooled / 77.26% shoot_to_goal de identificacao_omega_20260724.md Etapa 4. C9 FECHADO: sensibilidade 92.5%(0.5) -> 97.6%(1.0 rad/s). Artefatos: results/omega_excitation_analysis_20260807_133917.json, results/omega_threshold_sensitivity_20260807_133917.csv. C7 FECHADO: fit = NRMSE do compare() em simulacao, por evento, media no hold-out (lido de automation/identify_trans_dof.m); SgWin=7/SgOrder=2 e particao rng(42) agora no artigo. PAPER: 7 defeitos fatais do PDF de 07/08 corrigidos (Tabela II com omega placeholder de versao ANTIGA -- dessincronia Overleaf/repo; 10 paginas; subsecao III-G vazia; 2 TODO visiveis; Tabela IV estourando coluna; Figs.2-3 orfas apos as referencias; titulo sem subtitulo). B2: IC de K_omega REMOVIDO (Ljung-Box rejeita brancura). B1: narrativa causal alinhada em Intro/V-B/Conclusao. T5.4 DESBLOQUEADO: plant.py nao usa cinematica inversa em nenhum resultado, logo a assimetria sqrt(2) de inverse_kinematics_solver.m nao contamina o artigo (R1 continua pendente). Build: 0 erros, 0 refs indefinidas, 0 TODO visivel; 9 pag. com unsrt.bst, esperado 8 com IEEEtran.bst -- CONFIRMAR NO OVERLEAF. Docs: docs/REVISAO_MAIOR_20260807_RODADA2.md
```
