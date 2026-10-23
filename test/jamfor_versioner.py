"""
Jämför vad två versioner av appen visar för samma böcker – för omskrivningar som inte ska ändra något.
  python3 -m http.server 8765 &                 (i repot)
  python3 test/jamfor_versioner.py [git-ref]    (standard HEAD – jämför arbetskopian med senaste commit)
Öppnar varje bok (format 6, format 7 och den stora testboken) i båda versionerna, går igenom tidboken,
projekt, kunder, rapporternas flikar och inställningarna och jämför texten på skärmen.
"""
import sys, subprocess, tempfile, pathlib
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from stor_bok import bygg

REPO = pathlib.Path(__file__).resolve().parent.parent
REF = sys.argv[1] if len(sys.argv) > 1 else 'HEAD'
BAS = 'http://localhost:8765/'

def skarmar(b, url, bok):
    ctx = b.new_context(viewport={'width': 1400, 'height': 900}, service_workers='block'); pg = ctx.new_page(); fel = []
    pg.on('pageerror', lambda e: fel.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(600)
    pg.click('#brandBtn'); pg.click('[data-act=importBook]'); pg.wait_for_timeout(200)
    pg.set_input_files('#imFile', str(bok)); pg.wait_for_timeout(500); pg.click('[data-act=doImport]'); pg.wait_for_timeout(2500)
    ut = {}
    def ta(namn):
        pg.wait_for_timeout(150)
        ut[namn] = '\n'.join(pg.inner_text(s) for s in ['#mainBody', '#panel', '#status'] if pg.locator(s).count())
    klick = lambda sel: pg.evaluate("s => document.querySelector(s)?.click()", sel)
    ta('tid')
    for i in range(3): klick('.wk-nav button'); ta(f'vecka -{i + 1}')
    klick('[data-act=page][data-page=projekt]'); ta('projekt')
    for i in range(4):
        pg.evaluate("i => document.querySelectorAll('[data-act=openProject]')[i]?.click()", i * 7); ta(f'projekt {i}'); klick('[data-act=backList]')
    klick('[data-act=page][data-page=kunder]'); ta('kunder')
    klick('[data-act=openCustomer]'); ta('kund')
    klick('[data-act=page][data-page=rapporter]')
    for i in range(pg.evaluate("() => document.querySelectorAll('[data-act=repTab]').length")):
        pg.evaluate("i => document.querySelectorAll('[data-act=repTab]')[i].click()", i); ta(f'rapport {i}')
    klick('[data-act=page][data-page=installningar]'); ta('inställningar')
    ctx.close(); return ut, fel

def main():
    ref = REPO / '_jamfor.html'
    ref.write_bytes(subprocess.run(['git', '-C', str(REPO), 'show', f'{REF}:index.html'], capture_output=True, check=True).stdout)
    tmp = pathlib.Path(tempfile.mkdtemp()) / 'stor.sisyfos.json'; bygg(tmp)
    bocker = [REPO / 'test/bocker/format-6.json', REPO / 'test/bocker/format-7.json', tmp]
    skillnader = 0
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for bok in bocker:
                a, f1 = skarmar(b, BAS + '_jamfor.html', bok); c, f2 = skarmar(b, BAS + 'index.html', bok)
                for k in a:
                    x, y = a[k], c.get(k, '')
                    if x != y:
                        skillnader += 1
                        d = [(u, v) for u, v in zip(x.split('\n'), y.split('\n')) if u != v][:3]
                        print(f'SKILLNAD {bok.name} · {k}: {d}')
                print(f'{bok.name}: {len(a)} skärmar jämförda', 'skriptfel: ' + '; '.join(f1 + f2) if f1 or f2 else '')
            b.close()
    finally:
        ref.unlink(missing_ok=True)
    print('Lika överallt.' if not skillnader else f'{skillnader} skillnader (versionsnumret räknas också).')
    sys.exit(1 if skillnader else 0)

if __name__ == '__main__':
    main()
