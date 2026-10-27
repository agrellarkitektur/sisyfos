#!/usr/bin/env python3
"""
Sisyfos – månadsvyn i tidboken, Enter till smartshell och startrutan (0.17.2).

Kontrollerar i en riktig webbläsare att
  – en klick på en projektrad i månadssammanställningen markerar projektet i kalendern och öppnar smartmenyn,
  – projektets uppgifter fälls ut under raden och kan markeras för sig,
  – en klick på en dag med ett markerat projekt öppnar smartmenyn för dagen (timmar, snabbval, anteckning),
    med uppgifterna som knappar, och att tiden och anteckningen sparas på rätt uppgift,
  – + Projekt eller uppgift markerar ett projekt som inte har tid i månaden,
  – Enter utan fokus flyttar markören till smartshell, men inte i en dialog,
  – startrutan visas när det inte finns någon bok och inte för en befintlig bok, och att
    "Titta på exempelboken" och "Öppna en bok från fil" fungerar.

Kör:  python3 -m http.server 8765 &  python3 test/manad_test.py
"""
import json, pathlib, sys, datetime
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
URL = (sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html') + '?test'
BOKF = ROT / 'test' / 'bocker' / 'format-11.json'
BOK = json.loads(BOKF.read_text(encoding='utf-8'))
fel = 0
def ev(page, fn, arg=None):
    return page.evaluate("([f, a]) => { with (window.SISYFOS) { return eval('(' + f + ')')(a); } }", [fn, arg])
def ok(cond, text):
    global fel
    print(('OK  ' if cond else 'FEL ') + text); fel += not cond

def starta(b, bok=None, w=1280):
    ctx = b.new_context(viewport={'width': w, 'height': 900}, service_workers='block')
    if bok: ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(bok))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.clock.install(time=datetime.datetime(2026, 10, 20, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(1200)
    return ctx, pg, js

with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (1280, 390):
        ctx, pg, js = starta(b, BOK, w)
        ok(pg.locator('.wel').count() == 0, f'{w} px: ingen startruta för en befintlig bok')
        if w < 700: pg.click('[data-act=view][data-view=month]')
        else: pg.click('[data-act=view][data-view=month]')
        pg.wait_for_timeout(300)
        pg.click('#mBody tr.m-prow:has-text("Villa Strand") td >> nth=1'); pg.wait_for_timeout(300)
        ok(ev(pg, "() => st.mproj") == 'proj1', f'{w} px: klick på raden markerar projektet')
        ok(pg.locator('#menu:not([hidden]) [data-act=mprojOff]').count() == 1, f'{w} px: smartmenyn för projektet öppnas')
        ok(pg.locator('#mBody tr.m-trow').count() == 2, f'{w} px: uppgifterna fälls ut under projektet')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(100)
        pg.click('#mBody tr.m-trow:has-text("Skiss") td >> nth=1'); pg.wait_for_timeout(200)
        ok(ev(pg, "() => st.mtask") == 'upg2', f'{w} px: uppgiften markeras')
        pg.click('#mBody .mc[data-day="2026-10-21"]'); pg.wait_for_timeout(300)
        ok(pg.locator('#cpop:not([hidden])').count() == 1 and pg.evaluate("document.activeElement.id") == 'cpHours', f'{w} px: klick på en dag öppnar smartmenyn med timrutan i fokus')
        ok(pg.locator('#cpop .cp-tasks .chip[aria-pressed=true]:has-text("Skiss")').count() == 1, f'{w} px: uppgifterna som knappar, den markerade vald')
        pg.click('#cpop .cp-tasks .chip:has-text("Bygglov")'); pg.wait_for_timeout(300)
        ok(ev(pg, "() => st.mtask") == 'upg1' and pg.locator('#cpop .r-sub:has-text("Bygglov")').count() == 1, f'{w} px: byte av uppgift i smartmenyn')
        pg.click('#cpop .cp-chips .chip:has-text("2")'); pg.wait_for_timeout(200)
        pg.fill('#cpNote', 'från månadsvyn'); pg.wait_for_timeout(200); pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
        r = ev(pg, "() => { const e = cell('proj1~upg1', '2026-10-21'); return e && [e.hours, e.note]; }")
        ok(r == [2, 'från månadsvyn'], f'{w} px: tid och anteckning sparas på uppgiften ({r})')
        # Ett projekt utan tid i månaden
        pg.click('#mBody [data-act=mAdd]'); pg.wait_for_timeout(200)
        pg.fill('#pickQ', 'Lärkan'); pg.press('#pickQ', 'Enter'); pg.wait_for_timeout(300)
        ok(ev(pg, "() => st.mproj") == 'proj3', f'{w} px: + Projekt eller uppgift markerar projektet')
        pg.click('#mBody .mc[data-day="2026-10-23"]'); pg.wait_for_timeout(300)
        pg.fill('#cpHours', '3'); pg.press('#cpHours', 'Tab'); pg.wait_for_timeout(200); pg.keyboard.press('Escape'); pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
        ok(ev(pg, "() => cell('proj3~upg4', '2026-10-23')?.hours") == 3, f'{w} px: tid på ett projekt utan uppgiftsval')
        ok(pg.locator('#mBody tr.m-prow:has-text("Förskolan Lärkan")').count() == 1, f'{w} px: projektet syns i sammanställningen')
        # Avmarkera
        pg.click('[data-act=mprojOff] >> nth=0'); pg.wait_for_timeout(200)
        pg.click('#mBody .mc[data-day="2026-10-22"]'); pg.wait_for_timeout(300)
        ok(pg.locator('#cpop:not([hidden])').count() == 0, f'{w} px: utan markering öppnar dagen ingen smartmeny')
        if w > 700:
            # Enter till smartshell
            pg.evaluate("document.activeElement.blur()"); pg.keyboard.press('Enter'); pg.wait_for_timeout(100)
            ok(pg.evaluate("document.activeElement.id") == 'quickIn', 'Enter utan fokus: smartshell')
            pg.keyboard.type('? synk'); ok(pg.input_value('#quickIn') == '? synk', 'man kan skriva direkt'); pg.fill('#quickIn', '')
            pg.evaluate("document.activeElement.blur()")
            ev(pg, "() => { st.page = 'projekt'; render(); }"); pg.wait_for_timeout(200)
            pg.keyboard.press('Enter'); pg.wait_for_timeout(100)
            ok(pg.evaluate("document.activeElement.id") == 'quickIn', 'Enter på projektsidan: smartshell')
            pg.evaluate("document.activeElement.blur()")
            pg.click('#brandBtn'); pg.click('[data-act=about]'); pg.wait_for_timeout(200)
            pg.evaluate("document.activeElement.blur()"); pg.keyboard.press('Enter'); pg.wait_for_timeout(100)
            ok(pg.evaluate("document.activeElement.id") != 'quickIn', 'Enter i en dialog: inte smartshell')
        ok(not js, f'{w} px: inga JavaScript-fel' + (': ' + '; '.join(js) if js else ''))
        ctx.close()

    # Startrutan
    ctx, pg, js = starta(b)
    ok(pg.locator('.wel').count() == 1 and pg.locator('#shDock.sh-wel').count() == 1, 'startrutan visas utan bok (smartshell dold)')
    ok(all(pg.locator(f'.wel [data-act={a}]').count() == 1 for a in ('webLogin', 'importBook', 'askNew', 'welcomeSample')), 'startrutans val: logga in, öppna fil, ny bok, exempelboken')
    pg.click('.wel [data-act=welcomeSample]'); pg.wait_for_timeout(300)
    ok(pg.locator('.wel').count() == 0 and pg.locator('#quickIn').is_visible(), 'Titta på exempelboken visar tidboken')
    ctx.close()
    ctx, pg, js = starta(b)
    pg.click('.wel [data-act=importBook]'); pg.wait_for_timeout(300)
    pg.set_input_files('#imFile', str(BOKF)); pg.wait_for_timeout(300); pg.click('[data-act=doImport]'); pg.wait_for_timeout(800)
    ok(pg.locator('.wel').count() == 0 and ev(pg, "() => R().book.name") == 'Testbok format 11', 'Öppna en bok från fil: boken öppnas')
    pg.reload(); pg.wait_for_timeout(1200)
    ok(pg.locator('.wel').count() == 0, 'efter omladdning: ingen startruta')
    ok(not js, 'startrutan: inga JavaScript-fel' + (': ' + '; '.join(js) if js else ''))
    ctx.close()
    ctx, pg, js = starta(b, w=390)
    pg.screenshot(path=str(ROT / '_start390.png')) if '--bild' in sys.argv else None
    pg.click('.wel [data-act=askNew]'); pg.wait_for_timeout(300)
    ok(pg.locator('#dlg:not([hidden])').count() == 1, 'Starta en ny bok öppnar guiden (telefon)')
    ctx.close()
    b.close()

print('\n' + ('Allt OK' if not fel else f'{fel} fel'))
sys.exit(1 if fel else 0)
