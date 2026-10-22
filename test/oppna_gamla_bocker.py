#!/usr/bin/env python3
"""
Sisyfos – kontroll att gamla böcker går att öppna.

Löftet: en bok som sparats i en tidigare version ska alltid gå att öppna i en senare.
För varje fil i test/bocker/ (en per filformat) startar skriptet appen i en tom webbläsare,
lägger boken där en tidigare version skulle ha sparat den och kontrollerar att
  – sidan startar utan JavaScript-fel,
  – boken öppnas (bokens namn syns) och inte ersätts av exempelboken,
  – boken uppgraderas till appens filformat och sparas.

Kör:  python3 -m http.server 8765 &  python3 test/oppna_gamla_bocker.py
Kräver: pip install playwright && python3 -m playwright install chromium
"""
import json, pathlib, re, sys
from playwright.sync_api import sync_playwright

ROT = pathlib.Path(__file__).resolve().parent.parent
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/index.html'
appfmt = int(re.search(r'FORMAT_VERSION = (\d+)', (ROT / 'index.html').read_text(encoding='utf-8')).group(1))
fel = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for fil in sorted((ROT / 'test' / 'bocker').glob('*.json')):
        bok = json.loads(fil.read_text(encoding='utf-8'))
        namn = bok['register']['book']['name']
        ctx = b.new_context(viewport={'width': 1280, 'height': 800}, service_workers='block')
        # Så som 0.6 och tidigare sparade boken: bara i localStorage
        ctx.add_init_script(f"if (!sessionStorage.getItem('lagd')) {{ localStorage.setItem('sisyfos.bok', {json.dumps(json.dumps(bok))}); sessionStorage.setItem('lagd', '1'); }}")
        pg = ctx.new_page(); js = []
        pg.on('pageerror', lambda e: js.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(1200)
        visad = pg.inner_text('#bookName')
        dlg = pg.inner_text('#dlg h2') if pg.is_visible('#dlg') else ''
        sparad = json.loads(pg.evaluate("localStorage.getItem('sisyfos.bok')") or '{}')
        ok = not js and namn in visad and not dlg and sparad.get('version') == appfmt
        print(('OK  ' if ok else 'FEL ') + f"{fil.name}: format {bok.get('version')} → {sparad.get('version')}, visar ”{visad.strip()}”"
              + (f", dialog ”{dlg}”" if dlg else '') + (f", JS-fel: {js}" if js else ''))
        fel += not ok
        ctx.close()
    b.close()
sys.exit(1 if fel else 0)
