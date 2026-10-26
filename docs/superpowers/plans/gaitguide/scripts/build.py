import sys, re
def build(src, subs, out):
    s = open(src, encoding='utf-8').read()
    for k, f in subs.items():
        s = s.replace(k, open(f, encoding='utf-8').read())
    one = ''.join(ln.strip() for ln in s.splitlines())
    # balance check outside string literals / template text (rough)
    pairs = {'(': ')', '[': ']', '{': '}'}
    stack = []
    for ch in one:
        if ch in pairs: stack.append(ch)
        elif ch in pairs.values():
            if not stack or pairs[stack.pop()] != ch:
                print(src, 'UNBALANCED at', ch); break
    else:
        print(src, 'balanced' if not stack else 'left open: ' + ''.join(stack), len(one), 'chars')
    if '"' in one: print('  has a double quote')
    open(out, 'w', encoding='utf-8').write(one)
build('run_joints.jsx', {'__JOINTS__': 'joints.js'}, 'run_joints.one.js')
build('run_pelvis.jsx', {'__PELVIS__': 'pelvis.js'}, 'run_pelvis.one.js')
build('run_grf.jsx', {'__GRF__': 'grf.js'}, 'run_grf.one.js')
build('walk_joints.jsx', {'__WJOINTS__': 'walk_joints.js'}, 'walk_joints.one.js')
build('walk_pelvis.jsx', {'__WPELVIS__': 'walk_pelvis.js'}, 'walk_pelvis.one.js')
build('walk_grf.jsx', {'__WGRF__': 'walk_grf.js'}, 'walk_grf.one.js')
