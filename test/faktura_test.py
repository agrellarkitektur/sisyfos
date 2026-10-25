#!/usr/bin/env python3
"""
Sisyfos – test av fakturor (0.15.0).

Exempelboken i en tom webbläsare: slå på fakturor (villkoren måste godkännas), skapa en faktura ur
fakturaunderlaget, utfärda den (nummer, låst tid, PDF), kontrollera PDF:en, kreditera den (kreditfaktura,
tiden låses upp), ladda ner arkivet (zip med PDF:er, CSV och JSON) och kontrollera att varningen visas när
man häver hanterad tid som ingår i en faktura. Kontrollerar också OCR-numren och att samma faktura ger
samma PDF två gånger.

Kör:  python3 -m http.server 8765 &  python3 test/faktura_test.py
Kräver: pip install playwright && python3 -m playwright install chromium, samt pdftotext (poppler-utils)
"""
import io, json, re, subprocess, sys, tempfile, zipfile, pathlib
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
fel = []
def kolla(ok, txt):
    print(('OK  ' if ok else 'FEL ') + txt)
    if not ok: fel.append(txt)
def pdftext(b):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(b); f.flush()
        return subprocess.run(['pdftotext', '-layout', f.name, '-'], capture_output=True, text=True).stdout
def bok(pg): return json.loads(pg.evaluate("localStorage.getItem('sisyfos.bok')") or '{}')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 860}, service_workers='block', accept_downloads=True)
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.clock.install(time='2026-11-04T10:00:00')
    pg.goto(URL); pg.wait_for_timeout(800)
    pg.click('#brandBtn'); pg.click('[data-act=askSample]'); pg.wait_for_timeout(300)
    pg.locator('button:has-text("Ladda exempel")').last.click(); pg.wait_for_timeout(600)

    # OCR-numren (Luhn) – samma som bankgirots exempel 1234567 → 12345674
    pg.click('.rail [data-page=installningar]'); pg.wait_for_timeout(300)
    kolla(pg.is_visible('[data-act=invOnDlg]'), 'Inställningar → Fakturor: knappen Slå på fakturor')
    pg.click('[data-act=invOnDlg]'); pg.wait_for_timeout(200)
    pg.click('[data-act=invOnGo]'); pg.wait_for_timeout(100)
    kolla('läst' in pg.inner_text('#ioErr'), 'Villkoren måste godkännas: ' + pg.inner_text('#ioErr'))
    pg.check('#ioOk'); pg.fill('#ioVat', 'SE556677889901'); pg.fill('#ioBg', '123-4567'); pg.fill('#ioStart', '41')
    pg.click('[data-act=invOnGo]'); pg.wait_for_timeout(400)
    B = bok(pg); I = B['register']['book'].get('invoicing', {})
    kolla(I.get('on') and I.get('accepted') and I.get('bg') == '123-4567' and I.get('start') == 41, f"Påslaget sparat: {I.get('on')}, bg {I.get('bg')}, start {I.get('start')}")
    pg.select_option('#iv_ocr', 'len'); pg.wait_for_timeout(200)
    kolla('OCR 4143' in pg.inner_text('#ivOcrR'), 'Nästa faktura (41) får OCR 4143: ' + pg.inner_text('#ivOcrR'))
    pg.fill('#ivOcrT', '12345682'); pg.wait_for_timeout(100)
    kolla(pg.inner_text('#ivOcrR') == 'Numret är rätt uppbyggt', 'OCR med längdsiffra 12345682: ' + pg.inner_text('#ivOcrR'))
    pg.fill('#ivOcrT', '12345683'); pg.wait_for_timeout(100)
    kolla('stämmer inte' in pg.inner_text('#ivOcrR'), 'Fel kontrollsiffra upptäcks')

    # Fakturaunderlag → Skapa faktura
    pg.click('.rail [data-page=rapporter]'); pg.wait_for_timeout(300)
    pg.click('[data-act=repTab][data-tab=invoice]'); pg.wait_for_timeout(300)
    opts = pg.eval_on_selector_all('#ivS option', 'o => o.map(x => x.value)')
    kund = next(v for v in opts if v.startswith('c:'))
    pg.select_option('#ivS', kund); pg.wait_for_timeout(300)
    pg.select_option('#ivS', kund); pg.wait_for_timeout(200)
    if pg.is_disabled('[data-act=invNew]'):  # ingen öppen tid för kunden – ta första som har
        for v in opts:
            if v.startswith('c:') or v.startswith('p:'):
                pg.select_option('#ivS', v); pg.wait_for_timeout(200)
                if not pg.is_disabled('[data-act=invNew]'): break
    pg.click('[data-act=invNew]'); pg.wait_for_timeout(300)
    kolla(pg.is_visible('#ieForm'), 'Utkastet öppnas i redigeringen')
    sum1 = pg.inner_text('#ieSum')
    pg.click('[data-act=ieAdd]'); pg.wait_for_timeout(100)
    if len(sys.argv) > 2: pg.screenshot(path=str(pathlib.Path(sys.argv[2], 'utkast.png')))
    rad = pg.locator('#ieRows .ie-row').last
    rad.locator('[data-l=text]').fill('Utlägg, kopior'); rad.locator('[data-l=qty]').fill('2'); rad.locator('[data-l=unit]').fill('st'); rad.locator('[data-l=price]').fill('125,50'); pg.wait_for_timeout(100)
    kolla('251,00' in rad.inner_text(), 'Egen rad räknas: ' + rad.locator('.ie-amt').inner_text())
    kolla(pg.inner_text('#ieSum') != sum1, 'Summan uppdateras när man skriver')
    pg.click('[data-act=ieIssue]'); pg.wait_for_timeout(200)
    kolla('nummer 41' in pg.inner_text('#dlg'), 'Bekräftelsen visar nummer 41')
    with pg.expect_download() as dl: pg.click('[data-act=ieIssueGo]')
    pdf1 = pathlib.Path(dl.value.path()).read_bytes(); pg.wait_for_timeout(500)
    if len(sys.argv) > 2: pathlib.Path(sys.argv[2], 'faktura.pdf').write_bytes(pdf1); pg.screenshot(path=str(pathlib.Path(sys.argv[2], 'lista.png')), full_page=True)
    t = pdftext(pdf1)
    kolla(dl.value.suggested_filename.startswith('Faktura 41 '), 'PDF:ens namn: ' + dl.value.suggested_filename)
    for s in ['Faktura', 'Fakturanummer', '41', 'Förfallodag', 'OCR-nummer', '4143', 'Att betala', 'Bankgiro', '123-4567', 'Momsreg.nr SE556677889901', 'Utlägg, kopior', 'Betalningsvillkor: 30 dagar netto', 'Kontroll ']:
        kolla(s in t, f'PDF:en innehåller ”{s}”')
    B = bok(pg); F = [x for x in B['register']['invoices'] if x['status'] == 'issued']
    kolla(len(F) == 1 and F[0]['num'] == '41' and F[0]['ocr'] == '4143' and len(F[0].get('hash') or '') == 64, f"Utfärdad i boken: {[(x['num'], x['ocr']) for x in F]}")
    f0 = F[0]; sp = f0['spans']
    hd = B['register']['handled']
    kolla(sp and all(any(r['from'] <= s['from'] and r['to'] >= s['to'] for r in hd.get(s['pid'], [])) for s in sp), f'Tiden i fakturan är hanterad: {sp}')
    kolla(f0['pay'] == round(f0['net'] + f0['vatA'] + f0.get('round', 0), 2) and abs(f0['vatA'] - round(f0['net'] * 0.25, 2)) < 0.006, f"Beloppen: {f0['net']} + {f0['vatA']} = {f0['pay']}")

    # Samma faktura ger samma PDF
    pg.click('[data-act=repTab][data-tab=invoices]'); pg.wait_for_timeout(300)
    kolla('41' in pg.inner_text('.inv-t'), 'Listan visar faktura 41')
    with pg.expect_download() as dl: pg.click('[data-act=invPdf]')
    kolla(pathlib.Path(dl.value.path()).read_bytes() == pdf1, 'Samma faktura ger identisk PDF')

    # Häva hanterad tid som ingår i fakturan → varning
    pnamn = next(x['name'] for x in B['register']['projects'] if x['id'] == sp[0]['pid'])
    pg.fill('#quickIn', f'häv {sp[0]["from"][8:10].lstrip("0")}/{sp[0]["from"][5:7].lstrip("0")}-{sp[0]["to"][8:10].lstrip("0")}/{sp[0]["to"][5:7].lstrip("0")} "{pnamn}"'); pg.wait_for_timeout(200)
    pg.press('#quickIn', 'Enter'); pg.wait_for_timeout(300)
    kolla(pg.is_visible('#dlg') and 'ingår i' in pg.inner_text('#dlg'), 'Häv i fakturerad period varnar: ' + (pg.inner_text('#dlg h2') if pg.is_visible('#dlg') else pg.inner_text('#quickHint')))
    if pg.is_visible('#dlg'): pg.click('#dlg [data-act=closeDlg]'); pg.wait_for_timeout(100)

    # Kreditera
    pg.click('[data-act=invCredit]'); pg.wait_for_timeout(200)
    kolla(pg.is_checked('#crUnlock'), 'Kreditera: lås upp tiden är förvalt')
    with pg.expect_download() as dl: pg.click('[data-act=invCreditGo]')
    pdf2 = pathlib.Path(dl.value.path()).read_bytes(); t2 = pdftext(pdf2); pg.wait_for_timeout(500)
    if len(sys.argv) > 2: pathlib.Path(sys.argv[2], 'kredit.pdf').write_bytes(pdf2); pg.screenshot(path=str(pathlib.Path(sys.argv[2], 'lista.png')), full_page=True)
    for s in ['Kreditfaktura', 'Krediterar faktura', '41', '42', 'Att få tillbaka']:
        kolla(s in t2, f'Kreditfakturan innehåller ”{s}”')
    B = bok(pg); cr = [x for x in B['register']['invoices'] if x['kind'] == 'credit']
    kolla(len(cr) == 1 and cr[0]['num'] == '42' and cr[0]['credits'] == f0['id'] and cr[0]['pay'] == -f0['pay'], f"Kreditfaktura 42 = -{f0['pay']}: {[(x['num'], x['pay']) for x in cr]}")
    hd = B['register']['handled']
    kolla(not any(r['from'] <= sp[0]['from'] and r['to'] >= sp[0]['to'] for r in hd.get(sp[0]['pid'], [])), 'Tiden är upplåst efter krediteringen')
    kolla('krediterad (42)' in pg.inner_text('.inv-t').lower() and not pg.is_visible('[data-act=invCredit]'), 'Listan: krediterad, ingen kreditera-knapp')

    # Arkivet
    with pg.expect_download() as dl: pg.click('[data-act=invArchive]')
    z = zipfile.ZipFile(io.BytesIO(pathlib.Path(dl.value.path()).read_bytes()))
    names = z.namelist(); kolla(z.testzip() is None and len(names) == 4, f'Arkivet (zip) är helt: {names}')
    j = json.loads(z.read([n for n in names if n.endswith('.json')][0]))
    kolla(len(j['invoices']) == 2 and z.read([n for n in names if n.startswith('Faktura 41')][0]) == pdf1, 'Arkivets JSON har två fakturor och samma PDF')
    csv = z.read([n for n in names if n.endswith('.csv')][0]).decode('utf-8-sig')
    kolla('Kreditfaktura' in csv and csv.count('\r\n') == 3, 'Arkivets CSV har två rader')

    # Utkast: ta bort
    pg.click('[data-act=invBlank]'); pg.wait_for_timeout(200)
    pg.click('[data-act=ieDel]'); pg.wait_for_timeout(200); pg.click('#dlg .btn.primary'); pg.wait_for_timeout(500)
    kolla(len([x for x in bok(pg)['register']['invoices'] if x['status'] == 'draft']) == 0, 'Utkast kan tas bort')

    # Telefon: redigeringen ryms
    pg.set_viewport_size({'width': 390, 'height': 844}); pg.wait_for_timeout(200)
    pg.click('[data-act=invBlank]'); pg.wait_for_timeout(300)
    w = pg.evaluate("Math.max(...[...document.querySelectorAll('#dlg *')].map(e => e.getBoundingClientRect().right))")
    kolla(w <= 391, f'Redigeringen ryms på 390 px (högst {w:.0f})')
    if len(sys.argv) > 2: pg.screenshot(path=str(pathlib.Path(sys.argv[2], 'telefon.png')))
    kolla(not js, f'Inga JavaScript-fel {js}')

    # Guiden för ny bok: fakturor som tillägg (steg 4 av 5)
    ctx = b.new_context(viewport={'width': 1280, 'height': 860}, service_workers='block')
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(800)
    pg.click('#brandBtn'); pg.click('[data-act=askNew]'); pg.wait_for_timeout(300)
    pg.fill('#w_company', 'Testbolaget AB'); pg.fill('#w_orgNr', '556677-8899'); pg.fill('#w_address', 'Gatan 1\n123 45 Orten')
    for _ in range(3): pg.click('#wzForm button[type=submit]'); pg.wait_for_timeout(200)
    kolla('Ska Sisyfos göra fakturor?' in pg.inner_text('#dlg'), 'Guiden: steget Fakturor')
    kolla(not pg.is_visible('#w_ivBg'), 'Guiden: uppgifterna är dolda tills Ja väljs')
    pg.check('input[name=w_inv][value=yes]'); pg.wait_for_timeout(150)
    kolla(pg.input_value('#w_ivVat') == 'SE556677889901', 'Guiden föreslår momsnumret ur org.nr: ' + pg.input_value('#w_ivVat'))
    pg.fill('#w_ivBg', '5050-1055'); pg.click('#wzForm button[type=submit]'); pg.wait_for_timeout(200)
    kolla('villkoren' in pg.inner_text('#wzErr'), 'Guiden kräver att villkoren godkänns: ' + pg.inner_text('#wzErr'))
    pg.check('#w_ivOk'); pg.click('#wzForm button[type=submit]'); pg.wait_for_timeout(200)
    kolla('5050-1055' in pg.inner_text('#dlg'), 'Sammanfattningen visar fakturor')
    pg.click('#wzForm button[type=submit]'); pg.wait_for_timeout(600)
    I = bok(pg)['register']['book'].get('invoicing', {})
    kolla(I.get('on') and I.get('accepted') and I.get('bg') == '5050-1055' and I.get('vatNo') == 'SE556677889901', f'Ny bok med fakturor påslagna: {I.get("bg")}, {I.get("vatNo")}')
    kolla(not js, f'Guiden: inga JavaScript-fel {js}')
    b.close()

print('\n' + ('Alla kontroller gick igenom.' if not fel else f'{len(fel)} fel.'))
sys.exit(1 if fel else 0)
