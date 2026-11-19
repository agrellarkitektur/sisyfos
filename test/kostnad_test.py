#!/usr/bin/env python3
"""
Sisyfos 0.20.0 – kostnader på dagboken (filformat 12).

Kontrollerar i en riktig webbläsare att
  – exempelboken format 12 öppnas med sina kostnader (en borttagen räknas inte),
  – rutan i veckovyn visar att dagen har en kostnad, och kostnaden står i smartmenyn och dagvyn,
  – dialogen räknar antal × à-pris och påslag, sparar, ändrar, tar bort och Ångra lägger tillbaka,
  – en låst dag (hanterad period) inte tar emot en kostnad,
  – smartshell: kost strand tor kartunderlag 1500, antal × à-pris och påslag,
  – fakturaunderlaget (skärm, PDF, CSV, utan belopp) och projektdagboken har kostnaderna som egna rader,
    hanterade kostnader kommer inte med i underlaget, och summan räknar in dem,
  – fakturautkastet får en rad per kostnad och hanteringen låser kostnaderna,
  – kostnaderna påverkar inte budgeten eller timmarna och finns kvar efter omladdning.

Kör:  python3 -m http.server 8765 &  python3 test/kostnad_test.py
"""
import json, pathlib, sys, datetime, subprocess, tempfile
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
URL = (sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html') + '?test'
BOK = json.loads((ROT / 'test' / 'bocker' / 'format-12.json').read_text(encoding='utf-8'))
UT = ROT / 'test' / '_bilder'
fel = 0
def ev(page, fn, arg=None):
    return page.evaluate("([f, a]) => { with (window.SISYFOS) { return eval('(' + f + ')')(a); } }", [fn, arg])
def ok(cond, text):
    global fel
    print(('OK  ' if cond else 'FEL ') + text); fel += not cond

def pdftext(pg, js):
    b = bytes(ev(pg, js))
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f: f.write(b); p = f.name
    return subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout

def akt(pg, act, **data):
    attrs = ' '.join(f'data-{k}="{v}"' for k, v in data.items())
    pg.evaluate("(h) => { document.getElementById('tb')?.remove(); document.body.insertAdjacentHTML('beforeend', h); document.getElementById('tb').click(); }", f'<button id="tb" data-act="{act}" {attrs}>x</button>')
    pg.wait_for_timeout(300)

def shell(pg, txt):
    pg.fill('#quickIn', txt); pg.wait_for_timeout(250)
    return pg.inner_text('#quickHint')

def toast(pg):
    return pg.evaluate("() => document.getElementById('toast')?.innerText || ''")

def ango(pg):
    pg.click('#toast [data-act=toastAct]'); pg.wait_for_timeout(300)

KOSTER = "() => [...COST.values()].filter(c => !c.deleted).map(c => ({ id: c.id, text: c.text, date: c.date, amount: c.amount, qty: c.qty ?? null, unit: c.unit ?? null, price: c.price ?? null, markup: c.markup, total: cTot(c), task: c.taskId }))"
def kost(pg, text):
    return next((c for c in ev(pg, KOSTER) if c['text'] == text), None)

with sync_playwright() as p:
    b = p.chromium.launch()
    UT.mkdir(exist_ok=True)
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, service_workers='block', accept_downloads=True)
    ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(BOK))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.clock.install(time=datetime.datetime(2026, 11, 18, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(1200)

    # ── Boken och datamodellen
    ok(ev(pg, "() => [S.version, FORMAT_VERSION]") == [12, 12], 'format 12')
    ks = ev(pg, KOSTER)
    ok(sorted(c['text'] for c in ks) == ['Nybyggnadskarta', 'Plottning A1', 'Underkonsult VVS'], f'tre kostnader, den borttagna räknas inte ({[c["text"] for c in ks]})')
    ok(abs(kost(pg, 'Underkonsult VVS')['total'] - 13200) < .01, 'påslag 10 % på 12 000 kr = 13 200 kr')
    bud0 = ev(pg, "() => budgetPct(S.register.projects.find(p => p.id === 'proj1'))")
    h0 = ev(pg, "() => live().reduce((s, e) => s + e.hours, 0)")

    # ── Veckovyn: rutan visar kostnaden
    ev(pg, "() => { st.page = 'tid'; st.view = 'week'; st.week = '2026-10-19'; render(); }"); pg.wait_for_timeout(300)
    c20 = pg.locator('[data-cellbox="proj1~upg1|2026-10-20"]')
    ok('ko' in (c20.get_attribute('class') or '') and c20.locator('.kom').count() == 1, 'rutan 20 okt har märket kr')
    ok('kostnad' in (c20.locator('input').get_attribute('aria-label') or ''), 'rutans etikett nämner kostnaden')
    ok(pg.locator('[data-cellbox="proj1~upg1|2026-10-21"] .kom').count() == 0, 'den borttagna kostnaden ger inget märke')

    # ── Dialogen: ny kostnad med antal × à-pris och påslag
    ev(pg, "() => { st.week = '2026-11-16'; render(); }"); pg.wait_for_timeout(300)
    akt(pg, 'costAdd', key='proj1~upg1|2026-11-17')
    ok(pg.locator('#dlg:not([hidden]) #koForm').count() == 1, 'dialogen Ny kostnad öppnas')
    pg.fill('#koT', 'ritningskopior'); pg.fill('#koQ', '3'); pg.fill('#koU', 'st'); pg.fill('#koP', '120'); pg.wait_for_timeout(100)
    ok(pg.input_value('#koA') == '360', f'antal × à-pris räknar fram beloppet ({pg.input_value("#koA")})')
    pg.fill('#koM', '10'); pg.wait_for_timeout(100)
    ok('396' in pg.inner_text('#koSum'), f'påslaget visas ({pg.inner_text("#koSum")})')
    pg.screenshot(path=str(UT / 'kostnad-dialog-1280.png'))
    pg.click('#koForm button[type=submit]'); pg.wait_for_timeout(300)
    k = kost(pg, 'Ritningskopior')
    ok(k and k['amount'] == 360 and k['qty'] == 3 and k['unit'] == 'st' and k['price'] == 120 and k['markup'] == 10 and abs(k['total'] - 396) < .01, f'sparad med stor bokstav, 3 st × 120 kr + 10 % ({k})')
    ok('Ritningskopior' in toast(pg), 'besked med Ångra')
    ango(pg); ok(kost(pg, 'Ritningskopior') is None, 'Ångra tar bort den nya kostnaden')
    akt(pg, 'costAdd', key='proj1~upg1|2026-11-17')
    pg.fill('#koT', 'Ritningskopior'); pg.fill('#koQ', '3'); pg.fill('#koU', 'st'); pg.fill('#koP', '120'); pg.click('#koForm button[type=submit]'); pg.wait_for_timeout(300)
    k = kost(pg, 'Ritningskopior'); ok(k and k['total'] == 360, 'ny igen, utan påslag')
    ok(pg.locator('[data-cellbox="proj1~upg1|2026-11-17"] .kom').count() == 1, 'rutan 17 nov får märket')
    # Ändra: beloppet direkt (antal och à-pris tömda)
    akt(pg, 'costEdit', id=k['id'])
    ok(pg.input_value('#koQ') == '3', 'Ändra fyller i dialogen')
    pg.fill('#koQ', ''); pg.fill('#koP', ''); pg.fill('#koA', '450'); pg.click('#koForm button[type=submit]'); pg.wait_for_timeout(300)
    k2 = kost(pg, 'Ritningskopior'); ok(k2 and k2['id'] == k['id'] and k2['amount'] == 450 and k2['qty'] is None, f'ändrad till 450 kr utan antal ({k2})')
    ango(pg); k3 = kost(pg, 'Ritningskopior'); ok(k3 and k3['amount'] == 360 and k3['qty'] == 3, 'Ångra lägger tillbaka 3 st × 120 kr')
    # Ta bort
    akt(pg, 'costEdit', id=k['id']); pg.click('#koForm [data-act=costDel]'); pg.wait_for_timeout(300)
    ok(kost(pg, 'Ritningskopior') is None, 'Ta bort')
    ango(pg); ok(kost(pg, 'Ritningskopior') is not None, 'Ångra lägger tillbaka den borttagna')
    # Utan beskrivning eller belopp
    akt(pg, 'costAdd', key='proj1~upg1|2026-11-17'); pg.fill('#koA', '100'); pg.click('#koForm button[type=submit]'); pg.wait_for_timeout(250)
    ok(pg.locator('#dlg:not([hidden]) #koForm').count() == 1 and 'gäller' in toast(pg), 'utan beskrivning sparas inget')
    pg.fill('#koT', 'Tom'); pg.fill('#koA', ''); pg.click('#koForm button[type=submit]'); pg.wait_for_timeout(250)
    ok(kost(pg, 'Tom') is None and 'belopp' in toast(pg), 'utan belopp sparas inget')
    akt(pg, 'closeDlg')

    # ── Smartmenyn och dagvyn
    pg.locator('[data-cellbox="proj1~upg1|2026-11-17"] input').click(); pg.wait_for_timeout(200)
    ev(pg, "() => { st.view = 'day'; st.day = '2026-11-17'; render(); }"); pg.wait_for_timeout(300)
    ok(pg.locator('.dcards .ko-i:has-text("Ritningskopior")').count() == 1, 'dagvyn visar kostnaden')
    ev(pg, "() => { st.view = 'week'; render(); }"); pg.wait_for_timeout(300)

    # ── Låst: hanterad period i september
    akt(pg, 'costAdd', key='proj1~upg1|2026-09-10')
    ok(pg.locator('#dlg:not([hidden]) #koForm').count() == 0 and 'hanterad' in toast(pg), 'hanterad dag tar inte emot en kostnad')
    ok(ev(pg, "() => costRemove('kost1')") is None, 'en hanterad kostnad går inte att ta bort')

    # ── Smartshell
    hint = shell(pg, 'kost strand tor kartunderlag 1500')
    ok('Enter lägger kostnaden' in hint and 'Kartunderlag' in hint and 'torsdag' in hint, f'förhandsraden ({hint})')
    pg.press('#quickIn', 'Enter'); pg.wait_for_timeout(300)
    k = kost(pg, 'Kartunderlag'); ok(k and k['date'] == '2026-11-19' and k['amount'] == 1500 and k['task'] == 'upg1', f'kost strand tor … 1500 ({k})')
    shell(pg, 'kost strand plottning 6 st à 85 15 %'); pg.press('#quickIn', 'Enter'); pg.wait_for_timeout(300)
    k = kost(pg, 'Plottning')
    ok(k and k['qty'] == 6 and k['unit'] == 'st' and k['price'] == 85 and k['amount'] == 510 and k['markup'] == 15 and k['date'] == '2026-11-17', f'antal × à-pris och påslag, på den markerade dagen ({k})')
    ok('Skriv' in shell(pg, 'kost strand kartunderlag'), 'utan belopp: hjälptext')
    ok('Hittar inget projekt' in shell(pg, 'kost xyzzy 100'), 'okänt projekt')
    ok('en dag' in shell(pg, 'kost strand mån-fre kopior 100'), 'flera dagar går inte')
    pg.fill('#quickIn', '')

    # ── Budget och timmar påverkas inte
    ok(ev(pg, "() => budgetPct(S.register.projects.find(p => p.id === 'proj1'))") == bud0, 'budgeten oförändrad')
    ok(ev(pg, "() => live().reduce((s, e) => s + e.hours, 0)") == h0, 'timmarna oförändrade')

    # ── Fakturaunderlaget
    d = ev(pg, "() => { const d = invoiceData('p:proj1', '2026-10-01', '2026-10-31', true, false); return { any: d.any, nc: d.nc, csA: d.csA, ex: d.ex, texts: d.projects.flatMap(x => x.costs.map(c => c.text)), done: d.done.c, later: d.later.c, amount: d.amount }; }")
    ok(d['texts'] == ['Plottning A1', 'Underkonsult VVS'] and abs(d['csA'] - 13710) < .01, f'oktober: två öppna kostnader, 13 710 kr ({d["texts"]}, {d["csA"]})')
    ok(d['done'] == 0 and d['later'] > 0, 'november-kostnaderna räknas som senare, september (hanterad) är inte med')
    ok(d['ex'][0][0] == 'Kostnader', 'Att fakturera: raden Kostnader')
    ev(pg, "() => { const r = rep(); r.tab = 'invoice'; const v = invSel(); Object.assign(v, { sel: 'p:proj1', custom: true, from: '2026-10-01', to: '2026-10-31', old: true, rows: false, money: true }); }")
    pg.click('.rail [data-page=rapporter]'); pg.wait_for_timeout(500)
    pp = pg.inner_text('.paper').replace('\xa0', ' ').replace('\u202f', ' ')
    ok('Underkonsult VVS' in pp and '13 200' in pp and 'Plottning A1' in pp and '6 st' in pp, 'förhandsvisningen har kostnadstabellen')
    ok('Kostnader' in pp and 'Nybyggnadskarta' not in pp, 'hanterad kostnad står inte med')
    pg.screenshot(path=str(UT / 'kostnad-underlag-1280.png'), full_page=True)
    txt = pdftext(pg, "() => Array.from(invoicePdf(invoiceData('p:proj1', '2026-10-01', '2026-10-31', true, false), 'p:proj1'))")
    ok('Underkonsult VVS' in txt and '13 200' in txt and 'Kostnader' in txt, 'PDF:en har kostnaderna')
    csv = ev(pg, "() => invoiceCsv(invoiceData('p:proj1', '2026-10-01', '2026-10-31', true, false))")
    ok('Kostnad, påslag 10 %' in csv and '13200,00' in csv and 'Plottning A1 (6 st à 85,00)' in csv, 'CSV:en har kostnaderna')
    nm = ev(pg, "() => { invSel().money = false; const d = invoiceData('p:proj1', '2026-10-01', '2026-10-31', true, false); invSel().money = true; return d.nc; }")
    ev(pg, "() => { invSel().money = false; render(); }"); pg.wait_for_timeout(300)
    pp2 = pg.inner_text('.paper').replace('\xa0', ' ').replace('\u202f', ' '); ok('Kostnader' in pp2 and '2 st' in pp2 and '13 200' not in pp2, 'utan belopp: kostnaderna utan kronor')
    ev(pg, "() => { invSel().money = true; render(); }")
    # Bara kostnader (inga timmar): underlaget finns ändå
    d2 = ev(pg, "() => { const d = invoiceData('p:proj1', '2026-11-19', '2026-11-19', false, false); return [d.any, d.hours, d.nc]; }")
    ok(d2 == [True, 0, 1], f'en dag med bara en kostnad ger ett underlag ({d2})')

    # ── Projektdagboken
    dd = ev(pg, "() => { const d = diaryData('proj1', '2026-09-01', '2026-10-31', 'ex', { lay: 'task' }); return { cs: d.cs.map(c => [c.text, c.hd]), csA: d.csA, exA: d.exA }; }")
    ok(dd['cs'] == [['Nybyggnadskarta', True], ['Plottning A1', False], ['Underkonsult VVS', False]], f'dagboken har alla tre, den hanterade grå ({dd["cs"]})')
    dinc = ev(pg, "() => diaryData('proj1', '2026-10-01', '2026-10-31', 'inc', { lay: 'task' }).csA")
    ok(abs(dinc - 13710 * 1.25) < .01, 'inkl. moms räknar moms på kostnaderna')
    txt = pdftext(pg, "() => Array.from(diaryPdf(diaryData('proj1', '2026-09-01', '2026-10-31', 'ex', { lay: 'week', empty: false }), false))")
    ok('Kostnader' in txt and 'Nybyggnadskarta' in txt and 'Underkonsult VVS' in txt, 'dagbokens PDF har kostnaderna')

    # ── Fakturautkast och hantering
    ev(pg, "() => { const v = invSel(); Object.assign(v, { sel: 'p:proj1', custom: true, from: '2026-10-01', to: '2026-10-31', old: true }); }")
    n0 = ev(pg, "() => S.register.invoices.length")
    akt(pg, 'invNew'); pg.wait_for_timeout(300)
    x = ev(pg, "() => S.register.invoices.at(-1)")
    ok(ev(pg, "() => S.register.invoices.length") == n0 + 1 and x['status'] == 'draft', 'utkastet skapas')
    lk = [l for l in x['lines'] if 'Underkonsult' in l['text'] or 'Plottning' in l['text']]
    ok(len(lk) == 2 and any(l['qty'] == 6 and l['unit'] == 'st' and l['price'] == 85 and l['amount'] == 510 for l in lk) and any(l['qty'] == 1 and l['amount'] == 13200 for l in lk), f'utkastet har en rad per kostnad ({lk})')
    akt(pg, 'closeDlg')
    ev(pg, "() => { S.register.invoices.pop(); save(); }")
    ev(pg, "() => { S.register.handled.proj1 = [...(S.register.handled.proj1 || []), { id: 'hx', from: '2026-10-01', to: '2026-10-31', at: new Date().toISOString(), by: 'pers1' }]; derive(); }")
    ok(ev(pg, "() => costRemove('kost3')") is None, 'hanterad oktober låser kostnaderna')
    ok(not ev(pg, "() => invoiceData('p:proj1', '2026-10-01', '2026-10-31', true, false).nc"), 'hanterade kostnader kommer inte med i underlaget')
    ev(pg, "() => { S.register.handled.proj1 = S.register.handled.proj1.filter(h => h.id !== 'hx'); save(); derive(); }")

    # ── Sparas och finns kvar efter omladdning
    ev(pg, "() => save()"); pg.wait_for_timeout(400)
    pg.reload(); pg.wait_for_timeout(1200)
    ok(sorted(c['text'] for c in ev(pg, KOSTER)) == ['Kartunderlag', 'Nybyggnadskarta', 'Plottning', 'Plottning A1', 'Ritningskopior', 'Underkonsult VVS'], 'kostnaderna finns kvar efter omladdning')
    ok(not js, f'inga JavaScript-fel ({js[:2]})')

    # ── Telefon: smartmenyn med kostnaden och dialogen
    tel = b.new_context(viewport={'width': 390, 'height': 844}, service_workers='block', color_scheme='dark', is_mobile=True, has_touch=True)
    tel.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(BOK))}); sessionStorage.setItem('lagd', '1'); }}")
    tp = tel.new_page(); tj = []; tp.on('pageerror', lambda e: tj.append(str(e)))
    tp.clock.install(time=datetime.datetime(2026, 11, 18, 10, 0)); tp.goto(URL); tp.wait_for_timeout(1200)
    ev(tp, "() => { st.page = 'tid'; st.view = 'day'; st.week = '2026-10-19'; st.day = '2026-10-20'; render(); }"); tp.wait_for_timeout(300)
    ok(tp.locator('.dcards .ko-i:has-text("Underkonsult VVS")').count() == 1, 'telefon: dagvyn visar kostnaden')
    tp.screenshot(path=str(UT / 'kostnad-dag-390.png'))
    ev(tp, "() => { st.view = 'month'; st.month = '2026-10'; render(); }"); tp.wait_for_timeout(300)
    ev(tp, "() => { st.view = 'day'; render(); }"); tp.wait_for_timeout(200)
    akt(tp, 'menuFor', key='proj1~upg1|2026-10-20'); tp.wait_for_timeout(300)
    tp.screenshot(path=str(UT / 'kostnad-meny-390.png'))
    ok(tp.locator('[data-act=costAdd]:visible').count() >= 1, 'telefon: smartmenyn har Kostnad')
    akt(tp, 'closeCpop'); akt(tp, 'costAdd', key='proj1~upg1|2026-10-22'); tp.wait_for_timeout(300)
    tp.screenshot(path=str(UT / 'kostnad-dialog-390.png'))
    w = tp.evaluate("() => document.documentElement.scrollWidth")
    ok(w <= 390, f'ingen sidledsrullning ({w})')
    ok(not tj, f'telefon: inga JavaScript-fel ({tj[:2]})')
    b.close()

print('\n' + ('Allt gick igenom.' if not fel else f'{fel} fel.'))
sys.exit(1 if fel else 0)
