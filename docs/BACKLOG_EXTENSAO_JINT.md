# Backlog para a extensão JINT — conteúdo cortado do SBR/LARS 2026

> Regra do CFP: nada é descartado — o que saiu do paper de 6 páginas por limite
> de espaço fica registrado aqui para a versão estendida (JINT).
> Data: 2026-07-31. Decisões de corte aprovadas pelo autor (pacote A–F +
> reservas), sessão de finalização do artigo (ver docs/LOG_FINALIZACAO_ARTIGO_20260731.md).

## Cortes de texto (conteúdo condensado, não removido do arquivo-fonte)

| # | Item cortado/condensado | Onde estava | O que a extensão deve recuperar |
|---|---|---|---|
| A | Limitations 9→4 parágrafos | `06_limitations.tex` (versão íntegra no git anterior a 2026-07-31) | Tratamento completo por limitação: bracket empírico da zona morta e ausência de escada fina 0.5–1.0 rad/s; discussão de mitigação por pré-registro/determinismo; parágrafos dedicados às constantes cinemáticas (R/r 2.61 vs 2.699, deriva de versão de firmware; 0.3 rad/s herdado sem proveniência — results/reidentificacao_20260724.md Parte D); Ljung-Box e coloração sgolay; fairness do rSim; escopo in-distribution; ambiente Linux/ODE do rSim |
| B | bayesopt 9-param como subseção + discussão | `04_results.tex` IV-E (agora parágrafo) e `05_discussion.tex` V-D (removida) | História completa do controle negativo: v1 overfit por dado (K_w→piso 0.516, 5 eventos), v2 com proxy analítico no loop (Fase 0 GATE Spearman ρ=0.9992, 25 θ × 6 ev; ~1.6 ms/sim vs ~9.5 s/sim), treino 18 eventos/400 avals, ARD balanceado, gate hold-out (bate ideal, não bate vx/vy v2 — empata rotação, perde translação). Artefatos: results/phase0_proxy_ranking_20260614_2105.csv, eval_bayesopt_v2_holdout_20260614_2130.csv, figs F0/F4/F6/F7 |
| C | Figura de distribuição de bins | `04_results.tex` (fig:bins removida) | results/figs/bins_20260619_000422.png (e a regeneração pós-correção de raio bins_20260724_155551.png — mesma distribuição 264/1/0) |
| D | Discussão V-A e V-E íntegras | `05_discussion.tex` | Versões longas dos argumentos (framing DOF vs dado; lição metodológica com o parágrafo de calibração de escopo e_pos/e_ang) |
| E | Parágrafos de robustez completos | `04_results.tex` (Mode B; twin vs ideal; heading error) | Tabela Modo B completa (results/eval_twin_vs_rsim_modeB_20260617_0031.md); análise twin vs ideal por horizonte (results/phase0_metrics_report_20260616_0811.md); medianas de e_ang por horizonte tabuladas (results/window_errors_eang_twin_vs_ideal_20260731_023856.csv) |
| F | Related Work eixos (a)/(c) detalhados | `02_related_work.tex` | Descrições específicas por trabalho (validação de AGV comercial por algoritmo compartilhado; sincronização físico-virtual como métrica; trade-off fidelidade×custo do grey-box; ressalva de domínio do benchmark sim2real) |

## Figuras que não entraram (geradas e prontas)

| Figura | Arquivo | Nota |
|---|---|---|
| Fit hold-out vx/vy (overlay medido×simulado) | `latex/figures/fit_holdout_vxvy.png` + `results/figs/fit_holdout_vxvy_20260731_024049.{png,pdf}` | Fits Python reproduzem MATLAB a ≤0.05 p.p. (results/fit_holdout_vxvy_20260731_024049.csv). Custaria ~0.46 pág. |
| Resposta ao degrau de ω (medido×simulado, treino+hold-out) | `latex/figures/omega_stepresponse.png` = `results/figs/identificacao_omega_stepresponse_20260724_1727.png` | Evidência direta do resultado central de ω; na extensão, usar figure* largura dupla |
| Fig. ganho×amplitude (reserva de corte) | `latex/figures/omega_gain_amplitude.png` | Se cortada na rodada final de páginas, recuperar na extensão |

## Pendências técnicas herdadas (para a extensão, não para o SBR)

1. **Painel e_ang da Fig. twin vs rSim com ω promovido**: irrecuperável sem re-executar o rSim (trajetórias do run 20260617_0030 não foram persistidas; robosim indisponível no ambiente atual — bloqueio pré-existente). A extensão deve re-rodar `eval_twin_vs_rsim` com θ promovido e persistir trajetórias.
2. **Validação rotacional contra distribuição rica em rotação** (hold-out de competição tem 0 janelas mistas / 1 rot-dominada).
3. **Cross-log / segundo dataset / multi-robô** (P5 do plano).
4. **SLR completa** (Kitchenham) no lugar da mini-revisão de 20 refs.
5. **Grade de horizonte unificada** entre os dois harnesses (desvio D5) via re-execução de uma das campanhas.
