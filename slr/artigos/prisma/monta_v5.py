"""Entradas do funil de 23/10/2026: consulta SQL agregada ao Notion (UNION ALL, 23/10 ~18:40 UTC) transcrita,
estado dos 113 aprovados da passada 1 (v4 + 7 exclusoes da passada 2 + 1 confirmado com SKIM), PDFs da pasta
(iguais aos da v4: 260 arquivos, mesmo conjunto; conferido por ls no PC), incluidos TC (93 da v4 + Mostafa-4396).
Formato novo das tabelas rq e tipo: [chave, stage, via P1/TC, n, skim]; deriva_contagens.py aceita os dois formatos."""
import json
import shutil

S = '/tmp/claude-0/-home-claude/34873281-bdf0-55fb-a1fb-5708ff313525/scratchpad'
D = f'{S}/prisma23'
V4 = json.load(open(f'{D}/sql_2026-10-10_v4.json', encoding='utf-8'))
EC1, EC2, EC3 = 'EC1 Fora do escopo', 'EC2 Sem avaliação empírica', 'EC3 Não peer-reviewed'
EC4, EC5, EC6 = 'EC4 Idioma', 'EC5 Duplicata/versão anterior', 'EC6 Indisponível'
FT, TA, INC, RFR, NR, RIP = 'Excluded Full-Text', 'Excluded Title/Abstract', 'Included', 'Recommended Full Read', 'Not read', 'Read in Progress'
# colunas: stage, status, ec, n, com_pretriagem_27-09 (a), com_preskim (b), skim (c), skim_e_pretriagem (d)
q1_stage = [
    [FT, 'Finished', EC1, 2, 0, 0, 0, 0], [FT, NR, EC1, 2, 0, 0, 0, 0], [FT, NR, EC5, 1, 0, 0, 0, 0], [FT, NR, EC6, 1, 0, 0, 0, 0],
    [FT, RFR, EC1, 227, 162, 52, 0, 0], [FT, RFR, EC2, 6, 2, 4, 0, 0], [FT, RFR, EC3, 8, 3, 5, 0, 0], [FT, RFR, EC4, 11, 8, 1, 0, 0],
    [FT, RFR, EC5, 2, 1, 1, 0, 0], [FT, RFR, EC6, 2, 1, 1, 0, 0],
    [TA, NR, None, 1, 0, 0, 0, 0], [TA, NR, EC1, 5068, 0, 0, 0, 0], [TA, NR, EC2, 2, 0, 0, 0, 0], [TA, NR, EC4, 4, 0, 0, 0, 0],
    [TA, NR, EC5, 40, 0, 0, 0, 0], [TA, RFR, EC1, 3, 2, 1, 0, 0], [TA, RFR, EC6, 1, 1, 0, 0, 0],
    [INC, RIP, None, 1, 1, 0, 1, 1], [INC, RFR, None, 183, 90, 86, 2, 0],
]
# colunas: rq, stage, via, n, skim  (Excluded Title/Abstract fora da consulta: 5.115 sem RQ + 3 RQ1 + 1 RQ3 na v4)
q1_rq_stage = [
    [None, FT, 'TC', 6, 0], ['["RQ1","RQ2"]', INC, 'TC', 3, 0], ['["RQ1","RQ3"]', FT, 'TC', 2, 0], ['["RQ1","RQ3"]', INC, 'TC', 3, 0],
    ['["RQ1"]', FT, 'P1', 155, 0], ['["RQ1"]', INC, 'P1', 85, 1], ['["RQ2","RQ3"]', INC, 'TC', 1, 0], ['["RQ2"]', FT, 'TC', 21, 0],
    ['["RQ2"]', INC, 'TC', 19, 2], ['["RQ3"]', FT, 'TC', 56, 0], ['["RQ3"]', INC, 'TC', 67, 0], ['["RQ4"]', FT, 'P1', 22, 0],
    ['["RQ4"]', INC, 'P1', 6, 0],
]
# colunas: stage, tipo, via, n, skim
q2_tipo = [
    [FT, '(vazio)', 'P1', 176, 0], [FT, '(vazio)', 'TC', 85, 0], [FT, 'Survey', 'P1', 1, 0], [TA, '(vazio)', 'P1', 3, 0],
    [TA, '(vazio)', 'TC', 5116, 0], [INC, '(vazio)', 'P1', 76, 0], [INC, '(vazio)', 'TC', 83, 2], [INC, 'Journal', 'P1', 1, 1],
    [INC, 'Journal', 'TC', 1, 0], [INC, 'Preprint', 'TC', 1, 0], [INC, 'Survey', 'P1', 14, 0], [INC, 'Survey', 'TC', 8, 0],
]
assert sum(r[3] for r in q1_stage) == 5565 and sum(r[3] for r in q2_tipo) == 5565
assert sum(r[4] for r in q1_stage) == 271 and sum(r[3] for r in q1_rq_stage) == 5565 - 5115 - 3 - 1
assert sum(r[3] for r in q1_rq_stage if r[1] == INC) == 184 == sum(r[3] for r in q1_stage if r[0] == INC)
NEW = dict(V4)
NEW.update({'fonte': 'Notion, consulta SQL agregada (UNION ALL) de 23/10/2026; fonte e string copiados da v4 (banco com os '
                     'mesmos 5.565 registros). Colunas novas: skim (Notes iniciando em "SKIM ") e, nas tabelas rq e tipo, '
                     'via (P1 = nota PRE-TRIAGEM IA 27/09; TC = demais). Os 3 SKIM: 2 da RQ2 (13/09) e Mostafa-4396 (11/10).',
            'q1_stage': q1_stage, 'q1_stage_colunas': ['stage', 'status', 'ec', 'n', 'com_pretriagem_27-09', 'com_preskim', 'skim',
                                                        'skim_e_pretriagem'],
            'q1_rq_stage': q1_rq_stage, 'q1_rq_stage_colunas': ['rq', 'stage', 'via', 'n', 'skim'],
            'q2_tipo': q2_tipo, 'q2_tipo_colunas': ['stage', 'tipo', 'via', 'n', 'skim'],
            'q2_extracao': {'Data Extracted': 0, 'Quality Score preenchido': 1, 'Cite': 1},
            'p1_decididos_rows': 'p1_decididos_base.json (passada 1 congelada: 113 Included, 158 Excluded) e '
                                 'p1_aprovados_estado_2026-10-23.json (estado atual dos 113; chave skim = confirmado na passada 2)'})
json.dump(NEW, open(f'{D}/sql_2026-10-23.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

est = json.load(open(f'{D}/p1_aprovados_estado_2026-10-10_v4.json', encoding='utf-8'))
novas = {'SLR-2025-Ghandali-915': EC3, 'SLR-2025-Satyam-886': EC3, 'SLR-2025-Stepani-2511': EC4, 'SLR-2024-Lin-2372': EC4,
         'SLR-2025-Maksim-1096': EC4, 'SLR-2026-M-857': EC4, 'SLR-2025-T-338': EC4}
for p, ec in novas.items():
    assert est[p]['stage'] == INC, p
    est[p] = {'stage': FT, 'ec': ec}
assert est['SLR-2026-Mostafa-4396']['stage'] == INC
est['SLR-2026-Mostafa-4396'] = {'stage': INC, 'ec': None, 'skim': '11/10', 'status': RIP}
assert sum(1 for e in est.values() if e['stage'] == INC) == 91
json.dump(est, open(f'{D}/p1_aprovados_estado_2026-10-23.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

inc = json.load(open(f'{D}/incluidos_tc_2026-10-10_v4.json', encoding='utf-8'))
assert 'SLR-2026-Mostafa-4396' not in inc and len(inc) == 93
json.dump(sorted(inc + ['SLR-2026-Mostafa-4396']), open(f'{D}/incluidos_tc_2026-10-23.json', 'w', encoding='utf-8'), indent=0)
for a, b in (('pdfs_locais_2026-10-10_v4.txt', 'pdfs_locais_2026-10-23.txt'),
             ('pdfs_invalidos_2026-10-10_v4.txt', 'pdfs_invalidos_2026-10-23.txt'),
             ('pdfs_faltantes_2026-10-10_v4.csv', 'pdfs_faltantes_2026-10-23.csv')):
    shutil.copy(f'{D}/{a}', f'{D}/{b}')
print('ok')
