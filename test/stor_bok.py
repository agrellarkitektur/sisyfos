"""
Bygger en stor testbok för prestandamätning: tio år, 250 projekt, ~11 500 tidposter (~4 MB).
  python3 test/stor_bok.py /tmp/stor.sisyfos.json
Används av test/prestanda.py och test/jamfor_versioner.py. Samma bok varje gång (fast slumpfrö).
"""
import json, random, sys, datetime as dt, pathlib

def bygg(ut):
    random.seed(7)
    b = json.load(open(pathlib.Path(__file__).parent / 'bocker' / 'format-7.json', encoding='utf-8'))
    R = b['register']; pid = b['session']['personId']
    R['customers'] = [{'id': f'k{i}', 'name': f'Kund {i}', 'archived': False, 'created': '2017-01-01T00:00:00Z', 'notes': []} for i in range(60)]
    base = [p for p in R['projects'] if p.get('internal') or p.get('kind') == 'absence']
    projs = []
    for i in range(250):
        y = 2017 + i // 25
        projs.append({'id': f'p{i}', 'number': f'{y}-{i % 25 + 1:02d}', 'name': f'Projekt {i}', 'customerId': f'k{i % 60}', 'property': '',
                      'budgetKr': random.choice([0, 100000, 250000, 400000]), 'internal': False, 'color': i % 8,
                      'status': 'active' if y >= 2025 else random.choice(['active', 'closed']),
                      'tasks': [{'id': f't{i}a', 'name': 'Skiss', 'billable': True}, {'id': f't{i}b', 'name': 'Bygglov', 'billable': True}],
                      'roleRates': {}, 'personRates': {}, 'memberRoles': {}, 'notices': {}, 'notes': [], 'created': f'{y}-01-02T08:00:00Z', '_y': y})
    R['projects'] = projs + base
    ev, n = [], [0]
    def nid():
        n[0] += 1; return f'e{n[0]:07d}'
    d, end, idag = dt.date(2017, 1, 2), dt.date(2026, 10, 23), dt.date.today()
    end = max(end, idag)
    R['handled'] = {}; weeks = set()
    while d <= end:
        if d.weekday() < 5:
            act = [p for p in projs if p['_y'] <= d.year <= p['_y'] + 1] or projs[-25:]
            for p in random.sample(act, min(len(act), random.randint(3, 6))):
                eid = nid(); t = random.choice(p['tasks'])['id']
                ev.append({'id': nid(), 'entryId': eid, 'type': 'create', 'at': f'{d}T16:00:00.000Z', 'by': pid,
                           'data': {'date': str(d), 'projectId': p['id'], 'taskId': t, 'roleId': 'roll1', 'hours': random.choice([0.5, 1, 1.5, 2, 3]), 'note': 'Ritade fasad, möte med kund', 'rate': 950}})
                if random.random() < .3:
                    ev.append({'id': nid(), 'entryId': eid, 'type': 'update', 'at': f'{d}T17:00:00.000Z', 'by': pid, 'data': {'note': 'Ritade fasad och plan, möte med kund'}})
                if d < end - dt.timedelta(days=90):
                    R['handled'][f"{p['id']}|{str(d)[:7]}"] = {'at': '2026-01-01T00:00:00Z', 'by': pid, 'hours': 0, 'amount': 0}
            mon = d - dt.timedelta(days=d.weekday())
            if mon not in weeks and d < end - dt.timedelta(days=7):
                weeks.add(mon)
                ev.append({'id': nid(), 'entryId': None, 'type': 'week', 'at': f'{mon + dt.timedelta(days=4)}T17:00:00.000Z', 'by': pid, 'data': {'week': str(mon), 'checked': True}})
        d += dt.timedelta(days=1)
    for p in projs: del p['_y']
    ev.sort(key=lambda e: e['at'])
    b['logs'] = {pid: {'events': ev}}
    R['book']['name'] = 'Stor testbok'
    json.dump(b, open(ut, 'w', encoding='utf-8'), ensure_ascii=False)
    return sum(e['type'] == 'create' for e in ev)

if __name__ == '__main__':
    ut = sys.argv[1] if len(sys.argv) > 1 else 'stor.sisyfos.json'
    print(bygg(ut), 'tidposter →', ut)
