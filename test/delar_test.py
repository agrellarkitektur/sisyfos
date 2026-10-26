#!/usr/bin/env python3
"""
Sisyfos – boken i delar och nycklar per person (0.16.0, filformat 10, claude/etapp4.md).

Kontrollerar i en riktig webbläsare att
  – format 9 migreras till 10 med samma organisations-id på två enheter,
  – bookSplit/bookJoin är förlustfria (exempelboken i test/bocker och appens exempelbok),
  – timmar och belopp för hanterad tid, fakturor och personkortet inte ligger i registret,
  – krypteringen skapar en personlig nyckel som förs in i registret och en fil version 2 med delar,
  – filen öppnas igen till samma bok, och via Importera bok med lösenordet,
  – en medarbetare med egna nycklar bara kan läsa registret, sitt kort och sin logg – inte fakturorna
    (adm) eller någon annans logg – och att admins kopia av medarbetarens logg inte används av medarbetaren,
  – en ändrad del och en del som byter skribent upptäcks,
  – en äldre app (0.15.x) får en fil som säger "format 10" (stubben),
  – krock på nycklar vid sammanslagning: den äldsta nyckeln gäller, likadant åt båda hållen.

Kör:  python3 -m http.server 8765 &  python3 test/delar_test.py
"""
import json, pathlib, sys, tempfile
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
URL = (sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html') + '?test'
BOK = json.loads((ROT / 'test' / 'bocker' / 'format-9.json').read_text(encoding='utf-8'))
PW = 'ett långt testlösenord'
fel = 0
# Koden körs med appens funktioner i räckvidd (provkroken window.SISYFOS, bara med ?test i adressen)
def ev(page, fn, arg=None):
    return page.evaluate("([f, a]) => { with (window.SISYFOS) { return eval('(' + f + ')')(a); } }", [fn, arg])
def ok(cond, text):
    global fel
    print(('OK  ' if cond else 'FEL ') + text); fel += not cond

def starta(b, bok):
    ctx = b.new_context(viewport={'width': 1280, 'height': 800}, service_workers='block', accept_downloads=True)
    ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(bok))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1200)
    return ctx, pg, js

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, pg, js = starta(b, BOK)
    r = ev(pg, "() => ({ v: S.version, org: S.register.org, fmt: FORMAT_VERSION })")
    ok(r['v'] == r['fmt'] == 11 and r['org']['id'].startswith('o') and len(r['org']['id']) == 17, f"format 9 → {r['v']}, organisation {r['org']['id']}")
    ctx2, pg2, js2 = starta(b, BOK)
    org2 = ev(pg2, "() => S.register.org.id"); ctx2.close()
    ok(org2 == r['org']['id'], 'samma organisations-id på en annan enhet')

    # Delning fram och tillbaka
    r = ev(pg, """() => { const P = bookSplit(S), J = bookJoin(P), ex = sampleBook(), Je = bookJoin(bookSplit(ex));
      const regTxt = JSON.stringify(P.reg);
      return { same: canon(J) === canon(S), ex: canon(Je) === canon(ex), names: Object.keys(P).sort(),
        regHasInv: /"invoices"|"payments"/.test(regTxt), regHasCard: P.reg.register.people.some(p => ['employment', 'pct', 'balanceIn', 'balanceStart', 'vacation'].some(k => k in p)),
        regHasSum: Object.values(P.reg.register.handled).flat().some(h => 'hours' in h || 'amount' in h),
        admSums: !!P.adm.handledSums, signedInCard: Object.keys(P['card.' + me()].signed).length, signedAll: Object.keys(S.register.signed).length,
        prefsInLog: !!P['log.' + me()].prefs }; }""")
    ok(r['same'] and r['ex'], 'bookJoin(bookSplit(bok)) ger samma bok (format 9-boken och exempelboken)')
    ok(r['names'] == sorted(['reg', 'adm'] + [n for n in r['names'] if n.startswith(('card.', 'log.'))]) and any(n.startswith('card.') for n in r['names']), 'delar: ' + ', '.join(r['names']))
    ok(not r['regHasInv'] and not r['regHasCard'], 'registret saknar fakturor, betalningar och personkortet')
    ok(not r['regHasSum'], 'registret saknar timmar och belopp för hanterad tid' + (' (de ligger i adm)' if r['admSums'] else ''))
    ok(r['signedInCard'] == r['signedAll'], f"signerade veckor i personkortet ({r['signedInCard']})")
    ok(r['prefsInLog'], 'inställningarna följer den egna tidloggen')

    # Kryptering på → personlig nyckel och fil version 2
    r = ev(pg, """async pw => { const n = await encCreate(pw); await encStore(n.vault, n.key); const k = await keysEnsure();
      const txt = await encBookText(S), f = JSON.parse(txt), P = byId(R().people, me());
      const back = migrate(await decBook(f, st.enc.key));
      return { fp: k?.fp, regKeys: P.keys?.fp, v: f.version, parts: Object.keys(f.parts).sort(), to: Object.fromEntries(Object.entries(f.parts).map(([n, x]) => [n, Object.keys(x.to)])),
        same: canon(back) === canon(migrate(JSON.parse(JSON.stringify(S)))), stub: !!f.data?.ct, me: f.me, txt }; }""", PW)
    ok(r['fp'] and r['fp'] == r['regKeys'], f"personlig nyckel {r['fp']} förd in i registret")
    ok(r['v'] == 2 and r['me'] and 'reg' in r['parts'] and r['stub'], f"krypterad fil version 2 med {len(r['parts'])} delar och stubb")
    ok(r['same'], 'filen öppnas till samma bok')
    fil = r['txt']
    pg.click('.rail [data-page=installningar]'); pg.wait_for_timeout(400)
    txt = pg.inner_text('#page') if pg.query_selector('#page') else pg.inner_text('body')
    ok('Personlig nyckel' in txt and r['fp'][:4].upper() in txt.replace(' ', ''), 'Inställningar visar den personliga nyckeln')

    # Stubben: vad en äldre app (0.15.x) läser ur data
    r = ev(pg, """async t => { const f = JSON.parse(t); let b = await unseal(st.enc.key, f.data, AAD_DATA); if (f.zip === 'gzip') b = await gz(b, 'unzip');
      return JSON.parse(new TextDecoder().decode(b)); }""", fil)
    # En äldre app (FORMAT_VERSION 9) säger då: "Boken är sparad i en nyare version av Sisyfos (format 10)."
    ok(r.get('format') == 'sisyfos' and r.get('version') == 11, f"stubben för äldre appar: format {r.get('version')} (ger ”nyare version”)")

    # Ändrad del och fel skribent upptäcks
    r = ev(pg, """async t => {
      const f = JSON.parse(t), n = Object.keys(f.parts).find(x => x.startsWith('log.'));
      const a = JSON.parse(t); const ct = unb64(a.parts[n].ct); ct[5] ^= 1; a.parts[n].ct = b64(ct);
      let e1 = ''; try { await decBook(a, st.enc.key); } catch (e) { e1 = e.message; }
      const c = JSON.parse(t); c.parts.adm.sig = c.parts.reg.sig;
      let e2 = ''; try { await decBook(c, st.enc.key); } catch (e) { e2 = e.message; }
      return [e1, e2]; }""", fil)
    ok('ändrad eller skadad' in r[0], 'ändrad tidlogg upptäcks: ' + r[0])
    ok('ändrad eller skadad' in r[1], 'fel signatur upptäcks: ' + r[1])

    # En medarbetare med egna nycklar (Anna) – vad kan hon läsa ur admins fil?
    r = ev(pg, """async () => {
      const raw = rnd(32), mk = await aesKey(raw, ['encrypt', 'decrypt']), ak = await keysCreate('anna', mk), A = await keysOpen(ak, mk);
      const B = JSON.parse(JSON.stringify(S));
      B.register.people.push({ id: 'anna', name: 'Anna Berg', initials: 'AB', defaultRoleId: B.register.people[0].defaultRoleId, admin: false, employment: 'part', pct: 80, balanceStart: '2026-01-01', balanceIn: 3, vacation: { perYear: 25, yearStart: '04-01', saved: [] }, keys: keysPublic(A) });
      B.logs.anna = { events: [{ id: 'e1', entryId: 'p1', type: 'create', at: '2026-10-01T10:00:00Z', by: 'anna', data: { date: '2026-10-01', projectId: B.register.projects[0].id, taskId: B.register.projects[0].tasks[0].id, hours: 2, note: 'Annas tid' } }] };
      B.register.signed['anna|2026-09-28'] = { at: '2026-10-05T10:00:00Z', by: me() };
      const f = JSON.parse(await encBookText(B));
      const to = Object.fromEntries(Object.entries(f.parts).map(([n, x]) => [n, Object.keys(x.to).sort()]));
      const af = { ...f, me: 'anna', keys: { anna: { at: ak.at, fp: ak.fp, box: ak.box } } };
      const Ab = await decParts(af, mk);
      // Admins egen läsning av samma fil (där Annas logg är admins kopia) ger hela boken
      const Mb = await decParts(f, st.enc.key);
      return { to, me: me(), annaInv: (Ab.register.invoices || []).length, adminLog: !!Ab.logs[me()], annaLog: !!Ab.logs.anna,
        annaCard: Ab.register.people.find(p => p.id === 'anna')?.pct, adminCard: Ab.register.people.find(p => p.id === me())?.employment,
        annaSigned: Object.keys(Ab.register.signed), projects: Ab.register.projects.length,
        adminAll: canon(migrate(Mb)) === canon(migrate(JSON.parse(JSON.stringify(B)))) }; }""")
    m = r['me']
    ok(r['to']['reg'] == sorted([m, 'anna']), 'registret krypteras till admin och Anna')
    ok(r['to']['adm'] == [m] and r['to'][f'log.{m}'] == [m], 'fakturorna (adm) och admins logg bara till admin')
    ok(r['to']['card.anna'] == sorted([m, 'anna']) and r['to']['log.anna'] == sorted([m, 'anna']), 'Annas kort och logg till Anna och admin')
    ok(r['annaInv'] == 0 and not r['adminLog'] and r['adminCard'] is None, 'Anna ser inte fakturorna, admins tid eller admins personkort')
    ok(r['annaCard'] == 80 and r['annaSigned'] == ['anna|2026-09-28'] and r['projects'] > 0, 'Anna ser registret, sitt kort och sina signerade veckor')
    ok(not r['annaLog'], 'admins kopia av Annas logg används inte av Anna (bara Anna får skriva den)')
    ok(r['adminAll'], 'admin öppnar sin egen fil med Annas uppgifter förlustfritt')

    # Krock på nycklar vid sammanslagning: den äldsta gäller åt båda hållen
    r = ev(pg, """() => { const base = JSON.parse(JSON.stringify(S)), P = x => x.register.people.find(p => p.id === me());
      const a = JSON.parse(JSON.stringify(S)), t = JSON.parse(JSON.stringify(S));
      P(a).keys = { ...P(a).keys, at: '2026-10-25T10:00:00.000Z', fp: 'aaaa' }; P(t).keys = { ...P(t).keys, at: '2026-10-25T09:00:00.000Z', fp: 'bbbb' };
      const c1 = [], c2 = [], m1 = bookMerge(base, a, t, c1), m2 = bookMerge(base, t, a, c2);
      return [P(m1).keys.fp, P(m2).keys.fp, c1.length, c2.length]; }""")
    ok(r == ['bbbb', 'bbbb', 0, 0], f'krock på nycklar: den äldsta gäller åt båda hållen ({r})')

    # Nyckelringen i en fil från en annan enhet: en äldre tas över, en nyare inte
    r = ev(pg, """async () => { const old = await keysCreate(me(), st.enc.key), nyare = await keysCreate(me(), st.enc.key);
      old.at = '2020-01-01T00:00:00.000Z'; nyare.at = '2099-01-01T00:00:00.000Z';
      const f = e => ({ version: 2, me: me(), vault: st.enc.vault, keys: { [me()]: e } });
      await keysAdopt(f(old)); const a = (await kvGet('keys')).fp; await keysAdopt(f(nyare)); const b = (await kvGet('keys')).fp;
      return [a === old.fp, b === old.fp]; }""")
    ok(r == [True, True], 'nyckelringen från en annan enhet: den äldre tas över, en nyare inte')

    # Importera bok med den krypterade filen (version 2) och lösenordet – i en tom webbläsare
    with tempfile.TemporaryDirectory() as td:
        fp = pathlib.Path(td) / 'bok.sisyfos'; fp.write_text(fil, encoding='utf-8')
        c3 = b.new_context(viewport={'width': 1280, 'height': 800}, service_workers='block'); p3 = c3.new_page(); js3 = []
        p3.on('pageerror', lambda e: js3.append(str(e)))
        p3.goto(URL); p3.wait_for_timeout(1000)
        p3.click('#brandBtn'); p3.click('[data-act=importBook]'); p3.wait_for_timeout(200)
        p3.set_input_files('#imFile', str(fp)); p3.click('[data-act=doImport]'); p3.wait_for_timeout(300)
        p3.fill('#ulPw', PW); p3.click('[data-act=encOpenGo]'); p3.wait_for_timeout(2500)
        r = ev(p3, "async () => ({ name: R().book.name, keys: (await kvGet('keys'))?.fp, reg: byId(R().people, me()).keys?.fp, v: S.version })")
        ok(r['name'] == BOK['register']['book']['name'] and r['v'] == 11, f"Importera bok öppnar filen version 2 (”{r['name']}”)")
        ok(r['keys'] and r['keys'] == r['reg'], 'nyckelringen följer med importen')
        ok(not js3, 'inga JavaScript-fel vid importen' + (f': {js3}' if js3 else ''))
        c3.close()
    ok(not js, 'inga JavaScript-fel' + (f': {js}' if js else ''))
    ctx.close(); b.close()
print('Klart – inga fel' if not fel else f'{fel} fel'); sys.exit(1 if fel else 0)
