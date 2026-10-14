# ROADMAP — Refatoração do Doutorado (Gêmeo Digital SSL)

> **HISTÓRICO — superseded by `docs/SPEC_DTSSL.md` em 02/09/2026; mantido por rastreabilidade.**
> Plano de junho/2026 (artigo de qualificação). O artigo foi submetido ao SBR/LARS 2026 (ver
> `docs/LOG_FINALIZACAO_ARTIGO_20260731.md`), ω foi identificado e promovido em 24/07/2026 (Trilha B, F5,
> antecipada) e a estrutura do repositório mudou (`automation/` → `matlab/dtssl` + `matlab/legacy`;
> `slr/incluidos.bib` nunca existiu — a bibliografia é `latex/refs/references.bib`). Estado atual: `CLAUDE.md`.

**Princípio:** refatorar ≠ recomeçar. A metodologia grey-box por DOF (G_i(s) = K_i/(τ_i·s+1)·e^(−Td_i·s), 9 parâmetros, fidelidade observacional comportamental) está validada e **permanece**. Refatoramos: definições formais, revisão de literatura, documentação, automação e escrita.

**Restrição dura:** artigo de qualificação submetido até **31/07/2026**. Hoje: 10/06/2026 → ~7 semanas × 10h = ~70h.

**Divisão de trabalho:** você decide e valida; Claude executa e documenta. Claude Code = implementação (MATLAB/Python, pipelines, experimentos). Claude Cowork = SLR (triagem, extração), documentos, escrita.

---

## Trilha A — Artigo de qualificação (caminho crítico, intocável)

| Fase | Semanas | Suas horas | Entregável | Automação |
|---|---|---|---|---|
| **F0 — Infraestrutura** | 10–16/06 | 3h | Monorepo com `CLAUDE.md`, overlay aplicado, comandos `.claude/` funcionando | Claude Code aplica o overlay e ajusta caminhos |
| **F1 — Definição formal** | 10–17/06 | 3h | `docs/01_definicao_pesquisa.md`: problema, lacuna, tese em 1 frase, QPs, objetivos, hipóteses, escopo in/out — **validado com orientador (Gate G1: 17/06)** | Cowork gera drafts a partir do template; você edita e decide |
| **F2b — Pipeline experimental** | 11/06–08/07 | ~16h | (1) ω fechado: `sysid_initial_v2.mat` aprovado nos critérios (fit≥60%, K_w∈[0.5,2.0], τ_w∈[0.02,0.5]s, Td_w≤0.15s); (2) teste de excitação persistente formalizado (**Gate G2: 24/06**); (3) bayesopt vs. baselines (ideal, procest); (4) **figura central** RMSE multi-horizonte (**Gate G3: 08/07**) | Claude Code roda `automation/run_all_experiments.m`, gera tabelas/figuras; você valida números |
| **F2a — SLR-lite (Kitchenham §9)** | 13/06–08/07 | ~10h | Protocolo → busca → triagem → extração → tabela de síntese (30–60 primários) → vira Seção 2 do artigo | `slr_pipeline.py` deduplica e gera planilha; Cowork faz triagem fase 1 (você revisa amostra + casos DÚVIDA); leitura crítica dos incluídos é **sua** |
| **F3 — Escrita do artigo** | 08–29/07 | ~20h | Draft IMRaD completo (**Gate G4: 22/07**), revisão do orientador, **submissão 29–31/07** (JINT ou MDPI Robotics/Sensors) | Cowork redige seção a seção a partir de `docs/` + `results/` + `slr/incluidos.bib`; comando `/secao-artigo` |
| Buffer + reuniões | distribuído | ~10h | — | — |

### Gates e planos B
- **G1 falha** (definição não validada): reduza para confirmar apenas QPs e contribuição central; resto vai para a qualificação.
- **G2 falha** (excitação insuficiente para Td): fixe Td via estimativa de atraso por correlação cruzada, otimize só (K, τ) com bayesopt; reporte como limitação + plano de coleta dedicada pós-qualificação. **Não trave o artigo nisso.**
- **G3 atrasa**: corte ablations; figura central + 1 tabela bastam.
- **SLR atrasa**: no artigo, apresente como *related work* estruturado (mapping rápido); a SLR completa entra no documento de qualificação.

---

## Trilha B — Doutorado completo (pós-submissão)

| Fase | Período | Entregável |
|---|---|---|
| **F4 — Qualificação** | ago–out/2026 | Documento de qualificação = artigo expandido + SLR completa (relatório técnico Kitchenham, Tabela 8) + cronograma da tese + **decisão go/no-go da vertente RL** com critérios explícitos (fidelidade atingida? dados suficientes? tempo?) |
| **F5 — Coleta dedicada** | pós-quali | Experimentos de rotação pura para identificação rigorosa de ω; reidentificação com excitação garantida |
| **F6 — Vertente 2 (se go)** | 2027 | Residual learning sobre o grey-box e/ou RL no híbrido Simulink + MuJoCo/MJX; grSim/ER-Force como validação SSL-fiel (benchmark explícito do grSim — a banca vai cobrar) |
| **F7 — Tese** | 2027–mid/2028 | Escrita contínua: cada experimento já nasce como seção (`thesis/` espelha `docs/` + `results/`); defesa ~mid/2028 |

---

## Camada de automação (como o Claude trabalha aqui)

1. **`CLAUDE.md` na raiz** — contexto permanente: arquitetura, convenções, critérios de aceite, guardrails. É o que evita o Claude "reinventar" seu projeto a cada sessão.
2. **Comandos custom** (`.claude/commands/`): `/triagem`, `/experimento`, `/secao-artigo` — workflows repetíveis em 1 comando.
3. **Proveniência**: todo resultado gravado com commit hash + seed + θ usado. Números no artigo só de execuções reais registradas em `results/`.
4. **Integridade e declaração de IA**: mantenha `AI_LOG.md` (o que o Claude fez, o que você validou). Periódicos exigem declaração de uso de IA; triagem assistida na SLR deve ser reportada na seção de método da revisão. Referências: apenas de `slr/incluidos.bib` — nunca geradas de memória.

## Próximos 3 passos (esta semana)
1. Aplique o overlay no seu repo existente (não substitui `src/`), revise e personalize o `CLAUDE.md` — 30 min.
2. Preencha `docs/01_definicao_pesquisa.md` com o Cowork e leve à reunião com o orientador (Gate G1).
3. No Claude Code: rode `identify_omega_from_splits.m`, valide critérios de aceite, e execute o teste de excitação (`std(cmd_vw)` + posto da matriz de regressores).
