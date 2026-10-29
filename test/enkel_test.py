#!/usr/bin/env python3
"""
Sisyfos – enklare flöde för den ensamme och veckouppställning i rapporterna (0.19.0, filformat 11 oförändrat).

Kontrollerar i en riktig webbläsare att
  – avcheckningen per vecka är av för en ensam bok (book.checkWeeks saknas): ingen veckoknapp i vecko- och dagvyn,
    ch i smartshell säger att den är avstängd, en vecka som checkats av förut låser inte längre, en avslutad
    månad är redo att hanteras utan avcheckning, och månadsvyn visar inga veckor som "inte avcheckade",
  – hanterad tid syns i tidboken: rutorna i en hanterad period har en grön markering (.cell.hd) och är skrivskyddade,
    dagvyns ruta likaså (.dv-h.hd) och månadsvyns dagar (.mc.hd) – och en hantering i rapportflödet låser dagen,
  – Inställningar → Avcheckning och signering: Checka av veckorna slår på avcheckningen (knappen kommer tillbaka),
    signeringen går inte att slå på utan avcheckning,
  – projektdagboken Per dag och vecka: uppgifterna samma dag på en rad, en summarad per kalendervecka, veckor utan
    tid med "ingen rapporterad tid" när det valts – på skärmen och i PDF:en, med samma summa som Per uppgift,
  – fakturaunderlaget med dagboksrader Per dag och vecka – skärm och PDF.

Kör:  python3 -m http.server 8765 &  python3 test/enkel_test.py
"""
import json, pathlib, sys, datetime, subprocess, tempfile
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
URL = (sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html') + '?test'
BOK = json.loads((ROT / 'test' / 'bocker' / 'format-11.json').read_text(encoding='utf-8'))
fel = 0
def ev(page, fn, arg=None):
    return page.evaluate("([f, a]) => { with (window.SISYFOS) { return eval('(' + f + ')')(a); } }", [fn, arg])
def ok(cond, text):
    global fel
    print(('OK  ' if cond else 'FEL ') + text); fel += not cond

def starta(b, bok, w=1280):
    ctx = b.new_context(viewport={'width': w, 'height': 900}, service_workers='block')
    ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(bok))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.clock.install(time=datetime.datetime(2026, 11, 18, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(1200)
    return ctx, pg, js

def akt(pg, act, **data):
    attrs = ' '.join(f'data-{k}="{v}"' for k, v in data.items())
    pg.evaluate("(h) => { document.getElementById('tb')?.remove(); document.body.insertAdjacentHTML('beforeend', h); document.getElementById('tb').click(); }", f'<button id="tb" data-act="{act}" {attrs}>x</button>')
    pg.wait_for_timeout(300)

def vy(pg, view, d):
    ev(pg, "([v, d]) => { S.prefs.showWeekend = false; window.SISYFOS.st.view = v; window.SISYFOS.st.week = monday(d); window.SISYFOS.st.day = d; window.SISYFOS.st.month = d.slice(0, 7); render(); }", [view, d])
    pg.wait_for_timeout(250)

def skal(pg, txt):
    pg.fill('#quickIn', txt); pg.wait_for_timeout(250)
    return pg.inner_text('#quickHint')

def pdftext(pg, js):
    b = bytes(ev(pg, js))
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f: f.write(b); p = f.name
    return subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, js = starta(b, BOK)
    st = 'window.SISYFOS.st'

    # ── Avcheckningen är av för en ensam bok
    ok(ev(pg, "() => checkOn()") is False and ev(pg, "() => signOn()") is False, 'ensam bok: avcheckning och signering av')
    vy(pg, 'week', '2026-10-12')
    ok(pg.locator('.wk-head [data-act=checkWeek]').count() == 0 and pg.locator('.wk-head [data-act=weekStateMenu]').count() == 0, 'veckovyn: ingen knapp för avcheckning')
    vy(pg, 'day', '2026-10-13')
    ok(pg.locator('.wk-head [data-act=checkWeek]').count() == 0, 'dagvyn: ingen knapp för avcheckning')
    h = skal(pg, 'ch v42')
    ok('avstängd' in h, f'ch i smartshell: {h}')
    pg.fill('#quickIn', '')
    # en vecka som checkats av förut låser inte längre
    ev(pg, "() => weekEvent('2026-10-12', true)")
    ok(ev(pg, "() => weekState('2026-10-12').checked") is False and ev(pg, "() => locked('2026-10-13')") is False, 'en avcheckad vecka låser inte när avcheckningen är av')
    # redo att hanteras utan avcheckning
    rd = ev(pg, "() => perReady('proj1', '2026-10-01', '2026-10-31')")
    ok(rd['ready'] and rd['hours'] > 0 and not rd['open'], f'oktober redo att hanteras utan avcheckning ({rd["hours"]} h)')
    vy(pg, 'month', '2026-10-15')
    ok(pg.locator('.m-open-w').count() == 0 and pg.locator('.mw.open').count() == 0, 'månadsvyn: inga veckor "inte avcheckade"')

    # ── Hanterad tid syns i tidboken (1–15 sep är hanterad i Villa Strand)
    vy(pg, 'week', '2026-09-07')
    hd = pg.locator('.cell.hd'); n = hd.count()
    ok(n >= 5, f'veckovyn: hanterade rutor markerade ({n})')
    ok(pg.locator('.cell.hd .h-in[readonly]').count() == n, 'de hanterade rutorna är skrivskyddade')
    ok(pg.evaluate("() => getComputedStyle(document.querySelector('.cell.hd .hdm')).display") == 'block', 'den gröna pricken syns')
    vy(pg, 'day', '2026-09-08')
    ok(pg.locator('.dv-h.hd').count() >= 1, 'dagvyn: hanterad tid markerad')
    vy(pg, 'month', '2026-09-10')
    ok(pg.locator('.mc.hd[data-day="2026-09-08"]').count() == 1, 'månadsvyn: hanterad dag markerad')
    ok(pg.locator('.mc.hd[data-day="2026-09-22"]').count() == 0, 'månadsvyn: dag utan hanterad tid omarkerad')
    # hantera oktober i rapportflödet → dagen låses och markeras
    akt(pg, 'handle', p='proj1', ym='2026-10')
    if pg.locator('#dlg:not([hidden]) [data-act=forceHandle]').count(): pg.click('#dlg [data-act=forceHandle]'); pg.wait_for_timeout(300)
    ok(ev(pg, "() => !!handled('proj1', '2026-10-14')"), 'oktober hanterad i Villa Strand')
    vy(pg, 'week', '2026-10-12')
    c = pg.locator('.cell.hd[data-cellbox="proj1~upg1|2026-10-14"]')
    ok(c.count() == 1 and c.locator('.h-in[readonly]').count() == 1, 'hanterad dag är grön och låst i veckan')
    ok(pg.locator('.cell[data-cellbox^="proj3"] .h-in[readonly]').count() == 0, 'andra projekt i veckan är öppna')

    # ── Inställningen
    pg.click('.rail [data-page=installningar]'); pg.wait_for_timeout(400)
    ok(pg.locator('#setSign').is_disabled(), 'signering går inte att slå på utan avcheckning')
    pg.check('#setCheck'); pg.wait_for_timeout(300)
    ok(ev(pg, "() => checkOn()") is True and ev(pg, "() => R().book.checkWeeks") is True, 'Checka av veckorna slår på avcheckningen')
    ok(not pg.locator('#setSign').is_disabled(), 'signeringen kan nu slås på')
    ok(ev(pg, "() => weekState('2026-10-12').checked") is True, 'den tidigare avcheckningen gäller igen')
    pg.click('.rail [data-page=tid]'); pg.wait_for_timeout(300)
    vy(pg, 'week', '2026-11-09')
    ok(pg.locator('.wk-head [data-act=checkWeek]').count() == 1, 'knappen Checka av finns när avcheckningen är på')
    pg.click('.rail [data-page=installningar]'); pg.wait_for_timeout(300)
    pg.uncheck('#setCheck'); pg.wait_for_timeout(300)
    ok(ev(pg, "() => checkOn()") is False, 'och av igen')

    # ── Projektdagboken per dag och vecka
    akt(pg, 'unhandle', p='proj1', ym='2026-10')
    if pg.locator('#dlg:not([hidden]) [data-act=unhandleForce]').count(): pg.click('#dlg [data-act=unhandleForce]'); pg.wait_for_timeout(300)
    ev(pg, "() => { setCell('proj1~upg2', '2026-10-20', { hours: 1.5, note: 'skisser fasad' }); }")
    ev(pg, f"() => {{ const r = rep(); r.tab = 'diary'; r.pid = 'proj1'; r.custom = true; r.from = '2026-10-01'; r.to = '2026-11-15'; r.lay = 'task'; r.empty = false; r.amount = 'ex'; }}")
    pg.click('.rail [data-page=rapporter]'); pg.wait_for_timeout(500)
    tot_task = ev(pg, "() => { const d = diaryData('proj1', '2026-10-01', '2026-11-15', 'ex'); return [d.hours, d.amount, d.lay]; }")
    ok(tot_task[2] == 'task' and pg.locator('.paper tr.wk-s').count() == 0, 'Per uppgift som förut')
    pg.select_option('#rpLay', 'week'); pg.wait_for_timeout(400)
    ok(pg.locator('.paper tr.wk-s').count() >= 3, f'Per dag och vecka: summarad per vecka ({pg.locator(".paper tr.wk-s").count()})')
    rad = pg.locator('.paper tr:has-text("20 okt")').first.inner_text()
    ok('Bygglov' in rad and 'Skiss' in rad and '4,5' in rad.replace('.', ','), f'20 okt: båda uppgifterna på en rad ({rad!r})')
    v43 = pg.locator('.paper tr.wk-s:has-text("Vecka 43")').inner_text()
    ok('10' in v43, f'vecka 43 summeras ({v43!r})')
    ok(pg.locator('.paper tr.wk-e').count() == 0, 'utan valet syns inga tomma veckor')
    pg.check('#rpEmpty'); pg.wait_for_timeout(400)
    tom = pg.locator('.paper tr.wk-e').all_inner_texts()
    ok(len(tom) >= 2 and all('ingen rapporterad tid' in t for t in tom), f'veckor utan tid: {tom}')
    ok(any('Vecka 44' in t for t in tom) and any('Vecka 46' in t for t in tom), 'vecka 44–46 står som tomma')
    tot_week = ev(pg, "() => { const d = diaryData('proj1', '2026-10-01', '2026-11-15', 'ex'); const it = d.groups.flatMap(g => weekItems(g.rows, d.from, d.to, { empty: true, task: true })); return [it.filter(x => x.k === 'w').reduce((s, x) => s + x.hours, 0), it.filter(x => x.k === 'w').reduce((s, x) => s + x.amount, 0), d.lay, d.empty]; }")
    ok(abs(tot_week[0] - tot_task[0]) < 1e-9 and abs(tot_week[1] - tot_task[1]) < 0.01 and tot_week[2] == 'week' and tot_week[3] is True, f'veckornas summa = dagbokens summa ({tot_week[0]} h)')
    txt = pdftext(pg, "() => Array.from(diaryPdf(diaryData('proj1', '2026-10-01', '2026-11-15', 'ex'), false))")
    ok('Vecka 43' in txt and 'ingen rapporterad tid' in txt and 'Skiss: skisser fasad' in txt, 'PDF:en har veckorna, tomma veckor och uppgiften på dagen')
    ok('Bygglov' in txt and 'Summa' in txt, 'PDF:en har sammanställningen')

    # ── Fakturaunderlaget med dagboksrader per dag och vecka
    ev(pg, "() => { const r = rep(); r.tab = 'invoice'; }")
    pg.click('.rail [data-page=tid]'); pg.wait_for_timeout(200)
    pg.click('.rail [data-page=rapporter]'); pg.wait_for_timeout(400)
    pg.select_option('#ivS', 'p:proj1'); pg.wait_for_timeout(300)
    ok(pg.locator('#ivLay').is_disabled() if not pg.locator('#ivRows').is_checked() else True, 'Dagboksrader-valet är av utan dagboksrader')
    if not pg.locator('#ivRows').is_checked(): pg.check('#ivRows'); pg.wait_for_timeout(300)
    pg.select_option('#ivLay', 'week'); pg.wait_for_timeout(400)
    ws = pg.locator('.paper tr.wk-s').count()
    ok(ws >= 2, f'fakturaunderlaget: veckorader ({ws})')
    pg.check('#ivEmpty'); pg.wait_for_timeout(400)
    ok(pg.locator('.paper tr.wk-e').count() >= 1, 'fakturaunderlaget: veckor utan tid')
    txt = pdftext(pg, "() => { const v = rep().inv, [f, t] = [v.custom ? v.from : v.ym + '-01', v.custom ? v.to : v.ym + '-31']; return Array.from(invoicePdf(invoiceData(v.sel, f, t, v.old, v.rows), v.sel)); }")
    ok('Vecka' in txt and 'Att fakturera' in txt, 'fakturaunderlagets PDF har veckorna')

    # ── Telefonbredd: rapportreglagen och veckovyn utan knapp
    pg.set_viewport_size({'width': 390, 'height': 800}); pg.wait_for_timeout(300)
    ok(pg.evaluate("() => document.documentElement.scrollWidth <= 392"), 'rapporten ryms på 390 px')

    ok(not js, f'inga JavaScript-fel {js}')
    ctx.close(); b.close()

print('\nAllt OK' if not fel else f'\n{fel} fel'); sys.exit(1 if fel else 0)
