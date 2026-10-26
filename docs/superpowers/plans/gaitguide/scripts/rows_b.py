import re, json, sys
src = open(sys.argv[1], encoding='utf-8').read()

def table_after(title):
    i = src.index(title)
    lines = src[i:].splitlines()
    out = []
    started = False
    for ln in lines[1:]:
        if ln.startswith('|'):
            started = True
            out.append([c.strip() for c in ln.strip('|').split('|')])
        elif started:
            break
    return out[2:]  # drop header and separator

def num(s):
    return float(s.replace('−', '-'))

t3 = table_after('**Table 3')
joints = []
for r in t3:
    pct = int(r[0])
    vals = [num(v) for v in r[1:]]
    for k, sp in enumerate(['2,5', '3,5', '4,5']):
        for j, name in enumerate(['hip', 'knee', 'ankle']):
            joints.append({'pct': pct, 'speed': sp, 'joint': name, 'deg': vals[k * 3 + j]})
t5 = table_after('**Table 5')
pelvis = [{'pct': int(r[0]), 'tilt': num(r[1]), 'obl': num(r[2]), 'rot': num(r[3]), 'com': num(r[4]), 'vel': num(r[5])} for r in t5]
t6 = table_after('**Table 6')
grf = []
for r in t6:
    pct = int(r[0])
    v = [num(x) for x in r[1:]]
    for k, sp in enumerate(['2,5', '3,5', '4,5']):
        grf.append({'pct': pct, 'speed': sp, 'vert': v[k], 'ap': v[k + 3]})

def js(rows):
    parts = []
    for r in rows:
        items = []
        for k, v in r.items():
            items.append("%s:%s" % (k, ("'%s'" % v) if isinstance(v, str) else (('%g' % v))))
        parts.append('{' + ', '.join(items) + '}')
    return '[' + ','.join(parts) + ']'

out = sys.argv[2]
open(out + '/joints.js', 'w', encoding='utf-8').write(js(joints))
open(out + '/pelvis.js', 'w', encoding='utf-8').write(js(pelvis))
open(out + '/grf.js', 'w', encoding='utf-8').write(js(grf))
print(len(joints), len(pelvis), len(grf))
print(js(pelvis)[:300])
