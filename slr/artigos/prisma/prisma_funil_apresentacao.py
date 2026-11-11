"""Funil PRISMA da SLR 2026, versao para apresentacao (uma lamina, 3:2, pouco texto).

Uso:  python prisma_funil_apresentacao.py contagens_prisma_2026-10-23.json
Gera fig_funil_prisma_<data>.png e .pdf na pasta do JSON. Todos os numeros vem do JSON
(deriva_contagens.py) e, para a linha do teste-reteste, de ../reteste/resultado_reteste_*.json quando existir;
nada e digitado a mao. O fluxo fecha de cima para baixo: 290 buscados = 4 nao recuperados + 286 de texto
completo; 286 = avaliados + em avaliacao; avaliados = excluidos no texto completo + incluidos das bases.
"""
import glob
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
TXT, CORPO, SUAVE = '#111111', '#3f3f3f', '#8a8a8a'
FUNDO = '#ffffff'
U = 5.0  # unidades de dados por polegada
PT_T, PT_S, PT_B, PT_F = 14, 13, 10.5, 9.5  # titulo da caixa principal, da lateral, corpo, rodape


def f(n):
    return f'{n:,}'.replace(',', '.')


def lh(pt, k=1.55):
    return pt * k / 72 * U


class Fig:
    def __init__(self, w_in, h_in):
        self.fig = plt.figure(figsize=(w_in, h_in), facecolor=FUNDO)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, w_in * U)
        self.ax.set_ylim(0, h_in * U)
        self.ax.axis('off')
        self.W, self.H = w_in * U, h_in * U

    def caixa(self, x0, x1, ytop, titulo, n, corpo, borda, fundo, pt_t=PT_T, lw=2.2, cor_n=None):
        """Caixa com titulo + n a direita e ate duas linhas de corpo. Devolve o y de baixo."""
        pad = 0.75
        h = pad * 2 + lh(pt_t) + sum(lh(PT_B) for _ in corpo) - 0.2
        ybot = ytop - h
        self.ax.add_patch(FancyBboxPatch((x0, ybot), x1 - x0, h, boxstyle='round,pad=0,rounding_size=0.7',
                                         lw=lw, ec=borda, fc=fundo, zorder=1))
        y = ytop - pad - lh(pt_t) * 0.74
        self.ax.text(x0 + 1.3, y, titulo, fontsize=pt_t, color=TXT, weight='bold', ha='left', va='baseline')
        self.ax.text(x1 - 1.3, y, f'n = {f(n)}', fontsize=pt_t + 1, color=cor_n or TXT, weight='bold', ha='right',
                     va='baseline')
        for texto, cor in corpo:
            y -= lh(PT_B)
            self.ax.text(x0 + 1.3, y, texto, fontsize=PT_B, color=cor, ha='left', va='baseline')
        return ybot

    def seta(self, p0, p1):
        self.ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle='-|>,head_length=0.8,head_width=0.5', lw=2.0,
                                          color=CINZA, mutation_scale=12, zorder=0))

    def fase(self, rotulo, x, ytop, ybot):
        self.ax.plot([x + 1.3, x + 1.3], [ybot, ytop], color=CINZA, lw=1.4)
        self.ax.text(x + 0.3, (ytop + ybot) / 2, rotulo, rotation=90, ha='center', va='center', fontsize=10.5,
                     color=SUAVE, weight='bold')


def reteste(path_json):
    """Linha do teste-reteste, se o resultado estiver em ../reteste/ (layout da pasta slr\\artigos)."""
    pasta = os.path.join(os.path.dirname(os.path.abspath(path_json)), '..', 'reteste')
    arq = sorted(glob.glob(os.path.join(pasta, 'resultado_reteste_*.json')))
    if not arq:
        return None
    R = json.load(open(arq[-1], encoding='utf-8'))
    return (f'teste-reteste em amostra de {R["n"]}: concordância {R["po"] * 100:.0f}%, '
            f'kappa de Cohen {R["kappa"]:.2f}'.replace('.', ','))


def main(path_json):
    C = json.load(open(path_json, encoding='utf-8'))
    m = re.search(r'(\d{4}-\d{2}-\d{2})(_v(\d+))?\.json$', os.path.basename(path_json))
    data = m.group(1) + (m.group(2) or '')
    dd = '/'.join(reversed(m.group(1).split('-')))
    em_analise = C.get('p1_em_analise', C['p1_aprovados'])
    tc = C['buscados'] - C['nao_recuperados_ec6']
    assert tc == C['avaliados'] + C['pendentes_decisao_com_pdf'] + C['aguardando_pdf']
    assert C['avaliados'] == C['excl_tc'] + C['incluidos_bases']
    assert C['notion_included_total'] == C['incluidos_tc'] + em_analise
    et, lb, rq = C['excl_tc_por_ec'], C['log_por_base'], C['incluidos_tc_ocorrencias_rq']
    surveys = C['incluidos_tc_por_tipo'].get('Survey', 0)

    F = Fig(13.333, 9.0)
    ax = F.ax
    xl, xm0, xm1, xs0, xs1 = 0.6, 3.6, 36.4, 39.6, 66.0
    gap = 1.25

    ax.text(xm0, F.H - 2.3, 'Funil PRISMA: SLR 2026, Gêmeos Digitais de Robôs Móveis', fontsize=19, weight='bold',
            color=TXT)
    ax.text(xm0, F.H - 4.0, f'Estado em {dd}  ·  texto completo em andamento (passada 2 da RQ1 e RQ4)',
            fontsize=11.5, color=CORPO)
    ax.plot([xm0, xs1], [F.H - 4.9, F.H - 4.9], color=CINZA, lw=1.2)

    # 1. Identificacao
    y = F.H - 6.0
    m1 = F.caixa(xm0, xm1, y, 'Registros identificados nas bases', C['log_total'], [
        (f'SpringerLink {f(lb["SpringerLink"])}  ·  ACM DL {f(lb["ACM DL"])}  ·  OpenAlex {f(lb["OpenAlex"])}'
         f'  ·  Scopus {f(lb["Scopus"])}', CORPO),
        (f'Semantic Scholar {f(lb["Semantic Scholar"])}  ·  IEEE Xplore {f(lb["IEEE Xplore"])}'
         f'  ·  arXiv {f(lb["arXiv"])}     (5 strings de busca, julho de 2026)', CORPO),
    ], AZUL, AZUL_F)
    rem = C['removidos_ingestao'] + C['ec5_titulo'] + C['registro_vazio']
    s1 = F.caixa(xs0, xs1, y, 'Removidos antes da triagem', rem, [
        (f'deduplicação na ingestão {f(C["removidos_ingestao"])}', CORPO),
        (f'duplicatas por título {f(C["ec5_titulo"])}  ·  registro vazio {C["registro_vazio"]}', CORPO),
    ], CINZA, CINZA_F, pt_t=PT_S)
    F.seta((xm1 + 0.3, (y + m1) / 2), (xs0 - 0.3, (y + m1) / 2))
    F.fase('IDENTIFICAÇÃO', xl, y, m1)

    # 2. Triagem por titulo e resumo
    y2 = m1 - gap
    F.seta(((xm0 + xm1) / 2, m1 - 0.15), ((xm0 + xm1) / 2, y2 + 0.15))
    corpo2 = [('rodada 1, julho e agosto de 2026, um revisor', CORPO)]
    rt = reteste(path_json)
    if rt:
        corpo2.append((rt, CORPO))
    m2 = F.caixa(xm0, xm1, y2, 'Registros triados por título e resumo', C['triados_r1'], corpo2, AZUL, AZUL_F)
    er = C['excl_r1_por_ec']
    s2 = F.caixa(xs0, xs1, y2, 'Excluídos na triagem', C['excl_r1'], [
        (f'EC1 fora do escopo {f(er.get("EC1", 0))}  ·  EC4 idioma {er.get("EC4", 0)}', CORPO),
        (f'EC2 sem avaliação empírica {er.get("EC2", 0)}  ·  sem critério {er.get("sem", 0)}', CORPO),
    ], CINZA, CINZA_F, pt_t=PT_S)
    F.seta((xm1 + 0.3, (y2 + m2) / 2), (xs0 - 0.3, (y2 + m2) / 2))

    # 3. Aprovados na rodada 1 e passada 1 por resumo
    y3 = m2 - gap
    F.seta(((xm0 + xm1) / 2, m2 - 0.15), ((xm0 + xm1) / 2, y3 + 0.15))
    m3 = F.caixa(xm0, xm1, y3, 'Aprovados para leitura', C['aprov_r1'], [
        (f'RQ2 e RQ3: {C["tc_direto"]} direto ao texto completo', CORPO),
        (f'RQ1 e RQ4: passada 1 por resumo, {C["p1_total"]} → {C["p1_aprovados"]} aprovados '
         '(pré-triagem assistida por IA)', CORPO),
    ], AZUL, AZUL_F)
    ep = C['p1_excluidos_por_ec']
    s3 = F.caixa(xs0, xs1, y3, 'Excluídos na passada 1', C['p1_excluidos'], [
        ('decisão por resumo:  ' + '  ·  '.join(f'{k} {v}' for k, v in sorted(ep.items(), key=lambda t: -t[1])), CORPO),
    ], CINZA, CINZA_F, pt_t=PT_S)
    F.seta((xm1 + 0.3, (y3 + m3) / 2), (xs0 - 0.3, (y3 + m3) / 2))
    F.fase('TRIAGEM', xl, y2, min(m3, s3))

    # 4. Buscados para texto completo
    y4 = m3 - gap
    F.seta(((xm0 + xm1) / 2, m3 - 0.15), ((xm0 + xm1) / 2, y4 + 0.15))
    m4 = F.caixa(xm0, xm1, y4, 'Relatórios buscados para o texto completo', C['buscados'], [
        (f'{C["tc_direto"]} das RQ2 e RQ3  +  {C["p1_aprovados"]} aprovados na passada 1', CORPO),
    ], AZUL, AZUL_F)
    s4 = F.caixa(xs0, xs1, y4, 'Não recuperados', C['nao_recuperados_ec6'], [
        ('EC6 texto completo indisponível', CORPO),
    ], CINZA, CINZA_F, pt_t=PT_S)
    F.seta((xm1 + 0.3, (y4 + m4) / 2), (xs0 - 0.3, (y4 + m4) / 2))

    # 5. Texto completo: avaliados e em avaliacao
    y5 = m4 - gap
    F.seta(((xm0 + xm1) / 2, m4 - 0.15), ((xm0 + xm1) / 2, y5 + 0.15))
    m5 = F.caixa(xm0, xm1, y5, 'Relatórios de texto completo', tc, [
        (f'avaliados {C["avaliados"]}   ·   em avaliação {em_analise} (passada 2 da RQ1 e RQ4)', CORPO),
        (f'dos {em_analise} em avaliação: {C["pendentes_decisao_com_pdf"]} com PDF na pasta e '
         f'{C["aguardando_pdf"]} aguardando PDF', LAR),
    ], LAR, LAR_F)
    nomes = {'EC1': 'EC1 fora do escopo', 'EC2': 'EC2 sem avaliação empírica', 'EC3': 'EC3 não peer-reviewed',
             'EC4': 'EC4 idioma', 'EC5': 'EC5 duplicata'}
    ecs = sorted(et.items(), key=lambda t: (-t[1], t[0]))
    s5 = F.caixa(xs0, xs1, y5, 'Excluídos no texto completo', C['excl_tc'], [
        ('  ·  '.join(f'{nomes[k]} {v}' for k, v in ecs[:3]), CORPO),
        ('  ·  '.join(f'{nomes[k]} {v}' for k, v in ecs[3:]), CORPO),
    ], CINZA, CINZA_F, pt_t=PT_S)
    F.seta((xm1 + 0.3, (y5 + m5) / 2), (xs0 - 0.3, (y5 + m5) / 2))
    F.fase('ELEGIBILIDADE', xl, y4, min(m5, s5))

    # 6. Incluidos
    y6 = m5 - gap
    F.seta(((xm0 + xm1) / 2, m5 - 0.15), ((xm0 + xm1) / 2, y6 + 0.15))
    m6 = F.caixa(xm0, xm1, y6, 'Estudos incluídos', C['incluidos_tc'], [
        (f'{C["incluidos_bases"]} das bases + {C["outros_metodos"]} de outros métodos   ·   '
         f'{C["estudos_primarios_tc"]} estudos primários e {surveys} revisões de terceiros', CORPO),
        ('  ·  '.join(f'{k} {v}' for k, v in sorted(rq.items())) + ' (ocorrências)   ·   '
         f'+ {em_analise} em avaliação na passada 2', CORPO),
    ], VERDE, VERDE_F, lw=3.0, cor_n=VERDE)
    s6 = F.caixa(xs0, xs1, y6, 'Outros métodos', C['outros_metodos'], [
        ('snowballing backward 1  ·  entrada manual 1', CORPO),
    ], CINZA, CINZA_F, pt_t=PT_S)
    F.seta((xs0 - 0.3, (y6 + s6) / 2), (xm1 + 0.3, (y6 + s6) / 2))
    F.fase('INCLUÍDOS', xl, y6, min(m6, s6))

    yb = min(m6, s6)
    ax.text(xm0, yb - 1.6, f'Fonte: banco da SLR no Notion, consulta de {dd}.  No banco, Included = '
                           f'{f(C["notion_included_total"])}: {C["incluidos_tc"]} confirmados no texto completo + '
                           f'{em_analise} aprovados na passada 1 ainda em avaliação.', fontsize=PT_F, color=SUAVE)
    assert yb - 2.4 > 0, f'figura estourou embaixo: {yb:.2f}'
    out = os.path.join(os.path.dirname(os.path.abspath(path_json)), f'fig_funil_prisma_{data}')
    F.fig.savefig(out + '.png', dpi=300, facecolor=FUNDO)
    F.fig.savefig(out + '.pdf', facecolor=FUNDO)
    print('salvo:', out + '.png', '|', out + '.pdf', f'| sobra embaixo {yb - 2.4:.1f} un.')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'contagens_prisma_2026-10-23.json')
