#!/usr/bin/env python3
"""
Sisyfos – timpriser med datum, på kund och uppgift, och signering (0.17.0, filformat 11).

Kontrollerar i en riktig webbläsare att
  – format 10 migreras till 11 utan att något pris ändras,
  – prislistan (rPut/rv) ger rätt pris före, på och efter ett datum, och slår ihop steg med samma pris,
  – ordningen bok → kund → projekt → person i projektet → uppgift gäller (mest specifika vinner),
  – ett nytt pris i Redigera projekt "från datum" räknar om olåst tid från datumet, men inte tid före
    datumet eller i en avcheckad vecka – och Ångra lägger tillbaka både priset och posterna,
  – tid som skrivs in efteråt för en dag före datumet får det gamla priset,
  – "från början" räknar om all olåst tid,
  – centralt pris (Inställningar → Roller), kundens pris (kunddialogen) och uppgiftens pris (projektdialogen)
    fungerar, och att en ändring som kommer via synken räknar om den här enhetens olåsta tid,
  – signering är av för en ensam bok (knappen syns inte, sign i smartshell säger det), kan slås på,
    och att en signerad vecka kan låsas upp av administratören och då är öppen.
  – 0.17.1: samma pris "från början" eller med ett tidigare datum räknar om rapporterad tid, avcheckad tid
    frågas om (Använd det nya priset / Behåll de gamla priserna, med Ångra), Rensa i egenskapspanelen,
    panelens rubrik leder till projektsidan och smartmenyn har snabbknappar för tiden.

Kör:  python3 -m http.server 8765 &  python3 test/priser_test.py
"""
import json, pathlib, sys, datetime
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
URL = (sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html') + '?test'
BOK = json.loads((ROT / 'test' / 'bocker' / 'format-10.json').read_text(encoding='utf-8'))
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

RATES = "(ids) => Object.fromEntries(ids.map(([k, rk, d]) => { const id = [...E.values()].find(e => !e.deleted && e.projectId + '~' + e.taskId === rk && e.date === d)?.id; return [k, id ? E.get(id).rate : null]; }))"
POSTER = [['a', 'proj3~upg4', '2026-11-02'], ['b', 'proj3~upg4', '2026-11-10'], ['c', 'proj3~upg4', '2026-11-17'], ['d', 'proj1~upg1', '2026-11-17']]

def akt(pg, act, **data):
    # klickar en tillfällig knapp med data-act – samma väg som appens egna knappar
    attrs = ' '.join(f'data-{k}="{v}"' for k, v in data.items())
    pg.evaluate("(h) => { document.getElementById('tb')?.remove(); document.body.insertAdjacentHTML('beforeend', h); document.getElementById('tb').click(); }", f'<button id="tb" data-act="{act}" {attrs}>x</button>')
    pg.wait_for_timeout(300)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, js = starta(b, BOK)
    r = ev(pg, "() => ({ v: S.version, fmt: FORMAT_VERSION, rates: S.register.roles.map(r => r.rate), p2: S.register.projects[1].roleRates })")
    ok(r['v'] == r['fmt'] == 11 and r['rates'] == [950, 1150] and r['p2'] == {'roll1': 1000}, f"format 10 → {r['v']}, priserna oförändrade ({r['rates']}, {r['p2']})")

    # Prislistan
    r = ev(pg, """() => { const L = rPut(900, 1000, '2027-01-01');
      return { L, före: rv(L, '2026-12-31'), på: rv(L, '2027-01-01'), efter: rv(L, '2027-06-01'),
        åter: rPut(L, 900, '2027-01-01'), början: rPut(L, 1100, ''), tom: rPut(undefined, null, '2027-01-01'),
        arv: rv(rPut(undefined, 800, '2027-01-01'), '2026-12-31'), txt: rHist(L) }; }""")
    ok(r['L'] == [{'from': '', 'rate': 900}, {'from': '2027-01-01', 'rate': 1000}], f"prislista: {r['L']}")
    ok((r['före'], r['på'], r['efter']) == (900, 1000, 1000), 'pris före, på och efter datumet')
    ok(r['åter'] == 900 and r['början'] == 1100 and r['tom'] is None and r['arv'] is None, 'samma pris slås ihop, ”från början” ger ett tal, före första steget gäller nästa nivå')
    ok('1000 kr/h' in r['txt'].replace('\u00a0', '').replace('\u202f', '').replace(' 000', '000') and '2027' in r['txt'], 'prislistan som text: ' + r['txt'])

    # Ordningen bok → kund → projekt → person → uppgift
    r = ev(pg, """() => { const R0 = JSON.stringify(S.register), P = S.register.projects[0], C = S.register.customers[0], out = [];
      const f = () => rateFor(P.id, 'roll1', me(), '2026-11-18', 'upg1');
      out.push(f()); C.roleRates = { roll1: 1010 }; out.push(f()); P.roleRates = { roll1: 1020 }; out.push(f());
      P.personRates = { [me()]: { roll1: 1030 } }; out.push(f()); P.tasks[0].rate = 1040; out.push(f());
      out.push(rateFor(P.id, 'roll1', me(), '2026-11-18', 'upg2'));
      S.register = JSON.parse(R0); return out; }""")
    ok(r == [950, 1010, 1020, 1030, 1040, 1030], f'mest specifika priset vinner: {r}')

    # Fyra tidposter: v45 (checkas av), v46, v47 i Förskolan Lärkan (din roll där: Uppdragsansvarig) och v47 i Villa Strand (Arkitekt)
    ev(pg, "(L) => { for (const [, rk, d] of L) setCell(rk, d, { hours: 2, note: 'test' }); weekEvent('2026-11-02', true); }", POSTER)
    r = ev(pg, RATES, POSTER)
    ok(r == {'a': 1150, 'b': 1150, 'c': 1150, 'd': 950}, f'nya poster får rollens centrala pris: {r}')

    # Redigera projekt: 1 200 från 15 nov
    akt(pg, 'projEdit', p='proj3')
    ok(pg.locator('#pjForm').count() == 1, 'Redigera projekt öppnas')
    pg.fill('#pjForm [data-rr=roll2]', '1200')
    pg.fill('#pjRFD', '2026-11-15')
    pg.click('#pjForm button[type=submit]'); pg.wait_for_timeout(300)
    t = pg.inner_text('#toast') if pg.locator('#toast').count() else ''
    r = ev(pg, RATES, POSTER)
    ok(r == {'a': 1150, 'b': 1150, 'c': 1200, 'd': 950}, f'från 15 nov: bara olåst tid från datumet räknas om ({r})')
    ok('en tidpost fick det nya priset' in t, 'beskedet: ' + t.replace('\n', ' '))
    rr = ev(pg, "() => S.register.projects.find(p => p.id === 'proj3').roleRates")
    ok(rr == {'roll2': [{'from': '2026-11-15', 'rate': 1200}]}, f'projektets prislista: {rr}')
    # Tid som skrivs in efteråt för en tidigare dag
    ev(pg, "() => { setCell('proj3~upg4', '2026-11-12', { hours: 1, note: 'efteråt' }); setCell('proj3~upg4', '2026-11-16', { hours: 1, note: 'efteråt' }); }")
    r = ev(pg, RATES, [['e', 'proj3~upg4', '2026-11-12'], ['f', 'proj3~upg4', '2026-11-16']])
    ok(r == {'e': 1150, 'f': 1200}, f'tid som skrivs in efteråt får priset som gällde dagen ({r})')
    # Ångra
    pg.click('#toast button'); pg.wait_for_timeout(300)
    r = ev(pg, RATES, POSTER); rr = ev(pg, "() => S.register.projects.find(p => p.id === 'proj3').roleRates")
    ok(r['c'] == 1150 and rr == {}, f'Ångra lägger tillbaka priset och posten ({r}, {rr})')
    ev(pg, "() => { setCell('proj3~upg4', '2026-11-12', { hours: 0, note: '' }); setCell('proj3~upg4', '2026-11-16', { hours: 0, note: '' }); }")

    # Centralt pris från början: all olåst tid
    pg.click('.rail [data-page=installningar]'); pg.wait_for_timeout(300)
    inp = pg.locator('[data-role=roll2] [data-rolef=rate]')
    inp.fill('1160'); inp.press('Tab'); pg.wait_for_timeout(300)
    ok(pg.locator('#rrForm').count() == 1, 'nytt centralt pris frågar från när det gäller')
    pg.check('input[name=rrF][value=""]'); pg.click('#rrForm button[type=submit]'); pg.wait_for_timeout(300)
    r = ev(pg, RATES, POSTER)
    ok(r == {'a': 1150, 'b': 1160, 'c': 1160, 'd': 950}, f'centralt pris från början: olåst tid räknas om, avcheckad vecka inte ({r})')
    ok('annat timpris' in (pg.inner_text('#dlgTitle') if pg.locator('#dlgTitle').count() else ''), 'avcheckad tid med annat pris: dialogen frågar')
    pg.click('button:has-text("Behåll de gamla priserna")'); pg.wait_for_timeout(300)
    ok(ev(pg, RATES, POSTER)['a'] == 1150, 'Behåll de gamla priserna: den avcheckade posten orörd')
    ok(ev(pg, "() => S.register.roles[1].rate") == 1160, 'centralt pris utan prislista blir ett tal')

    # Kundens pris (Familjen Strand → Villa Strand) från 17 nov
    pg.click('.rail [data-page=kunder]'); pg.wait_for_timeout(300)
    pg.click('.ccard:has-text("Familjen Strand") h2'); pg.wait_for_timeout(300)
    pg.click('[data-act=custEdit]'); pg.wait_for_timeout(300)
    pg.fill('#cuForm [data-cr=roll1]', '1100'); pg.fill('#cuRFD', '2026-11-17')
    pg.click('#cuForm button[type=submit]'); pg.wait_for_timeout(300)
    r = ev(pg, RATES, POSTER)
    ok(r['d'] == 1100 and r['c'] == 1160, f'kundens pris gäller kundens projekt ({r})')

    # Uppgiftens pris i projektdialogen (Villa Strand, Bygglov)
    akt(pg, 'projEdit', p='proj1')
    if pg.locator('#pjForm').count():
        pg.fill('#pjForm .tk-row[data-tid=upg1] .tk-rate', '1300'); pg.check('input[name=pjRF][value=""]')
        pg.click('#pjForm button[type=submit]'); pg.wait_for_timeout(300)
    r = ev(pg, RATES, POSTER)
    ok(r['d'] == 1300, f'uppgiftens pris går före kundens ({r})')

    # Synk: ett pris som ändrats på en annan enhet räknar om den här enhetens olåsta tid
    r = ev(pg, """() => { const B = JSON.parse(JSON.stringify(S)); B.register.projects.find(p => p.id === 'proj3').roleRates = { roll2: [{ from: '2026-11-10', rate: 1250 }] };
      webApply(B); return null; }""")
    pg.wait_for_timeout(300)
    r = ev(pg, RATES, POSTER)
    ok(r == {'a': 1150, 'b': 1250, 'c': 1250, 'd': 1300}, f'ändring via synken räknar om olåst tid ({r})')

    # 0.17.1: pris satt "från i dag" och sedan rättat till "från början" utan att ändra värdet (inkorgen 2026-10-27)
    akt(pg, 'projEdit', p='proj3')
    pg.fill('#pjForm [data-rr=roll2]', '1300'); pg.click('#pjForm button[type=submit]'); pg.wait_for_timeout(300)
    r = ev(pg, RATES, POSTER)
    ok(r['b'] == 1250 and r['c'] == 1250, f'från i dag: tidigare dagar orörda ({r})')
    akt(pg, 'projEdit', p='proj3')
    ok(pg.input_value('#pjForm [data-rr=roll2]') == '1300', 'fältet visar dagens pris')
    pg.check('input[name=pjRF][value=""]'); pg.click('#pjForm button[type=submit]'); pg.wait_for_timeout(300)
    r = ev(pg, RATES, POSTER)
    ok(r['b'] == 1300 and r['c'] == 1300, f'samma pris "från början": olåst tid räknas om ({r})')
    ok(pg.locator('#dlgTitle:has-text("annat timpris")').count() == 1, 'den avcheckade veckan frågas om')
    pg.click('[data-act=repriceAskGo]'); pg.wait_for_timeout(300)
    r = ev(pg, RATES, POSTER); t = pg.inner_text('#toast')
    ok(r['a'] == 1300 and 'avcheckade' in t, f'Använd det nya priset: avcheckad tid räknas om ({r}, {t!r})')
    pg.click('#toast button'); pg.wait_for_timeout(300)
    ok(ev(pg, RATES, POSTER)['a'] == 1150, 'Ångra lägger tillbaka det avcheckade priset')
    # Samma pris skrivet om med ett tidigare datum räknar också om tid med ett avvikande sparat pris
    ev(pg, "() => { const e = [...E.values()].find(e => !e.deleted && e.projectId === 'proj3' && e.date === '2026-11-10'); const ev = { id: uid(), entryId: e.id, type: 'update', at: new Date().toISOString(), by: me(), dev: devId(), data: { rate: 999 } }; log().push(ev); apply(ev, me()); save(); }")
    akt(pg, 'projEdit', p='proj3')
    pg.fill('#pjForm [data-rr=roll2]', '1300'); pg.fill('#pjRFD', '2026-11-05'); pg.click('#pjForm button[type=submit]'); pg.wait_for_timeout(300)
    if pg.locator('button:has-text("Behåll de gamla priserna")').count(): pg.click('button:has-text("Behåll de gamla priserna")'); pg.wait_for_timeout(200)
    ok(ev(pg, RATES, POSTER)['b'] == 1300, 'ett avvikande sparat pris i den ändrade nivån räknas om från datumet')

    # Rensa i egenskapspanelen och snabbknappar i smartmenyn
    pg.click('.rail [data-page=tid]'); pg.wait_for_timeout(300)
    ev(pg, "() => { st.view = 'week'; st.week = '2026-11-16'; render(); }"); pg.wait_for_timeout(200)
    ev(pg, "() => select('proj3~upg4|2026-11-17')"); pg.wait_for_timeout(200)
    ok(pg.locator('#panel [data-act=clearCell]').count() == 1, 'Rensa finns i egenskapspanelen')
    ok(pg.locator('#panel .p-link[data-act=openProject]').count() == 1, 'panelens rubrik leder till projektsidan')
    pg.click('#panel [data-act=clearCell]'); pg.wait_for_timeout(200)
    ok(ev(pg, RATES, POSTER)['c'] is None or ev(pg, "() => cell('proj3~upg4', '2026-11-17')?.hours || 0") == 0, 'Rensa tömmer rutan')
    pg.click('#toast button'); pg.wait_for_timeout(200)
    box = pg.locator('.cell[data-cellbox="proj3~upg4|2026-11-17"]')
    if box.count():
        box.click(); pg.wait_for_timeout(300)
        ok(pg.locator('#cpop .cp-chips .chip').count() == 5, 'smartmenyn har snabbknappar för tiden')
        pg.click('#cpop .cp-chips .chip:has-text("4")'); pg.wait_for_timeout(200)
        ok(ev(pg, "() => cell('proj3~upg4', '2026-11-17')?.hours") == 4, 'snabbknappen sätter tiden')
        ev(pg, "() => closeCellPop()")

    # Signering – ensam bok: av
    pg.click('.rail [data-page=tid]'); pg.wait_for_timeout(300)
    ok(ev(pg, "() => signOn()") is False, 'signering är av för en ensam bok')
    pg.fill('#quickIn', 'sign v47'); pg.wait_for_timeout(300)
    ok('avstängd' in pg.inner_text('#quickHint'), 'sign i smartshell: ' + pg.inner_text('#quickHint'))
    pg.fill('#quickIn', '')
    pg.click('.rail [data-page=installningar]'); pg.wait_for_timeout(300)
    pg.check('#setSign'); pg.wait_for_timeout(200)
    ok(ev(pg, "() => signOn()") is True, 'signering kan slås på')
    # Den signerade veckan i exempelboken (v41) låses upp
    ok(ev(pg, "() => !!weekState('2026-10-05').signed") is True, 'v41 är signerad')
    pg.click('.rail [data-page=tid]'); pg.wait_for_timeout(200)
    pg.fill('#quickIn', 'öppna v41 2026'); pg.wait_for_timeout(300)
    ok('låser upp' in pg.inner_text('#quickHint'), 'öppna en signerad vecka: ' + pg.inner_text('#quickHint'))
    pg.press('#quickIn', 'Enter'); pg.wait_for_timeout(300)
    pg.fill('#cfType', 'ok'); pg.press('#cfType', 'Enter'); pg.wait_for_timeout(300)
    r = ev(pg, "() => weekState('2026-10-05')")
    ok(not r['signed'] and not r['checked'], f'v41 är upplåst och öppen ({r})')

    ok(not js, 'inga JavaScript-fel' + (': ' + '; '.join(js) if js else ''))
    b.close()

print('\n' + ('Allt OK' if not fel else f'{fel} fel'))
sys.exit(1 if fel else 0)
