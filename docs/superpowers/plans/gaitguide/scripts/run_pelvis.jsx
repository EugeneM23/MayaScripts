export default () => <claude.Visualize data-claude-component='run-pelvis-com' sources={{rows:{kind:'data', data:__PELVIS__}, panels:{kind:'data', data:[{key:'com', label:'ЦМ: высота от среднего, см', unit:' см', lo:-5, hi:5, step:5},{key:'tilt', label:'Таз: наклон вперёд от стойки, °', unit:'°', lo:0, hi:10, step:5},{key:'obl', label:'Таз: боковой наклон, + правая сторона выше, °', unit:'°', lo:-6, hi:6, step:6},{key:'rot', label:'Таз: поворот, + правая сторона вперёд, °', unit:'°', lo:-6, hi:6, step:6}]}, phases:{kind:'data', data:[{name:'опора правой', a:0, b:33.8, ground:1},{name:'полёт', a:33.8, b:50, ground:0},{name:'опора левой', a:50, b:83.8, ground:1},{name:'полёт', a:83.8, b:100, ground:0}]}}}>{({rows, panels, phases, datum}) => {
const left = 72, right = 664, ph = 100, gap = 46, y0 = 96;
const x = p => left + p / 100 * (right - left);
const val = (r, key) => key === 'com' ? r.com : key === 'tilt' ? r.tilt : key === 'obl' ? r.obl : r.rot;
const fmt = v => String(v).replace('.', ',');
const xt = Array.from({length: 11}, (_, i) => i * 10);
const last = y0 + 4 * ph + 3 * gap;
const low1 = rows.filter(r => r.pct < 50).reduce((a, r) => r.com < a.com ? r : a);
const low2 = rows.filter(r => r.pct >= 50).reduce((a, r) => r.com < a.com ? r : a);
const high1 = rows.filter(r => r.pct < 50).reduce((a, r) => r.com > a.com ? r : a);
const high2 = rows.filter(r => r.pct >= 50).reduce((a, r) => r.com > a.com ? r : a);
const yc = v => y0 + ph - (v + 5) / 10 * ph;
return <svg viewBox='0 0 760 712' role='img' aria-label='В беге ЦМ ниже всего в середине опоры, выше всего в полёте' fontSize='12'>
<text data-claude-text-id='title' x='24' y='30' fontSize='16' fontWeight='600' fill='var(--cds-text-primary)'>В беге ЦМ ниже всего в середине опоры, выше всего — в полёте</text>
<text data-claude-text-id='subtitle' x='24' y='52' fill='var(--cds-text-secondary)'>Бег 3,5 м/с, средние 28 бегунов. Серые полосы — опора правой и левой стопы</text>
{panels.map((pn, k) => { const py = y0 + k * (ph + gap); const y = v => py + ph - (v - pn.lo) / (pn.hi - pn.lo) * ph; const ticks = Array.from({length: Math.round((pn.hi - pn.lo) / pn.step) + 1}, (_, i) => pn.lo + i * pn.step); const d = rows.map((r, i) => `${i === 0 ? 'M' : 'L'}${x(r.pct)} ${y(val(r, pn.key))}`).join(' '); return <g key={pn.key} data-claude-anchor={`panel-${pn.key}`}>
{phases.filter(f => f.ground === 1).map(f => <rect key={f.a} x={x(f.a)} y={py} width={x(f.b) - x(f.a)} height={ph} fill='var(--cds-chart-reference-tint)'/>)}
<text x={left} y={py - 12} fontWeight='600' fill='var(--cds-text-primary)'>{pn.label}</text>
{ticks.map(v => <g key={v}><line x1={left} x2={right} y1={y(v)} y2={y(v)} stroke={v === 0 ? 'var(--cds-chart-axis)' : 'var(--cds-chart-grid)'}/><text x={left - 8} y={y(v) + 4} textAnchor='end' fill='var(--cds-text-secondary)'>{`${v > 0 ? '+' : ''}${v}`}</text></g>)}
<path d={d} fill='none' stroke='var(--cds-chart-categorical-1)' strokeWidth='2.5'/>
{rows.map(r => <circle key={r.pct} cx={x(r.pct)} cy={y(val(r, pn.key))} r='3.5' fill='var(--cds-chart-categorical-1)' {...datum(r, pn.key)}><title>{`${pn.label.split(',').at(0)}, ${r.pct} % цикла: ${fmt(val(r, pn.key))}${pn.unit}`}</title></circle>)}
</g>; })}
<g data-claude-anchor='com-extremes'>
<text x={x(low1.pct)} y={yc(low1.com) + 18} textAnchor='middle' fill='var(--cds-text-primary)' {...datum(low1, 'com')}>{`низ ${fmt(low1.com)}`}</text>
<text x={x(low2.pct)} y={yc(low2.com) + 18} textAnchor='middle' fill='var(--cds-text-primary)' {...datum(low2, 'com')}>{`низ ${fmt(low2.com)}`}</text>
<text x={x(high1.pct)} y={yc(high1.com) - 10} textAnchor='middle' fill='var(--cds-text-primary)' {...datum(high1, 'com')}>{`верх +${fmt(high1.com)}`}</text>
<text x={x(high2.pct)} y={yc(high2.com) - 10} textAnchor='middle' fill='var(--cds-text-primary)' {...datum(high2, 'com')}>{`верх +${fmt(high2.com)}`}</text>
</g>
<g data-claude-anchor='phases'>{phases.map(f => <text key={f.a} x={x((f.a + f.b) / 2)} y={last + 18} textAnchor='middle' fill='var(--cds-text-secondary)'>{f.name}</text>)}</g>
<g data-claude-anchor='x-axis'>{xt.map(p => <text key={p} x={x(p)} y={last + 40} textAnchor='middle' fill='var(--cds-text-secondary)'>{`${p} %`}</text>)}</g>
<text data-claude-text-id='x-label' x={right} y={last + 62} textAnchor='end' fill='var(--cds-text-secondary)'>доля двойного шага от касания правой стопой</text>
</svg>; }}</claude.Visualize>;
