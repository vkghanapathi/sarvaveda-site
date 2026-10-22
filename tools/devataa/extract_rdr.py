"""Rūpa Dhyāna Ratnāvalī -> devataa/data/devataa.json + web images.

Reads the five typed RDR volumes (Word tables: name | number | śloka | meaning)
and the scanned diagrams, matches each diagram to its entry by series letter and
number, and writes one registry. The registry is the source for the
sarvaveda.info/devataa pages and for Samūha; counts are always derived from it.

Text is carried exactly as typed: no normalisation of script, spelling or
punctuation (CLAUDE.md rule 17). Typists' notes are kept, not shown.

Usage:
  python tools/devataa/extract_rdr.py [--src DIR] [--soffice PATH] [--no-images]
"""
import argparse, glob, json, os, re, subprocess, sys, tempfile
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(SITE, 'devataa')
SRC = r'C:\Users\Datta\Documents\GDrive\Book Works\Roopa dhyana ratnavali'
SOFFICE = r'C:\Program Files\LibreOffice\program\soffice.exe'
DOCS = ['1 RDR 16.doc', '2 RDR 44.doc', '3 RDR 45.doc', '4 RDR 57.doc', '5RDR 47.doc']
IMG_PARTS = ['Part 04 Brahma', 'Part 05 Ganapati', 'Part 06 Devi', 'Part 07 Siva',
             'Part 08 Vishnu', 'Part 09  Kartikeya', 'Part 10  Nava Graha']

# ---------------------------------------------------------------- groups
# Groups follow the Parts of the book; subgroups follow the headings the
# volumes themselves carry. (series, lo, hi) ranges are inclusive.
GROUPS = [
    dict(id='ganapati', te='గణపతి', iast='Gaṇapati', en='Ganapati', part=5, subs=[
        dict(id='dvatrimshat', te='ద్వాత్రింశద్ గణపతులు', iast='Dvātriṃśad Gaṇapatayaḥ', ranges=[('GA', 0, 35)])]),
    dict(id='devi', te='దేవీ', iast='Devī', en='Devi', part=6, subs=[
        dict(id='rupa-1', te='దేవీ రూపములు (౧–౪౧)', iast='Devī-rūpāṇi 1–41', ranges=[('DE', 1, 41)]),
        dict(id='matrka', te='మాతృకలు', iast='Mātṛkāḥ', ranges=[('DE', 42, 49)]),
        dict(id='navadurga', te='నవదుర్గలు', iast='Navadurgāḥ', ranges=[('DE', 50, 59)]),
        dict(id='rupa-2', te='దేవీ రూపములు', iast='Devī-rūpāṇi', ranges=[('DE', 60, 134)]),
        dict(id='aksara', te='షట్చక్ర · అక్షర దేవతలు', iast='Ṣaṭcakra · Akṣara-devatāḥ', ranges=[('DE', 135, 199)]),
        dict(id='anya', te='ఇతర దేవీ రూపములు', iast='Anya Devī-rūpāṇi', ranges=[('HX', 14, 99), ('DE', None, None)]),
        dict(id='astalaksmi', te='అష్టలక్ష్మీ', iast='Aṣṭalakṣmī', ranges=[('LS', 1, 8)]),
        dict(id='sakti', te='శక్తులు', iast='Śaktayaḥ', ranges=[('LS', 9, 15), ('LS', 18, 26)])]),
    dict(id='siva', te='శివ', iast='Śiva', en='Siva', part=7, subs=[
        dict(id='rupa', te='శివమూర్తి రూపములు', iast='Śivamūrti-rūpāṇi', ranges=[('SI', 1, 11)]),
        dict(id='pancabrahma', te='పంచబ్రహ్మ రూపములు', iast='Pañcabrahma', ranges=[('SI', 12, 16)]),
        dict(id='tandava', te='తాండవములు', iast='Tāṇḍavāni', ranges=[('SI', 17, 23)]),
        dict(id='rudra', te='అష్టమూర్తులు · ఏకాదశ రుద్రులు', iast='Aṣṭamūrti · Ekādaśa Rudrāḥ', ranges=[('SI', 24, 35)]),
        dict(id='lila', te='శివ లీలామూర్తులు', iast='Līlāmūrtayaḥ', ranges=[('SI', 36, 68)]),
        dict(id='bhairava', te='అష్టభైరవులు', iast='Aṣṭabhairavāḥ', ranges=[('SI', 69, 78)]),
        dict(id='parivara', te='పరివారము', iast='Parivāra', ranges=[('SI', 79, 99), ('LS', 27, 30), ('HX', 12, 13)])]),
    dict(id='vishnu', te='విష్ణు', iast='Viṣṇu', en='Vishnu', part=8, subs=[
        dict(id='rupa', te='విష్ణు రూపములు', iast='Viṣṇu-rūpāṇi', ranges=[('VI', 1, 14)]),
        dict(id='caturvimsati', te='చతుర్వింశతి మూర్తులు', iast='Caturviṃśati-mūrtayaḥ', ranges=[('VI', 15, 38)]),
        dict(id='vyuha', te='చతుర్వ్యూహములు', iast='Caturvyūhāḥ', ranges=[('VI', 39, 42)]),
        dict(id='avatara', te='దశావతారములు', iast='Daśāvatārāḥ', ranges=[('VI', 43, 51)]),
        dict(id='anya', te='ఇతర రూపములు', iast='Anya-rūpāṇi', ranges=[('VI', 52, 99), ('VX', 1, 99)]),
        dict(id='sayana', te='శయన · ఆసన · స్థానక విధి', iast='Śayana · Āsana · Sthānaka', ranges=[('VV', 0, 99)])]),
    dict(id='kartikeya', te='కార్తికేయ', iast='Kārttikeya', en='Kartikeya', part=9, subs=[
        dict(id='rupa', te='సుబ్రహ్మణ్య రూపములు', iast='Subrahmaṇya-rūpāṇi', ranges=[('KA', 1, 99), ('LS', 16, 17)])]),
    dict(id='brahma', te='బ్రహ్మ', iast='Brahmā', en='Brahma', part=4, subs=[
        dict(id='rupa', te='చతుర్ముఖ బ్రహ్మ', iast='Caturmukha Brahmā', ranges=[('LS', 31, 31)])]),
    dict(id='navagraha', te='నవగ్రహములు', iast='Navagrahāḥ', en='Navagraha', part=10, subs=[
        dict(id='graha', te='నవగ్రహములు', iast='Navagrahāḥ', ranges=[('LS', 32, 40)])]),
]

# Image series letter (from the scan file name) -> registry series.
IMG_SERIES = {'a': 'GA', 'b': 'KA', 'c': 'DE', 'd': 'SI', 'e': 'VI', 'f': 'VX'}
# The 'h' scans are numbered on their own; map them by name to the text series.
H_MAP = {1: ('LS', 32), 2: ('LS', 33), 3: ('LS', 34), 4: ('LS', 35), 5: ('LS', 36),
         6: ('LS', 37), 7: ('LS', 38), 8: ('LS', 39), 9: ('LS', 40),
         10: ('LS', 31), 11: ('LS', 27), 12: ('HX', 12), 13: ('HX', 13)}
# The 'g' scans are the Śakti plates of volume 5, numbered on their own.
G_MAP = {1: 9, 2: 10, 3: 12, 4: 14, 5: 15, 6: 15, 7: 16, 8: 17, 9: 18, 11: 19, 12: 20, 13: 21, None: 22}
# File names whose number cannot be read by rule.
IMG_NUM_OVERRIDE = {
    'R-c-Sowbhagya Vageeswari Devi-111132': 132,
    'R-a-Ganapati-1': 1,
    'R-c- Sri Saraswati Devi-': None,       # unnumbered: kept as diagram-only
    'R-c- Sri Raja Rajeswari Devi': None,
    'R-C-kASHYAPA Silpasastra': None,
    'R-e-68': 68,
}
# Captions the file name cannot give by rule.
CAPTION_OVERRIDE = {
    'R-C-18 hands  bhadhra  kali 34': 'Ashtadasa-bhuja Bhadrakali',
    'R-C-lokottara &nigarbha 11&12': 'Lokottara & Nigarbha',
    'R-C-rahasya yogini 13 & athi rahasya yogini 14': 'Rahasya Yogini & Ati-rahasya Yogini',
    'R-d-89': '',
    'R-e-68': '',
}
# Typos in scan file names, corrected only in the English caption.
EN_FIX = {'Ddev': 'Devi', 'Tnadva': 'Tandava', 'Tadnava': 'Tandava', 'Myrthi': 'Murthi',
          'Sarbha': 'Sarabha', 'Ligodbhava': 'Lingodbhava', 'Nadikeswara': 'Nandikeswara',
          'Arthanareesvara': 'Ardhanareeswara', 'Vibhnnesvara': 'Vighneswara',
          'Mrthy': 'Murthy', 'Thravikrama': 'Trivikrama', 'Sirdhara': 'Sridhara',
          'Simsumara': 'Simsumara', 'Sudarshara': 'Sudarshana', 'Mastyavatara': 'Matsyavatara',
          'Anatha': 'Anantha', 'Ananatha': 'Anantha', 'Purushathtma': 'Purushottama',
          'keasva': 'Kesava', 'Vashakseva': 'Vishvaksena', 'Thripura': 'Tripura',
          'Tripurai': 'Tripurari', 'Ganaga': 'Ganga', 'Dawadassradha': 'Dvadasardha',
          'Indhrakshi': 'Indrakshi', 'Dhen': 'Dhenu', 'Gnasaktidhara': 'Jnanasaktidhara',
          'Seanani': 'Senani', 'thajakari': 'Tarakari', 'Thwritha': 'Tvarita',
          'Thwaritha': 'Tvarita', 'Ugravtara': 'Ugratara', 'tripupura': 'tripura',
          'sunadari': 'sundari', 'Sundahri': 'Sundari', 'Bhuvaveswari': 'Bhuvaneswari',
          'parivva': 'parivara', 'Svaranakarashana': 'Swarnakarshana', 'Bheeshna': 'Bheeshana',
          'Bhikhatana': 'Bhikshatana', 'kamadahava': 'Kamadahana', 'krodhava': 'Krodha',
          'Veerrbhadra': 'Veerabhadra', 'Sadyojiata': 'Sadyojata', 'Commoa': 'Common',
          'Sriu': 'Sri', 'ri': 'Sri', 'Chathrmukha': 'Chaturmukha', 'Tripua': 'Tripura',
          'Sara Verneswari': 'Sarva Varneswari', 'Laxmana': 'Lakshmana',
          'Kmakshi': 'Kamakshi', 'Gowrii': 'Gowri', 'Nithy': 'Nithya', 'Kinna': 'Klinna',
          'Shivs': 'Siva', 'Durja': 'Durga', 'Bogasakthi': 'Bhogasakthi', 'Devasana': 'Devasena',
          'Svapana': 'Svapna', 'Sundra': 'Sundara', 'Kethu': 'Ketu', 'Bhagmalini': 'Bhagamalini'}

TE_DIGITS = str.maketrans('౦౧౨౩౪౫౬౭౮౯', '0123456789')


# ---------------------------------------------------------------- doc tables
class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows = []; self.row = None; self.cell = None
    def handle_starttag(self, t, a):
        if t == 'tr': self.row = []
        elif t in ('td', 'th') and self.row is not None: self.cell = []
        elif t in ('br', 'p') and self.cell is not None: self.cell.append('\n')
    def handle_endtag(self, t):
        if t in ('td', 'th') and self.cell is not None:
            txt = re.sub(r'[ \t\u00a0]+', ' ', ''.join(self.cell))
            self.row.append('\n'.join(l.strip() for l in txt.split('\n') if l.strip()))
            self.cell = None
        elif t == 'tr' and self.row is not None:
            self.rows.append(self.row); self.row = None
    def handle_data(self, d):
        # newlines in the HTML source are only wrapping; <br>/<p> carry the real breaks
        if self.cell is not None: self.cell.append(re.sub(r'\s*[\r\n]+\s*', ' ', d))


def doc_rows(src, soffice):
    tmp = tempfile.mkdtemp(prefix='rdr_')
    paths = [os.path.join(src, 'Roopa Dhyana Ratnavali TL', d) for d in DOCS]
    subprocess.run([soffice, '--headless', '--convert-to', 'html', '--outdir', tmp] + paths,
                   check=True, capture_output=True)
    out = []
    for d in DOCS:
        p = TableParser()
        with open(os.path.join(tmp, os.path.splitext(d)[0] + '.html'), encoding='utf-8', errors='replace') as f:
            p.feed(f.read())
        out.append((d, [(r + ['', '', '', ''])[:4] for r in p.rows]))
    return out


def series_for(doc_i, row_i, num):
    """Which numbering series a row belongs to — from the volume and position."""
    if doc_i == 0: return 'GA'
    if doc_i == 1: return 'DE'
    if doc_i == 2: return 'DE' if row_i < 39 else 'SI'
    if doc_i == 3: return 'SI' if row_i < 24 else ('VI' if row_i < 89 else 'VV')
    return 'VV' if row_i < 22 else 'LS'


def split_title(sl):
    """The śloka cell often opens with the deity's title on a line of its own."""
    lines = sl.split('\n')
    if len(lines) > 1 and not re.search('[।॥|]', lines[0]) and len(lines[0]) < 60:
        return lines[0], '\n'.join(lines[1:])
    return '', sl


def build_entries(rows_by_doc):
    entries, last = [], None
    for di, (doc, rows) in enumerate(rows_by_doc):
        for ri, (name, num, sl, mean) in enumerate(rows):
            name = name.replace('\n', ' ').strip(); num = num.translate(TE_DIGITS).strip()
            if not (name or num or sl or mean):
                continue
            series = series_for(di, ri, num)
            src = dict(doc=doc, row=ri)
            # a typist's note (a page was missing) — keep it on the previous entry
            if not name and not num and not mean and ('పేజ్' in sl or 'పేజీ' in sl):
                if last: last.setdefault('notes', []).append(sl)
                continue
            if not name and not (num.isdigit() and last and last['series'] == series and int(num) == last['num']):
                if last is not None and not num:
                    t, body = split_title(sl)
                    last.setdefault('more', []).append(dict(title=t, shloka=body, meaning=mean, source=src))
                    continue
            if not num.isdigit():
                # named but unnumbered: infer from the gap if it is unambiguous
                nxt = next((r[1].translate(TE_DIGITS).strip() for r in rows[ri + 1:] if r[1].strip()), '')
                if last and last['series'] == series and last['num'] is not None and nxt.isdigit() and int(nxt) == last['num'] + 2:
                    num = str(last['num'] + 1)
            if num.isdigit() and last and last['series'] == series and last['num'] is not None:
                nxt = next((r[1].translate(TE_DIGITS).strip() for r in rows[ri + 1:] if r[1].strip()), '')
                if nxt == num and int(num) == last['num'] + 2:
                    num = str(last['num'] + 1)
            title, body = split_title(sl)
            e = dict(series=series, num=int(num) if num.isdigit() else None,
                     name_te=name or title, title_te=title, shloka_te=body, meaning_te=mean,
                     images=[], source=src)
            if e['num'] is None:
                e['kind'] = 'text'          # a heading or a passage of vidhi
            if e['series'] == 'GA' and e['num'] is not None and e['num'] <= 5 and di == 0 and ri < 6:
                e['kind'] = 'text'; e['num'] = None   # the opening ślokas
            entries.append(e); last = e
    return entries


# ---------------------------------------------------------------- images
def parse_image(fn):
    stem = os.path.splitext(fn)[0]
    m = re.match(r'[Rr]\s*[-_]*\s*([A-Za-z])', stem)
    if not m: return None
    letter = m.group(1).lower()
    if stem in IMG_NUM_OVERRIDE:
        num = IMG_NUM_OVERRIDE[stem]
    elif letter in ('a', 'b'):
        n = re.search(r'[Rr]\s*-\s*[ab]\s*-+\s*(\d+)', stem); num = int(n.group(1)) if n else None
    else:
        n = re.search(r'(\d+)\s*$', stem); num = int(n.group(1)) if n else None
    # caption: strip the series prefix and the numbers
    # a plate drawn for several entries names the others in brackets: (25-34) 35
    also = []
    for grp in re.findall(r'\(([\d,\s-]+)\)', stem) + re.findall(r'(\d+)\s*&', stem):
        for part in grp.split(','):
            part = part.strip()
            if re.fullmatch(r'\d+-\d+', part):
                lo, hi = map(int, part.split('-')); also += list(range(lo, hi + 1))
            elif part.isdigit(): also.append(int(part))
    cap = re.sub(r'^[Rr]\s*[-_]*\s*[A-Za-z]\s*-*\s*', '', stem)
    cap = re.sub(r'\(?[\d,\s-]+\)?', ' ', cap)
    cap = re.sub(r'\s+', ' ', re.sub(r'[`,]', ' ', cap).replace('&', ' & ').replace('_', ' ')).strip(' -,')
    words = []
    fix = {k[:1].upper() + k[1:].lower(): v for k, v in EN_FIX.items() if ' ' not in k}
    for w in cap.split(' '):
        w = w[:1].upper() + w[1:].lower() if w.isalpha() else w
        words.append(fix.get(w, w))
    cap = ' '.join(words).strip(' &')
    if stem in CAPTION_OVERRIDE: cap = CAPTION_OVERRIDE[stem]
    for k, v in EN_FIX.items():
        if ' ' in k: cap = cap.replace(k, v)
    if letter == 'h':
        series, num = H_MAP.get(num, ('HX', num))
    elif letter == 'g':
        series, num = 'LS', G_MAP.get(num)
    elif letter == 'f' and num is not None and num <= 8:
        series = 'LS'                      # f 1-8 are the Aṣṭalakṣmī plates
    else:
        series = IMG_SERIES.get(letter)
    return dict(series=series, num=num, also=[x for x in also if x != num], caption_en=cap, file=fn)


def attach_images(entries, src):
    byk = {(e['series'], e['num']): e for e in entries if e.get('num') is not None}
    orphans = []
    for part in IMG_PARTS:
        for fn in sorted(os.listdir(os.path.join(src, 'Upload RDR', part))):
            if not fn.lower().endswith('.jpg'): continue
            im = parse_image(fn)
            if not im or not im['series']:
                print('  skipped image', fn, file=sys.stderr); continue
            im['part'] = part
            key = (im['series'], im['num'])
            if im['num'] is not None and key in byk:
                byk[key]['images'].append(im)
                byk[key].setdefault('name_en', im['caption_en'])
                for n in im['also']:
                    o = byk.get((im['series'], n))
                    if o is not None and not any(x['file'] == fn for x in o['images']):
                        o['images'].append(dict(im, shared=True))
            else:
                e = dict(series=im['series'], num=im['num'], name_te='', name_en=im['caption_en'],
                         title_te='', shloka_te='', meaning_te='', images=[im], source=dict(image=fn))
                if im['num'] is not None: byk[key] = e
                orphans.append(e)
    return entries + orphans


def make_images(entries, src, write=True):
    from PIL import Image
    for size, sub in ((1100, 'full'), (360, 'thumb')):
        os.makedirs(os.path.join(OUT, 'img', sub), exist_ok=True)
    for e in entries:
        for k, im in enumerate(e['images']):
            name = e['id'] + ('' if k == 0 else f'-{k + 1}') + '.jpg'
            im['full'] = f'img/full/{name}'; im['thumb'] = f'img/thumb/{name}'
            if not write: continue
            srcp = os.path.join(src, 'Upload RDR', im['part'], im['file'])
            with Image.open(srcp) as I:
                I = I.convert('RGB')
                for box, sub, q in (((1100, 1100), 'full', 80), ((360, 480), 'thumb', 76)):
                    c = I.copy(); c.thumbnail(box, Image.LANCZOS)
                    c.save(os.path.join(OUT, 'img', sub, name), 'JPEG', quality=q,
                           optimize=True, progressive=True)


# ---------------------------------------------------------------- IAST
_V = {'అ': 'a', 'ఆ': 'ā', 'ఇ': 'i', 'ఈ': 'ī', 'ఉ': 'u', 'ఊ': 'ū', 'ఋ': 'ṛ', 'ౠ': 'ṝ', 'ఌ': 'ḷ',
      'ౡ': 'ḹ', 'ఎ': 'e', 'ఏ': 'e', 'ఐ': 'ai', 'ఒ': 'o', 'ఓ': 'o', 'ఔ': 'au'}
_M = {'ా': 'ā', 'ి': 'i', 'ీ': 'ī', 'ు': 'u', 'ూ': 'ū', 'ృ': 'ṛ', 'ౄ': 'ṝ', 'ౢ': 'ḷ', 'ె': 'e',
      'ే': 'e', 'ై': 'ai', 'ొ': 'o', 'ో': 'o', 'ౌ': 'au'}
_C = dict(zip('కఖగఘఙచఛజఝఞటఠడఢణతథదధనపఫబభమయరలవశషసహళఱ',
              'k kh g gh ṅ c ch j jh ñ ṭ ṭh ḍ ḍh ṇ t th d dh n p ph b bh m y r l v ś ṣ s h ḷ ṟ'.split()))


def iast(te):
    out, i = [], 0
    while i < len(te):
        ch = te[i]
        if ch in _C:
            out.append(_C[ch]); nx = te[i + 1] if i + 1 < len(te) else ''
            if nx == '్': i += 1
            elif nx in _M: out.append(_M[nx]); i += 1
            else: out.append('a')
        elif ch in _V: out.append(_V[ch])
        elif ch == 'ం': out.append('ṃ')
        elif ch == 'ః': out.append('ḥ')
        elif ch == 'ఁ': out.append('m̐')
        else: out.append(ch)
        i += 1
    s = ''.join(out)
    # anusvāra before a stop is written as that stop's nasal: Ānanda, Tāṇḍava
    for nas, cls in (('ṅ', 'kg'), ('ñ', 'cj'), ('ṇ', 'ṭḍ'), ('n', 'td'), ('m', 'pb')):
        s = re.sub('ṃ(?=[' + cls + '])', nas, s)
    return ' '.join(w[:1].upper() + w[1:] for w in s.split(' '))


# ---------------------------------------------------------------- main
def group_of(e):
    for g in GROUPS:
        for s in g['subs']:
            for (ser, lo, hi) in s['ranges']:
                if e['series'] == ser and (e['num'] is None and (ser in ('GA', 'VV') or lo is None) or
                                           lo is not None and
                                           e['num'] is not None and lo <= e['num'] <= hi):
                    return g['id'], s['id']
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=SRC); ap.add_argument('--soffice', default=SOFFICE)
    ap.add_argument('--no-images', action='store_true')
    a = ap.parse_args()
    entries = attach_images(build_entries(doc_rows(a.src, a.soffice)), a.src)
    # text-only rows inside a series follow their neighbour into its group
    prev = (None, None)
    for e in entries:
        g, s = group_of(e)
        if g is None and e.get('kind') == 'text': g, s = prev
        if g is None:
            print('  ungrouped', e['series'], e['num'], e['name_te'] or e.get('name_en'), file=sys.stderr)
            continue
        e['group'], e['sub'] = g, s; prev = (g, s)
    entries = [e for e in entries if e.get('group')]
    seen = {}
    for e in entries:
        base = f"{e['group']}-{e['series'].lower()}{e['num'] if e['num'] is not None else 't'}"
        seen[base] = seen.get(base, 0) + 1
        e['id'] = base if seen[base] == 1 else f'{base}-{seen[base]}'
        name = re.sub(r'^శ్ర\s', 'శ్రీ ', e['name_te'])
        e['name_iast'] = iast(name) if name else ''
    order = {(g['id'], s['id']): (gi, si) for gi, g in enumerate(GROUPS) for si, s in enumerate(g['subs'])}
    entries.sort(key=lambda e: (order[(e['group'], e['sub'])], e['series'], e['num'] if e['num'] is not None else -1))
    make_images(entries, a.src, write=not a.no_images)
    reg = dict(
        title='Rūpa Dhyāna Ratnāvalī', title_te='రూపధ్యాన రత్నావళి',
        about='Dhyāna ślokas of the deities with their iconographic diagrams and Telugu meaning.',
        source='Typed volumes RDR 16/44/45/57/47 and the scanned diagram plates (Parts 04–10).',
        groups=[{k: v for k, v in g.items()} for g in GROUPS],
        entries=entries)
    os.makedirs(os.path.join(OUT, 'data'), exist_ok=True)
    with open(os.path.join(OUT, 'data', 'devataa.json'), 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    n = len([e for e in entries if e.get('kind') != 'text'])
    print(f'{n} deities · {sum(1 for e in entries if e["images"])} with diagram · '
          f'{sum(1 for e in entries if e["shloka_te"] and e.get("kind") != "text")} with śloka')


if __name__ == '__main__':
    main()
