import json, re, sys, os, urllib.request
sys.path.insert(0, '.')
import remotezip as rz
OUT = '../wbds_data/files'
os.makedirs(OUT, exist_ok=True)
req = urllib.request.Request('https://ndownloader.figshare.com/files/68504641', headers=rz.UA)
with urllib.request.urlopen(req, timeout=120) as r:
    open('../wbds_data/WBDSinfo.csv', 'wb').write(r.read())
D = json.load(open('../wbds_data/dir.json'))
ents = D['entries']
url = rz.resolve('https://ndownloader.figshare.com/files/68194516')[0]
pat = re.compile(sys.argv[1])
sel = [e for e in ents if pat.search(e['name'])]
n = 0
for i, e in enumerate(sel):
    name = os.path.basename(e['name'])
    path = os.path.join(OUT, name)
    if os.path.exists(path):
        continue
    if i and i % 200 == 0:
        url = rz.resolve('https://ndownloader.figshare.com/files/68194516')[0]
    try:
        data = rz.member(url, e)
    except Exception:
        url = rz.resolve('https://ndownloader.figshare.com/files/68194516')[0]
        data = rz.member(url, e)
    open(path, 'wb').write(data)
    n += 1
print('fetched', n, 'of', len(sel))
