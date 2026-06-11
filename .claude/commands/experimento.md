Execute o ciclo experimental padrão.
1. Releia CLAUDE.md (critérios de aceite e guardrails).
2. Rode automation/run_all_experiments.m no MATLAB.
3. Verifique a saída: sem NaN, RMSE com ordem de grandeza plausível,
   bayesopt <= procest <= ideal na maioria dos splits (senão, investigue).
4. Confirme entrada no results/CHANGELOG.md com commit hash.
5. Resuma em 3 linhas: o que rodou, resultado principal, anomalia (se houver).
Nunca sobrescreva resultados antigos; nunca reporte número não executado.
