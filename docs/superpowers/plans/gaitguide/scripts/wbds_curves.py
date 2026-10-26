import csv, os, re, json, numpy as np, collections
F = '../wbds_data/files'
info = list(csv.DictReader(open('../wbds_data/WBDSinfo.csv', encoding='utf-8')))
subj = {}
speeds = collections.defaultdict(list)
for r in info:
    s = int(r['Subject']); subj[s] = r
    m = re.match(r'WBDS(\d+)walkO\d+([CSF])\.c3d$', r['FileName'])
    if m and r['GaitSpeed(m/s)'] not in ('--', ''):
        speeds[(s, m.group(2))].append(float(r['GaitSpeed(m/s)']))
def load(p):
    lines = open(p, encoding='utf-8').read().splitlines()
    head = lines[0].split('\t'); data = np.array([[float(x) for x in l.split('\t')] for l in lines[1:]])
    return head, data
G = 9.81
res = {}
for g in ['Young', 'Older']:
    for cond in 'SCF':
        cur = collections.defaultdict(list); pk = collections.defaultdict(list); sp = []; lg = []; hts = []
        for s, r in subj.items():
            if r['AgeGroup'] != g: continue
            p = os.path.join(F, 'WBDS%02dwalkO%sang.txt' % (s, cond)); q = os.path.join(F, 'WBDS%02dwalkO%sknt.txt' % (s, cond))
            if not (os.path.exists(p) and os.path.exists(q)): continue
            H, A = load(p); K, B = load(q)
            if np.isnan(A[:, H.index('RKneeAngleZ')]).any() or np.isnan(B[:, K.index('RGRFY')]).any(): continue
            col = lambda n: A[:, H.index(n)]
            kc = lambda n: B[:, K.index(n)]
            hip, knee, ank = col('RHipAngleZ'), col('RKneeAngleZ'), col('RAnkleAngleZ')
            tilt, obl, rot, add = col('RPelvisAngleZ'), col('RPelvisAngleX'), col('RPelvisAngleY'), col('RHipAngleX')
            vy, vx, vz = kc('RGRFY') / G, kc('RGRFX') / G, kc('RGRFZ') / G
            for n, v in [('hip', hip), ('knee', knee), ('ankle', ank), ('tilt', tilt), ('obl', obl), ('rot', rot), ('add', add), ('vy', vy), ('vx', vx), ('vz', vz)]:
                cur[n].append(v)
            # toe-off: first point after 40% where vertical force < 0.05 BW
            to = next(i for i in range(40, 101) if vy[i] < 0.05)
            pk['toe_off'].append(to)
            pk['knee_ic'].append(knee[0])
            i = int(np.argmax(knee[0:30])); pk['knee_load'].append(knee[i]); pk['knee_load_t'].append(i)
            i = 40 + int(np.argmin(knee[40:60])) if False else int(np.argmin(knee[25:50])) + 25; pk['knee_mid'].append(knee[i]); pk['knee_mid_t'].append(i)
            i = int(np.argmax(knee[50:90])) + 50; pk['knee_swing'].append(knee[i]); pk['knee_swing_t'].append(i)
            pk['knee_to'].append(knee[to])
            pk['hip_ic'].append(hip[0])
            i = int(np.argmin(hip[30:70])) + 30; pk['hip_ext'].append(hip[i]); pk['hip_ext_t'].append(i)
            i = int(np.argmax(hip[70:101])) + 70; pk['hip_flex'].append(hip[i]); pk['hip_flex_t'].append(i)
            i = int(np.argmin(ank[0:20])); pk['ank_load'].append(ank[i]); pk['ank_load_t'].append(i)
            i = int(np.argmax(ank[20:60])) + 20; pk['ank_df'].append(ank[i]); pk['ank_df_t'].append(i)
            i = int(np.argmin(ank[50:80])) + 50; pk['ank_pf'].append(ank[i]); pk['ank_pf_t'].append(i)
            i = int(np.argmax(vy[0:35])); pk['f1'].append(vy[i]); pk['f1_t'].append(100.0 * i / to)
            i = int(np.argmax(vy[30:to])) + 30; pk['f2'].append(vy[i]); pk['f2_t'].append(100.0 * i / to)
            i1 = int(np.argmax(vy[0:35])); i2 = int(np.argmax(vy[30:to])) + 30
            i = int(np.argmin(vy[i1:i2])) + i1; pk['valley'].append(vy[i]); pk['valley_t'].append(100.0 * i / to)
            pk['brake'].append(vx[:to].min()); pk['prop'].append(vx[:to].max())
            pk['obl_range'].append(np.ptp(obl)); pk['rot_range'].append(np.ptp(rot)); pk['tilt_range'].append(np.ptp(tilt)); pk['tilt_mean'].append(tilt.mean())
            pk['add_max'].append(add[:60].max())
            sp.append(np.mean(speeds[(s, cond)])); lg.append(float(r['LegLength'])); hts.append(float(r['Height']))
        n = len(sp)
        mean = {k: np.mean(np.array(v), 0) for k, v in cur.items()}
        stats = {k: (float(np.mean(v)), float(np.std(v))) for k, v in pk.items()}
        res[(g, cond)] = dict(n=n, speed=(float(np.mean(sp)), float(np.std(sp))), leg=float(np.mean(lg)), height=float(np.mean(hts)), mean={k: v.tolist() for k, v in mean.items()}, stats=stats)
        print('== %s %s n=%d speed %.2f±%.2f m/s, Fr %.3f, height %.1f' % (g, cond, n, np.mean(sp), np.std(sp), np.mean(np.array(sp) ** 2 / (G * np.array(lg))), np.mean(hts)))
        print('   ' + '  '.join('%s %.1f±%.1f' % (k, a, b) for k, (a, b) in stats.items()))
json.dump({'%s_%s' % k: v for k, v in res.items()}, open('../wbds_data/walk_norms.json', 'w'))
