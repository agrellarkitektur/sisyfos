#!/usr/bin/env python3
"""
Sisyfos 0.19.1 – rapporterna och att dra tid (filformat 11 oförändrat).

Kontrollerar i en riktig webbläsare att
  – veckosumman i Per dag och vecka har ett svart streck ovanför och en tom rad efter (skärm och PDF),
  – Timmar och Belopp har luft mellan sig (padding mellan högerställda kolumner),
  – fakturaunderlaget kan visas utan belopp (Belopp av = bara timmar) på skärmen och i PDF:en,
  – egna rader (underkonsult) läggs till i dialogen, räknar belopp × (1 + påslag), står i projektdagboken och
    fakturaunderlaget (skärm, PDF och CSV), ingår i summan och sparas inte i boken,
  – en ruta med tid kan dras till en annan dag: flyttas, slås ihop med tid som redan finns i raden den dagen, Ångra
    lägger tillbaka, en låst dag tar inte emot tid, och nära veckans kant byter veckan.

Kör:  python3 -m http.server 8765 &  python3 test/rapport2_test.py
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

def pdftext(pg, js):
    b = bytes(ev(pg, js))
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f: f.write(b); p = f.name
    return subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout

def akt(pg, act, **data):
    attrs = ' '.join(f'data-{k}="{v}"' for k, v in data.items())
    pg.evaluate("(h) => { document.getElementById('tb')?.remove(); document.body.insertAdjacentHTML('beforeend', h); document.getElementById('tb').click(); }", f'<button id="tb" data-act="{act}" {attrs}>x</button>')
    pg.wait_for_timeout(300)

def tid(pg, rk, d):
    return ev(pg, "([rk, d]) => { const e = cell(rk, d); return e ? [e.hours, e.note || '', e.rate] : null; }", [rk, d])

def ruta(pg, rk, d):
    return pg.locator(f'[data-cellbox="{rk}|{d}"]')

def dra(pg, rk, d, x, y=None, steg=12, vanta=0):
    box = ruta(pg, rk, d).bounding_box()
    sx, sy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    pg.mouse.move(sx, sy); pg.mouse.down()
    pg.mouse.move(sx + 8, sy, steps=2)
    pg.mouse.move(x, y if y is not None else sy, steps=steg)
    if vanta: pg.wait_for_timeout(vanta)
    pg.mouse.up(); pg.wait_for_timeout(350)

def kol(pg, d):
    b = pg.locator(f'.wkv .b-head .dh[data-dh="{d}"]').bounding_box()
    return b['x'] + b['width'] / 2

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, service_workers='block', accept_downloads=True)
    ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(BOK))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.clock.install(time=datetime.datetime(2026, 11, 18, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(1200)

    # ── Projektdagboken: veckosumman och kolumnerna
    ev(pg, "() => { const r = rep(); r.tab = 'diary'; r.pid = 'proj1'; r.custom = true; r.from = '2026-10-01'; r.to = '2026-11-15'; r.lay = 'week'; r.empty = true; r.amount = 'ex'; }")
    pg.click('.rail [data-page=rapporter]'); pg.wait_for_timeout(500)
    ws = pg.locator('.paper tr.wk-s').first
    bt = ws.evaluate("tr => getComputedStyle(tr.cells[0]).borderTopWidth")
    ok(float(bt.replace('px', '')) >= 1, f'veckosumman har ett streck ovanför ({bt})')
    ok(pg.locator('.paper tr.wk-g').count() >= 2, f'tom rad efter veckorna ({pg.locator(".paper tr.wk-g").count()})')
    sista = pg.locator('.paper table.dgrp tbody tr').last.get_attribute('class') or ''
    ok('wk-g' not in sista, 'ingen tom rad sist i tabellen')
    pl = pg.locator('.paper table.dgrp tbody tr:not(.wk-g):not(.wk-e) td.r + td.r').first.evaluate("td => parseFloat(getComputedStyle(td).paddingLeft)")
    ok(pl >= 20, f'luft mellan Timmar och Belopp ({pl} px)')
    gap = ev(pg, "() => { const d = diaryData('proj1', '2026-10-01', '2026-11-15', 'ex'); const it = weekItems(d.groups[0].rows, d.from, d.to, { empty: true }); return [it.length, it.filter(x => x.k !== 'd').length]; }")
    txt = pdftext(pg, "() => Array.from(diaryPdf(diaryData('proj1', '2026-10-01', '2026-11-15', 'ex'), false))")
    ok('Vecka 43' in txt and 'ingen rapporterad tid' in txt, 'PDF:en med veckor som förut')

    # ── Egna rader i projektdagboken
    tot0 = ev(pg, "() => diaryData('proj1', '2026-10-01', '2026-11-15', 'ex').amount")
    pg.click('[data-act=xrAdd][data-k=diary]'); pg.wait_for_timeout(300)
    pg.fill('#xrT', 'Underkonsult, se separat dagbok'); pg.fill('#xrH', '10'); pg.fill('#xrR', '800'); pg.fill('#xrM', '10'); pg.wait_for_timeout(200)
    ok(pg.input_value('#xrA').replace(' ', ' ').replace(' ', '') in ('8000', '8000,00'), f'beloppet räknas fram ({pg.input_value("#xrA")!r})')
    s = pg.inner_text('#xrSum').replace(' ', ' ')
    ok('8 800' in s, f'totalt med påslag i dialogen ({s!r})')
    pg.click('#xrForm button[type=submit]'); pg.wait_for_timeout(400)
    ok(pg.locator('.xr-l li').count() == 1, 'raden står i listan')
    pp = pg.inner_text('.paper').replace(' ', ' ')
    ok('Egna rader' in pp and 'Underkonsult, se separat dagbok' in pp and '10 %' in pp, 'egna rader i förhandsvisningen')
    d = ev(pg, "() => { const d = diaryData('proj1', '2026-10-01', '2026-11-15', 'ex'); return [d.amount, d.xrA, d.xr.length]; }")
    ok(abs(d[0] - tot0) < 0.01 and abs(d[1] - 8800) < 0.01 and d[2] == 1, f'tidens summa oförändrad, egna rader 8 800 ({d})')
    sm = pg.locator('.paper .tot-t tr.tot').inner_text().replace(' ', ' ')
    ok(f"{int(round(tot0 + 8800)):,}".replace(',', ' ') in sm, f'summan inkluderar egna rader ({sm!r})')
    txt = pdftext(pg, "() => Array.from(diaryPdf(diaryData('proj1', '2026-10-01', '2026-11-15', 'ex'), false))").replace(' ', ' ')
    ok('Egna rader' in txt and 'Underkonsult' in txt and '8 800' in txt, 'egna rader i PDF:en')
    ok('Underkonsult' not in json.dumps(ev(pg, "() => S")), 'egna rader sparas inte i boken')
    # utan belopp i dagboken: bara timmar
    pg.select_option('#rpAmt', 'none'); pg.wait_for_timeout(300)
    pp = pg.inner_text('.paper')
    ok('Underkonsult' in pp and '8 800' not in pp.replace(' ', ' '), 'utan belopp: egna rader bara med timmar')
    pg.select_option('#rpAmt', 'ex'); pg.wait_for_timeout(300)
    # ändra och ta bort med Ångra
    pg.click('.xr-l [data-act=xrEdit]'); pg.wait_for_timeout(300)
    pg.fill('#xrM', '0'); pg.click('#xrForm button[type=submit]'); pg.wait_for_timeout(300)
    ok(abs(ev(pg, "() => diaryData('proj1', '2026-10-01', '2026-11-15', 'ex').xrA") - 8000) < 0.01, 'påslag 0 % går bra')
    pg.click('.xr-l [data-act=xrDel]'); pg.wait_for_timeout(300)
    ok(pg.locator('.xr-l li').count() == 0, 'raden togs bort')
    pg.click('#toast [data-act=toastAct]'); pg.wait_for_timeout(300)
    ok(pg.locator('.xr-l li').count() == 1, 'Ångra lägger tillbaka raden')
    ev(pg, "() => { rep().pid = 'proj2'; render(); }"); pg.wait_for_timeout(300)
    ok(pg.locator('.xr-l li').count() == 0, 'egna rader hör till projektet')

    # ── Fakturaunderlaget: belopp av och egna rader
    ev(pg, "() => { const r = rep(); r.tab = 'invoice'; render(); }"); pg.wait_for_timeout(400)
    pg.select_option('#ivS', 'p:proj1'); pg.wait_for_timeout(300)
    if not pg.locator('#ivRows').is_checked(): pg.check('#ivRows'); pg.wait_for_timeout(300)
    ok(pg.locator('#ivAmt').is_checked(), 'belopp är på som standard')
    ok(' kr' in pg.inner_text('.paper'), 'med belopp: kronor i underlaget')
    pg.uncheck('#ivAmt'); pg.wait_for_timeout(400)
    pp = pg.inner_text('.paper')
    ok(' kr' not in pp.replace(' ', ' ') and 'Öppen tid' in pp and 'Att fakturera' not in pp, 'utan belopp: bara timmar, rubriken Öppen tid')
    get = "() => { const v = rep().inv, f = v.custom ? v.from : v.ym + '-01', t = v.custom ? v.to : v.ym + '-31'; return Array.from(invoicePdf(invoiceData(v.sel, f, t, v.old, v.rows), v.sel)); }"
    txt = pdftext(pg, get)
    ok(' kr' not in txt.replace(' ', ' ') and 'Timmar' in txt and 'Öppen tid' in txt, 'PDF:en utan belopp')
    pg.select_option('#ivLay', 'week'); pg.wait_for_timeout(300)
    ok(pg.locator('.paper tr.wk-s td').first.evaluate("td => td.parentElement.cells.length") == 2, 'veckosumman utan beloppskolumn')
    pg.check('#ivAmt'); pg.wait_for_timeout(300)
    pg.click('[data-act=xrAdd][data-k=inv]'); pg.wait_for_timeout(300)
    pg.fill('#xrT', 'Underkonsult el'); pg.fill('#xrA', '5000'); pg.fill('#xrM', '15'); pg.click('#xrForm button[type=submit]'); pg.wait_for_timeout(400)
    dd = ev(pg, "() => { const v = rep().inv, f = v.custom ? v.from : v.ym + '-01', t = v.custom ? v.to : v.ym + '-31', d = invoiceData(v.sel, f, t, v.old, v.rows); return [d.amount, d.xrA, d.vatA + d.vatX, d.vat]; }")
    ok(abs(dd[1] - 5750) < 0.01, f'belopp direkt med 15 % påslag = 5 750 ({dd[1]})')
    pp = pg.inner_text('.paper').replace(' ', ' ')
    tot = (dd[0] + dd[1]) * (1 + dd[3] / 100)
    ok('Egna rader' in pp and f"{round(tot):,}".replace(',', ' ') in pp, f'egna rader ingår i Att fakturera inkl. moms ({round(tot)})')
    txt = pdftext(pg, get).replace(' ', ' ')
    ok('Underkonsult el' in txt and '5 750' in txt, 'egna rader i fakturaunderlagets PDF')
    csv = ev(pg, "() => { const v = rep().inv, f = v.custom ? v.from : v.ym + '-01', t = v.custom ? v.to : v.ym + '-31'; return invoiceCsv(invoiceData(v.sel, f, t, v.old, v.rows)); }")
    ok('Underkonsult el' in csv and '5750,00' in csv, 'egna rader i CSV:en')

    # ── Dra tid till en annan dag
    ev(pg, "() => { S.prefs.showWeekend = false; window.SISYFOS.st.page = 'tid'; window.SISYFOS.st.view = 'week'; window.SISYFOS.st.week = '2026-10-19'; render(); }"); pg.wait_for_timeout(400)
    rk = 'proj1~upg1'
    ok(tid(pg, rk, '2026-10-22') is None and tid(pg, rk, '2026-10-19')[0] == 2, 'utgångsläge: 2 h mån 19 okt, inget tor 22 okt')
    dra(pg, rk, '2026-10-19', kol(pg, '2026-10-22'))
    ok(tid(pg, rk, '2026-10-19') is None and tid(pg, rk, '2026-10-22') and tid(pg, rk, '2026-10-22')[0] == 2, 'tiden flyttades till torsdag')
    t = pg.inner_text('#toast')
    ok('Flyttade 2' in t and 'tor 22 okt' in t and 'tor tor' not in t, f'besked ({t!r})')
    ok(not pg.locator('#cpop:not([hidden])').count() or pg.locator('#cpop').is_hidden(), 'smartmenyn öppnas inte efter dragningen')
    pg.click('#toast [data-act=toastAct]'); pg.wait_for_timeout(300)
    ok(tid(pg, rk, '2026-10-19') and tid(pg, rk, '2026-10-19')[0] == 2 and tid(pg, rk, '2026-10-22') is None, 'Ångra flyttar tillbaka')
    n20 = tid(pg, rk, '2026-10-20'); n19 = tid(pg, rk, '2026-10-19')
    dra(pg, rk, '2026-10-19', kol(pg, '2026-10-20'))
    m = tid(pg, rk, '2026-10-20')
    ok(tid(pg, rk, '2026-10-19') is None and m and abs(m[0] - (n19[0] + n20[0])) < 1e-9, f'ihop med tiden som fanns ({m})')
    ok((not n19[1] or n19[1] in m[1]) and (not n20[1] or n20[1] in m[1]), 'anteckningarna följer med')
    ok('ihop med' in pg.inner_text('#toast'), 'beskedet säger att tiden lades ihop')
    pg.click('#toast [data-act=toastAct]'); pg.wait_for_timeout(300)
    ok(tid(pg, rk, '2026-10-19')[0] == n19[0] and tid(pg, rk, '2026-10-20')[0] == n20[0], 'Ångra delar upp igen')
    # klick utan att dra öppnar som vanligt
    ruta(pg, rk, '2026-10-21').click(); pg.wait_for_timeout(300)
    ok(tid(pg, rk, '2026-10-21')[0] == 3.5, 'ett klick ändrar ingenting')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    # låst dag tar inte emot
    akt(pg, 'handle', p='proj1', **{'from': '2026-10-01', 'to': '2026-10-16'})
    if pg.locator('#dlg:not([hidden]) [data-act=forceHandle]').count(): pg.click('#dlg [data-act=forceHandle]'); pg.wait_for_timeout(300)
    hd = ev(pg, "() => !!handled('proj1', '2026-10-16')")
    ev(pg, "() => { window.SISYFOS.st.week = '2026-10-12'; render(); }"); pg.wait_for_timeout(300)
    if hd:
        before = tid(pg, rk, '2026-10-16')
        ok(ruta(pg, rk, '2026-10-16').get_attribute('class').find(' ro') >= 0, 'hanterad dag är låst')
    # vecka 43: flytta till en låst dag i vecka 42 via kanten
    ev(pg, "() => { window.SISYFOS.st.week = '2026-10-19'; render(); }"); pg.wait_for_timeout(300)
    hb = pg.locator('.wkv .b-head .dh').first.bounding_box()
    dra(pg, rk, '2026-10-19', hb['x'] + 2, vanta=1000)
    wk = ev(pg, "() => window.SISYFOS.st.week")
    ok(wk == '2026-10-12', f'nära veckans början byter veckan ({wk})')
    ok(tid(pg, rk, '2026-10-19') is not None, 'släppt på kanten flyttas ingenting')
    # i vecka 42: dra från fredag (hanterad) går inte; dra in tid till hanterad dag går inte
    if hd:
        ok(ev(pg, "([rk]) => moveDay(rk, '2026-10-21', '2026-10-16')", [rk]) is None, 'en låst dag tar inte emot tid')
        ok(tid(pg, rk, '2026-10-21')[0] == 3.5, 'tiden ligger kvar')
    # flytta mellan veckor
    ev(pg, "() => { window.SISYFOS.st.week = '2026-10-19'; render(); }"); pg.wait_for_timeout(300)
    lb = pg.locator('.wkv .b-head .dh').last.bounding_box()
    box = ruta(pg, rk, '2026-10-21').bounding_box(); sx, sy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    pg.mouse.move(sx, sy); pg.mouse.down(); pg.mouse.move(sx + 10, sy, steps=2)
    pg.mouse.move(lb['x'] + lb['width'] - 2, sy, steps=10); pg.wait_for_timeout(1000)
    wk = ev(pg, "() => window.SISYFOS.st.week")
    pg.mouse.move(kol(pg, '2026-10-27'), sy, steps=8); pg.mouse.up(); pg.wait_for_timeout(400)
    ok(wk == '2026-10-26', f'nära veckans slut byter till nästa vecka ({wk})')
    ok(tid(pg, rk, '2026-10-21') is None and tid(pg, rk, '2026-10-27') and tid(pg, rk, '2026-10-27')[0] == 3.5, 'tiden flyttades till tisdag i nästa vecka')
    ok(pg.locator(f'[data-cellbox="{rk}|2026-10-27"]').count() == 1, 'raden syns i den nya veckan')

    # telefon: rapporten med egna rader ryms
    ev(pg, "() => { const r = rep(); r.tab = 'invoice'; window.SISYFOS.st.page = 'rapporter'; render(); }")
    pg.set_viewport_size({'width': 390, 'height': 800}); pg.wait_for_timeout(400)
    ok(pg.evaluate("() => document.documentElement.scrollWidth <= 392"), 'rapporten med egna rader ryms på 390 px')

    ok(not js, f'inga JavaScript-fel {js}')
    ctx.close(); b.close()

print('\nAllt OK' if not fel else f'\n{fel} fel'); sys.exit(1 if fel else 0)
