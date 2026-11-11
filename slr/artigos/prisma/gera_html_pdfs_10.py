import csv
import html
import sys
from collections import OrderedDict

src, out = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src, encoding='utf-8-sig'), delimiter=';'))
grupos = OrderedDict()
TIT = {
    'verificar idioma antes (EC4?)': ('Conferir o idioma antes de baixar', 'Periódicos nacionais (China, Coreia, Rússia, Ucrânia). Abra a página: se o texto for só em chinês, coreano, russo ou ucraniano, é EC4 e não precisa baixar.'),
    'verificar versão publicada antes (EC3?)': ('Conferir se há versão publicada antes de baixar', 'Teses, Zenodo, blog científico ou preprint. Dez minutos no Google Scholar: publicado, baixe a versão publicada; não publicado, EC3.'),
    'aberto: navegador (o servidor recusa script)': ('Abertos: um clique no navegador', 'Acesso aberto, mas o servidor bloqueia download automático.'),
    'aberto: navegador pelo DOI': ('Abertos pela página do DOI', 'A editora marca como acesso aberto; o PDF está na página do DOI.'),
}
for r in rows:
    c = r['como_obter']
    if c.startswith('CAFe'):
        key = c
        titulo = ('CAFe: ' + c[len('CAFe ('):-1], 'Entre pelo CAFe (Periódicos CAPES) e baixe em sequência na mesma sessão.')
    else:
        key = c
        titulo = TIT.get(c, (c, ''))
    grupos.setdefault(key, (titulo, []))[1].append(r)
css = """
:root{--bg:#fbfbf9;--fg:#1d1d1b;--mut:#6b6b66;--line:#e2e2dc;--acc:#2f74c9;--warn:#c2571f;--card:#ffffff}
@media (prefers-color-scheme: dark){:root{--bg:#161615;--fg:#ececea;--mut:#a3a39d;--line:#33332f;--acc:#7fb0ef;--warn:#f0905f;--card:#1f1f1d}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:28px 0 4px}
p.sub{color:var(--mut);margin:0 0 16px}p.nota{color:var(--mut);margin:0 0 8px;font-size:14px}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:12px 0}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:600}td.n{color:var(--mut);white-space:nowrap}
code{font:13px ui-monospace,Consolas,monospace;user-select:all;white-space:nowrap}
a{color:var(--acc)}.obs{color:var(--warn);font-size:13px}
.wrap{overflow-x:auto}
"""
partes = [f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PDFs que faltam</title><style>{css}</style></head><body><main>',
          '<h1>PDFs que faltam baixar</h1>',
          f'<p class="sub">SLR 2026 · estado de 10/10/2026 · {len(rows)} registros: {sum(1 for r in rows if r["origem"] == "passada 1")} aprovados na passada 1 aguardando PDF e {sum(1 for r in rows if r["origem"].startswith("incluído"))} incluídos da RQ3 sem PDF (para a extração)</p>',
          '<div class="box">Salve cada arquivo em <code>slr\\artigos\\</code> com o nome <code>&lt;Paper ID&gt;.pdf</code> '
          '(clique no ID para selecionar e copiar). Se preferir não renomear, jogue tudo em <code>slr\\artigos\\_entrada\\</code> '
          'com o nome que vier: eu leio o DOI de cada PDF e renomeio.</div>']
for key, ((tit, nota), lst) in grupos.items():
    partes.append(f'<h2>{html.escape(tit)} ({len(lst)})</h2>')
    if nota:
        partes.append(f'<p class="nota">{html.escape(nota)}</p>')
    partes.append('<div class="wrap"><table><thead><tr><th>#</th><th>Paper ID</th><th>Título</th><th>Ano</th><th>Origem</th></tr></thead><tbody>')
    for r in lst:
        link = r['link'] or r['doi']
        tit_html = (f'<a href="{html.escape(link)}" target="_blank" rel="noopener">{html.escape(r["titulo"])}</a>'
                    if link else html.escape(r['titulo']))
        obs = f'<div class="obs">{html.escape(r["observacao"])}</div>' if r['observacao'] else ''
        partes.append(f'<tr><td class="n">{r["ordem"]}</td><td><code>{html.escape(r["pid"])}</code></td>'
                      f'<td>{tit_html}{obs}</td><td class="n">{html.escape(r["ano"])}</td><td class="n">{html.escape(r["origem"])}</td></tr>')
    partes.append('</tbody></table></div>')
partes.append('</main></body></html>')
open(out, 'w', encoding='utf-8').write('\n'.join(partes))
print('ok', len(rows), [(k, len(v[1])) for k, v in grupos.items()])
