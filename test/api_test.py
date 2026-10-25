#!/usr/bin/env python3
"""Testar api.php lokalt med PHP:s inbyggda server.

Bygger en låtsas-webbhotellstruktur i en tillfällig mapp:
  <tmp>/public_html/sisyfos/api.php  → datamappen hamnar i <tmp>/sisyfos-data (utanför webbroten)
och kör samma sak en gång till där mappen utanför inte går att skapa → datamappen blir sisyfos/data/.

Kör: python3 test/api_test.py   (kräver php i PATH)
"""
from urllib.parse import quote
import base64, hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN = 'Testnyckel för admin – åäö € 2026'
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
        s, d, _ = api.call('invite', {'note': 'Testare', 'max': 1}, headers={'X-Sisyfos-Admin': quote(ADMIN)})
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
        s, d, _ = api.call('accounts', headers={'X-Sisyfos-Admin': quote(ADMIN)})
        ok(s == 200 and d['accounts'][0]['email'] == 'anna@exempel.se' and d['accounts'][0]['rev'] == 14, 'admin ser kontot')
        s, d, _ = api.call('invites', headers={'X-Sisyfos-Admin': quote(ADMIN)})
        ok(d['invites'][0]['used'] == 1, 'admin ser att koden är använd')
        api.token = tok1
        s, d, _ = api.call('delete', {'login': login})
        ok(s in (401, 429), 'radering med fel lösenord nekas')
        s, d, _ = api.call('logout', {})
        ok(s == 200, 'utloggning')
        s, d, _ = api.call('info')
        ok(s == 401, 'token gäller inte efter utloggning')
        s, d, _ = api.call('remove', {'email': 'anna@exempel.se'}, headers={'X-Sisyfos-Admin': quote(ADMIN)})
        ok(s == 200, 'admin tar bort kontot')
        s, d, _ = api.call('accounts', headers={'X-Sisyfos-Admin': quote(ADMIN)})
        ok(d['accounts'] == [], 'inga konton kvar')

        # inget innehåll i klartext på disk
        datadir = os.path.join(web, 'data') if laget == 'inside' else os.path.join(tmp, 'sisyfos-data')
        alla = ''.join(open(os.path.join(r, f), errors='ignore').read() for r, _, fs in os.walk(datadir) for f in fs)
        ok(login not in alla and login2 not in alla, 'inloggningshemligheterna finns inte på disk')

        organisation(api, datadir)
    finally:
        srv.terminate(); srv.wait()
        shutil.rmtree(tmp, ignore_errors=True)


def del_(by, to, n=1):
    """En låtsasdel: servern kan inte läsa den, bara se skribenten (by) och läsarna (to)"""
    return {'by': by, 'epk': {'x': 'a', 'y': 'b'}, 'to': {p: {'iv': 'i', 'ct': 'c'} for p in to}, 'zip': 'gzip', 'iv': 'x', 'ct': 'y' * (40 + n), 'sig': 's'}


def fil(v, me, parts):
    return json.dumps({'format': 'sisyfos-krypterad', 'version': 2, 'app': 'test', 'saved': 'nu', 'vault': v, 'zip': 'gzip', 'org': 'otest', 'me': me,
                       'keys': {me: {'at': '2026', 'fp': 'f', 'box': {'iv': 'r', 'ct': 'q'}}}, 'parts': parts, 'data': {'iv': 's', 'ct': 't'}}).encode()


def organisation(api, datadir):
    """Organisationer (0.16.1): kod från serverns ägare, admin bjuder in, medarbetaren går med, delar med en skribent var"""
    adm = {'X-Sisyfos-Admin': quote(ADMIN)}
    s, d, _ = api.call('invite', {'note': 'Konto', 'max': 1}, headers=adm); kodA = d['code']
    s, d, _ = api.call('invite', {'note': 'Byrån', 'kind': 'org'}, headers=adm); kodO = d['code']
    ok(s == 201 and d['kind'] == 'org', 'kod för en organisation')
    vA, lA = vault(vid='va'), base64.b64encode(os.urandom(32)).decode()
    api.token = None
    s, d, _ = api.call('register', {'invite': kodO, 'email': 'ca@byran.se', 'login': lA, 'vault': vA})
    ok(s == 403, 'en organisationskod skapar inget konto')
    s, d, _ = api.call('register', {'invite': kodA, 'email': 'ca@byran.se', 'login': lA, 'vault': vA}); api.token = tA = d['token']
    s, d, _ = api.call('put', bok(vA, 1), headers={'X-Sisyfos-Base': '0'})
    ok(s == 200 and d['rev'] == 1, 'admin har en egen bok')
    s, d, _ = api.call('orgCreate', {'code': kodA, 'book': 'otest', 'name': 'Byrån', 'pid': 'pers1'})
    ok(s == 403, 'en kontokod skapar ingen organisation')
    s, d, _ = api.call('orgCreate', {'code': kodO, 'book': 'otest', 'name': 'Byrån', 'pid': 'pers1'})
    ok(s == 201 and d['org']['role'] == 'admin' and d['org']['pid'] == 'pers1', 'organisationen skapad, kontot är admin')
    oid = d['org']['id']; q = '&org=' + oid
    s, d, _ = api.call('info')
    ok(s == 409 and d['error'] == 'moved' and d['org']['id'] == oid, 'den egna boken har flyttat – en gammal enhet får veta vart')
    s, d, _ = api.call('info', query=q)
    ok(s == 200 and d['rev'] == 0 and d['org']['members'][0]['email'] == 'ca@byran.se', 'info för organisationen')

    # admin sparar registret, fakturorna, sitt kort och sin logg – och förvaltar Annas logg
    parts = {'reg': del_('pers1', ['pers1']), 'adm': del_('pers1', ['pers1']), 'card.pers1': del_('pers1', ['pers1']), 'log.pers1': del_('pers1', ['pers1']), 'log.anna': del_('pers1', ['pers1'])}
    s, d, _ = api.call('put', fil(vA, 'pers1', parts), headers={'X-Sisyfos-Base': '0'}, query=q)
    ok(s == 200 and d['rev'] == 1 and d['behind'] is False, 'admin sparar delarna → version 1')
    s, d, _ = api.call('put', fil(vA, 'pers1', {'reg': del_('pers2', ['pers1'])}), headers={'X-Sisyfos-Base': '1'}, query=q)
    ok(s == 403, 'en del som säger sig vara skriven av någon annan nekas')

    # inbjudan – och taket
    s, d, _ = api.call('orgInvite', {'pid': 'anna', 'note': 'Anna'}, query=q); kodM = d['code']
    ok(s == 201 and len(kodM) == 11, f'admin bjuder in Anna ({kodM})')
    for i in range(8):
        s, d, _ = api.call('orgInvite', {'pid': f'p{i}'}, query=q)
    ok(s == 201, 'tio platser: admin, Anna och åtta inbjudningar')
    s, d, _ = api.call('orgInvite', {'pid': 'p9'}, query=q)
    ok(s == 409 and d['error'] == 'org_full', 'den elfte nekas (tak 10)')
    s, d, _ = api.call('info', query=q)
    for x in d['org']['invites']:
        if x['pid'].startswith('p'): api.call('orgUninvite', {'code': x['code']}, query=q)
    s, d, _ = api.call('invites', headers=adm)
    ok(all(x['kind'] != 'member' for x in d['invites']), 'serverns ägare ser inte medarbetarkoderna')

    # Anna skapar konto med koden och lämnar sina nycklar
    vN, lN = vault(vid='vn'), base64.b64encode(os.urandom(32)).decode()
    api.token = None
    s, d, _ = api.call('register', {'invite': kodM, 'email': 'anna@byran.se', 'login': lN, 'vault': vN})
    ok(s == 201 and d['org']['id'] == oid and d['org']['pid'] == 'anna' and d['org']['role'] == 'member', 'Anna har konto och är medarbetare')
    api.token = tN = d['token']
    s, d, _ = api.call('get', raw=True, query=q); f = json.loads(d)
    ok(s == 200 and f['me'] == 'anna' and f['parts'] == {} and f['srv']['wrote'] == ['pers1'], 'Anna ser inga delar innan admin tagit in henne')
    keys = {'enc': {'kty': 'EC', 'crv': 'P-256', 'x': 'ex', 'y': 'ey'}, 'sig': {'kty': 'EC', 'crv': 'P-256', 'x': 'sx', 'y': 'sy'}, 'at': '2026-10-25', 'fp': 'abcd'}
    s, d, _ = api.call('orgKeys', {'keys': keys, 'env': {'vault': vN, 'keys': {'anna': {'at': '1', 'fp': 'abcd', 'box': {}}}, 'data': {'iv': 'a', 'ct': 'b'}}}, query=q)
    ok(s == 200, 'Anna lämnar sina offentliga nycklar och sitt omslag')
    s, d, _ = api.call('info', query=q)
    ok(s == 200 and 'email' not in d['org']['members'][0] and d['org']['invites'] == [], 'Anna ser inte medlemmarnas e-post eller inbjudningarna')
    s, d, _ = api.call('orgInvite', {'pid': 'x1'}, query=q)
    ok(s == 403, 'Anna kan inte bjuda in')
    s, d, _ = api.call('put', fil(vN, 'anna', {'reg': del_('anna', ['anna'])}), headers={'X-Sisyfos-Base': '1'}, query=q)
    ok(s == 403, 'Anna kan inte skriva registret')
    s, d, _ = api.call('put', fil(vN, 'anna', {'log.pers1': del_('anna', ['anna'])}), headers={'X-Sisyfos-Base': '1'}, query=q)
    ok(s == 403, 'Anna kan inte skriva någon annans tidlogg')

    # admin ser nycklarna, krypterar om till Anna och lämnar över hennes logg
    api.token = tA
    s, d, _ = api.call('info', query=q)
    anna = [m for m in d['org']['members'] if m['pid'] == 'anna'][0]
    ok(anna['keys']['fp'] == 'abcd' and anna['email'] == 'anna@byran.se', 'admin ser Annas nycklar')
    parts = {'reg': del_('pers1', ['pers1', 'anna'], 2), 'card.anna': del_('pers1', ['pers1', 'anna']), 'log.anna': del_('pers1', ['pers1', 'anna'], 3)}
    s, d, _ = api.call('put', fil(vA, 'pers1', parts), headers={'X-Sisyfos-Base': '1'}, query=q)
    ok(s == 200 and d['rev'] == 2, 'admin krypterar om till Anna → version 2')

    api.token = tN
    s, d, h = api.call('get', raw=True, query=q); f = json.loads(d)
    ok(sorted(f['parts']) == ['card.anna', 'log.anna', 'reg'] and h.get('X-Sisyfos-Rev') == '2' and f['keys']['anna']['fp'] == 'abcd', f"Anna får bara sina delar: {sorted(f['parts'])}")
    s, d, _ = api.call('put', fil(vN, 'anna', {'log.anna': del_('anna', ['anna', 'pers1'], 4)}), headers={'X-Sisyfos-Base': '1'}, query=q)
    ok(s == 409 and d['error'] == 'conflict', 'Annas logg har ändrats sedan version 1 → krock')
    s, d, _ = api.call('put', fil(vN, 'anna', {'log.anna': del_('anna', ['anna', 'pers1'], 4)}), headers={'X-Sisyfos-Base': '2'}, query=q)
    ok(s == 200 and d['rev'] == 3, 'Anna skriver sin tidlogg → version 3')

    api.token = tA
    s, d, _ = api.call('put', fil(vA, 'pers1', {'log.anna': del_('pers1', ['pers1'])}), headers={'X-Sisyfos-Base': '3'}, query=q)
    ok(s == 403, 'när Anna har skrivit sin logg kan admin inte ändra den')
    s, d, _ = api.call('put', fil(vA, 'pers1', {'log.pers1': del_('pers1', ['pers1'], 5)}), headers={'X-Sisyfos-Base': '2'}, query=q)
    ok(s == 200 and d['behind'] is True, 'admins egen logg sparas utan krock – men andra delar är nyare (behind)')
    s, d, _ = api.call('get', raw=True, query=q); f = json.loads(d)
    ok(len(f['parts']) == 6 and sorted(f['srv']['wrote']) == ['anna', 'pers1'] and f['srv']['role'] == 'admin', 'admin ser alla delar och att Anna skrivit sin logg')

    # lösenordsbyte följer med till omslaget
    v2 = dict(vA, pw={'iv': 'n2', 'ct': 'm2'})
    s, d, _ = api.call('vault', {'vault': v2})
    s, d, _ = api.call('get', raw=True, query=q)
    ok(json.loads(d)['vault']['pw']['ct'] == 'm2', 'nytt valv i organisationens omslag')

    # serverns ägare ser organisationen
    s, d, _ = api.call('accounts', headers=adm)
    ok(d['orgs'][0]['name'] == 'Byrån' and d['orgs'][0]['members'] == 2, 'serverns ägare ser organisationen')
    alla = ''.join(open(os.path.join(r, f), errors='ignore').read() for r, _, fs in os.walk(os.path.join(datadir, 'org')) for f in fs)
    ok('anna@byran.se' in alla and lN not in alla, 'organisationen på disk: e-post för admin, inga hemligheter')

    # admin tar bort Anna
    s, d, _ = api.call('orgRemove', {'pid': 'pers1'}, query=q)
    ok(s == 400, 'admin kan inte ta bort sig själv')
    s, d, _ = api.call('orgRemove', {'pid': 'anna'}, query=q)
    ok(s == 200, 'admin tar bort Anna')
    api.token = tN
    s, d, _ = api.call('get', raw=True, query=q)
    ok(s == 403, 'Anna når inte organisationen längre')
    s, d, _ = api.call('info')
    ok(s == 200 and d['orgs'] == [], 'Annas konto finns kvar utan organisation')
    api.token = tA
    s, d, _ = api.call('put', fil(vA, 'pers1', {'log.anna': del_('pers1', ['pers1'], 6)}), headers={'X-Sisyfos-Base': '4'}, query=q)
    ok(s == 200, 'admin förvaltar Annas logg igen')

    # Anna går med igen med ett befintligt konto
    s, d, _ = api.call('orgInvite', {'pid': 'anna'}, query=q); kodM2 = d['code']
    api.token = tN
    s, d, _ = api.call('orgJoin', {'code': kodM2})
    ok(s == 200 and d['org']['pid'] == 'anna', 'ett befintligt konto går med med koden')
    s, d, _ = api.call('orgJoin', {'code': kodM2})
    ok(s == 403, 'koden kan inte användas igen')

    # admin raderar sitt konto → organisationen tas bort
    api.token = tA
    s, d, _ = api.call('delete', {'login': lA})
    ok(s == 200, 'admin raderar kontot')
    ok(not os.path.isdir(os.path.join(datadir, 'org', oid)), 'organisationen är borttagen från disk')
    api.token = tN
    s, d, _ = api.call('info')
    ok(s == 200 and d['orgs'] == [], 'Annas konto står kvar utan organisation')
    api.token = None
    api.call('remove', {'email': 'anna@byran.se'}, headers=adm)


if __name__ == '__main__':
    if not shutil.which('php'):
        print('php saknas – hoppar över'); sys.exit(0)
    kor('outside')
    kor('inside')
    print(f'\n{"Alla test gick igenom." if not fel else f"{len(fel)} fel."}')
    sys.exit(1 if fel else 0)
