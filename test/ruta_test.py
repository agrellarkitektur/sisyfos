#!/usr/bin/env python3
"""
Sisyfos 0.20.3 – tomma rader i projektdagboken, rutornas utseende, utfälld dagbok och loggan.

I en riktig webbläsare med exempelboken format 12:
  1  en post vars timmar tömts men vars anteckning står kvar blir ingen rad med 0,0 i projektdagboken
     (anteckningen finns kvar i boken – inget går förlorat)
  2  tid utan anteckning är uttonad (fyllning och siffror), hanterad tid har ett grönt hänglås i rutan
  3  utfälld dagbok i veckan: förslagen har en fast höjd i projektet man skriver i – raden hoppar inte
  4  loggan: en genomskinlig PNG sparas också som PNG (rapporten utan vit ruta), en svart logga
     inverteras i mörkt läge; en bild utan genomskinlighet blir som förut (bara JPEG)

Kör:  python3 -m http.server 8765 &  python3 test/ruta_test.py
"""
import json, pathlib, sys, datetime
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
URL = (sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html') + '?test'
BOK = json.loads((ROT / 'test' / 'bocker' / 'format-12.json').read_text(encoding='utf-8'))
BILDER = ROT / 'test' / '_bilder'; BILDER.mkdir(exist_ok=True)
fel = 0
def ev(page, fn, arg=None):
    return page.evaluate("([f, a]) => { with (window.SISYFOS) { return eval('(' + f + ')')(a); } }", [fn, arg])
def ok(cond, text):
    global fel
    print(('OK  ' if cond else 'FEL ') + text); fel += not cond

# En bild ritad i sidan: svart text/figur på genomskinlig botten (eller vit botten med ogenomskinlig = True)
BILD = """async (a) => {
  const c = document.createElement('canvas'); c.width = 400; c.height = 120; const x = c.getContext('2d');
  if (a.vit) { x.fillStyle = '#fff'; x.fillRect(0, 0, 400, 120); }
  x.fillStyle = a.farg; x.fillRect(10, 20, 80, 80); x.font = 'bold 48px sans-serif'; x.fillText('AGRELL', 110, 80);
  const blob = await new Promise(r => c.toBlob(r, 'image/png'));
  const lg = await logoFrom(new File([blob], 'logga.png', { type: 'image/png' }));
  return { png: !!lg.png, dark: !!lg.dark, jpeg: lg.src.startsWith('data:image/jpeg'), lg };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, service_workers='block')
    ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(BOK))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.clock.install(time=datetime.datetime(2026, 11, 23, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(1200)
    ok(ev(pg, "() => S.version") == 12, 'format 12')

    # ── 1: tomma rader i projektdagboken
    RK, D = 'proj1~upg2', '2026-11-18'
    ev(pg, f"() => setCell('{RK}', '{D}', {{ hours: 1, note: 'Kommunikation angående dagsljus' }})")
    ev(pg, f"() => setCell('{RK}', '{D}', {{ hours: 0 }})")
    c = ev(pg, f"() => {{ const e = cell('{RK}', '{D}'); return e && [e.hours, e.note]; }}")
    ok(c == [0, 'Kommunikation angående dagsljus'], f'1: posten finns kvar med anteckningen (inget förloras) ({c})')
    rader = ev(pg, "() => diaryData('proj1', '2026-11-16', '2026-11-22', 'ex').rows.map(r => [r.date, r.hours])")
    ok(all(h > 0 for _, h in rader) and D not in [d for d, _ in rader], f'1: ingen rad med 0 h i projektdagboken ({rader})')
    grp = ev(pg, "() => diaryData('proj1', '2026-11-16', '2026-11-22', 'ex').groups.flatMap(g => g.rows).filter(r => !(r.hours > 0)).length")
    ok(grp == 0, '1: inte heller i uppställningen per uppgift/vecka')
    ev(pg, "() => { const r = rep(); r.tab = 'diary'; r.pid = 'proj1'; r.custom = true; r.from = '2026-11-16'; r.to = '2026-11-22'; r.lay = 'week'; r.empty = false; r.amount = 'ex'; st.page = 'rapporter'; render(); }")
    pg.wait_for_timeout(300)
    txt = pg.inner_text('.paper')
    ok('dagsljus' not in txt, '1: raden syns inte på skärmen')

    # ── 2: rutornas utseende
    ev(pg, f"() => {{ setCell('proj1~upg2', '2026-11-19', {{ hours: 2, note: '' }}); setCell('proj1~upg2', '2026-11-20', {{ hours: 2, note: 'Skisser' }}); st.page = 'tid'; st.view = 'week'; st.week = '2026-11-16'; render(); }}")
    pg.wait_for_timeout(300)
    utan = pg.locator('[data-cellbox="proj1~upg2|2026-11-19"]'); med = pg.locator('[data-cellbox="proj1~upg2|2026-11-20"]')
    ok('nonote' in (utan.get_attribute('class') or '') and 'nonote' not in (med.get_attribute('class') or ''), '2: rutan utan anteckning har nonote')
    fu = utan.locator('.h-in').evaluate("e => getComputedStyle(e).color"); fm = med.locator('.h-in').evaluate("e => getComputedStyle(e).color")
    ok(fu != fm, f'2: siffrorna uttonade utan anteckning ({fu} mot {fm})')
    bu = utan.evaluate("e => getComputedStyle(e).backgroundImage"); bm = med.evaluate("e => getComputedStyle(e).backgroundImage")
    ok(bu != bm, '2: fyllningen svagare utan anteckning')
    utan.screenshot(path=str(BILDER / 'ruta-utan-anteckning.png')); med.screenshot(path=str(BILDER / 'ruta-med-anteckning.png'))
    # Hanterad tid: Villa Strand 1–15 sep
    ev(pg, "() => { st.week = '2026-09-07'; render(); }"); pg.wait_for_timeout(300)
    hd = pg.locator('.cell.hd').first
    ok(hd.count() == 1, '2: hanterad ruta finns (v37)')
    m = hd.locator('.hdm').evaluate("e => { const s = getComputedStyle(e); return [s.display, (s.maskImage || s.webkitMaskImage || '').includes('svg'), s.backgroundColor, +s.opacity]; }")
    ok(m[0] == 'block' and m[1] and m[3] < 1, f'2: hänglåset syns som motiv i rutan ({m})')
    z = hd.locator('.h-in').evaluate("e => getComputedStyle(e).zIndex")
    ok(z == '1', '2: siffrorna ligger framför hänglåset')
    hd.screenshot(path=str(BILDER / 'ruta-hanterad.png'))
    pg.locator('.wkv').first.screenshot(path=str(BILDER / 'vecka-hanterad.png'))

    # ── 3: utfälld dagbok – fast höjd för förslagen
    ev(pg, "() => { S.prefs.expanded = ['proj1~upg2']; st.week = '2026-11-16'; render(); }"); pg.wait_for_timeout(300)
    ta = pg.locator('textarea[id="n_proj1~upg2_2026-11-17"]')
    ok(ta.is_visible(), '3: dagboken är utfälld')
    rad = pg.locator('section.row[data-pid="proj1"]').first
    h0 = rad.bounding_box()['height']
    ta.click(); pg.wait_for_timeout(200)
    hojd = [rad.bounding_box()['height']]
    for t in ['S', 'Sk', 'Skiss', 'Skisser. M', 'xyzåäö', '']:
        ta.fill(t); pg.wait_for_timeout(150); hojd.append(rad.bounding_box()['height'])
    sg = pg.locator('.r-diary [data-sugg="proj1~upg2|2026-11-17"]').evaluate("e => [getComputedStyle(e).display, e.getBoundingClientRect().height]")
    ok(sg[0] == 'flex' and abs(sg[1] - 128) < 1, f'3: förslagen har fast höjd ({sg})')
    ok(max(hojd) - min(hojd) < 1, f'3: raden hoppar inte medan man skriver ({h0} → {hojd})')
    rad.screenshot(path=str(BILDER / 'dagbok-utfalld.png'))
    pg.locator('.rail [data-page=projekt]').click(); pg.wait_for_timeout(200)
    ev(pg, "() => { st.page = 'tid'; render(); }"); pg.wait_for_timeout(200)
    ok(abs(pg.locator('section.row[data-pid="proj1"]').first.bounding_box()['height'] - h0) < 1, '3: utan fokus tar förslagen ingen plats')

    # ── 4: loggan
    svart = ev(pg, BILD, {'farg': '#111', 'vit': False})
    ok(svart['png'] and svart['dark'] and svart['jpeg'], f'4: svart genomskinlig logga – PNG, mörk, JPEG kvar för PDF ({svart["png"]}, {svart["dark"]})')
    rod = ev(pg, BILD, {'farg': '#c33', 'vit': False})
    ok(rod['png'] and not rod['dark'], '4: färgad genomskinlig logga – PNG, inverteras inte')
    vit = ev(pg, BILD, {'farg': '#111', 'vit': True})
    ok(not vit['png'] and not vit['dark'], '4: logga utan genomskinlighet – bara JPEG som förut')
    ev(pg, "(lg) => { R().book.logo = lg; const r = rep(); r.tab = 'diary'; r.pid = 'proj1'; st.page = 'rapporter'; render(); }", svart['lg'])
    pg.wait_for_timeout(300)
    img = pg.locator('.paper img.pp-logo')
    ok('tr' in img.get_attribute('class') and 'inv' in img.get_attribute('class') and img.get_attribute('src').startswith('data:image/png'), '4: rapporten visar PNG:en (tr, inv)')
    for tema, vant in [('light', 'none'), ('dark', 'invert(1)')]:
        ev(pg, f"() => {{ document.documentElement.dataset.theme = '{tema}'; }}"); pg.wait_for_timeout(100)
        f = img.evaluate("e => [getComputedStyle(e).filter, getComputedStyle(e).backgroundColor]")
        ok(f[0] == vant and f[1] in ('rgba(0, 0, 0, 0)', 'transparent'), f'4: {tema} – filter {f[0]}, ingen vit ruta')
        pg.locator('.pp-top').screenshot(path=str(BILDER / f'logga-{tema}.png'))
    ok(ev(pg, "() => diaryPdf(diaryData('proj1', '2026-11-16', '2026-11-22', 'ex'), false).length") > 1000, '4: PDF:en går att göra med loggan (JPEG)')
    ev(pg, "(lg) => { R().book.logo = lg; render(); }", vit['lg']); pg.wait_for_timeout(200)
    c2 = pg.locator('.paper img.pp-logo').get_attribute('class')
    ok('tr' not in c2 and 'inv' not in c2, '4: logga utan genomskinlighet visas som förut (vit ruta)')

    ok(not js, f'inga skriptfel ({js})')
    b.close()

print('\nAlla prov gick igenom.' if not fel else f'\n{fel} FEL')
sys.exit(1 if fel else 0)
