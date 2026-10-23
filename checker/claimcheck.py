"""claimcheck: deterministic claim-to-evidence checking for agent-written research papers.

Level 1 (traceability): does each numeric claim in the paper appear, at the precision reported, in some
execution artifact?  Level 2 (provenance): among the matching artifact values, is there one whose context
(JSON key path / CSV column+row / log line, plus file path) matches the claim's context (table row and
column header, caption, or sentence)?

Paper  = the submission's main LaTeX file with \\input/\\include and numeric \\newcommand/\\def macros expanded
         (falls back to the PDF text if there is no LaTeX).
Evidence = machine-written result files only: .json .jsonl .csv .tsv .log .out .txt  (never .tex, .py, .md,
         figures, or anything under proposal/tex) -- a number in the agent's own prose or code is not evidence.

usage:  python checker/claimcheck.py <submission_dir> [--out claims.csv]
"""
from __future__ import annotations
import csv, json, math, os, re, subprocess, sys, argparse, collections
from pathlib import Path

EVIDENCE_EXT = {'.json', '.jsonl', '.csv', '.tsv', '.log', '.out', '.txt'}
SKIP_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', '.ipynb_checkpoints'}
MAX_EVIDENCE_BYTES = 30_000_000          # per file; larger files are sampled from the head
STOP = set('the a an of and or in on for to with by at from is are was were be as that this it its we our than vs '
           'versus table fig figure eq section using use used across per each all mean median std sd ci value values '
           'result results row col column left right top bottom see also'.split())
SYN = {'acc': 'accuracy', 'err': 'error', 'rel': 'relative', 'abs': 'absolute', 'avg': 'mean', 'num': 'n',
       'pct': 'percent', 'perc': 'percent', 'std': 'sd', 'stdev': 'sd', 'iters': 'iterations', 'iter': 'iterations',
       'secs': 'seconds', 'sec': 'seconds', 'time': 'seconds', 'runtime': 'seconds', 'params': 'parameters',
       'lr': 'learning_rate', 'rmse': 'rmse', 'mae': 'mae', 'r2': 'r2', 'auc': 'auc', 'f1': 'f1'}

# ----------------------------------------------------------------------------------------------- numbers
NUM_RE = re.compile(r'(?<![A-Za-z0-9_.\\])([-−]?\d+\.\d+|[-−]?\d+)(?:\s*(?:\\times|×|x)\s*10\^\{?([-−]?\d+)\}?|[eE]([-+]?\d+))?(\s*\\?%)?')


def parse_num(m):
    """-> (value, decimals, is_percent, raw) or None"""
    mant, exp1, exp2, pct = m.group(1), m.group(2), m.group(3), m.group(4)
    mant = mant.replace('−', '-'); exp = exp1 or exp2
    try:
        v = float(mant) * (10 ** int(exp.replace('−', '-')) if exp else 1)
    except (ValueError, OverflowError):
        return None
    dec = len(mant.split('.')[1]) if '.' in mant else 0
    if exp:  # precision in absolute terms for scientific notation
        dec = dec - int(exp.replace('−', '-'))
    return v, dec, bool(pct), m.group(0).strip()


def sig_digits(raw_mant):
    s = raw_mant.lstrip('-−').replace('.', '').lstrip('0')
    return max(len(s), 1)


def tokens(text):
    text = re.sub(r'\\[A-Za-z]+', ' ', text)                      # latex commands
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)               # camelCase
    out = []
    for t in re.split(r'[^A-Za-z0-9]+', text.lower()):
        if not t or t.isdigit() or len(t) < 2 or t in STOP:
            continue
        t = SYN.get(t, t)
        if t.endswith('s') and len(t) > 4: t = t[:-1]
        out.append(t)
    return out


# ----------------------------------------------------------------------------------------------- paper
def find_main_tex(sub: Path):
    texs = [p for p in sub.rglob('*.tex') if not (set(p.parts) & SKIP_DIRS)]
    mains = [p for p in texs if '\\begin{document}' in p.read_text(errors='ignore')]
    if not mains:
        return None
    pref = [p for p in mains if p.name in ('report.tex', 'main.tex', 'paper.tex')]
    return sorted(pref or mains, key=lambda p: -p.stat().st_size)[0]


def expand_inputs(path: Path, seen=None, depth=0):
    seen = seen or set()
    if depth > 8 or path in seen or not path.exists():
        return ''
    seen.add(path)
    txt = path.read_text(errors='ignore')
    txt = re.sub(r'(?<!\\)%.*', '', txt)                           # comments

    def repl(m):
        name = m.group(2).strip()
        for cand in (path.parent / name, path.parent / (name + '.tex')):
            if cand.exists():
                return '\n' + expand_inputs(cand, seen, depth + 1) + '\n'
        return ''
    return re.sub(r'\\(input|include)\{([^}]+)\}', repl, txt)


MACRO_DEF = re.compile(r'\\(?:newcommand|renewcommand|providecommand)\*?\{?\\([A-Za-z@]+)\}?(?:\[\d\])?\{([^{}]*)\}|\\def\\([A-Za-z@]+)\{([^{}]*)\}')


def expand_macros(txt, sub: Path):
    macros = {}
    for p in sub.rglob('*.tex'):
        if set(p.parts) & SKIP_DIRS: continue
        for m in MACRO_DEF.finditer(re.sub(r'(?<!\\)%.*', '', p.read_text(errors='ignore'))):
            name, body = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            if re.search(r'\d', body) and len(body) < 80:
                macros[name] = body
    txt = MACRO_DEF.sub('', txt)
    for _ in range(3):                                           # nested macros
        txt = re.sub(r'\\([A-Za-z@]+)(?![A-Za-z@])(\{\})?', lambda m: macros.get(m.group(1), m.group(0)), txt)
    return txt, len(macros)


DROP_CMDS = r'(cite[a-z]*|ref|eqref|label|includegraphics|vspace|hspace|setlength|usepackage|documentclass|bibliographystyle|bibliography|url|href|cline|cmidrule|addplot|geometry|resizebox|scalebox|definecolor|columnwidth)'


def paper_units(sub: Path):
    """Yield (kind, context, text) units: table cells with row/col context, and prose sentences."""
    main = find_main_tex(sub)
    if main is None:
        pdfs = sorted(sub.rglob('report.pdf')) or sorted((sub / 'proposal').rglob('*.pdf')) if (sub / 'proposal').exists() else []
        if not pdfs:
            return [], dict(source='none')
        txt = subprocess.run(['pdftotext', '-q', str(pdfs[0]), '-'], capture_output=True, text=True).stdout
        return [('prose', s, s) for s in re.split(r'(?<=[.!?])\s+', txt) if s.strip()], dict(source='pdf', file=str(pdfs[0]))
    txt = expand_inputs(main)
    txt, nmac = expand_macros(txt, sub)
    txt = txt.split('\\begin{document}', 1)[-1].split('\\end{document}', 1)[0]
    txt = re.split(r'\\bibliography\{|\\begin\{thebibliography\}', txt)[0]
    txt = re.sub(r'\\' + DROP_CMDS + r'(\[[^\]]*\])?\{[^{}]*\}', ' ', txt)
    txt = re.sub(r'\\begin\{(figure|figure\*)\}.*?\\end\{\1\}', lambda m: ' '.join(re.findall(r'\\caption\{(.*?)\}\s*', m.group(0), re.S)), txt, flags=re.S)
    units = []
    # tables
    def table_repl(m):
        body = m if isinstance(m, str) else m.group(0); cap = ' '.join(re.findall(r'\\caption\{(.*?)\}', body, re.S))
        for tab in re.findall(r'\\begin\{tabular[x*]?\}(?:\{[^}]*\})+(.*?)\\end\{tabular[x*]?\}', body, re.S):
            rows = [r for r in re.split(r'\\\\', tab)]
            rows = [re.sub(r'\\(toprule|midrule|bottomrule|hline)', '', r).strip() for r in rows]
            rows = [r for r in rows if r]
            header = None
            for r in rows:
                cells = [c.strip() for c in r.split('&')]
                if header is None and not any(NUM_RE.search(c) and parse_num(NUM_RE.search(c)) and '.' in NUM_RE.search(c).group(1) for c in cells[1:]):
                    header = cells; continue
                for j, c in enumerate(cells):
                    if not NUM_RE.search(c): continue
                    col = header[j] if header and j < len(header) else ''
                    units.append(('table', f'{cells[0]} | {col} | {cap}', c))
        return ' '
    txt = re.sub(r'\\begin\{(table|table\*)\}.*?\\end\{\1\}', table_repl, txt, flags=re.S)
    txt = re.sub(r'\\begin\{tabular[x*]?\}.*?\\end\{tabular[x*]?\}', lambda m: table_repl(m.group(0)), txt, flags=re.S)
    for s in re.split(r'(?<=[.!?])\s+(?=[A-Z\\])', re.sub(r'\s+', ' ', txt)):
        if NUM_RE.search(s):
            units.append(('prose', s, s))
    return units, dict(source='tex', file=str(main), macros=nmac)


def extract_claims(units):
    claims = []
    for kind, ctx, text in units:
        for m in NUM_RE.finditer(text):
            p = parse_num(m)
            if not p: continue
            v, dec, pct, raw = p
            mant = m.group(1)
            if dec <= 0 and not pct and not m.group(2) and not m.group(3):
                continue                                         # integers: counts, years, indices -- out of scope v0
            if abs(v) == 0: continue
            claims.append(dict(kind=kind, raw=raw, value=v, dec=dec, pct=pct, sig=sig_digits(mant),
                               context=ctx[:400] if kind == 'table' else _window(text, m.start(), m.end())))
    return claims


def _window(s, a, b, w=160):
    return s[max(0, a - w):b + w].strip()


# ----------------------------------------------------------------------------------------------- evidence
BULK_LIST = 20          # a numeric list longer than this is raw data, not a reported summary
BULK_ROWS = 200         # same for CSV data rows / JSONL records
BULK_LINE_NUMS = 10     # a log line with more numbers than this is an array dump


def walk_json(o, path=(), bulk=False):
    if isinstance(o, dict):
        for k, v in o.items(): yield from walk_json(v, path + (str(k),), bulk)
    elif isinstance(o, list):
        b = bulk or len(o) > BULK_LIST
        for i, v in enumerate(o[:5000]): yield from walk_json(v, path + ('',), b)
    elif isinstance(o, bool) or o is None:
        return
    elif isinstance(o, (int, float)):
        if isinstance(o, float) and not math.isfinite(o): return
        yield float(o), ' '.join(p for p in path if p), bulk
    elif isinstance(o, str):
        for m in NUM_RE.finditer(o[:2000]):
            p = parse_num(m)
            if p: yield p[0], ' '.join(path), bulk


def evidence_index(sub: Path):
    rows = []   # (value, context, file)
    for p in sub.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in EVIDENCE_EXT or (set(p.parts) & SKIP_DIRS):
            continue
        rel = str(p.relative_to(sub)); fctx = ' '.join(tokens(rel))
        try:
            raw = p.read_bytes()[:MAX_EVIDENCE_BYTES].decode('utf-8', errors='ignore')
        except OSError:
            continue
        suf = p.suffix.lower()
        try:
            if suf == '.json':
                for v, ctx, b in walk_json(json.loads(raw)): rows.append((v, ctx, rel, fctx, b))
                continue
            if suf == '.jsonl':
                lines = raw.splitlines()[:200000]; big = len(lines) > BULK_ROWS
                for line in lines:
                    line = line.strip()
                    if line.startswith('{'):
                        for v, ctx, b in walk_json(json.loads(line), bulk=big): rows.append((v, ctx, rel, fctx, b))
                continue
        except (json.JSONDecodeError, RecursionError):
            pass
        if suf in ('.csv', '.tsv'):
            rd = list(csv.reader(raw.splitlines()[:200000], delimiter='\t' if suf == '.tsv' else ','))
            if not rd: continue
            hdr = rd[0]; big = len(rd) - 1 > BULK_ROWS
            for r in rd[1:]:
                rowlab = ' '.join(c for c in r if c and not NUM_RE.fullmatch(c.strip()))[:120]
                for j, c in enumerate(r):
                    m = NUM_RE.fullmatch(c.strip())
                    if m and parse_num(m): rows.append((parse_num(m)[0], f'{hdr[j] if j < len(hdr) else ""} {rowlab}', rel, fctx, big))
            continue
        for line in raw.splitlines()[:500000]:                    # logs, txt, out, and unparsable json
            if len(line) > 2000: line = line[:2000]
            ms = list(NUM_RE.finditer(line)); big = len(ms) > BULK_LINE_NUMS
            for m in ms:
                p = parse_num(m)
                if p: rows.append((p[0], line.strip()[:300], rel, fctx, big))
    return rows


# ----------------------------------------------------------------------------------------------- matching
PCT_CTX = re.compile(r'(percent|pct|%)', re.I)


def build_lookup(rows):
    """Sorted value arrays for binary search: one per scaling ('id', 'x100', 'd100'), each with row indices."""
    import numpy as np
    vals = np.fromiter((r[0] for r in rows), dtype=float, count=len(rows))
    idx = np.arange(len(rows))
    lk = {}
    for how, scale in (('id', 1.0), ('x100', 100.0), ('d100', 0.01)):
        v = vals * scale; ok = np.isfinite(v) & (v != 0)
        o = np.argsort(v[ok], kind='stable')
        lk[how] = (v[ok][o], idx[ok][o])
    return lk


def _bucket(v):  # kept for compatibility
    return round(math.copysign(math.log10(abs(v)), v), 1) if v else 0


def matches(claim, rows, lk):
    """Value equal at the claim's reported precision. Scaling is allowed only where it is meaningful:
    x100 when the claim is a percentage (evidence stored as a proportion); /100 when the evidence context says
    percent and the claim is not one."""
    import numpy as np
    v, dec = claim['value'], claim['dec']
    tol = 0.5 * 10 ** (-dec) * (1 + 1e-9)          # relative float slack; an absolute epsilon swamps tiny values
    pct = bool(claim.get('pct'))
    out = set()
    for how in ('id', 'x100', 'd100'):
        if how == 'x100' and not pct: continue
        if how == 'd100' and pct: continue
        arr, ix = lk[how]
        lo, hi = np.searchsorted(arr, v - tol, 'left'), np.searchsorted(arr, v + tol, 'right')
        for i in ix[lo:hi].tolist():
            if how == 'd100' and not PCT_CTX.search(rows[i][1] + ' ' + rows[i][2]): continue
            out.add(i)
    return sorted(out)


def provenance_score(claim, row):
    ct = set(tokens(claim['context'])); et = set(tokens(row[1])) | set(row[3].split())
    if not ct or not et: return 0.0
    return len(ct & et) / len(ct | et) ** 0.5 / len(ct) ** 0.5     # cosine-like overlap on token sets


CAL_OFFSETS = (-10, -8, -6, -4, -2, 2, 4, 6, 8, 10)   # calibration decoys, in units of the last reported digit
TEST_OFFSET = 7                                        # held-out decoy used only to measure false-match rates


def _at(claim, value):
    d = dict(claim); d['value'] = value; return d


def _shift(claim, k):
    return claim['value'] + k * 10 ** (-claim['dec'])


def best_score(claim, rows, lk, nonbulk_only=True):
    m = [i for i in matches(claim, rows, lk) if not (nonbulk_only and rows[i][4])]
    if not m: return 0.0, None, 0
    n = len(m)
    if n > 2000: m = m[:: n // 2000 + 1]
    sc, i = max((provenance_score(claim, rows[i]), i) for i in m)
    return sc, i, n


def verdict(claim, rows, lk, tau):
    """Calibrated Level-2 verdict for a claim value: best non-bulk context score must reach tau AND beat the
    best score of every calibration decoy at the same precision (a per-claim permutation test, p <= 1/11)."""
    s, i, n = best_score(claim, rows, lk)
    if n == 0: return 'untraced', s, i, 1.0
    dec_scores = [best_score(_at(claim, _shift(claim, k)), rows, lk)[0] for k in CAL_OFFSETS if _shift(claim, k) * claim['value'] > 0]
    p = (1 + sum(d >= s for d in dec_scores)) / (1 + len(dec_scores))
    return ('supported' if s >= tau and p <= 1 / 10 else 'unattributed'), s, i, p


def check(sub: Path, tau=0.12):
    units, meta = paper_units(sub)
    claims = extract_claims(units)
    rows = evidence_index(sub)
    lk = build_lookup(rows)
    for c in claims:
        m_all = matches(c, rows, lk)
        m_nb = [i for i in m_all if not rows[i][4]]
        c['L1'] = 'traced' if m_all else 'untraced'                       # naive baseline
        c['L1nb'] = 'traced' if m_nb else 'untraced'                      # + ignore bulk data
        c['L1_n_matches'] = len(m_all); c['L1nb_n_matches'] = len(m_nb)
        s, i, _ = best_score(c, rows, lk)
        c['L2ctx'] = 'untraced' if not m_nb else ('supported' if s >= tau else 'unattributed')   # + context
        v, s2, i2, p = verdict(c, rows, lk, tau)                          # + per-claim calibration (full method)
        c['L2'] = v; c['L2_score'] = round(s2, 3); c['L2_p'] = round(p, 3)
        c['L2_file'] = rows[i2][2] if i2 is not None else ''
        c['L2_context'] = rows[i2][1][:200] if i2 is not None else ''
        # held-out decoy through every stage
        dcl = _at(c, _shift(c, TEST_OFFSET))
        dm = matches(dcl, rows, lk); dnb = [j for j in dm if not rows[j][4]]
        ds, _, _ = best_score(dcl, rows, lk)
        c['decoy_L1'] = bool(dm); c['decoy_L1nb'] = bool(dnb)
        c['decoy_L2ctx'] = bool(dnb) and ds >= tau
        c['decoy_L2'] = verdict(dcl, rows, lk, tau)[0] == 'supported'
    meta.update(n_claims=len(claims), n_evidence_values=len(rows), n_bulk=sum(r[4] for r in rows))
    return claims, meta


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('sub'); ap.add_argument('--out'); ap.add_argument('--tau', type=float, default=0.12)
    a = ap.parse_args()
    claims, meta = check(Path(a.sub), a.tau)
    print(json.dumps(meta))
    if claims:
        keys = list(claims[0].keys())
        w = csv.DictWriter(open(a.out, 'w', newline='') if a.out else sys.stdout, fieldnames=keys); w.writeheader(); w.writerows(claims)
