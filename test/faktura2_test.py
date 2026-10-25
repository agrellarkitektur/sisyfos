#!/usr/bin/env python3
"""
Sisyfos – test av fakturor, del 2 (0.15.1).

Öppnar exempelboken test/bocker/format-9.json (fakturorna 101, 102, kreditfaktura 103 och ett utkast) med
dagens datum 2026-12-10 och kontrollerar:
- betalstatus: 101 är förfallen, 102 krediterad, 103 kvittad; filtren Obetalda och Förfallna; Betald … med datum
  (framtida datum vägras), Ångra, panelens summor
- kund i ett annat EU-land (kräver momsnummer med utländsk landskod) → faktura med omvänd betalningsskyldighet,
  båda momsnumren och ingen betal-QR; kund utanför EU → ingen svensk moms
- SIE-exporten: PC8 (CP437), en verifikation per faktura och betalning, varje verifikation går jämnt ut, rätt
  konton (1510, 3001/2611, 3308, 3305, 1930), perioden och påminnelsen om förra exporten
- att de utfärdade fakturorna från 0.15.0 är oförändrade (kontrollsummorna)

Kör:  python3 -m http.server 8765 &  python3 test/faktura2_test.py
Kräver: pip install playwright && python3 -m playwright install chromium, samt pdftotext (poppler-utils)
"""
import hashlib, json, pathlib, re, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
ROOT = pathlib.Path(__file__).resolve().parent
APPV = re.search(r"APP_VERSION = '([^']+)'", (ROOT.parent / 'index.html').read_text(encoding='utf-8')).group(1)
fel = []
def kolla(ok, txt):
    print(('OK  ' if ok else 'FEL ') + txt)
    if not ok: fel.append(txt)
def pdftext(b):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(b); f.flush()
        return subprocess.run(['pdftotext', '-layout', f.name, '-'], capture_output=True, text=True).stdout
def canon(v):
    if isinstance(v, list): return '[' + ','.join(canon(x) for x in v) + ']'
    if isinstance(v, dict): return '{' + ','.join(json.dumps(k, ensure_ascii=False) + ':' + canon(v[k]) for k in sorted(v)) + '}'
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    return json.dumps(v, ensure_ascii=False)
def bok(pg): return json.loads(pg.evaluate("localStorage.getItem('sisyfos.bok')") or '{}')

start = json.loads((ROOT / 'bocker' / 'format-9.json').read_text())
fore = {x['id']: x for x in start['register']['invoices'] if x['status'] == 'issued'}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, service_workers='block', accept_downloads=True)
    ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(start))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.clock.install(time='2026-12-10T10:00:00')
    pg.goto(URL); pg.wait_for_timeout(1200)
    pg.click('.rail [data-page=rapporter]'); pg.wait_for_timeout(300)
    pg.click('[data-act=repTab][data-tab=invoices]'); pg.wait_for_timeout(300)
    t = pg.inner_text('.inv-t')
    kolla('förfallen 2026-12-03 (7 dagar)' in t, 'Faktura 101 är förfallen sedan 7 dagar')
    kolla('krediterad (103)' in t and 'kvittad mot 102' in t, 'Faktura 102 krediterad, 103 kvittad mot 102')
    pg.click('[data-act=invF][data-f=late]'); pg.wait_for_timeout(200)
    rader = pg.locator('.inv-t tbody tr').count()
    kolla(rader == 1 and '101' in pg.inner_text('.inv-t'), f'Filtret Förfallna visar bara 101 ({rader} rader)')
    pg.click('[data-act=invF][data-f=all]'); pg.wait_for_timeout(200)
    panel = pg.inner_text('.panel') if pg.is_visible('.panel') else ''
    kolla('Förfallet' in panel and '169' in panel, 'Panelen visar förfallet belopp')

    # Betald …
    pg.click('.inv-t button.btn[data-act=invPay]'); pg.wait_for_timeout(200)
    kolla(pg.is_visible('#ipDate'), 'Betald … öppnar dialogen')
    pg.fill('#ipDate', '2026-12-20'); pg.click('[data-act=invPayGo]'); pg.wait_for_timeout(100)
    kolla('framtiden' in pg.inner_text('#ipErr'), 'Ett framtida datum vägras')
    pg.fill('#ipDate', '2026-12-08'); pg.click('[data-act=invPayGo]'); pg.wait_for_timeout(300)
    B = bok(pg); P = B['register'].get('payments', {})
    id101 = next(x['id'] for x in B['register']['invoices'] if x.get('num') == '101')
    kolla(P.get(id101, {}).get('date') == '2026-12-08', f'Betalningen sparas i register.payments: {P}')
    kolla('betald 2026-12-08' in pg.inner_text('.inv-t'), 'Listan: betald 2026-12-08')
    pg.click('#toast [data-act=toastAct]'); pg.wait_for_timeout(300)
    kolla(id101 not in bok(pg)['register'].get('payments', {}), 'Ångra tar bort betalningen')
    pg.click('.inv-t button.btn[data-act=invPay]'); pg.wait_for_timeout(200)
    pg.fill('#ipDate', '2026-12-08'); pg.press('#ipDate', 'Enter'); pg.wait_for_timeout(300)
    kolla(id101 in bok(pg)['register'].get('payments', {}), 'Betald igen (Enter i datumfältet)')
    pg.click('[data-act=invF][data-f=unpaid]'); pg.wait_for_timeout(200)
    kolla('Inga obetalda' in pg.inner_text('#main'), 'Filtret Obetalda: inga kvar')
    pg.click('[data-act=invF][data-f=all]'); pg.wait_for_timeout(200)

    # Kund i ett annat EU-land och kund utanför EU
    def kund(namn, zon, moms):
        pg.click('.rail [data-page=kunder]'); pg.wait_for_timeout(300)
        pg.locator(f'.ccard:has-text("{namn}") h2').first.click(); pg.wait_for_timeout(300)
        pg.click('[data-act=custEdit]'); pg.wait_for_timeout(200)
        pg.select_option('#cuZone', zon); pg.fill('#cuVat', moms); pg.click('#cuForm button[type=submit]'); pg.wait_for_timeout(300)
    kund('Brf Smeden', 'eu', '')
    kolla('momsregistreringsnumret' in pg.inner_text('#cuErr'), 'EU-kund utan momsnummer vägras')
    pg.fill('#cuVat', 'SE769600000001'); pg.click('#cuForm button[type=submit]'); pg.wait_for_timeout(200)
    kolla('SE' in pg.inner_text('#cuErr'), 'EU-kund med svenskt momsnummer vägras')
    pg.fill('#cuVat', 'de 123456789'); pg.click('#cuForm button[type=submit]'); pg.wait_for_timeout(300)
    C = next(c for c in bok(pg)['register']['customers'] if c['name'] == 'Brf Smeden')
    kolla(C.get('zone') == 'eu' and C.get('vatNo') == 'DE123456789', f"Kunden sparad: {C.get('zone')} {C.get('vatNo')}")
    kund('Kommunens lokalförvaltning', 'world', '')
    C3 = next(c for c in bok(pg)['register']['customers'] if c['name'] == 'Kommunens lokalförvaltning')
    kolla(C3.get('zone') == 'world', 'Kund utanför EU sparad')

    def faktura(kundnamn):
        pg.click('.rail [data-page=rapporter]'); pg.wait_for_timeout(300)
        pg.click('[data-act=repTab][data-tab=invoices]'); pg.wait_for_timeout(200)
        pg.click('[data-act=invBlank]'); pg.wait_for_timeout(200)
        cid = pg.eval_on_selector('#ieCust', f"(s) => [...s.options].find(o => o.text === {json.dumps(kundnamn)}).value")
        pg.select_option('#ieCust', cid); pg.wait_for_timeout(300)
        rad = pg.locator('#ieRows .ie-row').first
        rad.locator('[data-l=text]').fill('Gestaltningsprogram'); rad.locator('[data-l=qty]').fill('10'); rad.locator('[data-l=unit]').fill('h'); rad.locator('[data-l=price]').fill('1000'); pg.wait_for_timeout(100)
        return pg.input_value('#ieMode'), pg.is_disabled('#ieVat'), pg.inner_text('#ieSum')
    mode, dis, summa = faktura('Brf Smeden')
    kolla(mode == 'rc' and dis and '10 000,00' in summa.replace('\xa0', ' ').split('Att betala')[1], f'EU-kunden ger omvänd betalningsskyldighet, 0 % moms: {mode}, {dis}')
    pg.click('[data-act=ieIssue]'); pg.wait_for_timeout(200)
    kolla('IBAN' in pg.inner_text('#dlg'), 'Varning: utländsk kund men inget IBAN')
    with pg.expect_download() as dl: pg.click('[data-act=ieIssueGo]')
    t = pdftext(pathlib.Path(dl.value.path()).read_bytes()); pg.wait_for_timeout(500)
    for s in ['104', 'Omvänd betalningsskyldighet', 'Momsreg.nr DE123456789', 'Momsreg.nr SE556677889901', 'Moms 0 %']:
        kolla(s in t, f'EU-fakturan innehåller ”{s}”')
    kolla('Skanna med bankappen' not in t and 'Undantag från momsplikt' not in t, 'EU-fakturan: ingen betal-QR, inte ”Undantag från momsplikt”')
    mode, dis, summa = faktura('Kommunens lokalförvaltning')
    kolla(mode == 'export' and dis, f'Kund utanför EU: ingen svensk moms ({mode})')
    with pg.expect_download() as dl: pg.click('[data-act=ieIssue]'); pg.wait_for_timeout(200); pg.click('[data-act=ieIssueGo]')
    t = pdftext(pathlib.Path(dl.value.path()).read_bytes()); pg.wait_for_timeout(500)
    kolla('105' in t and 'omsatt utanför Sverige' in t, 'Exportfakturan 105 har texten om omsättning utanför Sverige')
    B = bok(pg); nya = {x['num']: x for x in B['register']['invoices'] if x.get('num') in ('104', '105')}
    kolla(nya.get('104', {}).get('vatMode') == 'rc' and nya['104']['vatA'] == 0 and nya['104']['buyer'].get('zone') == 'eu' and nya.get('105', {}).get('vatMode') == 'export', 'Momsläget fryses på fakturan')
    # en svensk faktura betald, en EU-faktura betald
    pg.locator('.inv-t tr:has-text("104") button.btn[data-act=invPay]').click(); pg.wait_for_timeout(200)
    pg.fill('#ipDate', '2026-12-10'); pg.click('[data-act=invPayGo]'); pg.wait_for_timeout(300)

    # SIE
    pg.click('[data-act=invSie]'); pg.wait_for_timeout(300)
    kolla(pg.input_value('#sieFrom') == '2026-11-03' and pg.input_value('#sieTo') == '2026-12-10', f"SIE-perioden föreslås: {pg.input_value('#sieFrom')} – {pg.input_value('#sieTo')}")
    info = pg.inner_text('#sieInfo')
    kolla('5' in info and '2' in info and 'verifikationer' in info, 'Antalet verifikationer visas: ' + info)
    pg.click('.sie-acc summary'); pg.fill('#sie_ar', '15'); pg.wait_for_timeout(100); pg.click('[data-act=invSieGo]'); pg.wait_for_timeout(100)
    kolla('4–6 siffror' in pg.inner_text('#sieErr'), 'Ett felaktigt konto vägras')
    pg.fill('#sie_ar', '1510'); pg.fill('#sie_series', 'B')
    with pg.expect_download() as dl: pg.click('[data-act=invSieGo]')
    raw = pathlib.Path(dl.value.path()).read_bytes(); pg.wait_for_timeout(300)
    kolla(dl.value.suggested_filename.endswith('.si'), 'Filnamnet: ' + dl.value.suggested_filename)
    txt = raw.decode('cp437')
    kolla(b'\r\n' in raw and '#FORMAT PC8' in txt and '#SIETYP 4' in txt and f'#PROGRAM "Sisyfos" {APPV}' in txt, 'SIE-huvudet: PC8, typ 4, programmet')
    kolla('Brf Smeden' in txt and 'å'.encode('cp437') in raw or 'ö'.encode('cp437') in raw, 'Svenska tecken i CP437')
    vers = re.findall(r'#VER (\S+) "" (\d{8}) "([^"]*)"\r\n\{\r\n(.*?)\r\n\}\r\n', txt, re.S)
    kolla(len(vers) == 7, f'7 verifikationer (5 fakturor, 2 betalningar): {len(vers)}')
    jamn = True; konton = {}
    for ser, dat, text, body in vers:
        tr = re.findall(r'#TRANS (\d+) \{\} (-?\d+\.\d\d)', body)
        if abs(sum(float(a) for _, a in tr)) > 0.001: jamn = False; print('  ojämn:', text, tr)
        konton[text] = {k: float(a) for k, a in tr}
    kolla(jamn and all(s == '"B"' for s, *_ in vers), 'Varje verifikation går jämnt ut, serie B')
    f101 = next(v for k, v in konton.items() if k.startswith('Faktura 101'))
    kolla(f101.get('1510') == 169375.0 and f101.get('3001') == -135500.0 and f101.get('2611') == -33875.0, f'Faktura 101: 1510/3001/2611 {f101}')
    k103 = next(v for k, v in konton.items() if k.startswith('Kreditfaktura 103'))
    kolla(k103.get('1510') == -15000.0 and k103.get('3001') == 12000.0 and k103.get('2611') == 3000.0, f'Kreditfaktura 103 vänder tecknen: {k103}')
    kolla(next(v for k, v in konton.items() if k.startswith('Faktura 104')) == {'1510': 10000.0, '3308': -10000.0}, 'EU-faktura 104: 3308 utan moms')
    kolla(next(v for k, v in konton.items() if k.startswith('Faktura 105')) == {'1510': 10000.0, '3305': -10000.0}, 'Exportfaktura 105: 3305 utan moms')
    bet = [v for k, v in konton.items() if k.startswith('Betalning')]
    kolla(len(bet) == 2 and {'1930': 169375.0, '1510': -169375.0} in bet, f'Betalningarna: 1930/1510 {bet}')
    datum = [d for _, d, *_ in vers]
    kolla(datum == sorted(datum), 'Verifikationerna i datumordning')
    B = bok(pg); I = B['register']['book']['invoicing']
    kolla(I.get('sieLast', {}).get('to') == '2026-12-10' and I.get('sie') == {'series': 'B'}, f"Exporten noteras: {I.get('sieLast')}, {I.get('sie')}")
    pg.click('[data-act=invSie]'); pg.wait_for_timeout(300)
    kolla(pg.input_value('#sieFrom') == '2026-12-11' and pg.input_value('#sie_series') == 'B', 'Nästa export börjar dagen efter förra, serien är kvar')
    pg.fill('#sieFrom', '2026-12-01'); pg.wait_for_timeout(100)
    kolla('Förra exporten' in pg.inner_text('#sieInfo'), 'Påminnelse när perioden överlappar förra exporten')
    pg.click('#dlg [data-act=closeDlg]'); pg.wait_for_timeout(100)

    # Fakturorna från 0.15.0 är oförändrade
    efter = {x['id']: x for x in B['register']['invoices'] if x['id'] in fore}
    def h(x): return hashlib.sha256(canon({k: v for k, v in x.items() if k != 'hash'}).encode()).hexdigest()
    kolla(all(efter[i] == fore[i] and h(efter[i]) == fore[i]['hash'] for i in fore), 'De gamla fakturorna och kontrollsummorna är oförändrade')
    kolla(not js, 'Inga JavaScript-fel: ' + '; '.join(js[:3]))
    b.close()

print(f'\n{len(fel)} fel.' if fel else '\nAlla kontroller gick igenom.')
sys.exit(1 if fel else 0)
