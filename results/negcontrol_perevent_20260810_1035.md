# Controle negativo (bayesopt) com estatistica POR EVENTO - 20260810_1035

Mesmo padrao do resultado principal: mediana por evento, n=10, h_ref=0.4 s,
bin translacional. Substitui os numeros por janela que nao eram comparaveis.

| comparacao | mediana A | mediana B | gap mediano | vitorias A | Wilcoxon p | rank-biserial |
|---|---|---|---|---|---|---|
| per-DOF vs ideal | 0.0421 | 0.1177 | +0.0689 | 10/10 | 0.0009766 | +1.000 |
| bayesopt vs ideal | 0.0421 | 0.1177 | +0.0690 | 10/10 | 0.0009766 | +1.000 |
| per-DOF vs bayesopt | 0.0421 | 0.0421 | +0.0038 | 7/10 | 0.04199 | +0.400 |

## Leitura

- per-DOF vs ideal: gap +0.0689 m, 10/10, p=0.000977 -> resultado principal, robusto.
- bayesopt vs ideal: gap +0.0690 m, 10/10, p=0.000977.
- **per-DOF vs bayesopt: gap +0.0038 m, 7/10 eventos, p=0.042, efeito +0.400**.

Se o gate do artigo (efeito >= 0.2 E p < 0.05) for aplicado a per-DOF vs bayesopt,
o veredito e o que aparece na ultima linha -- e e ELE que deve ser reportado, nao
o p por janela de 0.040 usado antes (objecao C3 da revisao V2).