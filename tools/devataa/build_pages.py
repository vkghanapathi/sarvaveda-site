"""Render sarvaveda.info/devataa from devataa/data/devataa.json.

Every count on the pages is computed here from the registry, so adding an
entry to the registry and re-running raises the counts everywhere.

Usage:  python tools/devataa/build_pages.py
"""
import html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'devataa')
CREDIT = ('Product designed by VKG Foundation; Implemented by SD Ventures and Supplies '
          'for Dharma Poshanam, licensee')
FONTS = ('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700'
         '&family=Noto+Serif+Devanagari:wght@400;600&family=Noto+Serif+Telugu:wght@400;600'
         '&family=Spectral:ital,wght@0,300;0,400;0,500;1,400&display=swap')

e_ = lambda s: html.escape(s or '', quote=True)
br = lambda s: '<br>'.join(e_(l) for l in (s or '').split('\n'))


def page(title, desc, body, depth=''):
    return f'''<!doctype html>
<html lang="te">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e_(title)} | SarvaVeda</title>
<meta name="description" content="{e_(desc)}" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="{e_(FONTS)}" rel="stylesheet" />
<link rel="stylesheet" href="/assets/adhikarana.css" />
<link rel="stylesheet" href="/devataa/devataa.css" />
</head>
<body>
<header class="site"><div class="wrap bar">
  <a class="home" href="/">SarvaVeda</a>
  <a href="/devataa/">Devatā</a>
  <a href="/jaimini">Jaiminīya</a>
  <a href="/brahmasutra">Vaiyāsika</a>
  <a href="/pada-kosha">Pada Kośa</a>
  <a href="/vvs">VVS</a>
</div></header>
<div class="wrap">
{body}
<footer class="site">
  Set from the typed volumes and scanned plates of the Rūpa Dhyāna Ratnāvalī; ślokas and meanings stand as typed.
  <a href="/devataa/data/devataa.json">Registry (JSON)</a> · <a href="/">sarvaveda.info</a>
  <div class="credit">{e_(CREDIT)}</div>
</footer>
</div>
<dialog id="plate"><img alt="" /><form method="dialog"><button aria-label="Close">×</button></form></dialog>
<script src="/devataa/devataa.js" defer></script>
</body>
</html>
'''


def counts(es):
    d = [e for e in es if e.get('kind') != 'text']
    return dict(n=len(d), img=sum(1 for e in d if e['images']),
                sl=sum(1 for e in d if e['shloka_te']))


def tally(c):
    pl = lambda n, one, many: f'{n} {one if n == 1 else many}'
    return ' · '.join((pl(c['n'], 'deity', 'deities'), pl(c['img'], 'diagram', 'diagrams'),
                       pl(c['sl'], 'śloka', 'ślokas')))


def facts(c, groups=None):
    items = ([(groups, 'groups')] if groups else []) + [
        (c['n'], 'deity' if c['n'] == 1 else 'deities'), (c['img'], 'with diagram'), (c['sl'], 'with dhyāna śloka')]
    return '<div class="facts">' + ''.join(f'<div><b>{v}</b><span>{k}</span></div>' for v, k in items) + '</div>'


def card(e):
    if e.get('kind') == 'text':
        parts = [f'<div class="passage" id="{e["id"]}">']
        if e['name_te']: parts.append(f'<h4 class="te">{e_(e["name_te"])}</h4>')
        for b in [dict(shloka=e['shloka_te'], meaning=e['meaning_te'])] + e.get('more', []):
            if b.get('title'): parts.append(f'<h4 class="te">{e_(b["title"])}</h4>')
            if b['shloka']: parts.append(f'<div class="sl te" lang="sa">{br(b["shloka"])}</div>')
            if b['meaning']: parts.append(f'<p class="mean te">{br(b["meaning"])}</p>')
        return '\n'.join(parts) + '</div>'
    name = e['name_te'] or ''
    rom = ' · '.join(x for x in (e.get('name_iast'), e.get('name_en')) if x)
    head = f'<span class="num">{e["num"] if e["num"] is not None else ""}</span>'
    title = f'<span class="te">{e_(name)}</span>' if name else f'<span>{e_(e.get("name_en") or "Unnamed plate")}</span>'
    figs = []
    for im in e['images']:
        cap = 'Shared plate' if im.get('shared') else ''
        figs.append(f'<figure><a href="{im["full"]}" class="plate"><img src="{im["thumb"]}" loading="lazy" '
                    f'alt="{e_(e.get("name_en") or e.get("name_iast") or name)}" /></a>'
                    + (f'<figcaption>{cap}</figcaption>' if cap else '') + '</figure>')
    if not figs:
        figs.append('<div class="noplate">No diagram plate for this form in the scanned set.</div>')
    body = []
    if e['shloka_te']:
        body.append(f'<div class="sl te" lang="sa">{br(e["shloka_te"])}</div>')
    else:
        body.append('<p class="empty">Dhyāna śloka for this plate is not in the typed volumes yet; '
                    'the diagram is shown alone.</p>')
    if e['meaning_te']:
        body.append(f'<p class="mean te"><b>తాత్పర్యము</b> {br(e["meaning_te"])}</p>')
    for b in e.get('more', []):
        if b.get('title'): body.append(f'<h4 class="te">{e_(b["title"])}</h4>')
        if b['shloka']: body.append(f'<div class="sl te" lang="sa">{br(b["shloka"])}</div>')
        if b['meaning']: body.append(f'<p class="mean te">{br(b["meaning"])}</p>')
    search = ' '.join(x for x in (name, e.get('name_iast'), e.get('name_en')) if x).lower()
    return (f'<article class="dv" id="{e["id"]}" data-q="{e_(search)}">'
            f'<div class="figs">{"".join(figs)}</div>'
            f'<div class="txt"><h3>{head}{title}</h3>'
            + (f'<div class="rom">{e_(rom)}</div>' if rom else '')
            + ''.join(body) + '</div></article>')


TOOLS = '''<div class="tools">
  <input type="search" id="find" placeholder="Find a deity — తెలుగు, IAST or English" aria-label="Find a deity" />
  <div class="script" role="group" aria-label="Script for ślokas">
    <button data-script="te" aria-pressed="true">తెలుగు</button><button data-script="dn" aria-pressed="false">देवनागरी</button>
  </div>
</div>
<p class="found" id="found" hidden></p>'''


def main():
    reg = json.load(open(os.path.join(OUT, 'data', 'devataa.json'), encoding='utf-8'))
    es = reg['entries']
    total = counts(es)
    cards = []
    for g in reg['groups']:
        ges = [e for e in es if e['group'] == g['id']]
        c = counts(ges)
        lead = next((im['thumb'] for e in ges for im in e['images']), None)
        subs_nav, secs = [], []
        for s in g['subs']:
            ses = [e for e in ges if e['sub'] == s['id']]
            if not ses: continue
            sc = counts(ses)
            subs_nav.append(f'<a href="#{s["id"]}"><span class="te">{e_(s["te"])}</span> <span class="n">{sc["n"]}</span></a>')
            secs.append(f'<section id="{s["id"]}"><h2 class="sec"><span class="te">{e_(s["te"])}</span>'
                        f'<span class="lk">{e_(s["iast"])} · {tally(sc)}</span></h2>'
                        + '\n'.join(card(e) for e in ses) + '</section>')
        body = (f'<div class="crumb"><a href="/devataa/">రూపధ్యాన రత్నావళి</a> › {e_(g["iast"])}</div>'
                f'<div class="masthead"><h1 class="te">{e_(g["te"])}</h1>'
                f'<div class="rom">{e_(g["iast"])} · Rūpa Dhyāna Ratnāvalī</div>'
                f'<p>Each form with its diagram plate, its dhyāna śloka and the Telugu meaning, as typed in the source volumes.</p></div>'
                + facts(c) + f'<nav class="subs">{"".join(subs_nav)}</nav>' + TOOLS + '\n'.join(secs))
        with open(os.path.join(OUT, f'{g["id"]}.html'), 'w', encoding='utf-8') as f:
            f.write(page(f'{g["iast"]} — Rūpa Dhyāna Ratnāvalī',
                         f'{c["n"]} forms of {g["en"]} with diagram, dhyāna śloka and meaning.', body))
        cards.append(f'<a class="gcard" href="/devataa/{g["id"]}.html">'
                     + (f'<img src="/devataa/{lead}" alt="" loading="lazy" />' if lead else '')
                     + f'<span class="te gname">{e_(g["te"])}</span><span class="rom">{e_(g["iast"])}</span>'
                     f'<span class="n">{tally(c)}</span></a>')
    ngroups = len([g for g in reg['groups'] if any(e['group'] == g['id'] for e in es)])
    body = ('<div class="masthead"><h1 class="te">రూపధ్యాన రత్నావళి</h1>'
            '<div class="rom">Rūpa Dhyāna Ratnāvalī · the forms of the devatās</div>'
            f'<p>{total["n"]} forms of the devatās, grouped as the book groups them — each with its diagram plate, '
            'its dhyāna śloka, and the meaning in Telugu.</p></div>'
            + facts(total, ngroups)
            + '<h2 class="sec">Groups of deities</h2><div class="groups">' + ''.join(cards) + '</div>'
            + '<h2 class="sec">Find across all groups</h2>' + TOOLS
            + '<div id="all-results" class="results"></div>'
            '<div class="note">Ślokas and meanings stand exactly as typed in the volumes. Where a plate has no śloka typed yet, '
            'or a śloka has no plate in the scanned set, the card says so. The registry behind these pages is open at '
            '<a href="/devataa/data/devataa.json">devataa.json</a>.</div>')
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page('Rūpa Dhyāna Ratnāvalī — Devatā',
                     f'{total["n"]} forms of the devatās with diagram plates, dhyāna ślokas and Telugu meaning.', body))
    print(f'{ngroups} groups · {total["n"]} deities · {total["img"]} with diagram · {total["sl"]} with śloka')


if __name__ == '__main__':
    main()
