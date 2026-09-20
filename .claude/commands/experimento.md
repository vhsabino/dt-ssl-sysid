Execute o ciclo experimental padrão do gêmeo (refatoração 2026-09-02).
1. Releia CLAUDE.md (θ oficial, convenções, guardrails) e docs/SPEC_DTSSL.md.
2. Rode a suíte: `python -m pytest` (com dataset DVC) — goldens e round-trips devem passar.
3. Rode a análise pedida: `dtssl analysis list` → `dtssl analysis run <nome> --out results/`
   (ou `dtssl gate twin-vs-ideal`, `dtssl replay <label> <evento>`).
4. Verifique a saída: sem NaN, e_pos com ordem de grandeza plausível (modelo < ideal na translação),
   cabeçalho com commit hash, θ, dataset e seed.
5. Confirme entrada no results/CHANGELOG.md com commit hash.
6. Resuma em 3 linhas: o que rodou, resultado principal, anomalia (se houver).
Nunca sobrescreva resultados antigos; nunca reporte número não executado; nunca altere a ordem de θ.
