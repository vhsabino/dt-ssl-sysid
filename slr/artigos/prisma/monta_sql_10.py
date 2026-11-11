"""Monta sql_2026-10-10.json e p1_decididos_2026-10-10.json a partir da consulta SQL empacotada
(UNION ALL) feita ao banco do Notion em 10/10/2026 e das consultas em modo rows (R1 a R3, R5).
Os numeros abaixo sao transcritos do resultado da consulta; os fechamentos (5.565) sao conferidos."""
import json
import os
import sys

S = '/tmp/claude-0/-home-claude/34873281-bdf0-55fb-a1fb-5708ff313525/scratchpad'
OLD = json.load(open(f'{S}/prisma09/sql_2026-10-09.json', encoding='utf-8'))
EC1, EC2, EC3 = 'EC1 Fora do escopo', 'EC2 Sem avaliação empírica', 'EC3 Não peer-reviewed'
EC4, EC5, EC6 = 'EC4 Idioma', 'EC5 Duplicata/versão anterior', 'EC6 Indisponível'
FT, TA, INC, RFR, NR = 'Excluded Full-Text', 'Excluded Title/Abstract', 'Included', 'Recommended Full Read', 'Not read'

# q = 'stage': (stage, status, ec, n, com_nota_P1, com_preskim)
q1_stage = [
    [FT, 'Finished', EC1, 2, 0, 0],
    [FT, NR, EC1, 2, 0, 0],
    [FT, NR, EC5, 1, 0, 0],
    [FT, NR, EC6, 1, 0, 0],
    [FT, RFR, EC1, 219, 154, 52],
    [FT, RFR, EC2, 5, 1, 4],
    [FT, RFR, EC3, 5, 0, 5],
    [FT, RFR, EC4, 4, 1, 1],
    [FT, RFR, EC5, 1, 0, 1],
    [FT, RFR, EC6, 1, 0, 1],
    [TA, NR, None, 1, 0, 0],
    [TA, NR, EC1, 5068, 0, 0],
    [TA, NR, EC2, 2, 0, 0],
    [TA, NR, EC4, 4, 0, 0],
    [TA, NR, EC5, 40, 0, 0],
    [TA, RFR, EC1, 3, 2, 1],
    [INC, RFR, None, 205, 112, 86],
    [INC, RFR, EC1, 1, 1, 0],
]
assert sum(r[3] for r in q1_stage) == 5565
# q = 'rq': (RQ Mapping, stage, n)
q1_rq_stage = [
    [None, FT, 6], [None, TA, 5115],
    ['["RQ1","RQ2"]', INC, 3],
    ['["RQ1","RQ3"]', FT, 2], ['["RQ1","RQ3"]', INC, 3],
    ['["RQ1"]', FT, 136], ['["RQ1"]', TA, 2], ['["RQ1"]', INC, 105],
    ['["RQ2","RQ3"]', INC, 1],
    ['["RQ2"]', FT, 21], ['["RQ2"]', INC, 19],
    ['["RQ3"]', FT, 56], ['["RQ3"]', TA, 1], ['["RQ3"]', INC, 67],
    ['["RQ4"]', FT, 20], ['["RQ4"]', INC, 8],
]
assert sum(r[2] for r in q1_rq_stage) == 5565
# q = 'fonte' e 'string': iguais a 09/10 (conferido linha a linha no resultado de 10/10)
q1_fonte = [
    ['["ACM DL","IEEE Xplore","OpenAlex/Claude Science","Scopus"]', 2], ['["ACM DL","IEEE Xplore"]', 8],
    ['["ACM DL","OpenAlex/Claude Science","Scopus"]', 10], ['["ACM DL","Scopus"]', 5], ['["ACM DL"]', 1409],
    ['["IEEE Xplore","OpenAlex/Claude Science","Scopus"]', 210], ['["IEEE Xplore","OpenAlex/Claude Science"]', 9],
    ['["IEEE Xplore","Scopus"]', 34], ['["IEEE Xplore"]', 420], ['["Manual"]', 1],
    ['["OpenAlex/Claude Science","Scopus","SpringerLink"]', 68], ['["OpenAlex/Claude Science","Scopus"]', 317],
    ['["OpenAlex/Claude Science","SpringerLink"]', 15], ['["OpenAlex/Claude Science"]', 642],
    ['["Scopus","SpringerLink"]', 10], ['["Scopus"]', 280], ['["Snowballing"]', 1], ['["SpringerLink"]', 2124],
]
q1_string = [['S1', 1399], ['S2', 164], ['S3', 597], ['S4', 2610], ['S5', 793], ['Snowball-B', 2]]
assert sum(r[1] for r in q1_fonte) == 5565 and sum(r[1] for r in q1_string) == 5565
assert sorted(map(tuple, q1_fonte)) == sorted(map(tuple, OLD['q1_fonte']))
assert sorted(map(tuple, q1_string)) == sorted(map(tuple, OLD['q1_string']))
# q = 'tipo': (stage, type, via, n)
q2_tipo = [
    [FT, '(vazio)', 'P1', 156], [FT, '(vazio)', 'TC', 85],
    [TA, '(vazio)', 'P1', 2], [TA, '(vazio)', 'TC', 5116],
    [INC, '(vazio)', 'P1', 98], [INC, '(vazio)', 'TC', 83],
    [INC, 'Journal', 'TC', 1], [INC, 'Preprint', 'TC', 1],
    [INC, 'Survey', 'P1', 15], [INC, 'Survey', 'TC', 8],
]
assert sum(r[3] for r in q2_tipo) == 5565
q1_outros = [[INC, '["Manual"]', 'Snowball-B', 1], [INC, '["Snowballing"]', 'Snowball-B', 1]]
assert q1_outros == OLD['q1_outros_metodos']
q2_extracao = {'Data Extracted': 0, 'Quality Score preenchido': 0, 'Cite': 1}

NEW = {
    'fonte': 'Notion, data source collection://e31d696b-bf40-48b5-82e5-9f9e906f7775, consulta SQL empacotada (UNION ALL) '
             'e consultas rows de 10/10/2026',
    'q1_stage': q1_stage, 'q1_stage_colunas': OLD['q1_stage_colunas'],
    'q1_outros_metodos': q1_outros, 'q1_rq_stage': q1_rq_stage, 'q1_fonte': q1_fonte, 'q1_string': q1_string,
    'q2_tipo': q2_tipo, 'q2_extracao': q2_extracao,
    'log_de_busca_protocolo_s3': OLD['log_de_busca_protocolo_s3'], 'plano_execucao_s5': OLD['plano_execucao_s5'],
    'p1_decididos_rows': 'prisma10/p1_decididos_2026-10-10.json (271 registros com nota PRE-TRIAGEM, todos decididos: '
                         '113 Included, 158 Excluded)',
}
os.makedirs(f'{S}/prisma10', exist_ok=True)
json.dump(NEW, open(f'{S}/prisma10/sql_2026-10-10.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# p1 decididos: 09/10 + Feng-1317 (unico pendente, agora Excluded Full-Text EC2; consulta rows R5 de 10/10)
P1 = json.load(open(f'{S}/prisma09/p1_decididos_2026-10-09.json', encoding='utf-8'))
assert not any(r['Paper ID'] == 'SLR-2025-Feng-1317' for r in P1)
P1.append({'Paper ID': 'SLR-2025-Feng-1317', 'Selection Stage': FT, 'Exclusion Criterion': EC2, 'Type': None,
           'Name': 'Digital Twin Robotics: Immersive Software-in-the-Loop Testing with OpenUSD, Isaac Sim, and ROS',
           'DOI': 'https://doi.org/10.1145/3721251.3734066', 'RQ Mapping': '["RQ1"]', 'Year': 2025})
assert len(P1) == 271
# aprovados: R2 (>=2025, arquivo) + R3 (<=2024, transcrito da resposta inline) devem ser os mesmos 113 de 09/10
R2 = {r['Paper ID'] for r in json.load(open(f'{S}/prisma10/raw/R2_included_p1_2025.json', encoding='utf-8'))['results']}
R3 = {'SLR-2022-Cijyun-5223', 'SLR-2024-Michele-4935', 'SLR-2023-Ayan-4763', 'SLR-2022-Kholood-4740', 'SLR-2023-Junfeng-4633',
      'SLR-2023-Yuchen-4558', 'SLR-2024-Zhang-4532', 'SLR-2024-Cludio-3751', 'SLR-2023-Jaqueline-3731', 'SLR-2024-Giuseppe-3583',
      'SLR-2024-Bentley-3518', 'SLR-2023-Harinarayanan-3508', 'SLR-2023-Bo-3503', 'SLR-2022-Adam-3455', 'SLR-2024-Ahmad-2438',
      'SLR-2023-Joo-2435', 'SLR-2022-Noah-2410', 'SLR-2022-Shang-2393', 'SLR-2024-Lin-2372', 'SLR-2022-G-2167', 'SLR-2022-J-2055',
      'SLR-2024-X-1879', 'SLR-2024-Liu-1421', 'SLR-2022-Wang-1339', 'SLR-2023-Xu-1336', 'SLR-2024-Zhou-1274',
      'SLR-2019-Josifovska-1119', 'SLR-2024-Gustavo-995', 'SLR-2023-Sijie-850', 'SLR-2023-Flavien-822', 'SLR-2021-Xuda-797',
      'SLR-2024-Wilson-782', 'SLR-2024-Jacob-781', 'SLR-2022-Ryota-771', 'SLR-2024-Ruwen-765', 'SLR-2023-Junru-760',
      'SLR-2022-Mahmoud-752', 'SLR-2023-Hongjiu-749', 'SLR-2022-Xin-742', 'SLR-2024-Jaeho-458', 'SLR-2023-Chengye-441',
      'SLR-2024-Marcel-289', 'SLR-2024-Marvin-250', 'SLR-2023-Taeyoon-122', 'SLR-2023-Jonathan-007', 'SLR-2024-Robert-002'}
assert len(R2) == 67 and len(R3) == 46
aprov_old = {r['Paper ID'] for r in P1 if r['Selection Stage'] == INC}
assert aprov_old == R2 | R3, (aprov_old ^ (R2 | R3))
json.dump(P1, open(f'{S}/prisma10/p1_decididos_2026-10-10.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok: sql_2026-10-10.json e p1_decididos_2026-10-10.json; aprovados da passada 1 iguais aos 113 de 09/10')
