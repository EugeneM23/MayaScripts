export default () => <claude.Visualize data-claude-component='run-joint-angles' sources={{rows:{kind:'data', data:__JOINTS__}, panels:{kind:'data', data:[{joint:'hip', label:'Бедро: сгибание +, разгибание −', lo:-20, hi:60, step:20},{joint:'knee', label:'Колено: сгибание', lo:0, hi:120, step:40},{joint:'ankle', label:'Голеностоп: тыльное сгибание +, подошвенное −', lo:-30, hi:30, step:15}]}, speeds:{kind:'data', data:[{speed:'2,5', toe:38.5, op:0.35},{speed:'3,5', toe:33.8, op:0.65},{speed:'4,5', toe:32.6, op:1}]}}}>{({rows, panels, speeds, datum}) => {
const left = 72, right = 664, ph = 128, gap = 54, y0 = 112;
const x = p => left + p / 100 * (right - left);
const band = speeds.find(s => s.speed === '3,5');
const xt = Array.from({length: 11}, (_, i) => i * 10);
const last = y0 + 3 * ph + 2 * gap;
return <svg viewBox='0 0 760 670' role='img' aria-label='Чем быстрее бег, тем сильнее колено сгибается в переносе' fontSize='12'>
<text data-claude-text-id='title' x='24' y='30' fontSize='16' fontWeight='600' fill='var(--cds-text-primary)'>Чем быстрее бег, тем сильнее колено сгибается в переносе</text>
<text data-claude-text-id='subtitle' x='24' y='52' fill='var(--cds-text-secondary)'>Средние кривые 28 бегунов, правая нога; 0 % — касание. Серая полоса — опора на 3,5 м/с</text>
<g data-claude-anchor='legend'>{speeds.map((s, k) => <g key={s.speed}><line x1={left + k * 112} x2={left + k * 112 + 26} y1='78' y2='78' stroke='var(--cds-chart-categorical-1)' strokeOpacity={s.op} strokeWidth='2.5'/><text x={left + k * 112 + 32} y='82' fill='var(--cds-text-secondary)'>{`${s.speed} м/с`}</text></g>)}</g>
{panels.map((pn, k) => { const py = y0 + k * (ph + gap); const y = v => py + ph - (v - pn.lo) / (pn.hi - pn.lo) * ph; const ticks = Array.from({length: Math.round((pn.hi - pn.lo) / pn.step) + 1}, (_, i) => pn.lo + i * pn.step); return <g key={pn.joint} data-claude-anchor={`panel-${pn.joint}`}>
<rect x={x(0)} y={py} width={x(band.toe) - x(0)} height={ph} fill='var(--cds-chart-reference-tint)'/>
<text x={left} y={py - 12} fontWeight='600' fill='var(--cds-text-primary)'>{pn.label}</text>
{ticks.map(v => <g key={v}><line x1={left} x2={right} y1={y(v)} y2={y(v)} stroke={v === 0 ? 'var(--cds-chart-axis)' : 'var(--cds-chart-grid)'}/><text x={left - 8} y={y(v) + 4} textAnchor='end' fill='var(--cds-text-secondary)'>{`${v}°`}</text></g>)}
{speeds.map(s => { const pts = rows.filter(r => r.joint === pn.joint && r.speed === s.speed); const d = pts.map((r, i) => `${i === 0 ? 'M' : 'L'}${x(r.pct)} ${y(r.deg)}`).join(' '); return <g key={s.speed} data-claude-anchor={`${pn.joint}-${s.speed.replace(',', '')}`}><path d={d} fill='none' stroke='var(--cds-chart-categorical-1)' strokeOpacity={s.op} strokeWidth='2.5'/>{pts.map(r => <circle key={r.pct} cx={x(r.pct)} cy={y(r.deg)} r='3.5' fill='var(--cds-chart-categorical-1)' fillOpacity={s.op} {...datum(r, 'deg')}><title>{`${pn.label.split(':').at(0)}, ${s.speed} м/с, ${r.pct} % цикла: ${String(r.deg).replace('.', ',')}°`}</title></circle>)}</g>; })}
{pn.joint === 'knee' ? <g data-claude-anchor='knee-peaks'><text x={right + 14} y={py + 10} fill='var(--cds-text-secondary)'>пик</text><text x={right + 14} y={py + 24} fill='var(--cds-text-secondary)'>в переносе</text>{speeds.map((s, j) => { const pk = rows.filter(r => r.joint === 'knee' && r.speed === s.speed).reduce((a, r) => r.deg > a.deg ? r : a); return <text key={s.speed} x={right + 14} y={py + 50 + (2 - j) * 20} fontSize='14' fontWeight='600' fill='var(--cds-chart-categorical-1)' fillOpacity={Math.max(s.op, 0.55)} {...datum(pk, 'deg')}>{`${Math.round(pk.deg)}°`}</text>; })}</g> : null}
</g>; })}
<text x={x(band.toe / 2)} y={y0 + 16} textAnchor='middle' fill='var(--cds-text-secondary)'>опора</text>
<text x={x((band.toe + 100) / 2)} y={y0 + 16} textAnchor='middle' fill='var(--cds-text-secondary)'>перенос</text>
<g data-claude-anchor='x-axis'>{xt.map(p => <text key={p} x={x(p)} y={last + 18} textAnchor='middle' fill='var(--cds-text-secondary)'>{`${p} %`}</text>)}</g>
<text data-claude-text-id='x-label' x={right} y={last + 40} textAnchor='end' fill='var(--cds-text-secondary)'>доля двойного шага от касания правой стопой</text>
</svg>; }}</claude.Visualize>;
