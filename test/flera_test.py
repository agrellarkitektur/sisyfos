#!/usr/bin/env python3
"""
Sisyfos – arbetet med flera (0.18.0, filformat 11 oförändrat).

Kontrollerar i en riktig webbläsare, med en bok där administratören (pers1 "Du") och medarbetaren Anna Berg (pers2)
båda har tid, att
  – administratören kan välja vems tidbok som visas (Din tid / Anna Berg) och ser vilka veckor som inte är avcheckade,
  – Annas tid är skrivskyddad för admin (ingen tid och ingen dagsanteckning kan skrivas, smartshell säger ifrån),
  – admin kan öppna Annas avcheckade vecka, signera den och låsa upp den – i personkortet (register.reopened/signed),
    och att markeringarna följer med delen card.<person> när boken delas (bookSplit/bookJoin förlustfritt),
  – Anna kan checka av på nytt efter att admin öppnat veckan,
  – smartshell: sign v45 Anna, öppna v45 Anna, proj … Anna 850 (pris för personen i projektet),
  – Så påverkas summan tar med Annas tid; admins godkännande sparas som en omräkning i Annas kort, görs på Annas enhet
    (repriceOrders) – också avcheckad tid när admin valt det nya priset, aldrig signerad – och städas sedan bort av admin,
  – projektsidans Medarbetare visar personerna med pris, öppen tid och genväg till tidboken,
  – personsammanställningen och dialogen Anställning, saldo och semester gäller personen som visas,
  – medarbetaren i en organisation ser bokens inställningar skrivskyddade, kan inte skapa projekt eller ändra budget,
    och ser inte budgetens förbrukning.

Kör:  python3 -m http.server 8765 &  python3 test/flera_test.py
"""
import json, pathlib, sys, datetime, re
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
URL = (sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html') + '?test'
fel = 0
def ev(page, fn, arg=None):
    return page.evaluate("([f, a]) => { with (window.SISYFOS) { return eval('(' + f + ')')(a); } }", [fn, arg])
def ok(cond, text):
    global fel
    print(('OK  ' if cond else 'FEL ') + text); fel += not cond

def bok2():
    b = json.loads((ROT / 'test' / 'bocker' / 'format-11.json').read_text(encoding='utf-8'))
    b['register']['people'].append({'id': 'pers2', 'name': 'Anna Berg', 'initials': 'AB', 'defaultRoleId': 'roll1', 'admin': False, 'employment': 'full', 'pct': 100,
                                    'balanceStart': '2026-10-01', 'balanceIn': 0, 'vacation': {'perYear': 25, 'yearStart': '04-01', 'from': '2026-04-01', 'saved': []}})
    evs = []
    def add(i, d, p, t, h, note):
        evs.append({'id': f'a{i}', 'entryId': f'ae{i}', 'type': 'create', 'at': d + 'T16:00:00.000Z', 'by': 'pers2', 'dev': 'eA',
                    'data': {'date': d, 'projectId': p, 'taskId': t, 'roleId': 'roll1', 'hours': h, 'note': note, 'rate': 950}})
    for i, d in enumerate(['2026-11-02', '2026-11-03', '2026-11-04'], 1): add(i, d, 'proj1', 'upg1', 6, 'Bygglovshandlingar')
    add(4, '2026-11-09', 'proj1', 'upg1', 7, 'Komplettering')
    add(5, '2026-11-10', 'proj1', 'upg1', 7, 'Komplettering')
    add(6, '2026-11-16', 'proj1', 'upg1', 5, 'Ritningar')
    evs.append({'id': 'aw1', 'entryId': None, 'type': 'week', 'at': '2026-11-06T16:00:00.000Z', 'by': 'pers2', 'dev': 'eA', 'data': {'week': '2026-11-02', 'checked': True}})
    b['logs']['pers2'] = {'events': evs}
    b['register']['book']['signWeeks'] = True   # exempelboken har signering avstängd (ensam)
    return b

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

def shell(pg, txt):
    pg.fill('#quickIn', txt); pg.wait_for_timeout(250)
    return pg.inner_text('#quickHint')

def toast(pg):
    return pg.evaluate("() => [...document.querySelectorAll('.toast, #toast')].map(t => t.innerText).join(' | ')")

WK45, WK46 = '2026-11-02', '2026-11-09'

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, js = starta(b, bok2())

    # Vems tidbok
    ok(pg.locator('[data-act=asMenu]').count() == 1, 'admin har knappen för vems tidbok')
    pg.click('[data-act=asMenu]'); pg.wait_for_timeout(250)
    meny = pg.inner_text('#menu')
    ok('Anna Berg' in meny and 'v 46 inte avcheckad' in meny, 'menyn visar Anna och att v 46 inte är avcheckad')
    pg.click('#menu [data-p=pers2]'); pg.wait_for_timeout(300)
    r = ev(pg, "() => ({ who: who(), viewing: viewing(), n: live().length, me: me(), lk: weekState('2026-11-16').checked })")
    ok(r['who'] == 'pers2' and r['viewing'] and r['n'] == 6 and r['me'] == 'pers1', f"Annas tidbok visas: {r}")
    ok(pg.locator('.as-bar').count() == 1 and 'Anna Bergs tidbok' in pg.inner_text('.as-bar'), 'raden ”Anna Bergs tidbok – skrivskyddad” syns')
    ok(pg.locator('.add-row').count() == 0, 'ingen ”Lägg till rad” i någon annans tidbok')
    ok(ev(pg, "() => { try { return document.querySelector('.board.locked') !== null; } catch (e) { return false; } }"), 'veckan visas låst')
    h = shell(pg, '3 strand ritade')
    ok('bara Anna skriver sin tid' in h, 'smartshell skriver ingen tid i Annas tidbok: ' + h)
    h = shell(pg, 'ch')
    ok('egen tid' in h, 'ch i Annas tidbok: ' + h)
    pg.fill('#quickIn', '')

    # Öppna, signera och låsa upp Annas vecka 45
    pg.click('[data-act=week][data-d="-7"]'); pg.wait_for_timeout(200); pg.click('[data-act=week][data-d="-7"]'); pg.wait_for_timeout(300)
    ok('Öppna åt Anna' in pg.inner_text('.as-bar') and 'Signera' in pg.inner_text('.as-bar'), 'v45 (avcheckad): Öppna åt Anna och Signera')
    pg.click('.as-bar [data-act=signWeek]'); pg.wait_for_timeout(300)
    pg.fill('#cfType', 'sign'); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    r = ev(pg, "() => ({ s: S.register.signed['pers2|2026-11-02'], own: S.register.signed['pers1|2026-11-02'] })")
    ok(bool(r['s']) and r['s']['by'] == 'pers1' and not r['own'], 'admin signerar Annas vecka (pers2|v45)')
    pg.click('.as-bar [data-act=unsignWeek]'); pg.wait_for_timeout(300)
    pg.fill('#cfType', 'ok'); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    r = ev(pg, "() => ({ s: S.register.signed['pers2|2026-11-02'] || null, o: S.register.reopened?.['pers2|2026-11-02'] || null, ws: weekState('2026-11-02', 'pers2') })")
    ok(r['s'] is None and r['o'] and not r['ws']['checked'], f"upplåst: signeringen borta och veckan öppen ({r['ws']})")
    n_log = ev(pg, "() => S.logs.pers2.events.length")
    ok(n_log == 7, 'admin skrev ingenting i Annas logg')
    # Anna checkar av på nytt (hennes händelse är nyare än öppningen)
    ev(pg, "() => { const e = { id: uid(), entryId: null, type: 'week', at: new Date().toISOString(), by: 'pers2', dev: 'eA', data: { week: '2026-11-02', checked: true } }; S.logs.pers2.events.push(e); apply(e, 'pers2'); save(); render(); }")
    ok(ev(pg, "() => weekState('2026-11-02', 'pers2').checked"), 'Anna checkar av igen – veckan är avcheckad')
    pg.click('.as-bar [data-act=reopenWeek]'); pg.wait_for_timeout(300)
    ok(not ev(pg, "() => weekState('2026-11-02', 'pers2').checked"), 'Öppna åt Anna öppnar veckan')
    pg.click('#toast [data-act=toastAct]')
    pg.wait_for_timeout(300)
    ok(ev(pg, "() => weekState('2026-11-02', 'pers2').checked"), 'Ångra stänger veckan igen')

    # Delarna: personkortet bär signerat och öppnat
    r = ev(pg, """() => { S.register.signed['pers2|2026-11-09'] = { at: '2026-11-17T10:00:00Z', by: 'pers1' }; S.register.reopened['pers2|2026-11-02'] = { at: '2026-11-17T09:00:00Z', by: 'pers1' };
      const P = bookSplit(S), back = bookJoin(P);
      const r = { card: Object.keys(P['card.pers2']), reg: 'reopened' in P.reg.register || 'signed' in P.reg.register, same: canon(back.register) === canon(S.register) };
      delete S.register.signed['pers2|2026-11-09']; delete S.register.reopened['pers2|2026-11-02']; derive(); return r; }""")
    ok('signed' in r['card'] and 'reopened' in r['card'] and not r['reg'] and r['same'], f"card.pers2 har signed och reopened, registret inte, förlustfritt ({r})")

    # Smartshell åt andra
    pg.click('.as-bar [data-act=asPick]'); pg.wait_for_timeout(300)
    ok(ev(pg, "() => !viewing()") and pg.locator('.as-bar').count() == 0, 'Till din tid')
    h = shell(pg, 'sign v45 Anna')
    ok('signerar' in h and 'Anna Berg' in h, 'sign v45 Anna: ' + h)
    pg.keyboard.press('Enter'); pg.wait_for_timeout(300); pg.fill('#cfType', 'sign'); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    ok(bool(ev(pg, "() => S.register.signed['pers2|2026-11-02']")), 'sign v45 Anna signerar Annas vecka')
    h = shell(pg, 'sign v46 anna')
    ok('inte avcheckad av Anna' in h, 'sign på en vecka Anna inte checkat av: ' + h)
    h = shell(pg, 'öppna v45 AB')
    ok('låser upp' in h and 'Anna Berg' in h, 'öppna v45 AB (initialer): ' + h)
    pg.keyboard.press('Enter'); pg.wait_for_timeout(300); pg.fill('#cfType', 'ok'); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    ok(not ev(pg, "() => S.register.signed['pers2|2026-11-02']") and not ev(pg, "() => weekState('2026-11-02', 'pers2').checked"), 'öppna v45 AB låser upp och öppnar')
    h = shell(pg, 'sign v45 Kalle')
    ok('Hittar ingen person' in h, 'okänt namn: ' + h)
    h = shell(pg, 'proj Tennishallen 100k Anna 850')
    ok('Anna Bergs timpris' in h and 'Tennishallen' in h, 'proj … Anna 850: ' + h)
    pg.keyboard.press('Enter'); pg.wait_for_timeout(400)
    r = ev(pg, "() => { const P = S.register.projects.find(p => p.name === 'Tennishallen'); return P && { pr: P.personRates, rr: P.roleRates, cust: P.customerId }; }")
    ok(r and r['pr'] == {'pers2': {'roll1': 850}} and not r['rr'] and not r['cust'], f"projektet får Annas pris, ingen kund ({r})")
    pg.goto(URL); pg.wait_for_timeout(1000)
    h = shell(pg, 'proj strand anna 1300')
    ok('Anna Bergs timpris i' in h and 'Villa Strand' in h, 'proj strand anna 1300 (befintligt projekt): ' + h)
    pg.keyboard.press('Enter'); pg.wait_for_timeout(400)
    r = ev(pg, "() => S.register.projects[0].personRates?.pers2")
    ok(r == {'roll1': [{'from': '2026-11-18', 'rate': 1300}]} and pg.locator('#dlg:not([hidden])').count() == 0, f"från i dag – ingen rapporterad tid berörs, sparas direkt ({r})")
    pg.click('#toast [data-act=toastAct]'); pg.wait_for_timeout(300)
    ok(ev(pg, "() => !S.register.projects[0].personRates?.pers2"), 'Ångra tar bort Annas pris')
    pg.fill('#quickIn', '')

    # Så påverkas summan med Annas tid: admins godkännande → omräkning i Annas kort
    n0 = ev(pg, "() => S.logs.pers2.events.length")
    r = ev(pg, """() => { const snap = rateSnap(), prevReg = JSON.stringify(S.register), P = S.register.projects[0];
      P.roleRates = { ...(P.roleRates || {}), roll1: 1200 };
      window.__fin = null; priceGate({ snap, keys: new Set(['pr|proj1|roll1']), from: '', prevReg, finish: ch => { window.__fin = { n: ch.length, others: ch.others, orders: ch.orders }; closeDlg(); } });
      return !!st.pg; }""")
    ok(r, 'priceGate öppnar dialogen för en ändring som rör Annas tid')
    txt = pg.inner_text('#dlg')
    ok('Anna Berg' in txt and 'avcheckade' in txt, 'dialogen nämner Anna och avcheckad tid')
    pg.click('#dlg [data-act=pgGo]'); pg.wait_for_timeout(300)
    r = ev(pg, """() => { const R0 = S.register.reprice || {}, k = Object.keys(R0); return { k, items: k.map(x => R0[x].items), fin: window.__fin, anna: S.logs.pers2.events.length }; }""")
    items = r['items'][0] if r['items'] else {}
    ok(len(r['k']) == 1 and r['k'][0].startswith('pers2|') and set(items) == {'ae1', 'ae2', 'ae3', 'ae4', 'ae5', 'ae6'} and set(items.values()) == {1200}, f"omräkningen i Annas kort: {r['k']} {items}")
    ok(r['anna'] == n0 and r['fin']['others'] == 6, 'admin skrev inget i Annas logg, beskedet räknar Annas poster')
    # Annas enhet: omräkningen görs vid synken
    r = ev(pg, """() => { S.session.personId = 'pers2'; derive(); const n = repriceOrders(); save();
      const rates = [...E.values()].filter(e => e.person === 'pers2' && !e.deleted).map(e => e.rate); S.session.personId = 'pers1'; derive(); const pr = repricePrune(); save();
      return { n, rates, pr, left: S.register.reprice }; }""")
    ok(r['n'] == 6 and set(r['rates']) == {1200}, f"Annas enhet räknar om sina poster ({r['n']}, {r['rates']})")
    ok(r['pr'] and not r['left'], f"admin städar bort den gjorda omräkningen ({r['left']})")
    # Signerad vecka räknas aldrig om, Behåll de gamla priserna gäller avcheckad tid
    r = ev(pg, """() => { S.register.signed['pers2|2026-11-09'] = { at: new Date().toISOString(), by: 'pers1' };
      const w = { id: uid(), entryId: null, type: 'week', at: new Date().toISOString(), by: 'pers2', dev: 'eA', data: { week: '2026-11-02', checked: true } }; S.logs.pers2.events.push(w); derive();
      const snap = rateSnap(), prevReg = JSON.stringify(S.register), P = S.register.projects[0]; P.roleRates.roll1 = 1250;
      priceGate({ snap, keys: new Set(['pr|proj1|roll1']), from: '', prevReg, finish: () => closeDlg() }); return !!st.pg; }""")
    pg.click('#dlg [data-act=pgMode][data-v=keep]'); pg.wait_for_timeout(200); pg.click('#dlg [data-act=pgGo]'); pg.wait_for_timeout(300)
    r = ev(pg, "() => { const R0 = S.register.reprice || {}; return Object.values(R0).flatMap(o => Object.keys(o.items)).sort(); }")
    ok(r == ['ae6'], f"bara Annas olåsta tid (v47) – inte avcheckad (Behåll) eller signerad: {r}")
    ev(pg, "() => { delete S.register.signed['pers2|2026-11-09']; delete S.register.reprice; save(); }")

    # Projektsidan: Medarbetare
    akt(pg, 'openProject', p='proj1'); pg.wait_for_timeout(300)
    t = pg.inner_text('.ppl')
    ok('Anna Berg' in t and 'Du' in t and pg.locator('.ppl [data-act=asGo][data-p=pers2]').count() == 1, 'projektsidans Medarbetare: Du och Anna Berg med genväg till tidboken')
    pg.click('.ppl [data-act=asGo][data-p=pers2]'); pg.wait_for_timeout(300)
    ok(ev(pg, "() => who() === 'pers2' && st.page === 'tid'"), 'Tidbok-knappen öppnar Annas tidbok')

    # Anställning, saldo och semester för Anna
    akt(pg, 'personDlg'); pg.wait_for_timeout(300)
    ok('Anna Berg' in pg.inner_text('#dlgTitle'), 'dialogen gäller Anna')
    pg.fill('#psIn', '12'); pg.click('#psForm [type=submit]'); pg.wait_for_timeout(300)
    r = ev(pg, "() => ({ a: S.register.people[1].balanceIn, du: S.register.people[0].balanceIn })")
    ok(r['a'] == 12 and r['du'] == 6, f"admin ändrar Annas ingående saldo, inte sitt eget ({r})")

    # Personsammanställningen följer valet
    pg.click('.rail [data-page=rapporter]'); pg.wait_for_timeout(300)
    akt(pg, 'repTab', tab='person'); pg.wait_for_timeout(300)
    ok(pg.locator('#rpPers').count() == 1 and pg.eval_on_selector('#rpPers', 'e => e.value') == 'pers2', 'personsammanställningen har val av person (Anna)')
    pg.select_option('#rpPers', ''); pg.wait_for_timeout(300)
    ok(ev(pg, "() => !viewing()"), 'val av ”Du” går tillbaka till din tid')
    ok(not js, 'admin: inga JavaScript-fel ' + '; '.join(js[:3]))
    ctx.close()

    # Medarbetaren i en organisation: skrivskyddat det hon inte skriver
    bk = bok2(); bk['session'] = {'personId': 'pers2'}
    ctx, pg, js = starta(b, bk)
    ev(pg, "() => { st.web = { email: 'anna@x.se', token: 't', org: 'o1', orgName: 'Testbolaget', role: 'member', pid: 'pers2' }; render(); }")
    ok(ev(pg, "() => document.body.classList.contains('ro') && !isAdm()"), 'medarbetaren: body.ro')
    ok(pg.locator('[data-act=asMenu]').count() == 0, 'medarbetaren väljer inte vems tidbok')
    h = shell(pg, 'budget strand 200k')
    ok('administratören' in h, 'budget i smartshell: ' + h)
    h = shell(pg, 'proj Nytt hus 50000')
    ok('administratören' in h, 'nytt projekt i smartshell: ' + h)
    h = shell(pg, '2 strand ritade')
    ok('administratören' not in h, 'tid går att skriva: ' + h)
    pg.fill('#quickIn', '')
    akt(pg, 'newProject')
    ok(pg.locator('#dlg:not([hidden])').count() == 0, 'Nytt projekt öppnas inte för medarbetaren')
    ok(ev(pg, "() => budgetPct(S.register.projects[0]) === null && alertsHtml().indexOf('budgeten') < 0"), 'medarbetaren ser inte budgetens förbrukning')
    pg.click('.rail [data-page=installningar]'); pg.wait_for_timeout(300)
    ok(pg.locator('#set-roles[inert]').count() == 1 and pg.locator('#set-book[inert]').count() == 0 and pg.locator('.set-ro').count() == 1, 'Inställningar: roller skrivskyddade, Spara boken går att använda')
    akt(pg, 'personDlg'); pg.wait_for_timeout(300)
    ok(pg.locator('#psForm .ro-note').count() == 1 and pg.locator('#psEmp[disabled]').count() == 1, 'medarbetaren ser sitt personkort skrivskyddat')
    js2 = [e for e in js if 'api' not in e.lower() and 'fetch' not in e.lower()]
    ok(not js2, 'medarbetaren: inga JavaScript-fel ' + '; '.join(js2[:3]))
    ctx.close()
    b.close()

print('\nAllt OK' if not fel else f'\n{fel} FEL'); sys.exit(1 if fel else 0)
