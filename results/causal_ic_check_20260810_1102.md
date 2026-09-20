# Condicao inicial causal vs central - 20260810_1102

O harness de avaliacao (phase0_replay/io.py:body_velocity_series) estima v0 por
np.gradient, uma diferenca CENTRAL, que em t0 usa a amostra t0+1 -- ou seja, UMA
amostra (16.7 ms) de dentro da janela. (O filtro Savitzky-Golay fica no caminho
de IDENTIFICACAO, nao no de avaliacao.) Aqui o v0 e recomputado com diferenca
para tras, estritamente causal, e tudo e re-pontuado.

| estimador de v0 | e_pos h=0.1 | h=0.4 | h=1.5 | gap por evento | vitorias | p |
|---|---|---|---|---|---|---|
| central (np.gradient, +-1 amostra) | 0.0079 | 0.0388 | 0.1193 | +0.0689 | 10/10 | 0.0009766 |
| causal (diferenca para tras, so passado) | 0.0128 | 0.0468 | 0.1335 | +0.0706 | 10/10 | 0.0009766 |

Diferenca em h_ref: +0.0080 m (+20.6 %).

Conclusao: o veredito nao depende do estimador. A vantagem sobrevive a um v0
estritamente causal, o que fecha a objecao de que parte dela viria de enxergar
dentro da janela de avaliacao.