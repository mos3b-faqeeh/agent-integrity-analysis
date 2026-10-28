"""Figures for the paper (static PDF, print-safe). Palette: validated categorical slots blue/orange/aqua,
with marker shape and direct labels as secondary encoding."""
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#6b6b66', 'axes.labelcolor': '#1f1f1d', 'xtick.color': '#4a4a46', 'ytick.color': '#4a4a46',
                     'axes.grid': True, 'grid.color': '#e6e5df', 'grid.linewidth': 0.6, 'axes.axisbelow': True})
BLUE, ORANGE, AQUA, INK, MUTED = '#2a78d6', '#eb6834', '#1baf7a', '#1f1f1d', '#6b6b66'
OUT = 'paper/figs/'

# Fig: rubric families
fam = [('Code–paper alignment', 118, 225, 'w'), ('Number traceability', 122, 324, 'w'), ('Held-fixed disclosure', 32, 99, 'w'),
       ('Test-set integrity', 23, 81, 'm'), ('Pre-stated method', 27, 99, 'w'), ('Execution claims', 72, 279, 'w'),
       ('Baseline honesty', 12, 144, 'm'), ('Selective reporting', 13, 252, 'm'), ('No hard-coded values', 2, 135, 'm'),
       ('No external code', 1, 81, 'm'), ('No replication of published method', 0, 99, 'm')]
fig, ax = plt.subplots(figsize=(5.6, 3.0))
ys = np.arange(len(fam))[::-1]
for y, (n, f, c, g) in zip(ys, fam):
    r = 100 * f / c; col = BLUE if g == 'w' else ORANGE
    ax.barh(y, r, height=0.62, color=col, edgecolor='white', linewidth=1)
    ax.text(r + 1, y, f'{r:.0f}%  ({f}/{c})', va='center', fontsize=7, color=INK)
ax.set_yticks(ys); ax.set_yticklabels([f[0] for f in fam]); ax.set_xlim(0, 70); ax.set_xlabel('Share of counted nodes failed (%)')
ax.grid(axis='y', visible=False)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=BLUE, label='Write-up vs. work'), Patch(color=ORANGE, label='Overt misconduct / selection')],
          loc='lower right', frameon=False, fontsize=7)
fig.tight_layout(); fig.savefig(OUT + 'rubric_families.pdf'); plt.close(fig)

# Fig: checker operating points on the held-out sample (annotator A)
r = pd.read_csv('data/derived/confirmation_results.csv'); r = r[r.reference == 'A'].set_index('setting')
pts = [('Value match (Level 1)', 0.688, None, 1.0, None)] + \
      [(s.capitalize(), r.loc[s, 'precision'], (r.loc[s, 'p_lo'], r.loc[s, 'p_hi']), r.loc[s, 'recall'], (r.loc[s, 'r_lo'], r.loc[s, 'r_hi'])) for s in ['strict', 'balanced', 'broad']]
fig, ax = plt.subplots(figsize=(4.0, 3.0))
for name, p, pc, rc, rcc in pts:
    xe = None if rcc is None else [[rc - rcc[0]], [rcc[1] - rc]]; ye = None if pc is None else [[p - pc[0]], [pc[1] - p]]
    col = MUTED if rcc is None else BLUE
    ax.errorbar(rc, p, xerr=xe, yerr=ye, fmt='o', color=col, ms=6, elinewidth=1, capsize=2, mec='white', mew=1)
    ax.annotate(name, (rc, p), xytext={'Broad': (8, -12), 'Balanced': (-52, 8), 'Strict': (6, 6)}.get(name, (6, 6)), textcoords='offset points', fontsize=7, color=INK)
ax.set_xlim(0, 1.08); ax.set_ylim(0.5, 1.02); ax.set_xlabel('Recall (share of traceable claims certified)'); ax.set_ylabel('Precision (certified claims that are traceable)')
fig.tight_layout(); fig.savefig(OUT + 'operating_points.pdf'); plt.close(fig)

# Fig: benchmark-wide certified share vs official integrity score
s = pd.read_csv('data/derived/benchmark_traceability_by_submission.csv')
V = {'astra-6': 'OpenAI', 'sol-5.6': 'OpenAI', 'opus-4.8': 'Anthropic', 'opus-5': 'Anthropic', 'opus-5.5': 'Anthropic', 'fable-5': 'Anthropic',
     'kimi-k3': 'Open-weight', 'deepseek-v4-pro': 'Open-weight', 'glm-5.3': 'Open-weight'}
C = {'OpenAI': (BLUE, 'o'), 'Anthropic': (ORANGE, 's'), 'Open-weight': (AQUA, '^')}
s['vendor'] = s.model.map(V)
fig, ax = plt.subplots(figsize=(5.0, 3.4))
for v, (col, mk) in C.items():
    x = s[s.vendor == v]; ax.scatter(x.R_integrity, 100 * x.S, s=14, color=col, marker=mk, alpha=0.35, linewidths=0)
ag = s.groupby('model').agg(R=('R_integrity', 'mean'), S=('S', 'mean'), n=('S', 'size')).reset_index()
txt = {'astra-6': (80, 86), 'sol-5.6': (70, 66), 'opus-5.5': (87, 24), 'kimi-k3': (24, 26), 'glm-5.3': (32, 40),
       'opus-5': (40, 56), 'deepseek-v4-pro': (66, 52), 'opus-4.8': (68, 44), 'fable-5': (70, 36)}
for _, a in ag.iterrows():
    col, mk = C[V[a.model]]
    ax.scatter(a.R, 100 * a.S, s=55, color=col, marker=mk, edgecolors='white', linewidths=1.2, zorder=3)
    ax.annotate(f'{a.model} (n={a.n})', (a.R, 100 * a.S), xytext=txt[a.model], textcoords='data', fontsize=6.5, color=INK,
                arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.6, shrinkA=1, shrinkB=4))
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([], [], color=c, marker=m, ls='', ms=6, label=v) for v, (c, m) in C.items()], frameon=False, fontsize=7, loc='upper left')
ax.set_xlabel('Official integrity score $R_{int}$ (% of G1 nodes passed)'); ax.set_ylabel('Claims certified by strict checker (%)')
ax.set_xlim(20, 102); ax.set_ylim(-2, 100)
fig.tight_layout(); fig.savefig(OUT + 'certified_vs_judge.pdf'); plt.close(fig)
print('ok')

# Fig: per-agent G1 node failure rate under each judge (majority labels), 30 re-graded submissions
pa = [('astra-6', 'OpenAI', 1.4, 0.0), ('sol-5.6', 'OpenAI', 8.8, 2.9), ('opus-5.5', 'Anthropic', 5.7, 0.0), ('opus-4.8', 'Anthropic', 17.3, 11.5),
      ('fable-5', 'Anthropic', 23.6, 3.6), ('opus-5', 'Anthropic', 24.1, 18.5), ('glm-5.3', 'Open-weight', 14.3, 8.2),
      ('kimi-k3', 'Open-weight', 31.9, 29.8), ('deepseek-v4-pro', 'Open-weight', 35.6, 31.1)]
fig, ax = plt.subplots(figsize=(5.0, 3.0))
ys = np.arange(len(pa))[::-1]
for y, (m, v, a, b) in zip(ys, pa):
    col, mk = C[v]
    ax.plot([b, a], [y, y], color='#c9c8c0', lw=2, solid_capstyle='round', zorder=1)
    ax.scatter(a, y, s=40, color=INK, marker='o', zorder=3, edgecolors='white', linewidths=1)
    ax.scatter(b, y, s=40, color=col, marker=mk, zorder=3, edgecolors='white', linewidths=1)
ax.set_yticks(ys); ax.set_yticklabels([p[0] for p in pa]); ax.grid(axis='y', visible=False)
ax.set_xlabel('G1 nodes failed (%)'); ax.set_xlim(-2, 40)
ax.legend(handles=[Line2D([], [], color=INK, marker='o', ls='', ms=6, label='Official judge (GPT-6-Astra)')] +
          [Line2D([], [], color=c, marker=m, ls='', ms=6, label=f'Second judge, {v} agent') for v, (c, m) in C.items()],
          frameon=False, fontsize=6.5, loc='upper right')
fig.tight_layout(); fig.savefig(OUT + 'judges_by_agent.pdf'); plt.close(fig)
print('ok2')
