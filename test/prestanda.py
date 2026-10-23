"""
Mäter hur lång tid vanliga åtgärder tar med en stor bok (test/stor_bok.py). Körs för hand:
  python3 -m http.server 8765 &      (i repot)
  python3 test/prestanda.py [sida]   (standard http://localhost:8765/index.html)
Skriver bästa tiden av tre per åtgärd i millisekunder. Siffrorna gäller den här datorn – jämför före och efter en ändring.
"""
import sys, tempfile, pathlib
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from stor_bok import bygg

U = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
KLICK = """async (sel) => { const el = document.querySelector(sel); if (!el) return -1; const t0 = performance.now(); el.click(); await new Promise(r => setTimeout(r, 0)); return Math.round(performance.now() - t0); }"""
TANGENT = """() => { const t = document.querySelector('.n-in'); if (!t) return -1; const t0 = performance.now();
  for (let i = 0; i < 10; i++) { t.value += 'x'; t.dispatchEvent(new Event('input', { bubbles: true })); } return Math.round((performance.now() - t0) / 10); }"""

def main():
    bok = pathlib.Path(tempfile.mkdtemp()) / 'stor.sisyfos.json'; n = bygg(bok)
    with sync_playwright() as p:
        b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 1400, 'height': 900}, service_workers='block'); pg = ctx.new_page()
        fel = []; pg.on('pageerror', lambda e: fel.append(str(e)))
        pg.goto(U); pg.wait_for_timeout(600)
        pg.click('#brandBtn'); pg.click('[data-act=importBook]'); pg.wait_for_timeout(200)
        pg.set_input_files('#imFile', str(bok)); pg.wait_for_timeout(500); pg.click('[data-act=doImport]'); pg.wait_for_timeout(2500)
        print(f'Stor bok: {n} tidposter, {bok.stat().st_size / 1e6:.1f} MB')
        def mat(namn, sel):
            ts = []
            for _ in range(3): ts.append(pg.evaluate(KLICK, sel)); pg.wait_for_timeout(120)
            print(f'  {namn:28s} {min(ts):5d} ms')
        mat('Tid, vecka bakåt', '.wk-nav button')
        mat('Projekt', '[data-act=page][data-page=projekt]')
        mat('Kunder', '[data-act=page][data-page=kunder]')
        mat('Rapporter', '[data-act=page][data-page=rapporter]')
        mat('Inställningar', '[data-act=page][data-page=installningar]')
        mat('Tid', '[data-act=page][data-page=tid]')
        print(f'  {"Tangenttryck i anteckning":28s} {pg.evaluate(TANGENT):5d} ms')
        if fel: print('Skriptfel:', fel[:3])
        b.close()

if __name__ == '__main__':
    main()
