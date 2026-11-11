"""Cronograma revisado da SLR (03/11/2026 a 29/01/2027), figura para a orientadora."""
import datetime as dt

import matplotlib

matplotlib.use('Agg')
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

D = dt.date
FASES = [  # (rotulo, inicio, fim, cor)
    ('Passada 2 (texto completo, RQ1 e RQ4): 81 registros', D(2026, 11, 3), D(2026, 11, 13), '#2f74c9'),
    ('Fechar a seleção: EC6, decisões pendentes, concordância, §8', D(2026, 11, 9), D(2026, 11, 20), '#2f74c9'),
    ('Snowballing backward e forward (âncoras e núcleo da RQ1)', D(2026, 11, 16), D(2026, 11, 27), '#2f74c9'),
    ('SBR 2026, João Pessoa (sem SLR)', D(2026, 11, 23), D(2026, 11, 25), '#bdbdb5'),
    ('Sprint 3: extração (§6) e DARE, com pré-extração assistida', D(2026, 11, 30), D(2026, 12, 18), '#e2662f'),
    ('Extração residual e revisão dos dados', D(2026, 12, 21), D(2026, 12, 23), '#e2662f'),
    ('Recesso', D(2026, 12, 24), D(2027, 1, 3), '#bdbdb5'),
    ('Sprint 4: tabelas do §7, síntese por RQ, funil final', D(2027, 1, 4), D(2027, 1, 22), '#1f9e74'),
    ('Texto do capítulo e revisão da orientadora', D(2027, 1, 18), D(2027, 1, 29), '#1f9e74'),
]
MARCOS = [('M3: seleção fechada', D(2026, 11, 27)), ('M4: extração fechada', D(2026, 12, 18)),
          ('M5: síntese e funil final', D(2027, 1, 22)), ('capítulo entregue', D(2027, 1, 29))]
REUNIOES = [D(2026, 11, 13), D(2026, 11, 27), D(2026, 12, 18), D(2027, 1, 22)]

fig, ax = plt.subplots(figsize=(13.333, 6.2), facecolor='white')
for i, (rot, a, b, cor) in enumerate(FASES):
    ax.barh(i, (b - a).days + 1, left=mdates.date2num(a), height=0.62, color=cor, alpha=0.9 if cor != '#bdbdb5' else 0.6)
for k, (rot, d) in enumerate(MARCOS):
    x = mdates.date2num(d) + 1
    ax.axvline(x, color='#444444', lw=1.1, ls='--', zorder=0)
    ax.text(x, -1.0 - 0.55 * (k % 2), f'{d.strftime("%d/%m")}  {rot}', ha='right' if k == len(MARCOS) - 1 else 'center', va='bottom', fontsize=9.5,
            color='#444444', bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none'))
for d in REUNIOES:
    ax.plot(mdates.date2num(d) + 0.5, len(FASES) - 0.25, marker='v', color='#e2662f', ms=9, zorder=3)
ax.text(mdates.date2num(D(2026, 11, 2)), len(FASES) - 0.25, 'reunião com a orientadora', fontsize=9.5, color='#e2662f',
        va='center', ha='right')
ax.set_ylim(-1.9, len(FASES) + 0.4)
ax.set_yticks(range(len(FASES)))
ax.set_yticklabels([f[0] for f in FASES], fontsize=10)
ax.tick_params(axis='y', length=0)
ax.invert_yaxis()
ax.set_xlim(mdates.date2num(D(2026, 11, 1)), mdates.date2num(D(2027, 2, 1)))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
ax.tick_params(axis='x', labelsize=9.5)
for s in ('top', 'right', 'left'):
    ax.spines[s].set_visible(False)
ax.grid(axis='x', color='#e6e6e2', lw=0.8)
ax.set_title('Cronograma revisado da SLR, de 03/11/2026 a 29/01/2027 (3,5 a 4 h por dia útil)', fontsize=13,
             weight='bold', loc='left', color='#111111', pad=10)
fig.subplots_adjust(left=0.37, right=0.985, top=0.9, bottom=0.08)
fig.savefig('fig_cronograma_slr_2026-11-03.png', dpi=250, facecolor='white')
fig.savefig('fig_cronograma_slr_2026-11-03.pdf', facecolor='white')
print('ok')
