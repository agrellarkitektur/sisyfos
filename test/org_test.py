#!/usr/bin/env python3
"""Testar organisationer (0.16.1) i tre webbläsare mot api.php på en lokal PHP-server.

A och A2 = admins två enheter, N = medarbetaren Anna. Provar: admin gör boken till en organisation med en kod från
serverns ägare, den andra enheten följer med (boken har flyttat), admin bjuder in Anna, Anna skapar konto med koden och
väntar, admin tar in henne (fingeravtrycket), Anna ser registret men inte fakturorna eller admins tid, Annas tid kommer
fram till admin, en ändring Anna inte får göra tas bort, admins ändring kommer fram till Anna, registrets nyckel är
densamma, filerna på servern är krypterade till rätt personer, admin tar bort Anna och boken krypteras om utan henne.

Kräver php, Playwright med Chromium (pip install playwright && playwright install chromium).
Kör: python3 test/org_test.py   (~1 min, körs i GitHub)
"""
from urllib.parse import quote
import glob, hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN = 'Testnyckel för admin – åäö € 2026'
EMAIL, PW = 'ca@byran.se', 'korrekt häst batteri'
EMAIL_N, PW_N = 'anna@byran.se', 'annas långa lösenord'
fel = []


def ok(cond, text):
    print(('OK  ' if cond else 'FEL ') + text, flush=True)
    if not cond:
        fel.append(text)


def ledig_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


BOK_JS = """() => new Promise((res, rej) => { const r = indexedDB.open('sisyfos'); r.onsuccess = () => { const db = r.result;
  const tx = db.transaction('kv'), g = tx.objectStore('kv').get('bok'), w = tx.objectStore('kv').get('web'), k = tx.objectStore('kv').get('keys');
  tx.oncomplete = () => { res({ bok: g.result ? JSON.parse(g.result.raw) : null, web: w.result || null, keys: k.result || null }); db.close(); }; }; r.onerror = () => rej(r.error); })"""


def bok(page):
    return page.evaluate(BOK_JS)


def shell(page, text):
    # startrutan (0.17.2) döljer smartshell tills man valt hur man börjar
    page.wait_for_function("() => document.querySelector('.wel-v') || document.getElementById('quickIn')?.offsetParent")
    if page.locator('.wel [data-act=welcomeSample]').count(): page.click('.wel [data-act=welcomeSample]'); page.wait_for_timeout(200)
    page.fill('#quickIn', text); page.wait_for_timeout(150); page.press('#quickIn', 'Enter'); page.wait_for_timeout(300)


def status(page):
    return page.inner_text('#saveState .t')


def vanta(page, rx, ms=25000):
    page.wait_for_function("(rx) => new RegExp(rx).test(document.querySelector('#saveState .t')?.textContent || '')", arg=rx, timeout=ms)


def synka(page, rx='Synkad'):
    shell(page, 'synk'); page.wait_for_timeout(300); vanta(page, rx)


def konto(page, kod, email, pw, ny=True):
    """Skapa konto: ny = krypteringen slås på samtidigt (återställningsnyckeln bekräftas)"""
    shell(page, 'webb'); page.wait_for_selector('[data-act=webReg]'); page.click('[data-act=webReg]')
    page.fill('#wInv', kod); page.fill('#wEmail', email)
    if ny:
        page.fill('#encPw', pw); page.fill('#encPw2', pw); page.click('[data-act=webRegGo]')
        page.wait_for_selector('.rk-key', timeout=20000)
        rk = page.inner_text('.rk-key').replace('\n', '').replace(' ', '')
        page.fill('#rkLast', rk[-4:]); page.click('[data-act=rkConfirm]')
    else:
        page.fill('#wPw', pw); page.click('[data-act=webRegGo]')


def logga_in(page, email, pw):
    shell(page, 'webb'); page.wait_for_selector('[data-act=webLogin]'); page.click('[data-act=webLogin]')
    page.fill('#wEmail', email); page.fill('#wPw', pw); page.click('[data-act=webLoginGo]')


def admkod(url, kind):
    req = urllib.request.Request(url + 'api.php?a=invite', data=json.dumps({'note': 'test', 'kind': kind}).encode(), headers={'X-Sisyfos-Admin': quote(ADMIN), 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req).read())['code']


TOAST_JS = """() => { window._t = []; new MutationObserver(() => { const t = document.querySelector('#toast'); if (t && !t.hidden) window._t.push(t.textContent); }).observe(document.querySelector('#toast'), { childList: true, subtree: true, attributes: true }); }"""


def toasts(page):
    t = page.evaluate('() => { const x = window._t || []; window._t = []; return x.join(" | "); }'); return t


def tills(fn, ms=25000):
    """Vänta tills fn() är sann (synken går i bakgrunden)"""
    t = time.time() + ms / 1000
    while time.time() < t:
        try:
            if fn(): return True
        except Exception: pass
        time.sleep(0.25)
    return False


def projekt(page):
    return sorted(p['name'] for p in bok(page)['bok']['register']['projects'])


def main():
    tmp = tempfile.mkdtemp(prefix='sisyfos-org-')
    web = os.path.join(tmp, 'pub', 'sisyfos'); os.makedirs(web)
    for f in ['index.html', 'sw.js', 'api.php', 'manifest.webmanifest', 'icon.svg', 'favicon-32.png']:
        shutil.copy(os.path.join(ROOT, f), web)
    with open(os.path.join(web, 'api-config.php'), 'w') as f:
        f.write("<?php return ['admin' => '%s'];\n" % hashlib.sha256(ADMIN.encode()).hexdigest())
    port = ledig_port()
    srv = subprocess.Popen(['php', '-S', f'127.0.0.1:{port}', '-t', os.path.join(tmp, 'pub')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f'http://127.0.0.1:{port}/sisyfos/'
    data = os.path.join(tmp, 'sisyfos-data')
    try:
        for _ in range(50):
            try: socket.create_connection(('127.0.0.1', port), 0.2).close(); break
            except OSError: time.sleep(0.1)
        kodA, kodO = admkod(url, 'account'), admkod(url, 'org')

        with sync_playwright() as p:
            br = p.chromium.launch()
            A, A2, N = (br.new_context(service_workers='block', accept_downloads=True).new_page() for _ in range(3))
            for namn, pg in (('A', A), ('A2', A2), ('N', N)):
                pg.on('pageerror', lambda e, n=namn: fel.append(f'sidfel {n}: {e}') or print('SIDFEL', n, e))
                pg.goto(url); pg.wait_for_selector('#saveState')
                pg.evaluate(TOAST_JS)

            # --- Admin: en egen bok på webben, på två enheter ---
            A.click('#brandBtn'); A.click('[data-act=importBook]')
            A.set_input_files('#imFile', os.path.join(ROOT, 'test', 'bocker', 'format-10.json')); A.wait_for_timeout(300)
            A.click('[data-act=doImport]'); A.wait_for_timeout(500)
            konto(A, kodA, EMAIL, PW); vanta(A, 'Synkad')
            logga_in(A2, EMAIL, PW); vanta(A2, 'Synkad')
            ok('Testbok format 10' in A2.inner_text('#bookName'), 'A2: admins egen bok från webben')

            # --- Admin gör boken till en organisation ---
            shell(A, 'webb'); A.wait_for_selector('[data-act=orgCreate]'); A.click('[data-act=orgCreate]')
            A.fill('#oCode', 'FEL00-00000'); A.click('[data-act=orgCreateGo]')
            A.wait_for_function("() => /gäller inte/.test(document.querySelector('#encErr')?.textContent || '')", timeout=20000)
            ok(True, 'fel kod för en organisation ger felmeddelande')
            A.fill('#oCode', kodO); A.click('[data-act=orgCreateGo]'); A.wait_for_selector('#dlg', state='hidden', timeout=20000)
            vanta(A, 'Synkad')
            w = bok(A)['web']
            ok(w['org'] and w['role'] == 'admin' and w['pid'] == 'pers1' and w['rev'] >= 1, f"A: organisationen skapad (version {w.get('rev')})")
            oid = w['org']
            parts = sorted(os.path.basename(f)[2:-5] for f in glob.glob(os.path.join(data, 'org', oid, 'p-*.json')))
            ok(parts == ['adm', 'card.pers1', 'log.pers1', 'reg'], f'delarna på servern: {parts}')
            regp = bok(A)['bok']['register']['people'][0]
            ok(regp['keys']['fp'] == bok(A)['keys']['fp'], 'registret har admins nyckel på den här enheten (inte den gamla ur den importerade boken)')

            # --- A2 följer med: boken har flyttat, och en ändring som inte var synkad kommer med ---
            shell(A2, 'proj Från andra enheten'); A2.wait_for_timeout(200)
            synka(A2)
            w2 = bok(A2)['web']
            ok(w2['org'] == oid and w2['role'] == 'admin', 'A2: följde med till organisationen')
            synka(A)
            ok('Från andra enheten' in projekt(A), 'A: projektet från A2 kom fram')

            # --- Admin bjuder in Anna ---
            shell(A, 'webb'); A.wait_for_selector('[data-act=orgInvite]'); A.click('[data-act=orgInvite]')
            A.fill('#oiName', 'Anna Berg'); A.click('[data-act=orgInviteGo]'); A.wait_for_selector('.org-code b.mono', timeout=20000)
            kodM = A.inner_text('.org-code b.mono')
            ok(len(kodM) == 11, f'A: kod till Anna {kodM}')
            A.click('#dlg [data-act=closeDlg]'); vanta(A, 'Synkad')
            anna = [x for x in bok(A)['bok']['register']['people'] if x['name'] == 'Anna Berg'][0]
            ok(anna['initials'] == 'AB' and not anna.get('keys'), 'Anna är tillagd i boken, utan nycklar')

            # --- Anna skapar konto med koden och väntar ---
            konto(N, kodM, EMAIL_N, PW_N)
            vanta(N, 'Väntar på att admin')
            wn = bok(N)
            ok(wn['web']['org'] == oid and wn['web']['pid'] == anna['id'] and wn['web']['role'] == 'member' and wn['keys']['pid'] == anna['id'], 'N: Anna är medarbetare och har nycklar för sin person')
            ok('Exempel' in N.inner_text('#bookName'), 'N: exempelboken visas medan hon väntar')

            # --- Admin tar in Anna ---
            synka(A)
            shell(A, 'webb'); A.wait_for_selector('[data-act=orgApprove]', timeout=20000)
            A.click('[data-act=orgApprove]'); A.wait_for_selector('[data-act=orgApproveGo]')
            fpN = wn['keys']['fp'].upper()
            ok(fpN[:4] in A.inner_text('#dlg'), 'A: dialogen visar Annas fingeravtryck')
            A.click('[data-act=orgApproveGo]')
            f = os.path.join(data, 'org', oid)
            tills(lambda: anna['id'] in json.load(open(os.path.join(f, 'p-reg.json')))['to'] and os.path.exists(os.path.join(f, f"p-card.{anna['id']}.json")) and anna['id'] in json.load(open(os.path.join(f, f"p-card.{anna['id']}.json")))['to'])
            vanta(A, 'Synkad')
            reg = json.load(open(os.path.join(f, 'p-reg.json'))); adm = json.load(open(os.path.join(f, 'p-adm.json')))
            card = json.load(open(os.path.join(f, f"p-card.{anna['id']}.json"))); logA = json.load(open(os.path.join(f, 'p-log.pers1.json')))
            ok(sorted(reg['to']) == sorted(['pers1', anna['id']]) and sorted(card['to']) == sorted(['pers1', anna['id']]), 'registret och Annas kort är krypterade till Anna och admin')
            ok(list(adm['to']) == ['pers1'] and list(logA['to']) == ['pers1'], 'fakturorna och admins tid bara till admin')

            # --- Anna ser boken ---
            synka(N)
            ok('Testbok format 10' in N.inner_text('#bookName'), 'N: organisationens bok är öppnad')
            bn = bok(N)
            ok(bn['bok']['session']['personId'] == anna['id'], 'N: inloggad som Anna')
            ok(bn['bok']['register']['invoices'] == [] and not any(bn['bok']['logs'].get('pers1', {}).get('events', [])), 'N: inga fakturor och ingen tid från admin')
            ok(len(bn['bok']['register']['projects']) == len(bok(A)['bok']['register']['projects']), 'N: samma projekt som admin')
            ok(bn['web']['pin'] == bok(A)['keys']['fp'], 'N: registrets nyckel är fäst på enheten (admins)')
            shell(N, 'rapp'); N.wait_for_timeout(300)
            ok(N.locator('[data-act=repTab][data-tab=invoices]').count() == 0, 'N: ingen flik för fakturor')

            # --- Annas tid kommer fram till admin ---
            shell(N, '2 strand ritade fasad'); synka(N)
            synka(A); synka(A2)
            for namn, pg in (('A', A), ('A2', A2)):
                ev = bok(pg)['bok']['logs'].get(anna['id'], {}).get('events', [])
                ok(any('Ritade fasad' in json.dumps(e, ensure_ascii=False) for e in ev), f'{namn}: Annas tid finns hos admin')
            logN = json.load(open(os.path.join(f, f"p-log.{anna['id']}.json")))
            ok(logN['by'] == anna['id'], 'Annas tidlogg är skriven av Anna')

            # --- En ändring Anna inte får göra tas bort ---
            shell(N, 'proj Annas eget projekt'); N.wait_for_timeout(200)
            synka(N); N.wait_for_timeout(500)
            ok('Annas eget projekt' not in projekt(N), 'N: projektet hon skapade togs bort (bara admin ändrar registret)')
            synka(A)
            ok('Annas eget projekt' not in projekt(A), 'A: projektet kom aldrig fram')

            # --- Admins ändring kommer fram till Anna ---
            toasts(N)
            shell(A, 'budget strand 333000'); synka(A); synka(N)
            t = toasts(N)
            ok('uppdaterades' in t and 'togs bort' not in t, f'N: boken uppdaterades, inget togs bort ({t})')
            bud = [x['budgetKr'] for x in bok(N)['bok']['register']['projects'] if x['name'] == 'Villa Strand'][0]
            ok(bud == 333000, f'N: admins nya budget kom fram ({bud})')

            # --- Inget skickas när inget har ändrats ---
            synka(A); synka(N); synka(A2)
            r0 = bok(A)['web']['rev']
            synka(A); synka(N); synka(A2); synka(A)
            ok(bok(A)['web']['rev'] == r0 == bok(N)['web']['rev'] == bok(A2)['web']['rev'], f"ingen ny version utan ändringar ({r0}, {bok(N)['web']['rev']}, {bok(A2)['web']['rev']})")
            t = toasts(A) + toasts(N) + toasts(A2)
            ok('togs bort' not in t and 'Ändrat på två' not in A.inner_text('body'), 'inga falska besked om borttagna ändringar eller krockar')

            # --- Anna på en ny enhet: samma nyckel ---
            N2 = br.new_context(service_workers='block').new_page(); N2.goto(url); N2.wait_for_selector('#saveState')
            logga_in(N2, EMAIL_N, PW_N)
            tills(lambda: bok(N2)['bok']['session']['personId'] == anna['id']); vanta(N2, 'Synkad')
            ok(bok(N2)['keys']['fp'] == wn['keys']['fp'] and 'Ritade fasad' in json.dumps(bok(N2)['bok']['logs'], ensure_ascii=False), 'N2: Annas andra enhet har samma nyckel och hennes tid')
            N2.context.close()

            # --- Admin tar bort Anna ---
            shell(A, 'webb'); A.wait_for_selector('[data-act=orgRemove]'); A.click('[data-act=orgRemove]'); A.click('[data-act=orgRemoveGo]')
            vanta(A, 'Synkad'); synka(A)
            reg = json.load(open(os.path.join(f, 'p-reg.json')))
            ok(list(reg['to']) == ['pers1'], 'registret är omkrypterat utan Anna')
            ok(any('Ritade fasad' in json.dumps(e, ensure_ascii=False) for e in bok(A)['bok']['logs'].get(anna['id'], {}).get('events', [])), 'A: Annas tid finns kvar i boken')
            shell(N, 'synk'); vanta(N, 'inte med i organisationen')
            ok(True, 'N: Anna är inte med i organisationen längre')

            # inget i klartext på servern
            alla = ''.join(open(x, errors='ignore').read() for x in glob.glob(os.path.join(data, 'org', oid, '*')))
            ok('Ritade fasad' not in alla and 'Villa Strand' not in alla, 'inget innehåll i klartext på servern')
            br.close()
    finally:
        srv.terminate(); shutil.rmtree(tmp, ignore_errors=True)
    print('\n' + ('ALLT GRÖNT' if not fel else f'{len(fel)} FEL:\n  ' + '\n  '.join(fel)))
    sys.exit(1 if fel else 0)


if __name__ == '__main__':
    main()
