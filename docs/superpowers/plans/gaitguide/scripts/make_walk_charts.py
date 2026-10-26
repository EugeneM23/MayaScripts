def rep(s, pairs, name):
    for a, b in pairs:
        assert a in s, (name, a)
        s = s.replace(a, b)
    return s
SPEEDS = "[{speed:'0,88', name:'медленно', toe:63.5, op:0.35},{speed:'1,24', name:'удобно', toe:61.8, op:0.65},{speed:'1,57', name:'быстро', toe:60.6, op:1}]"
j = open('run_joints.jsx', encoding='utf-8').read()
j = rep(j, [
 ("data-claude-component='run-joint-angles'", "data-claude-component='walk-joint-angles'"),
 ("__JOINTS__", "__WJOINTS__"),
 ("lo:-20, hi:60, step:20", "lo:-15, hi:45, step:15"),
 ("lo:0, hi:120, step:40", "lo:0, hi:75, step:25"),
 ("lo:-30, hi:30, step:15", "lo:-20, hi:20, step:10"),
 ("[{speed:'2,5', toe:38.5, op:0.35},{speed:'3,5', toe:33.8, op:0.65},{speed:'4,5', toe:32.6, op:1}]", SPEEDS),
 ("speeds.find(s => s.speed === '3,5')", "speeds.find(s => s.speed === '1,24')"),
 ("aria-label='Чем быстрее бег, тем сильнее колено сгибается в переносе'", "aria-label='Чем быстрее шаг, тем глубже колено сгибается после касания'"),
 (">Чем быстрее бег, тем сильнее колено сгибается в переносе</text>", ">Чем быстрее шаг, тем глубже колено сгибается после касания</text>"),
 (">Средние кривые 28 бегунов, правая нога; 0 % — касание. Серая полоса — опора на 3,5 м/с</text>", ">Средние кривые 24 взрослых 21–37 лет, правая нога; 0 % — касание. Серая полоса — опора</text>"),
 ("x1={left + k * 112} x2={left + k * 112 + 26}", "x1={left + k * 150} x2={left + k * 150 + 26}"),
 ("<text x={left + k * 112 + 32} y='82' fill='var(--cds-text-secondary)'>{`${s.speed} м/с`}</text>", "<text x={left + k * 150 + 32} y='82' fill='var(--cds-text-secondary)'>{`${s.name}, ${s.speed} м/с`}</text>"),
 ("<text x={right + 14} y={py + 10} fill='var(--cds-text-secondary)'>пик</text><text x={right + 14} y={py + 24} fill='var(--cds-text-secondary)'>в переносе</text>", "<text x={right + 14} y={py + 10} fill='var(--cds-text-secondary)'>пик после</text><text x={right + 14} y={py + 24} fill='var(--cds-text-secondary)'>касания</text>"),
 ("rows.filter(r => r.joint === 'knee' && r.speed === s.speed).reduce(", "rows.filter(r => r.joint === 'knee' && r.speed === s.speed && r.pct <= 30).reduce("),
 ("`${pn.label.split(':').at(0)}, ${s.speed} м/с,", "`${pn.label.split(':').at(0)}, ${s.name} ${s.speed} м/с,"),
], 'joints')
open('walk_joints.jsx', 'w', encoding='utf-8').write(j)

wp = """export default () => <claude.Visualize data-claude-component='walk-pelvis' sources={{rows:{kind:'data', data:__WPELVIS__}, panels:{kind:'data', data:[{key:'tilt', label:'Таз: наклон вперёд, °', lo:5, hi:15, step:5},{key:'obl', label:'Таз: боковой наклон, + правая сторона выше, °', lo:-8, hi:8, step:4},{key:'rot', label:'Таз: поворот, + правая сторона вперёд, °', lo:-8, hi:8, step:4}]}, speeds:{kind:'data', data:SPEEDS}, phases:{kind:'data', data:[{name:'двойная', a:0, b:11.8, both:1},{name:'на правой', a:11.8, b:50, both:0},{name:'двойная', a:50, b:61.8, both:1},{name:'на левой', a:61.8, b:100, both:0}]}}}>{({rows, panels, speeds, phases, datum}) => {
const left = 72, right = 664, ph = 120, gap = 52, y0 = 112;
const x = q => left + q / 100 * (right - left);
const val = (r, key) => key === 'tilt' ? r.tilt : key === 'obl' ? r.obl : r.rot;
const fmt = v => String(v).replace('.', ',');
const xt = Array.from({length: 11}, (_, i) => i * 10);
const last = y0 + 3 * ph + 2 * gap;
return <svg viewBox='0 0 760 640' role='img' aria-label='Чем быстрее шаг, тем сильнее таз качается и поворачивается' fontSize='12'>
<text data-claude-text-id='title' x='24' y='30' fontSize='16' fontWeight='600' fill='var(--cds-text-primary)'>Чем быстрее шаг, тем сильнее таз качается и поворачивается</text>
<text data-claude-text-id='subtitle' x='24' y='52' fill='var(--cds-text-secondary)'>Средние 24 взрослых 21–37 лет, 0 % — касание правой пяткой. Серые полосы — двойная опора</text>
<g data-claude-anchor='legend'>{speeds.map((s, k) => <g key={s.speed}><line x1={left + k * 150} x2={left + k * 150 + 26} y1='78' y2='78' stroke='var(--cds-chart-categorical-1)' strokeOpacity={s.op} strokeWidth='2.5'/><text x={left + k * 150 + 32} y='82' fill='var(--cds-text-secondary)'>{`${s.name}, ${s.speed} м/с`}</text></g>)}</g>
{panels.map((pn, k) => { const py = y0 + k * (ph + gap); const y = v => py + ph - (v - pn.lo) / (pn.hi - pn.lo) * ph; const ticks = Array.from({length: Math.round((pn.hi - pn.lo) / pn.step) + 1}, (_, i) => pn.lo + i * pn.step); return <g key={pn.key} data-claude-anchor={`panel-${pn.key}`}>
{phases.filter(f => f.both === 1).map(f => <rect key={f.a} x={x(f.a)} y={py} width={x(f.b) - x(f.a)} height={ph} fill='var(--cds-chart-reference-tint)'/>)}
<text x={left} y={py - 12} fontWeight='600' fill='var(--cds-text-primary)'>{pn.label}</text>
{ticks.map(v => <g key={v}><line x1={left} x2={right} y1={y(v)} y2={y(v)} stroke={v === 0 ? 'var(--cds-chart-axis)' : 'var(--cds-chart-grid)'}/><text x={left - 8} y={y(v) + 4} textAnchor='end' fill='var(--cds-text-secondary)'>{`${v > 0 && pn.key !== 'tilt' ? '+' : ''}${v}`}</text></g>)}
{speeds.map(s => { const pts = rows.filter(r => r.speed === s.speed); const d = pts.map((r, i) => `${i === 0 ? 'M' : 'L'}${x(r.pct)} ${y(val(r, pn.key))}`).join(' '); return <g key={s.speed} data-claude-anchor={`${pn.key}-${s.speed.replace(',', '')}`}><path d={d} fill='none' stroke='var(--cds-chart-categorical-1)' strokeOpacity={s.op} strokeWidth='2.5'/>{pts.map(r => <circle key={r.pct} cx={x(r.pct)} cy={y(val(r, pn.key))} r='3.5' fill='var(--cds-chart-categorical-1)' fillOpacity={s.op} {...datum(r, pn.key)}><title>{`${pn.label.split(',').at(0)}, ${s.name} ${s.speed} м/с, ${r.pct} % цикла: ${fmt(val(r, pn.key))}°`}</title></circle>)}</g>; })}
{pn.key !== 'tilt' ? <g data-claude-anchor={`range-${pn.key}`}><text x={right + 14} y={py + 10} fill='var(--cds-text-secondary)'>размах</text>{speeds.map((s, j) => { const vs = rows.filter(r => r.speed === s.speed).map(r => val(r, pn.key)); return <text key={s.speed} x={right + 14} y={py + 36 + (2 - j) * 20} fontSize='14' fontWeight='600' fill='var(--cds-chart-categorical-1)' fillOpacity={Math.max(s.op, 0.55)}>{`${fmt(Math.round((Math.max(...vs) - Math.min(...vs)) * 10) / 10)}°`}</text>; })}</g> : null}
</g>; })}
<g data-claude-anchor='phases'>{phases.map(f => <text key={f.a} x={x((f.a + f.b) / 2)} y={last + 18} textAnchor='middle' fill='var(--cds-text-secondary)'>{f.name}</text>)}</g>
<g data-claude-anchor='x-axis'>{xt.map(q => <text key={q} x={x(q)} y={last + 40} textAnchor='middle' fill='var(--cds-text-secondary)'>{`${q} %`}</text>)}</g>
<text data-claude-text-id='x-label' x={right} y={last + 62} textAnchor='end' fill='var(--cds-text-secondary)'>доля двойного шага от касания правой пяткой</text>
</svg>; }}</claude.Visualize>;
""".replace('SPEEDS', SPEEDS)
open('walk_pelvis.jsx', 'w', encoding='utf-8').write(wp)

g = open('run_grf.jsx', encoding='utf-8').read()
g = rep(g, [
 ("data-claude-component='run-ground-force'", "data-claude-component='walk-ground-force'"),
 ("__GRF__", "__WGRF__"),
 ("[{speed:'2,5', op:0.35},{speed:'3,5', op:0.65},{speed:'4,5', op:1}]", SPEEDS),
 ("const yv = v => y0 + ph - v / 3 * ph;", "const yv = v => y0 + ph - v / 1.2 * ph;"),
 ("const ya = v => y1 + ph - (v + 0.4) / 0.8 * ph;", "const ya = v => y1 + ph - (v + 0.3) / 0.6 * ph;"),
 ("const vt = [0, 1, 2, 3];", "const vt = [0, 0.4, 0.8, 1.2];"),
 ("const at = [-0.4, -0.2, 0, 0.2, 0.4];", "const at = [-0.3, -0.15, 0, 0.15, 0.3];"),
 ("aria-label='В беге сила опоры — один горб в середине опоры'", "aria-label='В ходьбе сила опоры — два горба; чем быстрее шаг, тем глубже провал между ними'"),
 (">В беге сила опоры — один горб в середине опоры, 2,3–2,6 веса тела</text>", ">В ходьбе сила опоры — два горба; чем быстрее шаг, тем глубже провал между ними</text>"),
 (">Средние 28 бегунов, сигнал с фильтром: удар пятки сглажен (без фильтра пики 2,4 · 2,65 · 2,8)</text>", ">Средние 24 взрослых 21–37 лет, правая стопа; 1 = вес тела</text>"),
 ("x1={left + k * 112} x2={left + k * 112 + 26}", "x1={left + k * 150} x2={left + k * 150 + 26}"),
 ("<text x={left + k * 112 + 32} y='82' fill='var(--cds-text-secondary)'>{`${s.speed} м/с`}</text>", "<text x={left + k * 150 + 32} y='82' fill='var(--cds-text-secondary)'>{`${s.name}, ${s.speed} м/с`}</text>"),
 ("`Вертикальная, ${s.speed} м/с,", "`Вертикальная, ${s.name} ${s.speed} м/с,"),
 ("`Вдоль хода, ${s.speed} м/с,", "`Вдоль хода, ${s.name} ${s.speed} м/с,"),
 ("<text x={right + 14} y={y0 + 10} fill='var(--cds-text-secondary)'>пик</text>", "<text x={right + 14} y={y0 + 10} fill='var(--cds-text-secondary)'>провал</text>"),
 ("const pk = rows.filter(r => r.speed === s.speed).reduce((a, r) => r.vert > a.vert ? r : a);", "const pk = rows.filter(r => r.speed === s.speed && r.pct >= 30 && r.pct <= 70).reduce((a, r) => r.vert < a.vert ? r : a);"),
], 'grf')
open('walk_grf.jsx', 'w', encoding='utf-8').write(g)
print('ok')
