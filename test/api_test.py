#!/usr/bin/env python3
"""Testar api.php lokalt med PHP:s inbyggda server.

Bygger en låtsas-webbhotellstruktur i en tillfällig mapp:
  <tmp>/public_html/sisyfos/api.php  → datamappen hamnar i <tmp>/sisyfos-data (utanför webbroten)
och kör samma sak en gång till där mappen utanför inte går att skapa → datamappen blir sisyfos/data/.

Kör: python3 test/api_test.py   (kräver php i PATH)
"""
import base64, hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN = 'testnyckel-for-admin'
fel = []


def ok(cond, text):
    print(('OK  ' if cond else 'FEL ') + text)
    if not cond:
        fel.append(text)


def ledig_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


class Api:
    def __init__(self, base):
        self.base = base; self.token = None

    def call(self, a, body=None, method=None, headers=None, raw=False, query=''):
        h = dict(headers or {})
        if self.token: h['X-Sisyfos-Token'] = self.token
        data = None
        if body is not None:
            data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode()
            h.setdefault('Content-Type', 'application/json')
        req = urllib.request.Request(f'{self.base}/api.php?a={a}{query}', data=data, headers=h, method=method or ('POST' if data is not None else 'GET'))
        try:
            with urllib.request.urlopen(req) as r:
                b = r.read(); return r.status, (b if raw else json.loads(b)), dict(r.headers)
        except urllib.error.HTTPError as e:
            b = e.read()
            try: return e.code, json.loads(b), dict(e.headers)
            except Exception: return e.code, b, dict(e.headers)


def vault(salt=None, vid='v-1'):
    salt = salt or base64.b64encode(os.urandom(16)).decode()
    return {'v': 1, 'id': vid, 'created': '2026-10-23T10:00:00Z', 'kdf': {'name': 'PBKDF2-SHA-256', 'iter': 600000, 'salt': salt},
            'pw': {'iv': 'aaaa', 'ct': 'bbbb'}, 'pwAt': '2026-10-23T10:00:00Z', 'rk': {'salt': 'c', 'iv': 'd', 'ct': 'e'}, 'rkAt': '2026-10-23T10:00:00Z'}


def bok(v, n):
    return json.dumps({'format': 'sisyfos-krypterad', 'version': 1, 'app': 'test', 'saved': n, 'vault': v, 'zip': 'gzip', 'data': {'iv': 'x', 'ct': 'y' * (50 + n)}}).encode()


def kor(laget):
    tmp = tempfile.mkdtemp(prefix='sisyfos-api-')
    web = os.path.join(tmp, 'public_html', 'sisyfos'); os.makedirs(web)
    shutil.copy(os.path.join(ROOT, 'api.php'), web)
    with open(os.path.join(web, 'api-config.php'), 'w') as f:
        f.write("<?php return ['admin' => '%s'];\n" % hashlib.sha256(ADMIN.encode()).hexdigest())
    if laget == 'inside':
        open(os.path.join(tmp, 'sisyfos-data'), 'w').close()  # en fil i vägen: mappen utanför webbroten går inte att skapa
    port = ledig_port()
    srv = subprocess.Popen(['php', '-S', f'127.0.0.1:{port}', '-t', os.path.join(tmp, 'public_html')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: socket.create_connection(('127.0.0.1', port), 0.2).close(); break
            except OSError: time.sleep(0.1)
        api = Api(f'http://127.0.0.1:{port}/sisyfos')
        print(f'--- datamappen {laget} ---')

        s, d, _ = api.call('status')
        ok(s == 200 and d['storage'] == laget and d['admin'] is True, f'status: lagring {d.get("storage")}, admin {d.get("admin")}')
        if laget == 'inside':
            ok(os.path.isfile(os.path.join(web, 'data', '.htaccess')), '.htaccess skapad i data/')
        else:
            ok(os.path.isdir(os.path.join(tmp, 'sisyfos-data', 'acc')), 'datamappen utanför webbroten')

        # inbjudningskoder
        s, d, _ = api.call('invite', {'note': 'test'}, headers={'X-Sisyfos-Admin': 'fel'})
        ok(s == 403, 'fel adminnyckel nekas')
        s, d, _ = api.call('invite', {'note': 'Testare', 'max': 1}, headers={'X-Sisyfos-Admin': ADMIN})
        ok(s == 201 and len(d['code']) == 11, f'inbjudningskod skapad ({d.get("code")})')
        kod = d['code']

        # kdf för okänd adress är stabil och ser äkta ut
        s, k1, _ = api.call('kdf', {'email': 'Anna@Exempel.se'})
        s, k2, _ = api.call('kdf', {'email': 'anna@exempel.se '})
        ok(k1 == k2 and k1['kdf']['iter'] == 600000 and len(base64.b64decode(k1['kdf']['salt'])) == 16, 'kdf: falskt salt stabilt för okänd adress')

        v = vault(); login = base64.b64encode(os.urandom(32)).decode()
        s, d, _ = api.call('register', {'invite': 'FEL00-00000', 'email': 'anna@exempel.se', 'login': login, 'vault': v})
        ok(s == 403, 'registrering med fel kod nekas')
        s, d, _ = api.call('register', {'invite': kod.lower(), 'email': 'Anna@Exempel.se', 'login': login, 'vault': v, 'device': 'Testdator'})
        ok(s == 201 and d['email'] == 'anna@exempel.se' and d['rev'] == 0, 'konto skapat (kod med gemener, adress normaliserad)')
        api.token = d['token']
        s, d, _ = api.call('register', {'invite': kod, 'email': 'bertil@exempel.se', 'login': login, 'vault': vault()})
        ok(s == 403, 'koden kan inte användas två gånger')

        s, k3, _ = api.call('kdf', {'email': 'anna@exempel.se'})
        ok(k3['kdf']['salt'] == v['kdf']['salt'], 'kdf: kontots riktiga salt')

        # spara och hämta
        s, d, _ = api.call('get', raw=True)
        ok(s == 404, 'ingen bok än')
        s, d, _ = api.call('put', bok(v, 1))
        ok(s == 428, 'put utan If-Match nekas')
        s, d, _ = api.call('put', b'{"format":"sisyfos","version":7}', headers={'X-Sisyfos-Base': '0'})
        ok(s == 400, 'okrypterad bok nekas')
        s, d, _ = api.call('put', bok(v, 1), headers={'If-Match': '"0"'})
        ok(s == 200 and d['rev'] == 1, 'första sparning → version 1')
        s, d, _ = api.call('put', bok(v, 2), headers={'X-Sisyfos-Base': '0'})
        ok(s == 409 and d['error'] == 'conflict' and d['rev'] == 1, 'krock med gammal version → 409 med serverns version')
        s, d, _ = api.call('put', bok(vault(vid='annan'), 2), headers={'X-Sisyfos-Base': '1'})
        ok(s == 409 and d['error'] == 'vault', 'bok med annat valv nekas')
        for n in range(2, 15):
            s, d, _ = api.call('put', bok(v, n), headers={'X-Sisyfos-Base': str(n - 1)})
        ok(s == 200 and d['rev'] == 14, 'flera sparningar → version 14')
        s, d, h = api.call('get', raw=True)
        ok(s == 200 and json.loads(d)['saved'] == 14 and h.get('X-Sisyfos-Rev') == '14', 'hämtar senaste versionen')
        s, d, _ = api.call('history')
        ok(len(d['history']) == 10 and d['history'][0]['rev'] == 13, 'tio tidigare versioner sparas')
        s, d, _ = api.call('get', raw=True, query='&rev=10')
        ok(s == 200 and json.loads(d)['saved'] == 10, 'hämtar en tidigare version')
        s, d, _ = api.call('get', raw=True, query='&rev=2')
        ok(s == 404, 'för gammal version finns inte kvar')

        # inloggning på ny enhet
        tok1 = api.token; api.token = None
        s, d, _ = api.call('get', raw=True)
        ok(s == 401, 'utan inloggning nekas')
        s, d, _ = api.call('login', {'email': 'anna@exempel.se', 'login': base64.b64encode(os.urandom(32)).decode()})
        ok(s == 401, 'fel lösenord nekas')
        s, d, _ = api.call('login', {'email': 'ingen@exempel.se', 'login': login})
        ok(s == 401 and d['message'] == 'Fel e-postadress eller lösenord.', 'okänt konto ger samma svar')
        s, d, _ = api.call('login', {'email': 'ANNA@exempel.se', 'login': login, 'device': 'Telefon'})
        ok(s == 200 and d['rev'] == 14 and d['vault']['id'] == 'v-1', 'inloggning ger valv och version')
        tok2 = d['token']; api.token = tok2
        s, d, _ = api.call('info')
        ok(len(d['devices']) == 2 and sum(x['this'] for x in d['devices']) == 1, 'två enheter, den här markerad')
        api.token = 'Bearer ' + tok1
        s, d, _ = api.call('info')
        ok(s == 200, 'token med "Bearer " fungerar också')

        # byt lösenord: nytt valv + ny inloggning, logga ut andra enheter
        api.token = tok1
        v2 = dict(v, kdf=dict(v['kdf'], salt=base64.b64encode(os.urandom(16)).decode()), pw={'iv': 'n', 'ct': 'm'})
        s, d, _ = api.call('vault', {'vault': v2})
        ok(s == 400, 'nytt salt utan ny inloggning nekas')
        login2 = base64.b64encode(os.urandom(32)).decode()
        s, d, _ = api.call('vault', {'vault': v2, 'login': login2, 'logoutOthers': True})
        ok(s == 200, 'lösenordsbyte sparat')
        api.token = tok2; s, d, _ = api.call('info')
        ok(s == 401, 'andra enheten utloggad')
        api.token = None
        s, d, _ = api.call('login', {'email': 'anna@exempel.se', 'login': login})
        ok(s == 401, 'gamla lösenordet gäller inte')
        s, d, _ = api.call('login', {'email': 'anna@exempel.se', 'login': login2})
        ok(s == 200 and d['vault']['pw']['ct'] == 'm', 'nya lösenordet ger nya valvet')

        # begränsning av försök
        for _ in range(8):
            s, d, _ = api.call('login', {'email': 'anna@exempel.se', 'login': login})
        s, d, _ = api.call('login', {'email': 'anna@exempel.se', 'login': login2})
        ok(s == 429, 'efter åtta fel spärras kontot en stund, även för rätt lösenord')

        # admin, utloggning och radering
        s, d, _ = api.call('accounts', headers={'X-Sisyfos-Admin': ADMIN})
        ok(s == 200 and d['accounts'][0]['email'] == 'anna@exempel.se' and d['accounts'][0]['rev'] == 14, 'admin ser kontot')
        s, d, _ = api.call('invites', headers={'X-Sisyfos-Admin': ADMIN})
        ok(d['invites'][0]['used'] == 1, 'admin ser att koden är använd')
        api.token = tok1
        s, d, _ = api.call('delete', {'login': login})
        ok(s in (401, 429), 'radering med fel lösenord nekas')
        s, d, _ = api.call('logout', {})
        ok(s == 200, 'utloggning')
        s, d, _ = api.call('info')
        ok(s == 401, 'token gäller inte efter utloggning')
        s, d, _ = api.call('remove', {'email': 'anna@exempel.se'}, headers={'X-Sisyfos-Admin': ADMIN})
        ok(s == 200, 'admin tar bort kontot')
        s, d, _ = api.call('accounts', headers={'X-Sisyfos-Admin': ADMIN})
        ok(d['accounts'] == [], 'inga konton kvar')

        # inget innehåll i klartext på disk
        datadir = os.path.join(web, 'data') if laget == 'inside' else os.path.join(tmp, 'sisyfos-data')
        alla = ''.join(open(os.path.join(r, f), errors='ignore').read() for r, _, fs in os.walk(datadir) for f in fs)
        ok(login not in alla and login2 not in alla, 'inloggningshemligheterna finns inte på disk')
    finally:
        srv.terminate(); srv.wait()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    if not shutil.which('php'):
        print('php saknas – hoppar över'); sys.exit(0)
    kor('outside')
    kor('inside')
    print(f'\n{"Alla test gick igenom." if not fel else f"{len(fel)} fel."}')
    sys.exit(1 if fel else 0)
