# Decomposicao do gap - 20260809_2308

Mediana de e_pos (m) no bin translacional, mesmas janelas/horizontes.

| variante | h=0.10s | h=0.20s | h=0.40s | h=0.70s | h=1.00s | h=1.50s |
|---|---|---|---|---|---|---|
| ideal (K=1, tau=0, Td=0) | 0.0264 | 0.0501 | 0.1005 | 0.1516 | 0.2165 | 0.2910 |
| + gain K | 0.0298 | 0.0570 | 0.1093 | 0.1668 | 0.2303 | 0.2769 |
| + time constant tau | 0.0090 | 0.0211 | 0.0455 | 0.0656 | 0.0918 | 0.1400 |
| full twin (+ dead time) | 0.0079 | 0.0178 | 0.0388 | 0.0617 | 0.0920 | 0.1193 |

## Contribuicao incremental (reducao de e_pos vs a variante anterior)
| passo | h=0.10s | h=0.20s | h=0.40s | h=0.70s | h=1.00s | h=1.50s |
|---|---|---|---|---|---|---|
| + gain K | -0.0034 | -0.0070 | -0.0088 | -0.0152 | -0.0138 | +0.0141 |
| + time constant tau | +0.0208 | +0.0359 | +0.0638 | +0.1012 | +0.1385 | +0.1369 |
| full twin (+ dead time) | +0.0010 | +0.0033 | +0.0066 | +0.0039 | -0.0002 | +0.0207 |