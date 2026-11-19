#!/usr/bin/env python3
"""Sisyfos 0.20.1 – synk mellan två enheter mot api.php (rättningarna A5 och B10 ur granskningen av 0.20.0).

  A5  A skapar ett projekt och synkar; B skriver tid på det utan nät; A tar bort projektet och synkar; B synkar.
      Tidboken på B ska gå att öppna, projektet ska finnas kvar med tiden, och A ska få tillbaka projektet.
  B10 Medan Så påverkas summan är öppen (st.pg) skickas inget till servern; när dialogen är stängd synkar enheten.

Kräver php och Playwright med Chromium.
Kör: python3 -m http.server 8765 &  python3 test/synk_test.py   (http-servern behövs inte – testet startar php -S)
"""
from urllib.parse import quote
import hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN = 'Testnyckel för admin – synk'
EMAIL, PW = 'synk@example.se', 'korrekt häst batteri synk'
BOK = json.load(open(os.path.join(ROOT, 'test', 'bocker', 'format-12.json'), encoding='utf-8'))
fel = []


def ok(cond, text):
    print(('OK  ' if cond else 'FEL ') + text, flush=True)
    if not cond: fel.append(text)


def ledig_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def ev(page, fn, arg=None):
    return page.evaluate("([f, a]) => { with (window.SISYFOS) { return eval('(' + f + ')')(a); } }", [fn, arg])


WEB_JS = """() => new Promise((res, rej) => { const r = indexedDB.open('sisyfos'); r.onsuccess = () => { const db = r.result;
  const g = db.transaction('kv').objectStore('kv').get('web'); g.onsuccess = () => { res(g.result || null); db.close(); }; }; r.onerror = () => rej(r.error); })"""


def shell(page, text):
    page.wait_for_function("() => document.querySelector('.wel-v') || document.getElementById('quickIn')?.offsetParent")
    if page.locator('.wel [data-act=welcomeSample]').count(): page.click('.wel [data-act=welcomeSample]'); page.wait_for_timeout(200)
    page.fill('#quickIn', text); page.wait_for_timeout(150); page.press('#quickIn', 'Enter'); page.wait_for_timeout(300)


def vanta_synk(page, ms=20000):
    page.wait_for_function("() => /Synkad/.test(document.querySelector('#saveState .t')?.textContent || '')", timeout=ms)


def synka(page):
    page.wait_for_timeout(1200)  # så att ett gammalt "Synkad" inte räknas
    shell(page, 'synk'); page.wait_for_timeout(300); vanta_synk(page)


def akt(pg, act, **data):
    attrs = ' '.join(f'data-{k}="{v}"' for k, v in data.items())
    pg.evaluate("(h) => { document.getElementById('tb')?.remove(); document.body.insertAdjacentHTML('beforeend', h); document.getElementById('tb').click(); }", f'<button id="tb" data-act="{act}" {attrs}>x</button>')
    pg.wait_for_timeout(300)


def rev(page, url):
    w = page.evaluate(WEB_JS)
    req = urllib.request.Request(url + 'api.php?a=info', headers={'X-Sisyfos-Token': w['token']})
    return json.loads(urllib.request.urlopen(req).read())['rev']


def main():
    tmp = tempfile.mkdtemp(prefix='sisyfos-synk-')
    web = os.path.join(tmp, 'pub', 'sisyfos'); os.makedirs(web)
    for f in ['index.html', 'sw.js', 'api.php', 'manifest.webmanifest', 'icon.svg', 'favicon-32.png']:
        shutil.copy(os.path.join(ROOT, f), web)
    with open(os.path.join(web, 'api-config.php'), 'w') as f:
        f.write("<?php return ['admin' => '%s'];\n" % hashlib.sha256(ADMIN.encode()).hexdigest())
    port = ledig_port()
    srv = subprocess.Popen(['php', '-S', f'127.0.0.1:{port}', '-t', os.path.join(tmp, 'pub')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f'http://127.0.0.1:{port}/sisyfos/'
    try:
        for _ in range(50):
            try: socket.create_connection(('127.0.0.1', port), 0.2).close(); break
            except OSError: time.sleep(0.1)
        req = urllib.request.Request(url + 'api.php?a=invite', data=json.dumps({'note': 'synk', 'max': 1}).encode(), headers={'X-Sisyfos-Admin': quote(ADMIN), 'Content-Type': 'application/json'})
        kod = json.loads(urllib.request.urlopen(req).read())['code']

        with sync_playwright() as p:
            br = p.chromium.launch()
            cA = br.new_context(service_workers='block'); cB = br.new_context(service_workers='block')
            cA.add_init_script(f"if (!localStorage.getItem('sisyfos.bok')) localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(BOK))});")
            A, B = cA.new_page(), cB.new_page()
            jsA, jsB = [], []
            A.on('pageerror', lambda e: jsA.append(str(e))); B.on('pageerror', lambda e: jsB.append(str(e)))
            for pg in (A, B): pg.goto(url + '?test'); pg.wait_for_selector('#saveState')

            # A: konto med boken format 12
            shell(A, 'webb'); A.wait_for_selector('[data-act=webReg]'); A.click('[data-act=webReg]')
            A.fill('#wInv', kod); A.fill('#wEmail', EMAIL); A.fill('#encPw', PW); A.fill('#encPw2', PW)
            A.click('[data-act=webRegGo]'); A.wait_for_selector('.rk-key', timeout=30000)
            rk = A.inner_text('.rk-key').replace('\n', '').replace(' ', '')
            A.fill('#rkLast', rk[-4:]); A.click('[data-act=rkConfirm]'); vanta_synk(A, 30000)
            ok(True, 'A: konto skapat och boken synkad')

            # B: logga in
            shell(B, 'webb'); B.wait_for_selector('[data-act=webLogin]'); B.click('[data-act=webLogin]')
            B.fill('#wEmail', EMAIL); B.fill('#wPw', PW); B.click('[data-act=webLoginGo]'); vanta_synk(B, 30000)
            ok(ev(B, "() => S.register.book.name") == 'Testbok format 12', 'B: inloggad med samma bok')

            # A5: projekt skapas på A, B skriver tid utan nät, A tar bort projektet
            shell(A, 'proj Nytt Uppdrag'); synka(A)
            pid = ev(A, "() => S.register.projects.find(p => p.name === 'Nytt Uppdrag')?.id")
            ok(bool(pid), f'A: projektet Nytt Uppdrag skapat ({pid})')
            synka(B)
            ok(ev(B, f"() => !!proj('{pid}')"), 'B: har projektet')
            cB.set_offline(True); B.wait_for_timeout(300)
            shell(B, '3 nytt utredning')
            ok(ev(B, f"() => live().filter(e => e.projectId === '{pid}').reduce((s, e) => s + e.hours, 0)") == 3, 'B: 3 h på Nytt Uppdrag utan nät')
            ev(A, f"() => {{ st.editProj = '{pid}'; return true; }}"); akt(A, 'projDelete')
            ok(not ev(A, f"() => S.register.projects.some(p => p.id === '{pid}')"), 'A: projektet borttaget (ingen tid på A)')
            synka(A)
            cB.set_offline(False); B.wait_for_timeout(300); synka(B)
            B.reload(); B.wait_for_selector('#saveState'); B.wait_for_timeout(1500)
            ok(not jsB, f'B: tidboken öppnas efter synk och omladdning ({jsB[:1]})')
            ok(ev(B, f"() => S.register.projects.find(p => p.id === '{pid}')?.name") == 'Nytt Uppdrag', 'B: projektet är tillbaka med sitt namn')
            ok(ev(B, f"() => live().filter(e => e.projectId === '{pid}').reduce((s, e) => s + e.hours, 0)") == 3, 'B: tiden finns kvar')
            ok(B.locator('.wkv :text("Nytt Uppdrag")').count() >= 1, 'B: raden syns i veckan')
            synka(A)
            ok(ev(A, f"() => S.register.projects.find(p => p.id === '{pid}')?.name") == 'Nytt Uppdrag', 'A: projektet kom tillbaka vid synken')
            ok(ev(A, f"() => [...E.values()].filter(e => !e.deleted && e.projectId === '{pid}').reduce((s, e) => s + e.hours, 0)") == 3, 'A: B:s 3 h finns i boken')
            ok(not jsA, f'A: inga fel ({jsA[:1]})')

            # B10: ingen synk medan Så påverkas summan är öppen
            r0 = rev(A, url)
            ev(A, "() => { st.pg = { L: [], mode: 'new' }; S.register.book.name = 'Inte godkänt'; save(); return true; }")
            shell(A, 'synk'); A.wait_for_timeout(6500)
            ok(rev(A, url) == r0, 'B10: inget skickas medan dialogen väntar på svar')
            ev(A, "() => { st.pg = null; return true; }")
            ev(A, "() => { S.register.book.name = 'Godkänt'; save(); return true; }")
            synka(A)
            ok(rev(A, url) > r0, 'B10: synkar när dialogen är stängd')
            synka(B)
            ok(ev(B, "() => S.register.book.name") == 'Godkänt', 'B10: B får det godkända – det ogodkända skickades aldrig')
            br.close()
    finally:
        srv.terminate(); shutil.rmtree(tmp, ignore_errors=True)
    print('\n' + ('ALLA OK' if not fel else f'{len(fel)} FEL'))
    sys.exit(1 if fel else 0)


main()
