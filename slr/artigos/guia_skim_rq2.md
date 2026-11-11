# Guia de Skim — RQ2 (44 estudos) · Sprint 2

**Objetivo do skim:** decidir INCLUI ou EXCLUI cada estudo em ~10 min, e deixar o registro no Notion pronto para a extração da Sprint 3. Não é leitura profunda — é veredito + 3 anotações.

**RQ2:** *Quais métricas e protocolos são usados para medir a fidelidade de gêmeos digitais de robôs móveis?*

---

## 1. Rotina por artigo (10 min, cronometrado)

| Min | O que ler | O que procurar |
|-----|-----------|----------------|
| 0–2 | Abstract + figuras/tabelas (folheie tudo) | Tem robô FÍSICO? Tem comparação físico↔virtual? |
| 2–5 | Seção de método/experimento | COMO a fidelidade é medida: métrica, sinal comparado (pose? velocidade? torque?), protocolo |
| 5–8 | Resultados + tabelas de erro | Números de fidelidade (RMSE, erro %, correlação…), condições do teste |
| 8–10 | Veredito + registro no Notion | Status, Notes (template abaixo), Type se survey |

Regra de ouro: **estourou 10 min sem achar a medição de fidelidade → provavelmente ela não existe → EC1.**

## 2. Árvore de decisão (na ordem)

1. **Existe robô/sistema físico no experimento?** Não → **EC1** (regra: DT/simulação sem contraparte física e sem medição de fidelidade → EC1).
2. **É artigo de controle puro** (rastreamento/estabilização, sem DT nem identificação por dados)? Sim → **EC1** (caso Rahib-4053).
3. **O domínio é robótica?** Não (água, agricultura, manufatura sem robô…) → **EC1** (caso Biswadip-4545 — cuidado com títulos que prometem "DT accuracy").
4. **Há medição quantitativa físico↔virtual** (métrica de fidelidade, sim2real gap medido, validação experimental do modelo)? Sim → **INCLUI**.
5. Mede fidelidade mas em robô não-móvel (braço, drone…)? → INCLUI se o **método/métrica é transferível** ao seu cenário; senão EC1. Anote a dúvida em Notes para revisão.
6. Survey/review? → INCLUI se peer-reviewed e relevante; marque `Type = Survey` (alimenta snowballing, não a síntese primária).
7. Sem avaliação empírica nenhuma (posição/visão)? → **EC2**. Idioma inacessível → **EC4**. PDF com conteúdo ≠ do prometido → reavaliar EC.

Na dúvida entre incluir/excluir: **inclua** — a Sprint 3 (DARE) elimina os fracos. Exclusão no skim só com critério claro.

## 3. Registro no Notion (por artigo, ~1 min)

- **INCLUI:** Status → `Read in Progress` não; use `Finished` só na Sprint 3. No skim: mantenha `Recommended Full Read`, Selection Stage → `Included`, e Notes com o template.
- **EXCLUI:** Selection Stage → `Excluded Full-Text`, Exclusion Criterion → ECx, RQ Mapping → limpar, Notes com justificativa de 1–2 frases.

Template de Notes (incluídos):
```
SKIM dd/mm: [robô/plataforma] | fidelidade medida por [métrica] sobre [sinal comparado]
| protocolo: [experimento] | relevância p/ tese: alta/média/baixa | [obs]
```
Esses 4 campos são exatamente o que a extração da Sprint 3 vai pedir — skim bem anotado = extração 2× mais rápida.

## 4. Ordem de leitura sugerida (44 RQ2)

1. Comece pelos 5–6 mais próximos da tese (omnidirecional/SSL, sim2real gap medido) para calibrar o "ótimo" da régua.
2. Depois, do mais recente (2026) ao mais antigo — os antigos que sobreviverem à régua calibrada são os que importam.
3. Capítulos Springer de coletânea por último: são os de maior taxa de EC1 no lote 1 (4/6) — não deixe eles roubarem energia do início.

## 5. Cadência e controle de qualidade

- **Meta:** ~21 estudos/dia útil no total da Sprint 2; para os 44 de RQ2, 2–3 dias de trabalho focado.
- **Teste-reteste (protocolo):** na 1ª semana, re-julgue 10% (≈4–5 estudos de RQ2) 2+ dias após o primeiro veredito, sem olhar a decisão anterior. Kappa baixo → recalibrar régua antes de seguir.
- **Gatilho 20/09:** ritmo < 16/dia → replanejar com a orientadora (cortar RQ1 por amostragem, p.ex.).
- Fim de cada dia: conte incluídos/excluídos (2 min) — alimenta a figura da reunião semanal.

## 6. Lote 2 (RQ3, 129 estudos) — download em paralelo

CSV `lote2_rq3_downloads.csv` na sua pasta: 33 ABERTOS (arXiv/MDPI/preprints — baixe primeiro, sem fricção), 84 via CAFe, 12 para verificar/difíceis, 1 já baixado no lote 1 (SLR-2020-A-1974, dual RQ2+RQ3). Regra dos 10 min por artigo nos difíceis → EC6.
