"""Teste-reteste da triagem T/A (amostra de 12/09/2026, reteste preenchido em 11/10/2026).
Le a planilha preenchida e o gabarito; calcula concordancia, kappa de Cohen (IC assintotico e bootstrap
estratificado), concordancia por estrato com IC de Wilson e lista as divergencias.
Uso: python analise_reteste.py <pasta do reteste> <saida.json>   (requer openpyxl)"""
import csv
import json
import math
import random
import sys

import openpyxl

U, OUT = sys.argv[1], sys.argv[2]
wb = openpyxl.load_workbook(f'{U}/reteste_TA_2026-09-12.xlsx', data_only=True)
ws = wb['Reteste T-A']
R = {}
for row in ws.iter_rows(min_row=1, values_only=True):
    if row and isinstance(row[1], str) and row[1].startswith('SLR-') and row[0] != 'ex.':
        R[row[1]] = {'n': int(row[0]), 'titulo': row[3], 'dec': row[6], 'ec': row[7] or '', 'obs': row[8] or ''}
G = {r['pid']: r for r in csv.DictReader(open(f'{U}/reteste_TA_2026-09-12_GABARITO_nao_abrir.csv', encoding='utf-8-sig'), delimiter=';')}
assert len(R) == 45 == len(G) and set(R) == set(G)
EX, AP = 'Excluir', 'Aprovar'
lin = []
for pid, g in G.items():
    orig = EX if g['decisao_original'].startswith('Exclu') else AP
    ret = EX if R[pid]['dec'] == 'Excluir' else AP if R[pid]['dec'].startswith('Aprovar') else None
    assert ret, pid
    lin.append({'pid': pid, 'estrato': g['estrato'], 'orig': orig, 'ret': ret, 'ec_ret': R[pid]['ec'],
                'rq': g['rq_atual'], 'titulo': R[pid]['titulo'], 'obs': R[pid]['obs']})


def kappa(L):
    n = len(L)
    a = sum(1 for x in L if x['orig'] == EX and x['ret'] == EX); b = sum(1 for x in L if x['orig'] == EX and x['ret'] == AP)
    c = sum(1 for x in L if x['orig'] == AP and x['ret'] == EX); d = sum(1 for x in L if x['orig'] == AP and x['ret'] == AP)
    po = (a + d) / n
    p1, q1 = (a + b) / n, (a + c) / n  # marginais de Excluir: original, reteste
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    k = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    return k, po, pe, (a, b, c, d)


def wilson(x, n, z=1.959964):
    p = x / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


k, po, pe, (a, b, c, d) = kappa(lin)
n = len(lin)
# Variancia assintotica de Fleiss, Cohen e Everitt (1969) para o kappa
pij = {('E', 'E'): a / n, ('E', 'A'): b / n, ('A', 'E'): c / n, ('A', 'A'): d / n}
pr = {'E': (a + b) / n, 'A': (c + d) / n}; pc = {'E': (a + c) / n, 'A': (b + d) / n}
t1 = sum(pij[(i, i)] * (1 - (pr[i] + pc[i]) * (1 - k)) ** 2 for i in 'EA')
t2 = (1 - k) ** 2 * sum(pij[(i, j)] * (pc[i] + pr[j]) ** 2 for i in 'EA' for j in 'EA' if i != j)
t3 = (k - pe * (1 - k)) ** 2
se = math.sqrt((t1 + t2 - t3) / (n * (1 - pe) ** 2))
random.seed(20261011)
A_ = [x for x in lin if x['estrato'] == 'A']; B_ = [x for x in lin if x['estrato'] == 'B']
boot = []
for _ in range(20000):
    s = [random.choice(A_) for _ in A_] + [random.choice(B_) for _ in B_]
    kb = kappa(s)[0]
    if not math.isnan(kb):
        boot.append(kb)
boot.sort()
lo, hi = boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot)) - 1]
res = {'n': n, 'tabela': {'excl_excl': a, 'excl_aprov': b, 'aprov_excl': c, 'aprov_aprov': d},
       'po': po, 'pe': pe, 'kappa': k, 'kappa_ic95_assintotico': [k - 1.96 * se, k + 1.96 * se], 'kappa_se': se,
       'kappa_ic95_bootstrap_estratificado': [lo, hi], 'pabak': 2 * po - 1,
       'estrato_A': {'n': len(A_), 'concordam': sum(x['orig'] == x['ret'] for x in A_)},
       'estrato_B': {'n': len(B_), 'concordam': sum(x['orig'] == x['ret'] for x in B_)}}
for s in ('estrato_A', 'estrato_B'):
    res[s]['ic95_wilson'] = wilson(res[s]['concordam'], res[s]['n'])
res['total_ic95_wilson'] = wilson(a + d, n)
res['ec_nas_exclusoes_concordantes'] = sorted({x['ec_ret'] for x in A_ if x['ret'] == EX})
res['divergencias'] = [{k_: x[k_] for k_ in ('pid', 'estrato', 'orig', 'ret', 'ec_ret', 'rq', 'titulo', 'obs')}
                       for x in sorted(lin, key=lambda y: (y['estrato'], y['pid'])) if x['orig'] != x['ret']]
json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k_: v for k_, v in res.items() if k_ != 'divergencias'}, ensure_ascii=False, indent=1))
for x in res['divergencias']:
    print(x['estrato'], x['pid'], x['orig'], '->', x['ret'], x['ec_ret'], x['rq'], '|', x['titulo'][:70], '|', x['obs'])
