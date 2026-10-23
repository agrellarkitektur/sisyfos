#!/usr/bin/env python3
"""Testar lagring på webben (0.13.0) i två webbläsare mot api.php på en lokal PHP-server.

Två webbläsarkontexter = två enheter med egen lagring. Provar: skapa konto (krypteringen slås på,
återställningsnyckeln bekräftas), logga in på den andra enheten, ändringar på båda som slås ihop,
en krock som visas i en dialog, byte av lösenord som loggar ut den andra enheten, inloggning igen,
tidigare versioner, adminvyn, utloggning med borttagning och radering av kontot.

Kräver php, Playwright med Chromium (pip install playwright && playwright install chromium).
Kör: python3 test/webb_test.py   (körs inte i GitHub – för hand före en ny version)
"""
from urllib.parse import quote
import hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN = 'Testnyckel för admin – åäö € 2026'
EMAIL, PW, PW2 = 'testare@example.se', 'korrekt häst batteri', 'nytt lösenord för test'
fel = []


def ok(cond, text):
    print(('OK  ' if cond else 'FEL ') + text, flush=True)
    if not cond:
        fel.append(text)


def ledig_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


BOK_JS = """() => new Promise((res, rej) => { const r = indexedDB.open('sisyfos'); r.onsuccess = () => { const db = r.result;
  const tx = db.transaction('kv'), g = tx.objectStore('kv').get('bok'), w = tx.objectStore('kv').get('web');
  tx.oncomplete = () => { res({ bok: g.result ? JSON.parse(g.result.raw) : null, web: w.result || null }); db.close(); }; }; r.onerror = () => rej(r.error); })"""


def bok(page):
    return page.evaluate(BOK_JS)


def shell(page, text):
    page.fill('#quickIn', text); page.wait_for_timeout(150); page.press('#quickIn', 'Enter'); page.wait_for_timeout(300)


def status(page):
    return page.inner_text('#saveState .t')


def vanta_synk(page, ms=20000):
    page.wait_for_function("() => /Synkad/.test(document.querySelector('#saveState .t')?.textContent || '')", timeout=ms)


def synka(page):
    shell(page, 'synk'); page.wait_for_timeout(300); vanta_synk(page)


def projekt(page):
    return sorted(p['name'] for p in bok(page)['bok']['register']['projects'])


def main():
    tmp = tempfile.mkdtemp(prefix='sisyfos-webb-')
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
        req = urllib.request.Request(url + 'api.php?a=invite', data=json.dumps({'note': 'test', 'max': 1}).encode(), headers={'X-Sisyfos-Admin': quote(ADMIN), 'Content-Type': 'application/json'})
        kod = json.loads(urllib.request.urlopen(req).read())['code']
        ok(len(kod) == 11, f'inbjudningskod {kod}')

        with sync_playwright() as p:
            br = p.chromium.launch()
            A = br.new_context(service_workers='block').new_page()
            B = br.new_context(service_workers='block').new_page()
            for pg in (A, B):
                pg.on('pageerror', lambda e: fel.append('sidfel: ' + str(e)) or print('SIDFEL', e))
                pg.goto(url); pg.wait_for_selector('#saveState')

            # --- A: importera en bok och skapa konto ---
            A.click('#brandBtn'); A.click('[data-act=importBook]')
            A.set_input_files('#imFile', os.path.join(ROOT, 'test', 'bocker', 'format-7.json')); A.wait_for_timeout(300)
            A.click('[data-act=doImport]'); A.wait_for_timeout(500)
            shell(A, 'webb'); A.wait_for_selector('[data-act=webReg]')
            A.click('[data-act=webReg]')
            A.fill('#wInv', 'fel-kod'); A.fill('#wEmail', EMAIL); A.fill('#encPw', PW); A.fill('#encPw2', PW)
            A.click('[data-act=webRegGo]'); A.wait_for_selector('.rk-key', timeout=20000)
            rk = A.inner_text('.rk-key').replace('\n', '').replace(' ', '')
            A.fill('#rkLast', rk[-4:]); A.click('[data-act=rkConfirm]')
            A.wait_for_function("() => /gäller inte/.test(document.querySelector('#encErr')?.textContent || '')", timeout=20000)
            ok(True, 'fel inbjudningskod ger felmeddelande (krypteringen är ändå på)')
            A.fill('#wInv', kod); A.fill('#wPw', PW); A.click('[data-act=webRegGo]')
            vanta_synk(A)
            d = bok(A)
            ok(d['web']['rev'] == 1 and d['web']['email'] == EMAIL, f"A: konto skapat och boken sparad (version {d['web']['rev']})")
            ls = A.evaluate('() => JSON.stringify(Object.assign({}, localStorage))')
            ok(d['web']['token'].split('.')[0] not in ls, 'token finns inte i localStorage')

            # --- B: logga in (exempelboken ersätts utan fråga) ---
            shell(B, 'webb'); B.wait_for_selector('[data-act=webLogin]')
            B.click('[data-act=webLogin]'); B.fill('#wEmail', EMAIL); B.fill('#wPw', 'fel lösenord'); B.click('[data-act=webLoginGo]')
            B.wait_for_function("() => /Fel e-postadress/.test(document.querySelector('#encErr')?.textContent || '')", timeout=20000)
            ok(True, 'B: fel lösenord ger felmeddelande')
            B.fill('#wPw', PW); B.click('[data-act=webLoginGo]')
            vanta_synk(B)
            ok('Testbok format 7' in B.inner_text('#bookName'), 'B: boken från webben är öppnad')

            # --- Ändringar på båda: nya projekt och tid ---
            shell(A, 'proj Alfaprojekt'); shell(B, 'proj Betaprojekt')
            shell(A, '2 strand ritade på A'); shell(B, '3 smeden möte på B')
            synka(A); synka(B); synka(A)
            pa, pb = projekt(A), projekt(B)
            ok('Alfaprojekt' in pa and 'Betaprojekt' in pa, f'A har båda projekten: {pa}')
            ok(pa == pb, 'A och B har samma projekt')
            ea, eb = bok(A)['bok']['logs'], bok(B)['bok']['logs']
            na = {k: len(v['events']) for k, v in ea.items()}; nb = {k: len(v['events']) for k, v in eb.items()}
            ok(na == nb and sum(na.values()) >= 229, f'händelser lika på båda: {na} / {nb}')
            notes = json.dumps(ea, ensure_ascii=False)
            ok('Ritade på A' in notes and 'Möte på B' in notes, 'tiden från båda enheterna finns')

            # --- Utan nät: ändringen väntar och skickas när nätet kommer tillbaka ---
            A.context.set_offline(True); shell(A, 'proj Offlineprojekt'); A.wait_for_timeout(6000)
            ok('Offline' in status(A), f'A utan nät: {status(A)}')
            A.context.set_offline(False); vanta_synk(A); synka(B)
            ok('Offlineprojekt' in projekt(B), 'ändringen från tiden utan nät kom fram till B')

            # --- Krock: samma budget ändras olika ---
            shell(A, 'budget strand 111000'); shell(B, 'budget strand 222000')
            synka(A)
            shell(B, 'synk'); B.wait_for_selector('text=Ändrat på två enheter', timeout=20000)
            txt = B.inner_text('#dlg')
            ok('Villa Strand' in txt, 'B: krockdialogen nämner projektet')
            B.click('[data-act=webCfTheirs]'); B.wait_for_timeout(300); synka(B); synka(A)
            bud = lambda pg: [x['budgetKr'] for x in bok(pg)['bok']['register']['projects'] if x['name'] == 'Villa Strand'][0]
            ok(bud(A) == 111000 and bud(B) == 111000, f'den andra enhetens budget valdes: {bud(A)} / {bud(B)}')

            # --- Tidigare versioner ---
            shell(A, 'webb'); A.click('[data-act=webHist]'); A.wait_for_selector('#whBox .snaps')
            n = A.locator('#whBox .snaps li').count()
            ok(n >= 3, f'tidigare versioner listas ({n})'); A.click('#dlg [data-act=closeDlg]')

            # --- Byt lösenord på A och logga ut B ---
            A.click('[data-act=encPw]'); A.fill('#ulPw', PW); A.fill('#encPw', PW2); A.fill('#encPw2', PW2); A.check('#wOthers')
            A.click('[data-act=encUnlockGo]'); A.wait_for_selector('#dlg', state='hidden', timeout=20000)
            shell(B, 'synk'); B.wait_for_function("() => /gått ut/.test(document.querySelector('#saveState .t')?.textContent || '')", timeout=20000)
            ok(True, 'B: inloggningen har gått ut efter lösenordsbytet')
            shell(B, 'proj Gammaprojekt')  # ändring medan B är utloggad
            shell(B, 'webb'); B.click('[data-act=webLogin]'); B.fill('#wPw', PW2); B.click('[data-act=webLoginGo]')
            vanta_synk(B); synka(A)
            ok('Gammaprojekt' in projekt(A), 'B:s ändring från utloggat läge kom fram efter ny inloggning')

            # --- Admin ---
            shell(A, 'webb admin'); A.fill('#wAdm', ADMIN); A.click('[data-act=webAdmGo]'); A.wait_for_selector('.adm-t')
            ok(EMAIL in A.inner_text('#admBox'), 'adminvyn visar kontot')
            A.click('[data-act=webAdmInvite]'); A.wait_for_selector('.inv-code')
            ok(True, 'adminvyn skapar en ny kod'); A.click('#dlg [data-act=closeDlg]')

            # --- B loggar ut och tar bort allt ---
            shell(B, 'webb'); B.click('[data-act=webOut]'); B.check('input[name=wOut][value=wipe]'); B.click('[data-act=webOutGo]')
            B.wait_for_load_state('load'); B.wait_for_selector('#saveState'); B.wait_for_timeout(800)
            ls = B.evaluate('() => Object.keys(localStorage).filter(k => k.startsWith("sisyfos.bok"))')
            ok('Exempel' in B.inner_text('#bookName'), f'B: allt borttaget, exempelboken visas ({ls})')

            # --- A raderar kontot ---
            shell(A, 'webb'); A.click('[data-act=webDel]'); A.fill('#wPw', PW2); A.click('[data-act=webDelGo]')
            A.wait_for_selector('[data-act=webReg]', timeout=20000)
            ok(bok(A)['web'] is None, 'A: kontot raderat, boken kvar')
            req = urllib.request.Request(url + 'api.php?a=accounts', headers={'X-Sisyfos-Admin': quote(ADMIN)})
            ok(json.loads(urllib.request.urlopen(req).read())['accounts'] == [], 'inga konton kvar på servern')
            br.close()
    finally:
        srv.terminate(); shutil.rmtree(tmp, ignore_errors=True)
    print('\n' + ('ALLT GRÖNT' if not fel else f'{len(fel)} FEL:\n  ' + '\n  '.join(fel)))
    sys.exit(1 if fel else 0)


if __name__ == '__main__':
    main()
