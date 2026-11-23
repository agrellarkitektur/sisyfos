#!/usr/bin/env python3
"""
Sisyfos 0.20.2 – rapporternas reglage (filformat 12 oförändrat).

Kontrollerar i en riktig webbläsare att
  – fakturaunderlaget och projektdagboken har Från och Till synliga från början (ingen Egen period),
    och att pilarna går en hel månad i taget,
  – Belopp, uppställning och tomma veckor ligger under Fler val, som är stängd från början och minns sitt läge,
  – rapportförslagen ger all öppen tid till och med i dag – oavsett vad perioden ovanför står på –
    och att underlaget (skärm och PDF) säger dagen, inte månaden,
  – Hanterat före och med detta underlag: tidigare hanterad tid och kostnad + det här underlaget, totalt och mot budget
    (skärm och PDF), bara med belopp.

Kör:  python3 -m http.server 8765 &  python3 test/rapport3_test.py
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
def nb(s): return s.replace('\xa0', ' ').replace(' ', ' ')
def kr(x): return f"{int(round(x)):,}".replace(',', ' ')
PDF = "() => { const v = rep().inv, [f, t] = v.custom ? [v.from, v.to] : [v.ym + '-01', v.ym + '-31']; return Array.from(invoicePdf(invoiceData(v.sel, f, t, v.old, v.rows), v.sel)); }"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, service_workers='block', accept_downloads=True)
    ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(BOK))}); sessionStorage.setItem('lagd', '1'); }}")
    pg = ctx.new_page(); js = []
    pg.on('pageerror', lambda e: js.append(str(e)))
    pg.clock.install(time=datetime.datetime(2026, 11, 23, 10, 0))
    pg.goto(URL); pg.wait_for_timeout(1200)
    ok(ev(pg, "() => today()") == '2026-11-23', 'klockan står på 23 nov 2026')

    # ── Fakturaunderlaget: reglagen
    ev(pg, "() => { rep().tab = 'invoice'; }")
    pg.click('.rail [data-page=rapporter]'); pg.wait_for_timeout(500)
    ok(pg.locator('#ivCustom').count() == 0 and pg.locator('#ivM').count() == 0, 'ingen Egen period och ingen månadsväljare')
    ok(pg.locator('#ivFrom').is_visible() and pg.locator('#ivTo').is_visible(), 'Från och Till syns från början')
    ok(pg.locator('details.rep-adv').count() == 1 and not pg.locator('details.rep-adv').evaluate('d => d.open'), 'Fler val finns och är stängd')
    ok(not pg.locator('#ivAmt').is_visible() and not pg.locator('#ivLay').is_visible(), 'Belopp och uppställning ligger under Fler val')
    ok('Med belopp' in pg.inner_text('.rep-adv summary'), f"sammanfattningen säger läget ({pg.inner_text('.rep-adv summary')!r})")
    ok(pg.locator('#ivOld').is_visible() and pg.locator('#ivRows').is_visible(), 'All öppen tid före perioden och Dagboksrader syns')

    pg.select_option('#ivS', 'p:proj1'); pg.wait_for_timeout(300)
    pg.fill('#ivFrom', '2026-10-01'); pg.locator('#ivFrom').dispatch_event('change'); pg.wait_for_timeout(300)
    pg.fill('#ivTo', '2026-10-31'); pg.locator('#ivTo').dispatch_event('change'); pg.wait_for_timeout(300)
    v = ev(pg, "() => { const v = rep().inv; return [v.custom, v.from, v.to]; }")
    ok(v == [True, '2026-10-01', '2026-10-31'], f'datumen sätter perioden ({v})')
    pg.click('[data-act=ivMonth][data-d="-1"]'); pg.wait_for_timeout(300)
    ok(pg.input_value('#ivFrom') == '2026-09-01' and pg.input_value('#ivTo') == '2026-09-30', 'bakåtpilen ger september')
    pg.click('[data-act=ivMonth][data-d="1"]'); pg.click('[data-act=ivMonth][data-d="1"]'); pg.wait_for_timeout(300)
    ok(pg.input_value('#ivFrom') == '2026-11-01' and pg.input_value('#ivTo') == '2026-11-30', 'framåtpilen ger november')

    # ── Rapportförslagen: all öppen tid till och med i dag, oberoende av perioden
    pg.fill('#ivFrom', '2026-09-01'); pg.locator('#ivFrom').dispatch_event('change'); pg.wait_for_timeout(200)
    pg.fill('#ivTo', '2026-09-30'); pg.locator('#ivTo').dispatch_event('change'); pg.wait_for_timeout(300)
    sug = pg.locator('.rep-sug .sug[data-act=ivSuggest]')
    ok(sug.count() >= 1, f'rapportförslag finns ({sug.count()})')
    ok('till och med i dag' in pg.inner_text('.rep-sug .lbl'), 'rubriken säger till och med i dag')
    knapp = pg.locator('.rep-sug .sug[data-s="p:proj1"]')
    if not knapp.count(): knapp = pg.locator('.rep-sug .sug[data-s^="c:"]').first
    s = knapp.get_attribute('data-s'); knapp.click(); pg.wait_for_timeout(400)
    v = ev(pg, "() => { const v = rep().inv; return [v.sel, v.custom, v.from, v.to, v.old]; }")
    ok(v[0] == s and v[1] and v[3] == '2026-11-23' and v[4], f'förslaget: till och med i dag, all öppen tid ({v})')
    ok(pg.input_value('#ivTo') == '2026-11-23', 'Till-fältet visar dagens datum')
    ok('on' in (pg.locator(f'.rep-sug .sug[data-s="{s}"]').get_attribute('class') or ''), 'förslaget är markerat')
    first = ev(pg, "() => { const v = rep().inv; return invoiceData(v.sel, v.from, v.to, true).first; }")
    ok(first and first < '2026-11-01', f'öppen tid före november kommer med ({first})')
    per = nb(pg.locator('.paper .pp-facts div:has(dt:text-is("Period")) dd').inner_text())
    ok('23 nov 2026' in per and 'November' not in per, f'perioden på skärmen slutar i dag ({per!r})')
    txt = nb(pdftext(pg, PDF))
    ok('23 nov 2026' in txt and 'November 2026' not in txt, 'PDF:en säger till och med 23 nov 2026')
    # samma resultat oavsett vad perioden stod på
    pg.fill('#ivFrom', '2026-06-01'); pg.locator('#ivFrom').dispatch_event('change'); pg.wait_for_timeout(200)
    pg.locator(f'.rep-sug .sug[data-s="{s}"]').click(); pg.wait_for_timeout(300)
    v2 = ev(pg, "() => { const v = rep().inv; return [v.sel, v.custom, v.from, v.to, v.old]; }")
    ok(v2 == v, f'förslaget påverkas inte av datumen ovanför ({v2})')
    # en hel månad som slutar i dag heter inte bara månaden
    ok(ev(pg, "() => periodLabel('2026-11-01', '2026-11-23')") == '1 nov 2026 – 23 nov 2026', 'etiketten mitt i månaden')
    ok(ev(pg, "() => periodLabel('2026-10-01', '2026-10-31')") == 'Oktober 2026', 'en hel månad i det förflutna heter månaden')

    # ── Fler val och Hanterat före och med detta underlag
    pg.click('.rep-adv summary'); pg.wait_for_timeout(300)
    ok(pg.locator('#ivAmt').is_visible() and pg.locator('#ivPrev').is_visible(), 'Fler val öppnas')
    ok(ev(pg, "() => rep().adv") is True, 'läget sparas')
    ok(not pg.locator('#ivPrev').is_checked() and pg.locator('.paper .prev-t').count() == 0, 'Hanterat före är av från början')
    pg.select_option('#ivS', 'p:proj1'); pg.wait_for_timeout(300)
    ok(pg.locator('details.rep-adv').evaluate('d => d.open'), 'Fler val förblir öppen efter omritning')
    pg.check('#ivPrev'); pg.wait_for_timeout(400)
    ok(pg.locator('.paper .prev-t').count() == 1, 'tabellen syns')
    exp = ev(pg, """() => { const P = proj('proj1'); let h = 0; for (const e of pEs('proj1')) if (!e.deleted && e.hours > 0 && billable(e) && handled('proj1', e.date)) h += amountOf(e);
      for (const c of pCosts('proj1')) if (handled('proj1', c.date)) h += cTot(c);
      const v = rep().inv, d = invoiceData(v.sel, v.from, v.to, v.old, v.rows), x = d.projects[0]; return [h, x.amount + x.csA, P.budgetKr]; }""")
    ok(exp[0] > 4500, f'det finns hanterad tid och kostnad i Villa Strand ({exp[0]})')
    rad = nb(pg.locator('.paper .prev-t tbody tr').first.inner_text())
    ok(kr(exp[0]) in rad and kr(exp[1]) in rad and kr(exp[0] + exp[1]) in rad, f'Före, Detta underlag och Totalt ({rad!r})')
    if exp[2]:
        ok(kr(exp[2]) in rad and f"{round((exp[0] + exp[1]) / exp[2] * 100)} %" in rad, 'budget och andel')
    txt = nb(pdftext(pg, PDF))
    ok('Hanterat före och med detta underlag' in txt and kr(exp[0] + exp[1]) in txt, 'tabellen i PDF:en')
    ok('Med belopp · ' in pg.inner_text('.rep-adv summary') and 'Tidigare hanterat' in pg.inner_text('.rep-adv summary'), 'sammanfattningen tar med valet')
    # egna rader står för sig
    pg.click('[data-act=xrAdd][data-k=inv]'); pg.wait_for_timeout(300)
    pg.fill('#xrT', 'Underkonsult el'); pg.fill('#xrA', '5000'); pg.click('#xrForm button[type=submit]'); pg.wait_for_timeout(400)
    rader = [nb(t) for t in pg.locator('.paper .prev-t tbody tr').all_inner_texts()]
    ok(len(rader) == 3 and 'Egna rader' in rader[1] and 'Summa' in rader[2] and kr(exp[0] + exp[1] + 5000) in rader[2], f'egna rader och summa ({rader})')
    # bara med belopp
    pg.uncheck('#ivAmt'); pg.wait_for_timeout(300)
    ok(pg.locator('#ivPrev').is_disabled() and pg.locator('.paper .prev-t').count() == 0, 'utan belopp: ingen tabell, valet avstängt')
    ok('Bara timmar' in pg.inner_text('.rep-adv summary'), 'sammanfattningen: Bara timmar')
    pg.check('#ivAmt'); pg.wait_for_timeout(300)
    ok(pg.locator('.paper .prev-t').count() == 1, 'belopp på igen: tabellen tillbaka')
    # alla projekt: en rad per projekt + summa
    pg.select_option('#ivS', 'all'); pg.wait_for_timeout(300)
    np = ev(pg, "() => { const v = rep().inv; return invoiceData(v.sel, v.from, v.to, v.old, v.rows).projects.length; }")
    ok(pg.locator('.paper .prev-t tbody tr').count() == np + (1 if np > 1 else 0), f'alla projekt: {np} projekt (+ summa)')

    # ── Projektdagboken
    ev(pg, "() => { rep().tab = 'diary'; rep().pid = 'proj1'; render(); }"); pg.wait_for_timeout(400)
    ok(pg.locator('#rpCustom').count() == 0 and pg.locator('#rpFrom').is_visible() and pg.locator('#rpTo').is_visible(), 'dagboken: Från och Till, ingen Egen period')
    ok(pg.locator('#rpAmt').is_visible(), 'dagboken: Fler val är öppen (läget delas)')
    pg.click('.rep-adv summary'); pg.wait_for_timeout(300)
    ok(not pg.locator('#rpAmt').is_visible() and not pg.locator('#rpLay').is_visible(), 'dagboken: Belopp och uppställning under Fler val')
    pg.click('[data-act=rpMonth][data-d="-1"]'); pg.wait_for_timeout(300)
    f0, t0 = pg.input_value('#rpFrom'), pg.input_value('#rpTo')
    ok(t0.endswith(('-30', '-31', '-28', '-29')) and f0.endswith('-01'), f'dagboken: pilen ger en hel månad ({f0} – {t0})')
    k = pg.locator('.rep-sug .sug[data-act=rpOpen]').first
    if k.count():
        k.click(); pg.wait_for_timeout(400)
        ok(ev(pg, "() => rep().to") >= '2026-11-23', 'dagboken: förslaget går till och med i dag')

    # ── 390 px
    pg.set_viewport_size({'width': 390, 'height': 844}); pg.wait_for_timeout(300)
    ev(pg, "() => { rep().tab = 'invoice'; rep().adv = true; render(); }"); pg.wait_for_timeout(400)
    w = pg.locator('.rep-ctl').evaluate('e => [e.scrollWidth, e.clientWidth]')
    ok(w[0] <= w[1] + 1, f'reglagen ryms på 390 px ({w})')
    ok(not js, f'inga JavaScript-fel {js}')
    bild = ROT / 'test' / '_bilder'; bild.mkdir(exist_ok=True)
    pg.locator('.rep-ctl').screenshot(path=str(bild / 'rapport3_390.png'))
    pg.set_viewport_size({'width': 1280, 'height': 900}); ev(pg, "() => { render(); }"); pg.wait_for_timeout(300)
    pg.locator('.rep-ctl').screenshot(path=str(bild / 'rapport3_1280.png'))
    pg.locator('.paper').screenshot(path=str(bild / 'rapport3_paper.png'))
    b.close()
print('\nAllt OK' if not fel else f'\n{fel} FEL'); sys.exit(1 if fel else 0)
