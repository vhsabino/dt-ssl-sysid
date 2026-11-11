"""Funil PRISMA da SLR 2026 (gemeos digitais de robos moveis), versao detalhada (acompanhamento), no estilo da
figura de 11/09/2026. Desde 23/10 grava fig_funil_prisma_<data>_detalhado; a versao para apresentacao
(prisma_funil_apresentacao.py) grava fig_funil_prisma_<data>.

Uso:  python prisma_funil.py contagens_prisma_2026-10-02.json
Gera fig_funil_prisma_<data>.png e .pdf na mesma pasta do JSON. Todos os numeros vem do JSON,
que e derivado das consultas ao banco do Notion (deriva_contagens.py); nada e digitado a mao aqui.
"""
import json
import os
import re
import sys

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

AZUL, AZUL_F = '#2f74c9', '#eef4fc'
CINZA, CINZA_F = '#bdbdb5', '#f5f5f3'
LAR, LAR_F = '#e2662f', '#fdf1eb'
VERDE, VERDE_F = '#1f9e74', '#e9f6f1'
TXT, CORPO, SUAVE, MARINHO = '#111111', '#444444', '#8a8a8a', '#1d3a6b'
FUNDO = '#fbfbf9'
U = 5.0  # unidades de dados por polegada


def f(n):
    return f'{n:,}'.replace(',', '.')


def curtos(ids):
    return ', '.join(re.sub(r'^SLR-\d{4}-', '', i) for i in ids)


def linhas_ids(ids, por_linha=6):
    """Lista de IDs curtos entre parenteses, quebrada em linhas para caber na caixa."""
    c = [re.sub(r'^SLR-\d{4}-', '', i) for i in ids]
    g = [', '.join(c[k:k + por_linha]) for k in range(0, len(c), por_linha)] or ['']
    return [('(' if k == 0 else '') + t + (')' if k == len(g) - 1 else ',') for k, t in enumerate(g)]


def lh(pt, k=1.62):
    return pt * k / 72 * U


class Fig:
    def __init__(self, w_in=20, h_in=24.6):
        self.fig = plt.figure(figsize=(w_in, h_in), facecolor=FUNDO)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w_in * U)
        self.ax.set_ylim(0, h_in * U)
        self.ax.axis('off')
        self.H = h_in * U

    def caixa(self, x0, x1, ytop, linhas, borda, fundo, alinhar='center', lw=2.6):
        """linhas: lista de (texto, pt, cor, peso) ou (rotulo, numero, pt, cor, peso) para colunas."""
        pad = 1.35
        h = pad * 2 + sum(lh(ln[-3]) for ln in linhas) - 0.25
        ybot = ytop - h
        self.ax.add_patch(FancyBboxPatch((x0, ybot), x1 - x0, h, boxstyle='round,pad=0,rounding_size=0.9',
                                         lw=lw, ec=borda, fc=fundo, zorder=1))
        y = ytop - pad
        for ln in linhas:
            pt, cor, peso = ln[-3], ln[-2], ln[-1]
            y -= lh(pt) * 0.78
            if len(ln) == 5:
                self.ax.text(x0 + 1.8, y, ln[0], fontsize=pt, color=cor, weight=peso, ha='left', va='baseline')
                self.ax.text(x1 - 1.8, y, ln[1], fontsize=pt, color=cor, weight=peso, ha='right', va='baseline')
            else:
                xa = {'center': (x0 + x1) / 2, 'left': x0 + 1.8}[alinhar]
                self.ax.text(xa, y, ln[0], fontsize=pt, color=cor, weight=peso, ha=alinhar, va='baseline')
            y -= lh(pt) * 0.22
        return ybot

    def seta(self, p0, p1):
        self.ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle='-|>,head_length=0.9,head_width=0.55', lw=2.4,
                                          color=CINZA, mutation_scale=14, zorder=0))

    def fase(self, rotulo, ytop, ybot):
        self.ax.plot([3.6, 3.6], [ybot, ytop], color=CINZA, lw=1.6)
        self.ax.text(2.1, (ytop + ybot) / 2, rotulo, rotation=90, ha='center', va='center', fontsize=12.5,
                     color=SUAVE, weight='bold')


def reteste_txt(path_json):
    """Resultado do teste-reteste, se estiver em ../reteste/ (layout da pasta slr\\artigos)."""
    import glob
    arq = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(path_json)), '..', 'reteste',
                                        'resultado_reteste_*.json')))
    if not arq:
        return None
    R = json.load(open(arq[-1], encoding='utf-8'))
    return f'teste-reteste feito (n = {R["n"]}): concordância {R["po"] * 100:.0f}%, kappa {R["kappa"]:.2f}'.replace('.', ',')


def main(path_json):
    C = json.load(open(path_json, encoding='utf-8'))
    m = re.search(r'(\d{4}-\d{2}-\d{2})(_v(\d+))?\.json$', os.path.basename(path_json))
    data = m.group(1) + (m.group(2) or '')
    dd = '/'.join(reversed(m.group(1).split('-'))) + (f' (atualização {m.group(3)})' if m.group(3) else '')
    F = Fig()
    ax = F.ax
    xm0, xm1, xs0, xs1 = 6.0, 56.0, 60.5, 96.5
    gap = 3.4

    ax.text(xm0, F.H - 5.2, 'Funil PRISMA: SLR 2026, Gêmeos Digitais de Robôs Móveis', fontsize=26, weight='bold',
            color=TXT)
    p2 = C.get('p1_confirmados')
    p2txt = ('passada 2 não iniciada' if p2 is None else
             f'passada 2 em andamento ({p2 + len(C["pos_p1_excl_ids"]) + len(C["pos_p1_ec6_ids"])} de {C["p1_aprovados"]} decididos)')
    ax.text(xm0, F.H - 9.0, f'Estado em {dd}   ·   passada 1 concluída   ·   {p2txt}   ·   '
                            f'{f(C["notion_included_total"])} incluídos ({f(C.get("p1_em_analise", C["p1_aprovados"]))} em análise)',
            fontsize=15, color=CORPO)
    ax.plot([xm0, xs1], [F.H - 11.0, F.H - 11.0], color=CINZA, lw=1.4)

    # 1. Identificacao
    y = F.H - 13.5
    lb = C['log_por_base']
    m1 = F.caixa(xm0, xm1, y, [
        (f'Registros identificados nas bases      n = {f(C["log_total"])}', 17, TXT, 'bold'),
        ('7 fontes × 5 strings (S1 a S5), buscas de 11 e 12/07/2026 (log do protocolo, §3)', 13, CORPO, 'normal'),
        (f'SpringerLink {f(lb["SpringerLink"])}  ·  ACM DL {f(lb["ACM DL"])}  ·  OpenAlex {f(lb["OpenAlex"])}'
         f'  ·  Scopus {f(lb["Scopus"])}', 13, CORPO, 'normal'),
        (f'Semantic Scholar {f(lb["Semantic Scholar"])}  ·  IEEE Xplore {f(lb["IEEE Xplore"])}'
         f'  ·  arXiv {f(lb["arXiv"])}', 13, CORPO, 'normal'),
        ('Web of Science, complementar no protocolo, não aparece no log', 12, LAR, 'normal'),
    ], AZUL, AZUL_F)
    rem = C['removidos_ingestao'] + C['ec5_titulo'] + C['registro_vazio']
    s1 = F.caixa(xs0, xs1, y, [
        (f'Removidos antes da triagem      n = {f(rem)}', 16, TXT, 'bold'),
        ('deduplicação na ingestão (log − banco) *', f(C['removidos_ingestao']), 13, CORPO, 'normal'),
        ('duplicatas por título normalizado (EC5)', f(C['ec5_titulo']), 13, CORPO, 'normal'),
        ('registro vazio (27 e 28/08)', f(C['registro_vazio']), 13, CORPO, 'normal'),
        ('* conferir no log de ingestão o que foi DOI e o que foi outro motivo', 11.5, SUAVE, 'normal'),
    ], CINZA, CINZA_F, alinhar='left')
    yb = min(m1, s1)
    F.seta((xm1 + 0.3, (y + m1) / 2), (xs0 - 0.3, (y + m1) / 2))
    F.fase('IDENTIFICAÇÃO', y, yb)

    # 2. Triagem rodada 1
    y2 = yb - gap
    F.seta(((xm0 + xm1) / 2, m1 - 0.2), ((xm0 + xm1) / 2, y2 + 0.2))
    e = C['excl_r1_por_ec']
    m2 = F.caixa(xm0, xm1, y2, [
        (f'Registros triados por título e resumo      n = {f(C["triados_r1"])}', 17, TXT, 'bold'),
        ('rodada 1 (jul e ago/2026), todas as RQs, pelo pesquisador', 13, CORPO, 'normal'),
        ('verificação assistida com confirmação individual (26 a 28/08)', 13, CORPO, 'normal'),
        (reteste_txt(path_json) or 'teste-reteste de ~10% ainda pendente', 12.5, LAR, 'bold'),
    ], AZUL, FUNDO)
    s2 = F.caixa(xs0, xs1, y2, [
        (f'Excluídos      n = {f(C["excl_r1"])}', 16, TXT, 'bold'),
        ('EC1  Fora do escopo *', f(e['EC1']), 13, CORPO, 'normal'),
        ('EC4  Idioma', f(e['EC4']), 13, CORPO, 'normal'),
        ('EC2  Sem avaliação empírica', f(e['EC2']), 13, CORPO, 'normal'),
        ('sem critério (Youndo-914)', f(e['sem']), 13, LAR, 'normal'),
        ('* inclui 607 front-matter de proceedings excluídos em lote (§8, 12/07)', 11.5, SUAVE, 'normal'),
    ], CINZA, CINZA_F, alinhar='left')
    F.seta((xm1 + 0.3, (y2 + m2) / 2), (xs0 - 0.3, (y2 + m2) / 2))
    yb2 = min(m2, s2)

    # 3. Triagem rodada 2 (passada 1)
    y3 = yb2 - gap
    F.seta(((xm0 + xm1) / 2, m2 - 0.2), ((xm0 + xm1) / 2, y3 + 0.2))
    m3 = F.caixa(xm0, xm1, y3, [
        (f'Aprovados na rodada 1      n = {f(C["aprov_r1"])}', 17, TXT, 'bold'),
        (f'RQ2 e RQ3: direto ao texto completo      {f(C["tc_direto"])}', 13, CORPO, 'normal'),
        (f'RQ1 e RQ4: passada 1 por resumo, com pré-triagem IA      {f(C["p1_total"])}', 13, CORPO, 'normal'),
        (f'passada 1: {f(C["p1_aprovados"])} aprovados  ·  {f(C["p1_excluidos"])} excluídos  ·  '
         + (f'{C["p1_pendentes"]} sem decisão ({curtos(C["p1_pendentes_ids"])})' if C['p1_pendentes']
            else 'fechada em 09/10 (nenhum sem decisão)'), 13, LAR, 'bold'),
    ], AZUL, AZUL_F)
    pe = C['p1_excluidos_por_ec']
    s3 = F.caixa(xs0, xs1, y3, [
        (f'Excluídos na passada 1      n = {f(C["p1_excluidos"])}', 16, TXT, 'bold'),
        ('EC1  Fora do escopo', f(pe.get('EC1', 0)), 13, CORPO, 'normal'),
        ('EC4  Idioma', f(pe.get('EC4', 0)), 13, CORPO, 'normal'),
        ('EC2  Sem avaliação empírica', f(pe.get('EC2', 0)), 13, CORPO, 'normal'),
        ('decisão por resumo: no PRISMA conta como triagem', 11.5, SUAVE, 'normal'),
    ], CINZA, CINZA_F, alinhar='left')
    F.seta((xm1 + 0.3, (y3 + m3) / 2), (xs0 - 0.3, (y3 + m3) / 2))
    yb3 = min(m3, s3)
    F.fase('TRIAGEM', y2, yb3)

    # 4. Recuperacao
    y4 = yb3 - gap
    F.seta(((xm0 + xm1) / 2, m3 - 0.2), ((xm0 + xm1) / 2, y4 + 0.2))
    m4 = F.caixa(xm0, xm1, y4, [
        (f'Relatórios buscados (texto completo)      n = {f(C["buscados"])}', 17, TXT, 'bold'),
        (f'{f(C["tc_direto"])} da RQ2 e RQ3  +  {f(C["p1_aprovados"])} aprovados na passada 1', 13, CORPO,
         'normal'),
        (f'aguardando PDF: {f(C["aguardando_pdf"])}, todos aprovados na passada 1 (RQ3 grupo F resolvido em 09/10)',
         13, LAR, 'bold'),
    ], AZUL, AZUL_F)
    s4 = F.caixa(xs0, xs1, y4, [
        (f'Não recuperados      n = {f(C["nao_recuperados_ec6"])}', 16, TXT, 'bold'),
        ('EC6  Indisponível', f(C['nao_recuperados_ec6']), 13, CORPO, 'normal'),
    ] + ([(f'{len(C["pos_p1_ec6_ids"])} aprovados na passada 1: {curtos(C["pos_p1_ec6_ids"])}', 11.5, SUAVE, 'normal')]
         if C.get('pos_p1_ec6_ids') else []), CINZA, CINZA_F, alinhar='left')
    F.seta((xm1 + 0.3, (y4 + s4) / 2), (xs0 - 0.3, (y4 + s4) / 2))
    yb4 = min(m4, s4)

    # 5. Elegibilidade
    y5 = yb4 - gap
    F.seta(((xm0 + xm1) / 2, m4 - 0.2), ((xm0 + xm1) / 2, y5 + 0.2))
    m5 = F.caixa(xm0, xm1, y5, [
        (f'Relatórios avaliados no texto completo      n = {f(C["avaliados"])}', 17, TXT, 'bold'),
        ('RQ2 e RQ3 fechadas (os 22 pendentes da RQ3 foram decididos em 09/10: 4 incluídos, 18 excluídos)', 13,
         CORPO, 'normal'),
        (f'com PDF e sem decisão: {C["pendentes_decisao_com_pdf"]}, todos da passada 1', 13, LAR, 'bold'),
        ('passada 2 (texto completo) da RQ1 e RQ4 não iniciada' if C.get('p1_confirmados') is None else
         f'passada 2 (texto completo) da RQ1 e RQ4 em andamento: {C["p1_confirmados"]} '
         + ('confirmado' if C["p1_confirmados"] == 1 else 'confirmados') + ' com SKIM', 13, LAR, 'bold'),
    ], LAR, LAR_F)
    et = C['excl_tc_por_ec']
    s5 = F.caixa(xs0, xs1, y5, [
        (f'Excluídos no texto completo      n = {f(C["excl_tc"])}', 16, TXT, 'bold'),
    ] + [(r, f(et.get(k, 0)), 13, CORPO, 'normal') for k, r in sorted(
        [('EC1', 'EC1  Fora do escopo *'), ('EC3', 'EC3  Não peer-reviewed'), ('EC2', 'EC2  Sem avaliação empírica'),
         ('EC4', 'EC4  Idioma'), ('EC5', 'EC5  Duplicata ou versão anterior')],
        key=lambda t: (-et.get(t[0], 0), t[0]))] + [
        (f'* {C["excl_tc_registro_com_etapa_errada"]} registro marcado Excluded Title/Abstract por engano',
         11.5, SUAVE, 'normal'),
    ] + ([(f'{len(C["excl_sem_pdf_rq3_ids"]) + len(C["excl_sem_pdf_p1_ids"])} decididos sem o PDF: '
           f'{len(C["excl_sem_pdf_rq3_ids"])} da RQ3 (09/10) e {len(C["excl_sem_pdf_p1_ids"])} da passada 1', 11.5, SUAVE, 'normal'),
          *[(t, 11.5, SUAVE, 'normal') for t in linhas_ids(C['excl_sem_pdf_p1_ids'])]]
         if C.get('excl_sem_pdf_rq3_ids') or C.get('excl_sem_pdf_p1_ids') else []) + [
    ], CINZA, CINZA_F, alinhar='left')
    F.seta((xm1 + 0.3, (y5 + m5) / 2), (xs0 - 0.3, (y5 + m5) / 2))
    yb5 = min(m5, s5)
    F.fase('ELEGIBILIDADE', y4, yb5)

    # 6. Incluidos
    y6 = yb5 - gap
    F.seta(((xm0 + xm1) / 2, m5 - 0.2), ((xm0 + xm1) / 2, y6 + 0.2))
    rq = dict(C['incluidos_tc_ocorrencias_rq'])
    for q, n in C.get('p1_aprovados_por_rq', {}).items():
        rq[q] = rq.get(q, 0) + n
    tp = C['incluidos_tc_por_tipo']
    nt = C['notion_included_total']
    surveys = tp.get('Survey', 0) + C['incluidos_p1_survey']
    m6 = F.caixa(xm0, xm1, y6, [
        (f'Estudos incluídos      n = {f(nt)}  ({f(C.get("p1_em_analise", C["p1_aprovados"]))} em análise)', 18, MARINHO, 'bold'),
        (f'{f(C["incluidos_tc"])} confirmados no texto completo ({f(C["incluidos_bases"])} das bases + '
         f'{C["outros_metodos"]} de outros métodos)', 13, CORPO, 'normal'),
        (f'{f(C.get("p1_em_analise", C["p1_aprovados"]))} aprovados na passada 1, em análise: texto completo pendente (passada 2)', 13,
         LAR, 'bold'),
        (f'RQ1 {rq.get("RQ1", 0)}  ·  RQ2 {rq.get("RQ2", 0)}  ·  RQ3 {rq.get("RQ3", 0)}  ·  RQ4 {rq.get("RQ4", 0)}'
         f'   (ocorrências; há estudos em duas RQs)', 13, CORPO, 'normal'),
        (f'{surveys} revisões de terceiros (Type Survey: {tp.get("Survey", 0)} confirmadas, '
         f'{C["incluidos_p1_survey"]} em análise): related-SLRs, não primários', 12.5, CORPO, 'normal'),
        (f'{C.get("incluidos_sem_pdf", 0)} incluídos sem PDF na pasta ({curtos(C.get("incluidos_sem_pdf_ids", []))}): '
         f'obter para a extração', 12.5, LAR, 'bold'),
        (f'estudos primários: {f(C["estudos_primarios_tc"])} confirmados + '
         f'{f(C.get("p1_em_analise", C["p1_aprovados"]) - C["incluidos_p1_survey"])} em análise   ·   extração (§6) e DARE: '
         f'{C["extracao"]["Data Extracted"]} de {f(nt)}', 13, LAR, 'bold'),
    ], VERDE, VERDE_F, lw=3.0)
    s6 = F.caixa(xs0, xs1, y6, [
        (f'Outros métodos      n = {C["outros_metodos"]}', 16, TXT, 'bold'),
        ('snowballing backward: DROPO (Tiboni-SB001, 12/07)', 12.5, CORPO, 'normal'),
        ('entrada manual: asRoBallet (EXT, 02/09), o +1 do banco', 12.5, CORPO, 'normal'),
        ('asRoBallet é preprint arXiv: EC3 a decidir', 12.5, LAR, 'bold'),
        ('snowballing sistemático (§3): não iniciado', 12.5, LAR, 'bold'),
    ], CINZA, CINZA_F, alinhar='left')
    F.seta((xs0 - 0.3, (y6 + s6) / 2), (xm1 + 0.3, (y6 + s6) / 2))
    yb6 = min(m6, s6)
    F.fase('INCLUÍDOS', y6, yb6)

    # Pendencias
    y7 = yb6 - 3.0
    pc = C.get('pdfs_faltantes_por_categoria', {})
    pp = C.get('pdfs_faltantes_por_prioridade', {})
    rq3_pend = C['rq3_pendentes_com_pdf'] + C['rq3_grupo_F_com_pdf'] + C['rq3_grupo_F_sem_pdf']
    pend = [
        ((f'PDFs: {C["aguardando_pdf"] + C.get("incluidos_sem_pdf", 0)} a obter (pdfs_faltantes_{data}.html): '
          f'{pp.get("ir atrás", 0)} valem ir atrás até o autor, {pp.get("rota fácil", 0)} só por rota fácil'
          + (f', {pp["provável exclusão"]} prováveis exclusões sem precisar do PDF' if pp.get('provável exclusão') else '')) if pp else
         (f'PDFs: {C["aguardando_pdf"] + C.get("incluidos_sem_pdf", 0)} a obter (pdfs_faltantes_{data}.csv): '
          f'{pc.get("verificar", 0)} para conferir antes (idioma ou peer review), {pc.get("aberto", 0)} abertos no '
          f'navegador, {pc.get("CAFe", 0)} pelo CAFe, {pc.get("sem DOI", 0)} sem DOI'), 13, CORPO, 'normal'),
        (f'Passada 2 (texto completo): {C.get("p1_em_analise", C["p1_aprovados"])} aprovados na passada 1 em análise'
         + (f' e {rq3_pend} pendentes da RQ3' if rq3_pend else '') + f'; {C["pendentes_decisao_com_pdf"]} já têm PDF',
         13, CORPO, 'normal'),
        ('Marcação no Notion: excluídos da passada 1 estão como Excluded Full-Text (decisão por resumo)'
         + ('' if not C.get('included_com_ec_preenchido') else '; há Included com EC preenchido'), 13, CORPO, 'normal'),
        ('Decidir: EC do Youndo-914, EC3 do asRoBallet, Type Survey para Literature Review; os decididos sem PDF '
         'ficam em elegibilidade ou vão para a triagem', 13, CORPO, 'normal'),
        ('Snowballing backward e forward sobre os incluídos, depois da passada 2', 13, CORPO, 'normal'),
        (('Teste-reteste (kappa); ' if not reteste_txt(path_json) else 'Reteste feito, registrar no §8; ')
         + 'Web of Science e log de ingestão no §8; extração e DARE', 13, CORPO, 'normal'),
    ]
    y7b = F.caixa(xm0, xs1, y7, [('O que falta para fechar o funil', 16, LAR, 'bold')] + pend, LAR, FUNDO,
                  alinhar='left', lw=2.0)

    yf = y7b - 2.6
    ax.plot([xm0, xs1], [yf, yf], color=CINZA, lw=1.4)
    ax.text(xm0, yf - 2.9, f'Incluídos: {f(nt)}, dos quais {C.get("p1_em_analise", C["p1_aprovados"])} aprovados na passada 1 (por resumo) '
                           f'seguem em análise até a leitura do texto completo; {f(C["incluidos_tc"])} confirmados.',
            fontsize=14, weight='bold', color=TXT)
    ax.text(xm0, yf - 5.6, f'Fonte: banco da SLR no Notion (consultas de {dd}) e log de busca do protocolo (§3). '
                           'Números gerados por deriva_contagens.py e prisma_funil.py.', fontsize=11.5, color=SUAVE)
    ymin = yf - 7.6
    ax.set_ylim(ymin, F.H)
    F.fig.set_size_inches(20, (F.H - ymin) / U)

    out = os.path.join(os.path.dirname(os.path.abspath(path_json)), f'fig_funil_prisma_{data}_detalhado')
    F.fig.savefig(out + '.png', dpi=170, facecolor=FUNDO)
    F.fig.savefig(out + '.pdf', facecolor=FUNDO)
    print('salvo:', out + '.png', '|', out + '.pdf')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'contagens_prisma_2026-10-09.json')
