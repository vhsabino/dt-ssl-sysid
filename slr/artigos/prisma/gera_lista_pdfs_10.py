import csv, json, re, collections, sys
S = '/tmp/claude-0/-home-claude/34873281-bdf0-55fb-a1fb-5708ff313525/scratchpad'
pre = {r['pid']: r for r in csv.DictReader(open(f'{S}/pretriagem/pretriagem_rq1_rq4_2026-09-27.csv', encoding='utf-8-sig'))}
st27 = {r['pid']: r for r in csv.DictReader(open('/mnt/user-data/outputs/slr/preskim/pretriagem/pdf_status_candidatos_2026-09-27.csv', encoding='utf-8-sig'))}
look = {o['pid']: o for o in json.load(open(f'{S}/prisma09/lookup_resultado.json', encoding='utf-8'))}
local = set(open(f'{S}/prisma10/pdfs_locais_2026-10-10.txt').read().split())
aprov = json.load(open(f'{S}/prisma09/p1_aprovados_113.json', encoding='utf-8'))
GF = json.load(open(f'{S}/prisma09/rq3_grupoF_dois.json'))  # DOIs dos 18 do grupo F (09/10)
INC_SEM_PDF = json.load(open(f'{S}/prisma10/contagens_prisma_2026-10-10.json', encoding='utf-8'))['incluidos_sem_pdf_ids']
lote2 = {r['pid']: r for r in csv.DictReader(open('/mnt/user-data/outputs/slr/lote2_faltantes_20260912.csv', encoding='utf-8-sig'), delimiter=';')}
TIT_F = {
 'SLR-2021-Nguyen-5290': ('Constructing an Intelligent Navigation System for Autonomous Mobile Robot Based on Deep Reinforcement Learning', 2021),
 'SLR-2022-Miao-4755': ('Reinforcement Learning for Mobile Robot Obstacle Avoidance with Deep Deterministic Policy Gradient', 2022),
 'SLR-2024-Yunfeng-4680': ('Robot Navigation Based on Reinforcement Learning: An Overview', 2024),
 'SLR-2024-Zakaria-4587': ('Deep Reinforcement Learning for Mobile Robots: Overview and Issues', 2024),
 'SLR-2023-Chen-4265': ('Bridging the Reality Gap via Progressive Bayesian Optimisation', 2023),
 'SLR-2024-Mengyuan-4264': ('A Novel Framework for Adaptive Quadruped Robot Locomotion Learning in Uncertain Environments', 2024),
 'SLR-2026-Philippe-4238': ('Accelerating SME Robotics: Reinforcement Learning for Efficient Bin-Picking', 2026),
 'SLR-2026-Zhenyao-4198': ('Sim-to-Real Reinforcement Learning for Hybrid Robotic System: Platform Design and Enhanced Hindsight Experience Replay', 2026),
 'SLR-2026-Kim-2321': ('Enhancing Sim-to-Real Performance with High-Fidelity Simulations Using Multi-Body Dynamics and Data-Driven Friction Models', 2026),
 'SLR-2024-Miao-2272': ('Research on Digital Twin Simulation Method of Industrial Robot Integrated with Reinforcement Learning', 2024),
 'SLR-2025-Jhonattan-485': ('DSR Framework: A Hybrid Approach (Digital-Synthetic-Real) for Accelerated Training of AI Models in Mobile Robotics', 2025),
 'SLR-2023-Qi-436': ('An Adaptive Path Planning Approach for Digital Twin-Enabled Robot Arm Based on Inverse Kinematics and Deep Reinforcement Learning', 2023),
 'SLR-2026-Arkapravo-420': ('Framework for Real-Time Robotic Manipulation in the Metaverse Using Digital Twins and Reinforcement Learning', 2026),
 'SLR-2024-Anhtu-408': ('The Application of the Reinforcement Learning Method for Mobile Robot Navigation in an Unknown Environment', 2024),
 'SLR-2022-U-276': ('A Multi-Agent Reinforcement Learning Approach for the Efficient Control of Mobile Robots', 2022),
 'SLR-2023-Diego-264': ('Estimating Virtual Fixture Parameters in Digital Twin Environments for Robot Manipulation Tasks using Reinforcement Learning', 2023),
 'SLR-2022-T-259': ('Automatic Tuning of the Motion Control System of a Mobile Robot Along a Trajectory Based on the Reinforcement Learning Method', 2022),
 'SLR-2022-Saleh-234': ('Digital Twin Simulations Based Reinforcement Learning for Navigation and Control of a Wheel-on-Leg Mobile Robot', 2022),
}
EDITORA = [('10.1007', 'Springer'), ('10.1186', 'Springer (BMC)'), ('10.1109', 'IEEE'), ('10.1016', 'Elsevier'), ('10.1145', 'ACM'),
           ('10.1115', 'ASME'), ('10.1080', 'Taylor & Francis'), ('10.1201', 'CRC (Taylor & Francis)'), ('10.3390', 'MDPI'),
           ('10.1088', 'IOP'), ('10.1146', 'Annual Reviews'), ('10.20965', 'Fuji (JRM)'), ('10.1515', 'De Gruyter'),
           ('10.3389', 'Frontiers'), ('10.1002', 'Wiley'), ('10.5281', 'Zenodo'), ('10.59350', 'Rogue Scholar (blog)'),
           ('10.11575', 'repositório U. Calgary (tese)'), ('10.20517', 'OAE Publishing'), ('10.3785', 'periódico chinês'),
           ('10.16182', 'periódico chinês'), ('10.3795', 'periódico coreano (KSME)'), ('10.5302', 'periódico coreano (ICROS)'),
           ('10.21685', 'periódico russo'), ('10.21869', 'periódico russo'), ('10.31548', 'periódico ucraniano'),
           ('10.64972', 'periódico polonês'), ('10.14210', 'Univali (BR)')]
NACIONAL = ('10.3785', '10.16182', '10.3795', '10.5302', '10.21685', '10.21869', '10.31548')
NAO_REVISADO = ('10.5281', '10.59350', '10.11575')
BLOQ = ('mdpi.com', 'sciencedirect.com', 'tandfonline.com', 'dl.acm.org', 'preprints.org', 'iopscience')
def bare(d): return re.sub(r'^https?://(dx\.)?doi\.org/', '', (d or '').strip(), flags=re.I).strip()
def editora(d):
    for p, n in EDITORA:
        if d.startswith(p + '/') or d.startswith(p + '.'): return n
    return 'outra' if d else ''
linhas = []
alvo = [(a['pid'], 'passada 1') for a in aprov] + [(p, 'incluído sem PDF (extração)') for p in INC_SEM_PDF]
for pid, origem in alvo:
    if pid in local: continue
    if origem == 'passada 1':
        r = pre[pid]; titulo, ano, rq, tipo, link = r['titulo'], r['ano'], r['rq'], r['tipo'], r['link']
        doi = bare(r['doi']); ec3 = r['ec3_verificar'] == 'sim'
    else:
        titulo, ano = TIT_F[pid]; rq, tipo, link = 'RQ3', '', ''; doi = GF[pid]; ec3 = False
    urls = [u for u in look.get(pid, {}).get('urls', []) if 'repositorio.ufpe.br' not in u]
    s27 = st27.get(pid, {})
    if s27.get('status_pdf') == 'abrir_no_navegador' and s27.get('url_pdf'):
        urls = urls + [s27['url_pdf']]
    pdf_urls = [u for u in urls if not u.startswith('https://doi.org/')]
    oa_doi = [u for u in urls if u.startswith('https://doi.org/')]
    ed = editora(doi)
    obs = []
    if doi.startswith(NACIONAL): obs.append('periódico nacional: confira o idioma antes de baixar (EC4?)')
    if doi.startswith(NAO_REVISADO) or ec3: obs.append('EC3 a verificar (preprint, tese ou não revisado): procure a versão publicada')
    if tipo == 'capitulo': obs.append('capítulo de coletânea')
    if tipo == 'survey' or (origem == 'passada 1' and any(a['pid'] == pid and a['type'] == 'Survey' for a in aprov)): obs.append('survey de terceiros (related-SLR pelo protocolo)')
    if origem.startswith('incluído'): obs.append('já incluído na RQ3 em 09/10 (decisão sua); o PDF é para a extração')
    melhor = pdf_urls[0] if pdf_urls else (('https://doi.org/' + doi) if doi else link)
    if doi.startswith(NACIONAL):
        como = 'verificar idioma antes (EC4?)'; url = melhor
    elif doi.startswith(NAO_REVISADO) or ec3:
        como = 'verificar versão publicada antes (EC3?)'; url = melhor
    elif not doi:
        como = 'sem DOI: use o link' if link else 'sem DOI nem link: buscar pelo título'; url = link
    elif pdf_urls:
        como = 'aberto: navegador (o servidor recusa script)'; url = pdf_urls[0]
    elif oa_doi:
        como = 'aberto: navegador pelo DOI'; url = 'https://doi.org/' + doi
    else:
        como = f'CAFe ({ed})'; url = 'https://doi.org/' + doi
    titulo = titulo.replace('\\[', '[').replace('\\]', ']')
    linhas.append({'pid': pid, 'origem': origem, 'rq': rq, 'ano': ano, 'titulo': titulo, 'editora': ed, 'como_obter': como,
                   'link': url, 'doi': ('https://doi.org/' + doi) if doi else link, 'observacao': '; '.join(obs),
                   'baixado': ''})
ordem_como = lambda c: (0 if c.startswith('verificar') else 1 if c.startswith('aberto') else 2 if c.startswith('CAFe') else 3)
tam = collections.Counter(x['como_obter'] for x in linhas)
linhas.sort(key=lambda x: (ordem_como(x['como_obter']), -tam[x['como_obter']], x['como_obter'], x['origem'], x['pid']))
for i, x in enumerate(linhas, 1): x['ordem'] = i
cols = ['ordem', 'pid', 'origem', 'rq', 'ano', 'titulo', 'editora', 'como_obter', 'link', 'doi', 'observacao', 'baixado']
out = sys.argv[1]
with open(out, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols, delimiter=';', quoting=csv.QUOTE_MINIMAL); w.writeheader()
    for x in linhas: w.writerow({k: x[k] for k in cols})
c = collections.Counter(x['como_obter'] for x in linhas)
print(len(linhas)); [print(' ', k, v) for k, v in sorted(c.items(), key=lambda kv: -kv[1])]
print('por origem:', collections.Counter(x['origem'] for x in linhas))
print('com observacao EC4:', [x['pid'] for x in linhas if 'EC4' in x['observacao']])
print('com observacao EC3:', [x['pid'] for x in linhas if 'EC3' in x['observacao']])
