#!/usr/bin/env python3
"""
Sisyfos 0.20.1 – rättningarna ur granskningen av 0.20.0 (claude/granskning.md i projektet).

Ett prov per fynd, i en riktig webbläsare med exempelboken format 12:
  A1  två poster i samma ruta (två enheter) slås ihop – rutan och summorna visar samma, nästa ändring skriver ihop dem
  A2  egna kommandon med skriptkod körs inte i smartshellens förteckning; en medarbetares inställningar hamnar inte hos admin
  A3  fingeravtrycket räknas ur nycklarna – ett påhittat avtryck godtas inte
  A4  för få PBKDF2-varv från servern eller i en fil vägras
  A5  ett projekt eller en uppgift som tagits bort medan någon annan skrev tid läggs tillbaka; vyerna klarar tid utan projekt
  A6  kost strand taxi 1 500 bokför 1 500 kr
  B1  avrundningen till öre är lika åt båda håll (kreditfakturans moms)
  B2  en händelse i en persons logg ändrar inte någon annans post eller kostnad
  B11 en ruta som tömts på en annan enhet förblir tömd (användarens beslut)
  B12 fakturautkastet behåller radens belopp i en bok utan avrundning
  B13 en fakturas låsning omfattar bara dagar den själv låste – kreditering låser upp
  C   restoreRow räknar inte upp, dag efter projektet i snabbinmatningen, Summa kostnader i dagboken

Kör:  python3 -m http.server 8765 &  python3 test/rattning_test.py
"""
import json, pathlib, sys, datetime, subprocess, tempfile
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
URL = (sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html') + '?test'
BOK = json.loads((ROT / 'test' / 'bocker' / 'format-12.json').read_text(encoding='utf-8'))
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

def shell(pg, txt, enter=False):
    pg.fill('#quickIn', txt); pg.wait_for_timeout(250)
    h = pg.inner_text('#quickHint')
    if enter: pg.press('#quickIn', 'Enter'); pg.wait_for_timeout(300)
    return h

# Händelse i en logg: create med fasta id:n
EVJS = """(a) => { const [pid, ev] = a; S.logs[pid] = S.logs[pid] || { events: [] }; S.logs[pid].events.push(ev); return true; }"""
def hand(pg, pid, **e):
    ev(pg, EVJS, [pid, e])

def cr(eid, at, d, p, t, h, note='', rate=1000, dev='devX'):
    return dict(id='h' + eid, entryId=eid, type='create', at=at, by='pers1', dev=dev,
                data=dict(date=d, projectId=p, taskId=t, roleId='roll1', hours=h, note=note, rate=rate))

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, service_workers='block', accept_downloads=True)
    ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(BOK))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.clock.install(time=datetime.datetime(2026, 11, 18, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(1200)
    ok(ev(pg, "() => S.version") == 12, 'format 12')

    # ── A1: två poster i samma ruta
    RK, D = 'proj1~upg2', '2026-11-16'
    hand(pg, 'pers1', **cr('dA', '2026-11-16T08:00:00.000Z', D, 'proj1', 'upg2', 4, 'ritade', dev='telefon'))
    hand(pg, 'pers1', **cr('dB', '2026-11-16T09:00:00.000Z', D, 'proj1', 'upg2', 3, 'möte', dev='dator'))
    ev(pg, "() => { derive(); st.page = 'tid'; st.view = 'week'; st.week = '2026-11-16'; render(); }"); pg.wait_for_timeout(200)
    c = ev(pg, f"() => {{ const e = cell('{RK}', '{D}'); return {{ h: e.hours, note: e.note, dups: e.dups }}; }}")
    dag = ev(pg, f"() => live().filter(e => e.date === '{D}' && e.taskId === 'upg2').reduce((s, e) => s + e.hours, 0)")
    ok(c['h'] == 7 and dag == 7, f'A1: rutan visar 7 h och dagens summa 7 h ({c["h"]}, {dag})')
    ok('ritade' in c['note'] and 'möte' in c['note'], f'A1: anteckningarna efter varandra ({c["note"]})')
    dbok = ev(pg, "() => diaryData('proj1', '2026-11-01', '2026-11-30', true).hours")
    ok(abs(dbok - 7) < 1e-9, f'A1: projektdagboken räknar 7 h ({dbok})')
    ev(pg, f"() => setCell('{RK}', '{D}', {{ hours: 2 }})"); ev(pg, "() => derive()")
    efter = ev(pg, f"() => [cell('{RK}', '{D}').hours, live().filter(e => e.date === '{D}' && e.taskId === 'upg2').reduce((s, e) => s + e.hours, 0)]")
    ok(efter == [2, 2], f'A1: rättad till 2 h – rutan och summan 2 efter omräkning ur loggen ({efter})')
    ok(ev(pg, "() => S.logs.pers1.events.some(e => e.type === 'delete' && e.data?.merged)"), 'A1: ihopslagningen är skriven i loggen (dubbletten borttagen)')
    # IDX pekade på en borttagen post medan en annan levde
    hand(pg, 'pers1', **cr('dC', '2026-11-17T08:00:00.000Z', '2026-11-17', 'proj1', 'upg2', 5))
    hand(pg, 'pers1', **cr('dD', '2026-11-17T09:00:00.000Z', '2026-11-17', 'proj1', 'upg2', 1))
    hand(pg, 'pers1', id='xD', entryId='dD', type='delete', at='2026-11-17T10:00:00.000Z', by='pers1', dev='dator')
    ok(ev(pg, "() => { derive(); return cell('proj1~upg2', '2026-11-17')?.hours; }") == 5, 'A1: den kvarvarande posten nås från rutan när den andra tagits bort')

    # ── B11: en ruta som tömts förblir tömd
    hand(pg, 'pers1', **cr('dE', '2026-11-10T08:00:00.000Z', '2026-11-10', 'proj1', 'upg2', 3))
    hand(pg, 'pers1', id='xE1', entryId='dE', type='delete', at='2026-11-10T10:00:00.000Z', by='pers1', dev='telefon')
    hand(pg, 'pers1', id='xE2', entryId='dE', type='update', at='2026-11-10T11:00:00.000Z', by='pers1', dev='dator', data={'hours': 6})
    ok(ev(pg, "() => { derive(); return cell('proj1~upg2', '2026-11-10'); }") is None, 'B11: senare ändring väcker inte en tömd ruta')

    # ── B2: händelser i en annans logg
    ev(pg, """() => { S.register.people.push({ ...S.register.people[0], id: 'pers2', name: 'Anna Berg', initials: 'AB', admin: false, keys: undefined }); S.logs.pers2 = { events: [] }; return true; }""")
    eid = ev(pg, "() => live().find(e => e.hours > 0 && e.projectId === 'proj1').id")
    h0 = ev(pg, f"() => E.get('{eid}').hours")
    hand(pg, 'pers2', id='b2a', entryId=eid, type='update', at='2026-11-18T09:00:00.000Z', by='pers2', dev='x', data={'hours': 0.5, 'rate': 1})
    hand(pg, 'pers2', id='b2b', entryId='kost1', type='cost', at='2026-11-18T09:00:00.000Z', by='pers2', dev='x', data={'deleted': True})
    hand(pg, 'pers2', id='b2c', entryId=eid, type='create', at='2026-11-18T09:01:00.000Z', by='pers2', dev='x', data={'date': '2026-11-18', 'projectId': 'proj1', 'taskId': 'upg1', 'hours': 9, 'rate': 1})
    r = ev(pg, f"() => {{ derive(); const e = E.get('{eid}'); return [e.hours, e.rate, e.person, !!COST.get('kost1') && !COST.get('kost1').deleted]; }}")
    ok(r[0] == h0 and r[1] != 1 and r[2] == 'pers1' and r[3], f'B2: Annas logg ändrar inte admins post eller kostnad ({r})')

    # ── A2: skriptkod i egna kommandon och inställningar ur rätt tidlogg
    ev(pg, """() => { S.prefs.aliases = { xx: '<img src=x onerror="window.__x=1">', ok: 'v43', bad: 5 }; S = migrate(S); derive(); return true; }""")
    ok(ev(pg, "() => !('bad' in S.prefs.aliases) && 'xx' in S.prefs.aliases"), 'A2: migrate tar bort egna kommandon som inte är text')
    ev(pg, "() => { const d = document.createElement('div'); d.id = 'a2'; d.innerHTML = shRefHtml(''); document.body.append(d); }"); pg.wait_for_timeout(400)
    ok(not ev(pg, "() => !!window.__x") and pg.locator('#a2 img').count() == 0, 'A2: egna kommandon med HTML körs inte i förteckningen')
    ok('&lt;img' in ev(pg, "() => document.getElementById('a2').innerHTML"), 'A2: betydelsen visas som text')
    ev(pg, "() => document.getElementById('a2').remove()")
    j = ev(pg, """() => { const b = JSON.parse(JSON.stringify(S)); b.session = { personId: 'pers1' }; b.prefs = { aliases: { mitt: 'v1' }, hiddenRows: { a: 1 }, weekRows: {} };
      const P = bookSplit(b); P['log.pers2'] = { log: { events: [] }, prefs: { aliases: { anna: 'v9' }, hiddenRows: { z: 1 }, weekRows: {} }, session: { personId: 'pers2' } };
      const x = bookJoin(P, 'pers1'); return [Object.keys(x.prefs.aliases), Object.keys(x.prefs.hiddenRows), x.session.personId]; }""")
    ok(j == [['mitt'], ['a'], 'pers1'], f'A2: admins inställningar och session tas ur den egna tidloggen ({j})')

    # ── A3: fingeravtrycket räknas ur nycklarna
    a3 = ev(pg, """async () => {
      const x = async a => crypto.subtle.exportKey('jwk', (await crypto.subtle.generateKey(a, true, a.name === 'ECDH' ? ['deriveBits'] : ['sign', 'verify'])).publicKey);
      const pub = { enc: await x({ name: 'ECDH', namedCurve: 'P-256' }), sig: await x({ name: 'ECDSA', namedCurve: 'P-256' }), at: '1' };
      const fp = await keyFp(pub);
      return [await keyFpOk({ ...pub, fp }) === fp, await keyFpOk({ ...pub, fp: 'aaaabbbbccccdddd' })]; }""")
    ok(a3 == [True, None], f'A3: äkta avtryck godtas, påhittat vägras ({a3})')

    # ── A4: golv för antalet varv
    a4 = ev(pg, """() => { const t = (k, m) => { try { kdfOk(k, m); return 'ok'; } catch (e) { return 'nej'; } };
      return [t({ name: 'PBKDF2-SHA-256', iter: 1 }, 600000), t({ name: 'PBKDF2-SHA-256', iter: 600000 }, 600000), t({ name: 'MD5', iter: 600000 }, 600000), t({ name: 'PBKDF2-SHA-256', iter: 99999 }, 100000), t({ name: 'PBKDF2-SHA-256', iter: 100000 }, 100000)]; }""")
    ok(a4 == ['nej', 'ok', 'nej', 'nej', 'ok'], f'A4: 1 varv och okänd metod vägras, 600 000 godtas ({a4})')

    # ── A5: borttaget projekt mot osynkad tid (sammanslagningen)
    a5 = ev(pg, """() => {
      const base = JSON.parse(JSON.stringify(S)), P0 = JSON.parse(JSON.stringify(base.register.projects.find(p => p.id === 'proj3')));
      base.register.projects.push({ ...P0, id: 'projX', name: 'Nytt Uppdrag', tasks: [{ id: 'tX', name: 'Utredning', billable: true }] });
      const ours = JSON.parse(JSON.stringify(base)), theirs = JSON.parse(JSON.stringify(base));
      ours.logs.pers1.events.push({ id: 'a5', entryId: 'eX', type: 'create', at: '2026-11-18T09:00:00.000Z', by: 'pers1', dev: 'B', data: { date: '2026-11-18', projectId: 'projX', taskId: 'tX', roleId: 'roll1', hours: 3, note: '', rate: 900 } });
      theirs.register.projects = theirs.register.projects.filter(p => p.id !== 'projX');
      const cf = [], m = bookMerge(base, ours, theirs, cf), P = m.register.projects.find(p => p.id === 'projX');
      // ingen version har projektet kvar (t.ex. admin som redan synkat borttagningen): Återställt projekt
      const b2 = JSON.parse(JSON.stringify(theirs)), o2 = JSON.parse(JSON.stringify(theirs)), t2 = JSON.parse(JSON.stringify(theirs));
      t2.logs.pers1.events.push(ours.logs.pers1.events.find(e => e.id === 'a5'));
      const m2 = bookMerge(b2, o2, t2, []), P2 = m2.register.projects.find(p => p.id === 'projX');
      return [P?.name, P?.tasks.map(t => t.id), cf.length, P2?.name, P2?.tasks[0]?.billable]; }""")
    ok(a5[:3] == ['Nytt Uppdrag', ['tX'], 0], f'A5: projektet läggs tillbaka ur den andra versionen, ingen krock ({a5[:3]})')
    ok(a5[3] == 'Återställt projekt' and a5[4] is True, f'A5: utan källa blir det Återställt projekt med debiterbar uppgift ({a5[3:]})')
    a5u = ev(pg, """() => {
      const base = JSON.parse(JSON.stringify(S)), ours = JSON.parse(JSON.stringify(base)), theirs = JSON.parse(JSON.stringify(base));
      ours.logs.pers1.events.push({ id: 'a5u', entryId: 'eU', type: 'create', at: '2026-11-18T09:00:00.000Z', by: 'pers1', dev: 'B', data: { date: '2026-11-18', projectId: 'proj1', taskId: 'upg2', roleId: 'roll1', hours: 3, note: '', rate: 900 } });
      theirs.register.projects.find(p => p.id === 'proj1').tasks = theirs.register.projects.find(p => p.id === 'proj1').tasks.filter(t => t.id !== 'upg2');
      const m = bookMerge(base, ours, theirs, []); return m.register.projects.find(p => p.id === 'proj1').tasks.map(t => t.name); }""")
    ok('Skiss' in a5u, f'A5: en borttagen uppgift med tid läggs tillbaka ({a5u})')
    # Vyerna: tid på ett projekt som saknas (medarbetaren, eller innan sammanslagningen)
    js.clear()
    ev(pg, """() => { S.logs.pers1.events.push({ id: 'a5v', entryId: 'eV', type: 'create', at: '2026-11-18T09:00:00.000Z', by: 'pers1', dev: 'B', data: { date: '2026-11-17', projectId: 'projBorta', taskId: 'tB', roleId: 'roll1', hours: 3, note: 'x', rate: 900 } });
      S.logs.pers1.events.push({ id: 'a5w', entryId: 'eW', type: 'create', at: '2026-11-18T09:00:00.000Z', by: 'pers1', dev: 'B', data: { date: '2026-11-17', projectId: 'proj1', taskId: 'upgBorta', roleId: 'roll1', hours: 2, note: 'y', rate: 900 } });
      derive(); st.view = 'week'; st.week = '2026-11-16'; render(); return true; }"""); pg.wait_for_timeout(300)
    for v in ['month', 'day']:
        ev(pg, f"() => {{ st.view = '{v}'; st.day = '2026-11-17'; st.month = '2026-11'; render(); }}"); pg.wait_for_timeout(200)
    ev(pg, "() => { st.page = 'rapporter'; render(); }"); pg.wait_for_timeout(200)
    ev(pg, "() => { st.page = 'tid'; st.view = 'week'; render(); }"); pg.wait_for_timeout(200)
    ok(not js, f'A5: vecka, månad, dag och rapporter ritas utan fel med tid på ett saknat projekt ({js[:1]})')
    ok(pg.locator('.wkv :text("Borttaget projekt")').count() >= 1, 'A5: tiden syns på raden Borttaget projekt')
    iv = ev(pg, "() => invoiceData('p:proj1', '2026-11-01', '2026-11-30', true, true).projects.reduce((s, x) => s + x.lines.reduce((t, l) => t + l.hours, 0), 0)")
    ok(iv >= 2, f'A5: tid på en borttagen uppgift faller inte ur fakturaunderlaget ({iv} h)')
    ev(pg, "() => { S.logs.pers1.events = S.logs.pers1.events.filter(e => !['a5v', 'a5w'].includes(e.id)); derive(); render(); }")

    # ── A6: belopp med mellanslag i kost
    ev(pg, "() => { st.page = 'tid'; st.view = 'week'; st.week = '2026-11-16'; st.sel = null; st.selDay = '2026-11-18'; render(); }"); pg.wait_for_timeout(300)
    h = shell(pg, 'kost strand taxi 1 500')
    ok('Taxi' in h and '1 500' in h.replace('\xa0', ' ').replace(' ', ' ') and 'Taxi 1' not in h, f'A6: förhandsraden Taxi – 1 500 kr ({h})')
    shell(pg, 'kost strand taxi 1 500', enter=True)
    k = ev(pg, "() => [...COST.values()].filter(c => !c.deleted && c.text === 'Taxi').map(c => c.amount)")
    ok(k == [1500], f'A6: Taxi bokförs med 1 500 kr ({k})')
    shell(pg, 'kost strand resa 2 st à 1 200', enter=True)
    k = ev(pg, "() => [...COST.values()].filter(c => !c.deleted && c.text === 'Resa').map(c => [c.qty, c.price, c.amount])")
    ok(k == [[2, 1200, 2400]], f'A6: 2 st à 1 200 = 2 400 kr ({k})')
    shell(pg, 'kost strand kartunderlag 1500', enter=True)
    k = ev(pg, "() => [...COST.values()].filter(c => !c.deleted && c.text === 'Kartunderlag').map(c => c.amount)")
    ok(k == [1500], f'A6: utan mellanslag som förut ({k})')
    shell(pg, 'kost strand plottning 6 st à 85', enter=True)
    k = ev(pg, "() => [...COST.values()].filter(c => !c.deleted && c.text === 'Plottning').map(c => [c.qty, c.price])")
    ok(k == [[6, 85]], f'A6: 6 st à 85 som förut ({k})')

    # ── C: dag efter projektet
    q = ev(pg, "() => ['3 strand igår', '3 strand tor möte', '2 lärkan 10/11', '3 strand fm möte', '3 strand ritade'].map(s => { const x = parseQuick(s); return [x.days, x.note]; })")
    ok(q[0] == [['2026-11-17'], ''], f'C: 3 strand igår → i går ({q[0]})')
    ok(q[1] == [['2026-11-19'], 'Möte'], f'C: 3 strand tor möte → torsdag, anteckningen Möte ({q[1]})')
    ok(q[2] == [['2026-11-10'], ''], f'C: 2 lärkan 10/11 → 10 nov ({q[2]})')
    ok(q[3][1] == 'Fm möte' and len(q[3][0]) == 1, f'C: fm (flera dagar) blir kvar i anteckningen ({q[3]})')
    ok(q[4][1] == 'Ritade', f'C: vanlig anteckning orörd ({q[4]})')

    # ── C: ta bort rad och lägg tillbaka räknar inte upp
    rr = ev(pg, """() => { const rk = 'proj1~upg2', wk = '2026-11-02', d = '2026-11-03'; setCell(rk, d, { hours: 4 });
      removeRowData(rk, wk); setCell(rk, d, { hours: 2 }); removeRowData(rk, wk); restoreRow(rk, wk); const a = cell(rk, d)?.hours;
      removeRowData(rk, wk); restoreRow(rk, wk); const b = cell(rk, d)?.hours; derive(); return [a, b, cell(rk, d)?.hours]; }""")
    ok(rr[1] == rr[0] and rr[2] == rr[0], f'C: restoreRow lägger inte på samma timmar igen ({rr})')

    # ── C: Summa kostnader i projektdagboken (PDF)
    t = pdftext(pg, "() => Array.from(diaryPdf(diaryData('proj1', '2026-09-01', '2026-11-30', true)))")
    ok('Summa kostnader' in t and 'Summa beskrivning' not in t, 'C: projektdagbokens kostnadstabell summeras som Summa kostnader')

    # ── B1: avrundning lika åt båda håll
    b1 = ev(pg, "() => [r2(771.875), r2(-771.875), r2(-0.004), r2(3087.5 * 0.25), r2(-3087.5 * 0.25)]")
    ok(b1 == [771.88, -771.88, 0, 771.88, -771.88], f'B1: r2 symmetrisk ({b1})')
    b1b = ev(pg, "() => { const x = { status: 'draft', vat: 25, lines: [{ amount: 3087.5 }] }, y = { status: 'draft', vat: 25, lines: [{ amount: -3087.5 }] }; return [invCalc(x).vatA, invCalc(y).vatA, invCalc(x).total + invCalc(y).total]; }")
    ok(b1b[0] == -b1b[1] and abs(b1b[2]) < 1e-9, f'B1: kreditens moms tar ut fakturans ({b1b})')

    # ── B12: utkastet behåller beloppet i en bok utan avrundning
    b12 = ev(pg, """() => { S.register.book.rounding = 0; S.register.book.invoicing = { ...(S.register.book.invoicing || {}), on: true };
      const rk = 'proj2~upg3'; setCell(rk, '2026-11-02', { hours: 4/3, note: 'a' }); setCell(rk, '2026-11-03', { hours: 2/3, note: 'b' }); setCell(rk, '2026-11-04', { hours: 13/6, note: 'c' });
      return true; }""")
    ok(b12, 'B12: bok utan avrundning med 1:20 + 0:40 + 2:10')
    b12r = ev(pg, """() => { st.page = 'rapporter'; rep().tab = 'invoice'; const v = invSel(); v.sel = 'p:proj2'; v.old = true; v.rows = false; render();
      const d = invoiceData('p:proj2', '2026-11-01', '2026-11-30', true, false); return d.amount; }""")
    pg.wait_for_timeout(200)
    b12d = ev(pg, """() => { const per = rep().inv; per.from = '2026-11-01'; per.to = '2026-11-30'; per.custom = true;
      const n0 = S.register.invoices.length; try { invNewFromBasis(); } catch (e) { return 'fel: ' + e.message; }
      const x = S.register.invoices.at(-1); if (S.register.invoices.length === n0) return 'inget utkast';
      const before = invCalc(x).net; invEdRead(); const after = invCalc(x).net; closeDlg(); return [before, after, x.lines.map(l => [l.qty, l.price, l.amount])]; }""")
    if isinstance(b12d, list):
        ok(abs(b12d[0] - b12d[1]) < 0.005, f'B12: beloppet ändras inte när utkastet läses ({b12d[0]} → {b12d[1]}, underlaget {b12r:.2f})')
    else:
        ok(False, f'B12: utkastet ({b12d})')

    # ── B13: fakturans spann bara över dagar den själv låser
    b13 = ev(pg, """() => { const pid = 'proj1';
      hdSet(pid, '2026-10-01', '2026-10-31', true);
      const span = { pid, from: '2026-09-16', to: '2026-11-30' }, kept = spanMinus(span, S.register.handled[pid] || []);
      return kept.map(s => [s.from, s.to]); }""")
    ok(['2026-10-01', '2026-10-31'] not in b13 and all(not (a <= '2026-10-15' <= z) for a, z in b13), f'B13: den nya fakturan låser inte oktober som redan var hanterad ({b13})')

    ok(not js, f'inga JavaScript-fel ({js[:2]})')
    b.close()

print('\n' + ('ALLA OK' if not fel else f'{fel} FEL'))
sys.exit(1 if fel else 0)
