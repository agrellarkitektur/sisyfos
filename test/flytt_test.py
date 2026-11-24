#!/usr/bin/env python3
"""
Sisyfos 0.20.4 – flytten till sisyfos.danaid.cloud.

Appen hämtas i en riktig webbläsare från tre låtsade adresser (Playwright svarar med filerna i repot):
  1  gamla adressen (agrellarkitektur.se/sisyfos/): ingen flyttrad utan ?flytt; med ?flytt raden, stegen,
     länken till den nya adressen och knappen som sparar en kopia som fil (en hel bok i JSON)
  2  texterna om servern följer adressen: Loopia på den gamla, one.com och sisyfos.danaid.cloud på den
     nya, servern man hämtade appen från på en annan adress
  3  synpunkter går till feedback.php bredvid appen på båda adresserna (förut alltid till webbhotellet)
  4  nya adressen: startrutan säger hur man flyttar och har *Öppna en bok från fil*; en sparad fil från den
     gamla adressen importeras och ger samma summor

Kör:  python3 test/flytt_test.py   (ingen http-server behövs)
"""
import json, pathlib, sys, datetime, mimetypes
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
BOK = json.loads((ROT / 'test' / 'bocker' / 'format-12.json').read_text(encoding='utf-8'))
GAMLA, NYA, ANNAN = 'https://agrellarkitektur.se/sisyfos/', 'https://sisyfos.danaid.cloud/', 'https://example.org/tid/'
fel = 0
def ok(cond, text):
    global fel
    print(('OK  ' if cond else 'FEL ') + text); fel += not cond
def ev(page, fn, arg=None):
    return page.evaluate("([f, a]) => { with (window.SISYFOS) { return eval('(' + f + ')')(a); } }", [fn, arg])

synpunkter = []
def svara(route):
    url = route.request.url
    bas = next(b for b in (GAMLA, NYA, ANNAN) if url.startswith(b))
    rel = url[len(bas):].split('?')[0] or 'index.html'
    if rel == 'feedback.php':
        synpunkter.append(url)
        return route.fulfill(status=200, content_type='application/json', body='{"ok":true}')
    if rel == 'api.php':
        return route.fulfill(status=404, body='')
    f = ROT / rel
    if not f.is_file():
        return route.fulfill(status=404, body='')
    route.fulfill(status=200, content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream', body=f.read_bytes())

def sida(b, url, bok=True, w=1280):
    ctx = b.new_context(viewport={'width': w, 'height': 900}, service_workers='block', accept_downloads=True)
    for bas in (GAMLA, NYA, ANNAN):
        ctx.route(bas + '**', svara)
    if bok:
        ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(BOK))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); pg.js = []
    pg.on('pageerror', lambda e: pg.js.append(str(e)))
    pg.clock.install(time=datetime.datetime(2026, 11, 24, 10, 0))
    pg.goto(url); pg.wait_for_timeout(1200)
    return ctx, pg

def integritet(pg):
    ev(pg, "() => closeDlg()")
    ev(pg, "() => { const b = document.createElement('button'); b.dataset.act = 'dataInfo'; document.body.append(b); b.click(); b.remove(); }")
    pg.wait_for_timeout(200)
    return pg.inner_text('#dlg')

def synpunkt(pg):
    ev(pg, "() => { const b = document.createElement('button'); b.dataset.act = 'feedback'; document.body.append(b); b.click(); b.remove(); }")
    pg.wait_for_timeout(200)
    till = pg.inner_text('.fb-to')
    pg.fill('#fbMsg', 'Prov från flytt_test')
    pg.wait_for_timeout(3100)
    pg.click('#fbSend'); pg.wait_for_timeout(500)
    ev(pg, "() => closeDlg()"); pg.wait_for_timeout(200)
    return till

with sync_playwright() as p:
    b = p.chromium.launch()

    # ── 1: gamla adressen
    ctx, pg = sida(b, GAMLA + 'index.html?test')
    ok(ev(pg, "() => S.version") == 12, '1: boken öppnas på gamla adressen')
    ok(pg.locator('.alert.move').count() == 0, '1: ingen flyttrad utan ?flytt (MOVE_ON av)')
    t = integritet(pg)
    ok('Loopia' in t and 'agrellarkitektur.se' in t and 'one.com' not in t, '2: gamla adressen: Loopia i Data och integritet')
    till = synpunkt(pg)
    ok('agrellarkitektur.se' in till, f'2: synpunkter via agrellarkitektur.se ({till[:40]} …)')
    ok(synpunkter and synpunkter[-1].startswith(GAMLA + 'feedback.php'), f'3: synpunkten gick till feedback.php bredvid appen ({synpunkter[-1:]})')
    ok(not pg.js, f'inga JS-fel ({pg.js})')
    ctx.close()

    ctx, pg = sida(b, GAMLA + 'index.html?test&flytt')
    al = pg.locator('.alert.move')
    ok(al.count() == 1, '1: med ?flytt syns raden Sisyfos flyttar')
    txt = al.inner_text() if al.count() else ''
    ok('sisyfos.danaid.cloud' in txt and 'Öppna en bok från fil' in txt and 'Synka' not in txt, '1: stegen för en bok utan konto (inget om synk)')
    ok(pg.locator('.alert.move a[href="https://sisyfos.danaid.cloud/"]').count() >= 1, '1: länk till nya adressen')
    with pg.expect_download() as dl:
        pg.click('.alert.move [data-act=moveSave]')
    d = dl.value; data = json.loads(open(d.path(), encoding='utf-8').read())
    ok(data.get('format') == 'sisyfos' and data.get('version') == 12 and d.suggested_filename.endswith('.sisyfos.json'), f'1: kopian sparad som fil ({d.suggested_filename})')
    fil = d.path(); sparad = pathlib.Path('/tmp/sisyfos-flytt-test.json'); sparad.write_bytes(pathlib.Path(fil).read_bytes())
    summa_gamla = ev(pg, "() => live().reduce((s, e) => s + (e.hours || 0), 0)")
    pg.click('[data-act=view][data-view=month]'); pg.wait_for_timeout(300)
    ok(pg.locator('.alert.move').count() == 1, '1: raden syns också i månadsvyn')
    # Med konto (låtsat): stegen om synk och nytt konto
    ev(pg, "() => { st.web = { token: 'x', email: 'a@b.se' }; const a = document.querySelector('#alerts'); a.innerHTML = alertsHtml(); }")
    txt = pg.inner_text('.alert.move')
    ok('Synka boken' in txt and 'återställningsnyckeln' in txt and 'organisation' not in txt, '1: med konto: synka först, nytt konto och ny återställningsnyckel')
    ev(pg, "() => { st.web = { token: 'x', email: 'a@b.se', org: 'o1', role: 'admin' }; document.querySelector('#alerts').innerHTML = alertsHtml(); }")
    txt = pg.inner_text('.alert.move')
    ok('medarbetarna synka' in txt and 'Bjud in' in txt, '1: organisationens admin: medarbetarna synkar, bjud in igen')
    ev(pg, "() => { st.web = { token: 'x', email: 'n@b.se', org: 'o1', role: 'member' }; document.querySelector('#alerts').innerHTML = alertsHtml(); }")
    txt = pg.inner_text('.alert.move')
    ok('admin flyttar boken' in txt and pg.locator('.alert.move [data-act=moveSave]').count() == 0, '1: medarbetare: admin flyttar, ingen knapp')
    ev(pg, "() => { st.web = null; document.querySelector('#alerts').innerHTML = alertsHtml(); }")
    pg.set_viewport_size({'width': 390, 'height': 844}); pg.wait_for_timeout(300)
    (ROT / 'test' / '_bilder').mkdir(exist_ok=True)
    pg.screenshot(path=str(ROT / 'test' / '_bilder' / 'flytt-390.png'))
    ok(pg.locator('.alert.move').bounding_box()['width'] <= 390, '1: raden ryms på telefon')
    ok(not pg.js, f'inga JS-fel ({pg.js})')
    ctx.close()

    # ── 4: nya adressen, tom webbläsare
    ctx, pg = sida(b, NYA + '?test', bok=False)
    ok(pg.locator('.wel-v').count() == 1, '4: nya adressen: startrutan')
    ok('Flyttar du från agrellarkitektur.se' in pg.inner_text('.wel-move'), '4: startrutan säger hur man flyttar')
    ok(pg.locator('.alert.move').count() == 0, '4: ingen flyttrad på nya adressen')
    t = integritet(pg)
    ok('one.com' in t and 'sisyfos.danaid.cloud' in t and 'Loopia' not in t, '2: nya adressen: one.com i Data och integritet')
    ev(pg, "() => closeDlg()"); pg.wait_for_timeout(200)
    pg.click('.wel [data-act=importBook]'); pg.wait_for_timeout(200)
    pg.set_input_files('#imFile', str(sparad)); pg.click('[data-act=doImport]'); pg.wait_for_timeout(800)
    ok(ev(pg, "() => S.version") == 12 and pg.locator('.wel-v').count() == 0, '4: boken importerad på nya adressen')
    summa_nya = ev(pg, "() => live().reduce((s, e) => s + (e.hours || 0), 0)")
    ok(abs(summa_nya - summa_gamla) < 1e-9 and summa_nya > 0, f'4: samma timmar som på gamla adressen ({summa_nya} = {summa_gamla})')
    kost = ev(pg, "() => [...COST.values()].filter(c => !c.deleted).length")
    ok(kost == 3, f'4: kostnaderna följde med ({kost})')
    till = synpunkt(pg)
    ok('sisyfos.danaid.cloud' in till and synpunkter[-1].startswith(NYA + 'feedback.php'), f'3: nya adressen: synpunkten till {synpunkter[-1]}')
    ok(not pg.js, f'inga JS-fel ({pg.js})')
    ctx.close()

    # ── 2: en annan adress (egen server eller en kopia)
    ctx, pg = sida(b, ANNAN + 'index.html?test')
    t = integritet(pg)
    ok('example.org' in t and 'Loopia' not in t and 'one.com' not in t, '2: annan adress: servern som appen hämtades från')
    till = synpunkt(pg)
    ok(synpunkter[-1].startswith(GAMLA + 'feedback.php'), f'3: annan adress: synpunkter till webbhotellet som förut ({synpunkter[-1]})')
    ok(not pg.js, f'inga JS-fel ({pg.js})')
    ctx.close()
    b.close()

print(f'\n{"Alla test gick igenom." if not fel else f"{fel} fel."}')
sys.exit(1 if fel else 0)
