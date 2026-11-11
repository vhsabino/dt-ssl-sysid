"""Deriva as caixas do funil PRISMA a partir das consultas ao banco do Notion.

Uso: python deriva_contagens.py 2026-10-09
Entrada: sql_<data>.json (resultados das consultas SQL), p1_decididos_base.json (passada 1 congelada),
p1_aprovados_estado_<data>.json (estado atual dos aprovados; chave "skim" = confirmado na passada 2),
pdfs_locais_<data>.txt (PDFs na pasta slr\\artigos), pdfs_invalidos_<data>.txt, incluidos_tc_<data>.json.
Saida: contagens_prisma_<data>.json. Cada caixa tem assert de fechamento.
Desde 23/10: aprovados da passada 1 com nota "SKIM dd/mm: INCLUI" (confirmados na passada 2) saem de
"em analise" e entram nos incluidos por texto completo; as tabelas rq e tipo aceitam o formato novo
[chave, stage, via, n, skim] e o antigo.
"""
import collections
import csv
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = sys.argv[1] if len(sys.argv) > 1 else '2026-10-09'
S = json.load(open(os.path.join(BASE, f'sql_{DATA}.json'), encoding='utf-8'))
# Passada 1 congelada (fechou em 09/10; arquivo de 10/10). Decisoes posteriores sobre os aprovados ficam em EST.
_p1b = os.path.join(BASE, 'p1_decididos_base.json')
_p1 = os.path.join(BASE, f'p1_decididos_{DATA}.json')
P1 = json.load(open(_p1 if os.path.exists(_p1) else _p1b if os.path.exists(_p1b) else os.path.join(BASE, 'p1_decididos.json'),
                    encoding='utf-8'))
_est = os.path.join(BASE, f'p1_aprovados_estado_{DATA}.json')
EST = json.load(open(_est, encoding='utf-8')) if os.path.exists(_est) else {}
LOCAL_ARQ = set(open(os.path.join(BASE, f'pdfs_locais_{DATA}.txt')).read().split())
_inv = os.path.join(BASE, f'pdfs_invalidos_{DATA}.txt')
INVALIDOS = set(open(_inv).read().split()) if os.path.exists(_inv) else set()  # previas, arquivos errados
LOCAL = LOCAL_ARQ - INVALIDOS
CSV_PRE = [os.path.join(BASE, '..', 'preskim', 'pretriagem', 'pretriagem_rq1_rq4_2026-09-27.csv'),  # PC: slr\\artigos\\prisma
           os.path.join(BASE, '..', 'pretriagem', 'pretriagem_rq1_rq4_2026-09-27.csv')]  # rascunho da sessao
PRE = {r['pid']: r for r in csv.DictReader(open(next(c for c in CSV_PRE if os.path.exists(c)), encoding='utf-8-sig'))}

rows = [dict(zip(S['q1_stage_colunas'], r)) for r in S['q1_stage']]


def soma(f, campo='n'):
    return sum(r[campo] for r in rows if f(r))


C = {}
# Identificacao
C['banco_total'] = soma(lambda r: True)
C['outros_metodos'] = sum(r[3] for r in S['q1_outros_metodos'])
C['banco_bases'] = C['banco_total'] - C['outros_metodos']
log = S['log_de_busca_protocolo_s3']
C['log_por_base'] = {b: sum(v) for b, v in log.items() if isinstance(v, list) and b != 'ordem'}
C['log_total'] = sum(C['log_por_base'].values())
C['log_por_string'] = {s: sum(log[b][i] for b in C['log_por_base']) for i, s in enumerate(log['ordem'])}
C['registro_vazio'] = 1  # plano de execucao, secao 5 (27-28/08)
C['banco_pos_ingestao'] = C['banco_bases'] + C['registro_vazio']
C['removidos_ingestao'] = C['log_total'] - C['banco_pos_ingestao']
C['ec5_titulo'] = soma(lambda r: r['stage'] == 'Excluded Title/Abstract' and r['status'] == 'Not read'
                       and (r['ec'] or '').startswith('EC5'))
fonte_occ = collections.Counter()
for k, n in S['q1_fonte']:
    for b in json.loads(k):
        fonte_occ[b] += n
C['banco_ocorrencias_por_fonte'] = dict(fonte_occ)
C['banco_por_string'] = dict(S['q1_string'])

# Triagem, rodada 1 (titulo/resumo, todas as RQs)
C['triados_r1'] = C['banco_bases'] - C['ec5_titulo']
r1 = [r for r in rows if r['stage'] == 'Excluded Title/Abstract' and r['status'] == 'Not read'
      and not (r['ec'] or '').startswith('EC5')]
C['excl_r1_por_ec'] = {(r['ec'] or 'sem criterio')[:3]: r['n'] for r in r1}
C['excl_r1'] = sum(r['n'] for r in r1)
C['aprov_r1'] = C['triados_r1'] - C['excl_r1']
pos_r1 = soma(lambda r: r['status'] == 'Recommended Full Read' or r['stage'] != 'Excluded Title/Abstract') - C['outros_metodos']
assert C['aprov_r1'] == pos_r1, (C['aprov_r1'], pos_r1)

# Triagem, rodada 2 (passada 1 por resumo, RQ1 e RQ4)
C['p1_total'] = soma(lambda r: True, 'com_pretriagem_27-09')
aprov_base = [r['Paper ID'] for r in P1 if r['Selection Stage'] == 'Included']
excl_base = [r for r in P1 if r['Selection Stage'] != 'Included']
C['p1_aprovados'] = len(aprov_base)
C['p1_excluidos_por_ec'] = collections.Counter((r.get('Exclusion Criterion') or 'sem')[:3] for r in excl_base)
C['p1_excluidos'] = len(excl_base)
C['p1_pendentes'] = C['p1_total'] - len(P1)
assert C['p1_pendentes'] == soma(lambda r: r['stage'] == 'Identified', 'com_pretriagem_27-09')
assert C['p1_total'] == C['p1_pendentes'] + C['p1_aprovados'] + C['p1_excluidos'] == 271
# Decisoes tomadas depois da passada 1 sobre os aprovados: EC6 vai para "nao recuperados"; o resto para elegibilidade
EST_P1 = {p: EST.get(p, {'stage': 'Included', 'ec': None}) for p in aprov_base}
POS = {p: e for p, e in EST_P1.items() if e['stage'] != 'Included'}
C['pos_p1_ec6_ids'] = sorted(p for p, e in POS.items() if (e['ec'] or '').startswith('EC6'))
C['pos_p1_excl_ids'] = sorted(p for p, e in POS.items() if not (e['ec'] or '').startswith('EC6'))
C['pos_p1_excl_por_ec'] = dict(collections.Counter(POS[p]['ec'][:3] for p in C['pos_p1_excl_ids']))
C['p1_confirmados_ids'] = sorted(p for p, e in EST_P1.items() if e['stage'] == 'Included' and e.get('skim'))
C['p1_confirmados'] = len(C['p1_confirmados_ids'])  # passada 2: INCLUI com prefixo SKIM
C['p1_em_analise_ids'] = sorted(p for p, e in EST_P1.items() if e['stage'] == 'Included' and not e.get('skim'))
C['p1_em_analise'] = len(C['p1_em_analise_ids'])
assert C['p1_em_analise'] + C['p1_confirmados'] == soma(lambda r: r['stage'] == 'Included', 'com_pretriagem_27-09'), C['p1_em_analise']
if 'skim_e_pretriagem' in S['q1_stage_colunas']:
    assert C['p1_confirmados'] == soma(lambda r: r['stage'] == 'Included', 'skim_e_pretriagem'), C['p1_confirmados']
C['passada2_decididos'] = C['p1_confirmados'] + len(C['pos_p1_excl_ids']) + len(C['pos_p1_ec6_ids'])
assert soma(lambda r: r['stage'].startswith('Excluded'), 'com_pretriagem_27-09') == C['p1_excluidos'] + len(POS)
assert soma(lambda r: (r['ec'] or '').startswith('EC6'), 'com_pretriagem_27-09') == len(C['pos_p1_ec6_ids'])
C['p1_excl_marcados_FT'] = soma(lambda r: r['stage'] == 'Excluded Full-Text', 'com_pretriagem_27-09')
C['p1_excl_marcados_TA'] = soma(lambda r: r['stage'] == 'Excluded Title/Abstract', 'com_pretriagem_27-09')
pend_pre = [p for p in PRE.values() if p['pid'] not in {r['Paper ID'] for r in P1}]
C['p1_pendentes_por_rq_grupo'] = {f"{k[0]} {k[1]}": v for k, v in
                                   sorted(collections.Counter((p['rq'], p['grupo']) for p in pend_pre).items())}
assert len(pend_pre) == C['p1_pendentes']
C['p1_pendentes_ids'] = sorted(p['pid'] for p in pend_pre)

# Recuperacao de texto completo
C['tc_direto'] = C['aprov_r1'] - C['p1_total']  # RQ2, RQ3 e decisoes anteriores ao Sprint 2
C['buscados'] = C['tc_direto'] + C['p1_aprovados']
_ec6 = lambda r: r['stage'].startswith('Excluded') and (r['ec'] or '').startswith('EC6')  # noqa: E731
C['nao_recuperados_tc'] = soma(_ec6) - soma(_ec6, 'com_pretriagem_27-09')
C['nao_recuperados_ec6'] = C['nao_recuperados_tc'] + len(C['pos_p1_ec6_ids'])
C['rq3_pendentes_com_pdf'] = soma(lambda r: r['stage'] == 'Identified', 'com_preskim')
ident_tc = soma(lambda r: r['stage'] == 'Identified') - C['p1_pendentes']
# RQ3 sem pre-skim (grupo F): lista da data, ou a de 09/10 (18), ou vazia quando nao ha mais Identified
_gf = [os.path.join(BASE, f'rq3_grupoF_{DATA}.json'), os.path.join(BASE, 'rq3_grupoF_18.json')]
GF = [] if ident_tc == 0 else json.load(open(next(p for p in _gf if os.path.exists(p))))
assert len(GF) == ident_tc - C['rq3_pendentes_com_pdf'], (len(GF), ident_tc)
C['rq3_grupo_F_com_pdf'] = sum(1 for p in GF if p in LOCAL)
C['rq3_grupo_F_sem_pdf'] = len(GF) - C['rq3_grupo_F_com_pdf']
C['rq3_grupo_F_sem_pdf_ids'] = sorted(p for p in GF if p not in LOCAL)
C['p1_aprov_com_pdf'] = sum(1 for p in C['p1_em_analise_ids'] if p in LOCAL)
C['p1_aprov_sem_pdf_ids'] = sorted(p for p in C['p1_em_analise_ids'] if p not in LOCAL)
C['p1_aprov_sem_pdf'] = len(C['p1_aprov_sem_pdf_ids'])
C['p1_aprov_so_previa_ids'] = sorted(p for p in C['p1_aprov_sem_pdf_ids'] if p in INVALIDOS)
C['aguardando_pdf'] = C['rq3_grupo_F_sem_pdf'] + C['p1_aprov_sem_pdf']
C['recuperados'] = C['buscados'] - C['nao_recuperados_ec6'] - C['aguardando_pdf']

# Elegibilidade (texto completo)
C['pendentes_decisao_com_pdf'] = C['rq3_pendentes_com_pdf'] + C['rq3_grupo_F_com_pdf'] + C['p1_aprov_com_pdf']
C['avaliados'] = C['recuperados'] - C['pendentes_decisao_com_pdf']
ft = [r for r in rows if r['stage'] == 'Excluded Full-Text' and not (r['ec'] or '').startswith('EC6')]
excl_tc = collections.Counter()
for r in ft:
    excl_tc[r['ec'][:3]] += r['n'] - r['com_pretriagem_27-09']
erro_etapa = soma(lambda r: r['stage'] == 'Excluded Title/Abstract' and r['status'] == 'Recommended Full Read') \
    - C['p1_excl_marcados_TA']
excl_tc['EC1'] += erro_etapa
for p in C['pos_p1_excl_ids']:  # aprovados na passada 1 e excluidos depois (com ou sem o PDF)
    excl_tc[POS[p]['ec'][:3]] += 1
C['excl_tc_por_ec'] = dict(sorted(excl_tc.items()))
C['excl_tc'] = sum(excl_tc.values())
C['excl_tc_registro_com_etapa_errada'] = erro_etapa
# Exclusoes contadas aqui mas decididas sem o PDF na pasta (pela pagina da editora ou pelo resumo)
GF_ALL = json.load(open(os.path.join(BASE, 'rq3_grupoF_18.json'))) if os.path.exists(
    os.path.join(BASE, 'rq3_grupoF_18.json')) else []
_inc_ids = json.load(open(os.path.join(BASE, f'incluidos_tc_{DATA}.json'))) if os.path.exists(
    os.path.join(BASE, f'incluidos_tc_{DATA}.json')) else []
C['excl_sem_pdf_rq3_ids'] = sorted(p for p in GF_ALL if p not in _inc_ids and p not in LOCAL) if _inc_ids else []
C['excl_sem_pdf_p1_ids'] = sorted(p for p in C['pos_p1_excl_ids'] if p not in LOCAL)  # previa conta como sem PDF
C['incluidos_tc'] = soma(lambda r: r['stage'] == 'Included') - C['p1_em_analise']
C['incluidos_bases'] = C['incluidos_tc'] - C['outros_metodos']
assert C['avaliados'] == C['incluidos_bases'] + C['excl_tc'], (C['avaliados'], C['incluidos_bases'], C['excl_tc'])

# Incluidos: tipo e RQ
tipo = collections.Counter()
C['incluidos_p1_survey'] = 0
for row in S['q2_tipo']:
    st, t, via, n = row[:4]
    sk = row[4] if len(row) > 4 else 0  # formato novo: confirmados na passada 2 (SKIM) entre os P1
    if st != 'Included':
        continue
    if via == 'TC':
        tipo[t] += n
    else:
        tipo[t] += sk
        if t == 'Survey':
            C['incluidos_p1_survey'] += n - sk
C['incluidos_tc_por_tipo'] = {k: v for k, v in tipo.items() if v}
rq = collections.Counter()
so_p1 = 0
p1_rq = {}
for row in S['q1_rq_stage']:
    if len(row) == 3:  # formato antigo: [rq, stage, n]; Included so-RQ1 ou so-RQ4 vieram da passada 1
        k, st, n = row
        via, sk = ('P1' if k in ('["RQ1"]', '["RQ4"]') else 'TC'), 0
    else:  # formato novo: [rq, stage, via, n, skim]
        k, st, via, n, sk = row
    if st != 'Included' or not k:
        continue
    if via == 'P1':
        so_p1 += n - sk
        p1_rq[json.loads(k)[0]] = p1_rq.get(json.loads(k)[0], 0) + n - sk
        n = sk  # confirmados na passada 2 contam como incluidos por texto completo
    for q in (json.loads(k) if n else []):
        rq[q] += n
assert so_p1 == C['p1_em_analise'], (so_p1, C['p1_em_analise'])
C['incluidos_tc_ocorrencias_rq'] = dict(sorted(rq.items()))
C['p1_aprovados_por_rq'] = p1_rq
# Conciliacao com o Notion: tudo que esta como Included la = incluidos por texto completo + aprovados na passada 1
C['notion_included_total'] = soma(lambda r: r['stage'] == 'Included')
assert C['notion_included_total'] == C['incluidos_tc'] + C['p1_em_analise']
C['estudos_primarios_tc'] = C['incluidos_tc'] - tipo.get('Survey', 0)
C['extracao'] = S['q2_extracao']
C['included_com_ec_preenchido'] = soma(lambda r: r['stage'] == 'Included' and r['ec'])
# Incluidos por texto completo sem PDF na pasta (precisam do PDF para a extracao); lista de IDs vinda do Notion
_inc = os.path.join(BASE, f'incluidos_tc_{DATA}.json')
if os.path.exists(_inc):
    INC = json.load(open(_inc))
    assert len(INC) == C['incluidos_tc'], (len(INC), C['incluidos_tc'])
    C['incluidos_sem_pdf_ids'] = sorted(p for p in INC if p not in LOCAL)
    C['incluidos_sem_pdf'] = len(C['incluidos_sem_pdf_ids'])

# Lista de PDFs faltantes (se existir), deve fechar com 'aguardando_pdf'
LISTA = os.path.join(BASE, f'pdfs_faltantes_{DATA}.csv')
if os.path.exists(LISTA):
    lf = list(csv.DictReader(open(LISTA, encoding='utf-8-sig'), delimiter=';'))
    if 'como_obter' in lf[0]:  # listas ate a v2 de 10/10
        cat = collections.Counter()
        for x in lf:
            c = x['como_obter']
            cat['CAFe' if c.startswith('CAFe') else 'aberto' if c.startswith('aberto') else
                'verificar' if c.startswith('verificar') else 'sem DOI'] += 1
        C['pdfs_faltantes_por_categoria'] = dict(cat)
        C['pdfs_faltantes_detalhe'] = dict(collections.Counter(x['como_obter'] for x in lf))
    C['pdfs_faltantes_por_origem'] = dict(collections.Counter(x['origem'] for x in lf))
    # a lista tem os que aguardam PDF (buscados) e, a parte, os incluidos sem PDF (ja decididos; PDF para a extracao)
    if 'prioridade' in lf[0]:
        C['pdfs_faltantes_por_prioridade'] = dict(collections.Counter(x['prioridade'] for x in lf))
    n_incl = sum(1 for x in lf if x['origem'].startswith('incluído'))
    assert len(lf) - n_incl == C['aguardando_pdf'], (len(lf) - n_incl, C['aguardando_pdf'])
    assert n_incl == C.get('incluidos_sem_pdf', 0), (n_incl, C.get('incluidos_sem_pdf'))
    assert {x['pid'] for x in lf} == (set(C['p1_aprov_sem_pdf_ids']) | set(C.get('incluidos_sem_pdf_ids', []))
                                      | set(C['rq3_grupo_F_sem_pdf_ids']))

# Fechamento global do banco
assert C['banco_total'] == 5565
assert C['banco_bases'] == C['ec5_titulo'] + C['excl_r1'] + C['aprov_r1']
assert C['aprov_r1'] == C['p1_excluidos'] + C['p1_pendentes'] + C['buscados']
assert C['buscados'] == C['nao_recuperados_ec6'] + C['aguardando_pdf'] + C['recuperados']
assert C['recuperados'] == C['avaliados'] + C['pendentes_decisao_com_pdf']
assert sum(C['banco_por_string'].values()) == C['banco_total']
assert sum(C['log_por_string'].values()) == C['log_total']

# Concordancia passada 1 x pre-triagem (para o par. 8)
conc = collections.Counter()
grp = collections.Counter()
for r in P1:
    pid = r['Paper ID']
    d = 'aprovado' if r['Selection Stage'] == 'Included' else 'excluido'
    conc[f"{PRE[pid]['classe']} -> {d}"] += 1
    grp[f"grupo {PRE[pid]['grupo']} -> {d}"] += 1
C['p1_x_pretriagem'] = dict(sorted(conc.items()))
C['p1_por_grupo'] = dict(sorted(grp.items()))
C['p1_excluidos_por_ec'] = dict(C['p1_excluidos_por_ec'])

json.dump(C, open(os.path.join(BASE, f'contagens_prisma_{DATA}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
for k, v in C.items():
    print(k, '=', v)
print('OK: todos os fechamentos conferem')
