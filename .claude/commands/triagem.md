Faça a triagem fase 1 da SLR.
1. Leia slr/protocolo_slr.md (critérios I1-I3, E1-E5).
2. Abra slr/triagem.csv e processe APENAS linhas com fase1_decisao vazia.
3. Para cada uma, com base em título+resumo, preencha fase1_decisao com
   I, E ou DUVIDA, e fase1_motivo com os códigos (ex.: "E2" ou "I1+I2").
4. Em caso de informação insuficiente, use DUVIDA — nunca chute.
5. Ao final, rode `python slr/scripts/slr_pipeline.py stats slr/triagem.csv`
   e me apresente o resumo + lista de DUVIDA para eu decidir.
