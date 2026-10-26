import csv, os, re, json, numpy as np
F = '../wbds_data/files'
G = 9.81
info = list(csv.DictReader(open('../wbds_data/WBDSinfo.csv', encoding='utf-8')))
subj = {int(r['Subject']): r for r in info}
def load(p):
    lines = open(p, encoding='utf-8').read().splitlines()
    return lines[0].split('\t'), np.array([[float(x) for x in l.split('\t')] for l in lines[1:]])
N = json.load(open('../wbds_data/walk_norms.json'))
lab = {'S': None, 'C': None, 'F': None}
sp = {c: '%.2f' % N['Young_' + c]['speed'][0] for c in 'SCF'}
print(sp, {c: N['Young_' + c]['stats']['toe_off'][0] for c in 'SCF'})
def fmt(v): return '%g' % round(v, 2)
joints, pelvis, grf = [], [], []
for c in 'SCF':
    m = N['Young_' + c]['mean']
    s = sp[c].replace('.', ',')
    for p in range(0, 101, 5):
        for j in ('hip', 'knee', 'ankle'):
            joints.append("{pct:%d, speed:'%s', joint:'%s', deg:%s}" % (p, s, j, fmt(m[j][p])))
        pelvis.append("{pct:%d, speed:'%s', tilt:%s, obl:%s, rot:%s}" % (p, s, fmt(m['tilt'][p]), fmt(m['obl'][p]), fmt(m['rot'][p])))
    # GRF normalised to stance, per subject
    V, X = [], []
    for k, r in subj.items():
        if r['AgeGroup'] != 'Young': continue
        q = os.path.join(F, 'WBDS%02dwalkO%sknt.txt' % (k, c))
        if not os.path.exists(q): continue
        K, B = load(q)
        vy = B[:, K.index('RGRFY')] / G; vx = B[:, K.index('RGRFX')] / G
        if np.isnan(vy).any(): continue
        to = next(i for i in range(40, 101) if vy[i] < 0.05)
        t = np.linspace(0, to, 101)
        V.append(np.interp(t, np.arange(101), vy)); X.append(np.interp(t, np.arange(101), vx))
    V = np.mean(V, 0); X = np.mean(X, 0)
    print(c, 'f1 %.3f at %d%%, valley %.3f at %d%%, f2 %.3f at %d%%, brake %.3f, prop %.3f' % (
        V[:50].max(), V[:50].argmax(), V[30:70].min(), 30 + V[30:70].argmin(), V[50:].max(), 50 + V[50:].argmax(), X.min(), X.max()))
    for p in range(0, 101, 5):
        grf.append("{pct:%d, speed:'%s', vert:%s, ap:%s}" % (p, s, fmt(V[p]), fmt(X[p])))
open('walk_joints.js', 'w').write('[' + ','.join(joints) + ']')
open('walk_pelvis.js', 'w').write('[' + ','.join(pelvis) + ']')
open('walk_grf.js', 'w').write('[' + ','.join(grf) + ']')
print(len(joints), len(pelvis), len(grf))
for c in 'SCF':
    m = N['Young_' + c]['mean']
    print(c, 'tilt', ['%.1f' % m['tilt'][p] for p in range(0, 101, 10)])
    print(c, 'obl ', ['%.1f' % m['obl'][p] for p in range(0, 101, 10)])
    print(c, 'rot ', ['%.1f' % m['rot'][p] for p in range(0, 101, 10)])
