# Plano V3 — executado em 2026-08-10

Base: `docs/REVISAO_INDEPENDENTE_V3_SBR2026.md` (**weak reject**, "com os
bloqueadores corrigidos, sobe para accept"). Pedido do autor: corrigir de forma
assertiva e definitiva, focar nos bloqueadores, eliminar contradições, remover
informação desnecessária, e responder sobre originalidade e reprodutibilidade.

---

## 1. Bloqueadores da V3

| # | Bloqueador | Estado |
|---|---|---|
| B1 | ~2 páginas acima do limite | **PARCIAL** — 8 páginas; ver §4 |
| B2 | Frase quebrada na Conclusão (um `%` engoliu meia frase) | **CORRIGIDO** |
| B3a | §V-C dizia que o heading perde para o rSim; Tab. II diz que ganha em todos os horizontes | **CORRIGIDO** |
| B3b | C1 dizia "o lag, não o dead time"; abstract dizia "partes comparáveis" | **CORRIGIDO** |
| B4 | URL do artefato retorna 404 | **É PLACEHOLDER** — trocar antes de submeter |
| B5 | `v0` não-causal poderia enxergar dentro da janela | **MEDIDO E FECHADO** |

Sobre B5, o revisor supôs Savitzky–Golay (±3 amostras). O harness de avaliação
usa `np.gradient`, diferença central de **uma** amostra; o SG está no caminho de
identificação. Recomputando tudo com diferença para trás, estritamente causal:
o erro sobe (0,039 → 0,047 m em h_ref) mas o **gap por evento aumenta** (+0,069
→ +0,071 m) e continua 10/10 no mesmo p. Artefato:
`results/causal_ic_check_20260810_1102.md`. Declarado no artigo.

---

## 2. Contradições numéricas — varredura definitiva

Fixado **um valor canônico por grandeza**, todos da mesma execução
(`results/epos_eang_three_models_20260810_1022.md`, que é a fonte da Tabela II
e da Fig. 2):

| grandeza | antes | agora |
|---|---|---|
| e_pos do modelo em h_ref | 0,038 **e** 0,039 | **0,039** |
| e_pos do rSim em h_ref | 0,129 **e** 0,131 | **0,129** |
| gap contra o rSim | +0,093 / +0,282 (campanha antiga) | fator 3, sem números incomensuráveis |
| fit closed-loop de ω | 52,6% **e** 44,8% | **44,8%**, recomputado sob o critério do artigo |
| K_ω em malha fechada | 1,35 / 1,3–1,5 / 1,307 / 1,378 | **1,378** (uma descrição); a faixa 1,3–1,5 fica rotulada como outra grandeza |

A raiz do "K_ω com quatro valores" era o ajuste closed-loop descrito em quatro
lugares. Agora há **uma** descrição, no início de IV-D.

---

## 3. Originalidade — o que mudou

Era 3/5 nas três revisões: FOPDT é livro-texto e viés de malha fechada é
clássico. A diluição aparecia como *explicação de um resultado negativo*.

Passou a ser um **procedimento de triagem reutilizável**, declarado em C4 e
desenvolvido na Discussão: duas quantidades computáveis do log **antes** de
ajustar qualquer modelo — a *actuation share* e a *explained variance* — com
regra de decisão e os três DOFs deste robô como validação (94–96% contra 56%).
Isso muda a contribuição de "documentamos um caso" para "propomos uma triagem",
que é o que sustenta nota mais alta sem dado novo.

Também foi corrigida a formulação anterior, tecnicamente errada, de que isso
seria "uma reformulação prática de excitação persistente" — excitação
persistente é propriedade espectral; as duas medidas são complementares.

---

## 4. Páginas — a decisão que resta

Build limpo (0 erros, 0 refs indefinidas, 0 TODO): **8 páginas** com proxy do
`IEEEtran.bst`, sendo 170 palavras na página 8. Corpo: ~6.100 palavras.

Uma página IEEE A4 comporta ~950 palavras. Para 6 páginas com referências
(~370 no IEEEtran), o corpo precisa caber em ~5.330. **Faltam ~800 palavras.**

Os cortes de redundância pura estão esgotados — nesta rodada saíram o parágrafo
de contexto do rSim (~55 palavras), a descrição duplicada do ajuste closed-loop
(~90) e a compressão de IV-D (~120). **Todo corte restante remove conteúdo que
algum revisor pediu explicitamente.** O menu, com o custo declarado:

| Corte | Economia | O que se perde | Quem pediu o que sai |
|---|---|---|---|
| Fig. 1 (degrau de ω) | ~0,20 pág. | única evidência medido-vs-simulado | S1 da 1ª revisão |
| Tabela II (três modelos) | ~0,17 pág. | os números de e_ang do rSim; a Fig. 2 cobre e_pos | C6 da 2ª revisão |
| Parágrafo da condição inicial | ~0,18 pág. | a resposta ao B5 e ao "quanto é IC" | item 4 da 2ª, B5 da 3ª |
| Procedimento de triagem (Discussão) | ~0,20 pág. | o ganho de originalidade desta rodada | recomendação desta sessão |
| Ablação de Shapley | ~0,15 pág. | a atribuição ordem-independente | B4 da 2ª revisão |

Qualquer combinação que some ~0,85 pág. fecha em 6. **Nenhuma é indolor.**

A alternativa honesta, já registrada duas vezes: o artigo em 6 páginas não
comporta as duas contribuições (fidelidade translacional **e** diagnóstico de
identificabilidade). Um artigo só sobre a triagem — que é a parte original —
caberia com folga e seria mais difícil de rejeitar.

---

## 5. Reprodutibilidade — a pasta existe e está completa

`open-source/`, **63 arquivos**:

- `phase0_replay/` (20 módulos), `matlab/` (6), `scripts/` (**18**, um por claim)
- `config/` (4 JSON), `docs/` (pré-registro), `results/` (**14** artefatos), `figures/` (4)
- `requirements.txt`, `README.md` reescrito

O README agora tem uma **tabela de um comando por afirmação do artigo**, as
definições operacionais (hold-out fit, free run, actuation share, explained
variance, placeholder) e a nota sobre a condição inicial causal. Todos os
scripts desta sessão estão inclusos.

Falta só uma coisa: **trocar o URL placeholder** `anon-ssl-dt/behavioral-twin-ssl`
pelo repositório anonimizado real. Enquanto for 404, o revisor não consegue
verificar o pré-registro nem o determinismo, que são os argumentos de rigor do
artigo.

---

## 6. Título

Aplicado: *"A Behavioral Model for Digital Twins of Omnidirectional Soccer
Robots: Diagnosing Identifiability from Competition Logs"*.

Removido "for Reality-Gap Mitigation", que prometia transferência — treinar e
transferir uma política — algo que o artigo não faz e que três revisões
independentes apontaram. O reality gap permanece como motivação na Introdução,
onde é legítimo. **Atualizar o registro no JEMS.**

---

## 7. Aberto

1. **Páginas** — decisão do §4.
2. **URL do repositório** — placeholder.
3. `vx` tem **um** evento de hold-out (n=1) com 46 disponíveis. Re-particionar é
   barato e removeria uma objeção recorrente.
4. Gate pré-registrado por janela × resultado por evento: declarado no texto,
   não reconciliado.
5. `katyara2024benchmarking` está no `.bib` e não é citada.
