import {e,n,dateLabel} from './utils.js';

function axisNumber(value) {
  if (value >= 1000) return `${Number((value / 1000).toFixed(2))}k`;
  return Number(value.toFixed(1)).toString();
}

export function chartMarkup(rows, {id='daily', metric='complaints', title='Daily reporting volume', caption=true} = {}) {
  const series = rows.map(row => ({date:row.date, value:row[metric] || 0}));
  const maximum = Math.max(1,...series.map(row => row.value));
  const step = Math.pow(10,Math.floor(Math.log10(maximum))) / 2;
  const top = Math.ceil(maximum / step) * step;
  const denominator = Math.max(1,series.length-1);
  const points = series.map((row,i) => `${(i/denominator*1000).toFixed(3)},${(200-row.value/top*200).toFixed(3)}`);
  const line = series.length === 1 ? `M0,${200-series[0].value/top*200} L1000,${200-series[0].value/top*200}` : `M${points.join(' L')}`;
  const area = `${line} L1000,200 L0,200 Z`;
  const indices = series.length === 59 ? [0,14,30,44,58] : [...new Set(Array.from({length:Math.min(5,series.length)},(_,i) => Math.round(i*(series.length-1)/(Math.min(5,series.length)-1 || 1))))];
  const label = metric === 'narratives' ? 'With a narrative' : 'Complaints';
  const total = series.reduce((sum,row) => sum + row.value,0);
  const description = `${series.length} daily observations. ${n(total)} ${label.toLowerCase()} in the selected period. Use left and right arrow keys to inspect a day.`;
  return `<div class="chart-frame" tabindex="0" role="group" aria-label="${e(title)}" aria-describedby="${id}-desc" data-chart="${e(JSON.stringify({series,top,label}))}">
    <span class="sr-only" id="${id}-desc">${e(description)}</span>
    <div class="chart-y" aria-hidden="true">${[0,1,2,3,4].map(i=>`<span style="top:${i*25}%">${axisNumber(top*(1-i/4))}</span>`).join('')}</div>
    <svg class="chart-svg" viewBox="0 0 1000 200" preserveAspectRatio="none" role="img" aria-labelledby="${id}-title ${id}-desc" data-series-count="${series.length}">
      <title id="${id}-title">${e(title)}</title>
      ${[0,50,100,150,200].map(y=>`<line class="chart-grid" x1="0" y1="${y}" x2="1000" y2="${y}"/>`).join('')}
      <path class="chart-area" d="${area}"/><path class="chart-line" d="${line}"/>
      <g class="chart-hover" hidden><line class="chart-marker" x1="0" y1="0" x2="0" y2="200"/><circle class="chart-point" cx="0" cy="0" r="3.5"/></g>
    </svg>
    <div class="chart-x" aria-hidden="true">${indices.map(i=>`<span style="left:${series.length===1?50:i/denominator*100}%">${dateLabel(series[i].date)}</span>`).join('')}</div>
    <div class="chart-tooltip" hidden><span></span><strong class="numeric"></strong><small></small></div>
    <span class="sr-only chart-live" aria-live="polite"></span>
  </div>${caption?'<p class="chart-caption">Hover or focus the chart to inspect a day. Arrow keys move between dates.</p>':''}`;
}

export function bindCharts(root) {
  root.querySelectorAll('[data-chart]').forEach(frame => {
    const {series,top,label} = JSON.parse(frame.dataset.chart);
    const svg = frame.querySelector('svg');
    const marker = frame.querySelector('.chart-hover');
    const line = marker.querySelector('line');
    const point = marker.querySelector('circle');
    const tooltip = frame.querySelector('.chart-tooltip');
    const live = frame.querySelector('.chart-live');
    let index = 0;
    function show(i, announce=false) {
      index = Math.max(0,Math.min(series.length-1,i));
      const row = series[index];
      const x = series.length===1 ? 500 : index/(series.length-1)*1000;
      const y = 200-row.value/top*200;
      line.setAttribute('x1',x); line.setAttribute('x2',x);
      point.setAttribute('cx',x); point.setAttribute('cy',y);
      marker.removeAttribute('hidden');
      tooltip.hidden=false;
      tooltip.querySelector('span').textContent=dateLabel(row.date,true);
      tooltip.querySelector('strong').textContent=n(row.value);
      tooltip.querySelector('small').textContent=label;
      const plot=svg.getBoundingClientRect();
      const width=tooltip.offsetWidth || 136;
      tooltip.style.left=`${Math.max(33,Math.min(frame.clientWidth-width-3,32+x/1000*plot.width-width/2))}px`;
      if(announce) live.textContent=`${dateLabel(row.date,true)}: ${n(row.value)} ${label.toLowerCase()}.`;
    }
    function hide() { marker.setAttribute('hidden',''); tooltip.hidden=true; }
    svg.addEventListener('pointermove',event=>{
      const bounds=svg.getBoundingClientRect();
      show(Math.round((event.clientX-bounds.left)/bounds.width*(series.length-1)));
    });
    svg.addEventListener('pointerleave',()=>{if(document.activeElement!==frame)hide();});
    frame.addEventListener('focus',()=>show(index,true));
    frame.addEventListener('blur',hide);
    frame.addEventListener('keydown',event=>{
      if(['ArrowRight','ArrowLeft','Home','End'].includes(event.key)) {
        event.preventDefault();
        show(event.key==='Home'?0:event.key==='End'?series.length-1:index+(event.key==='ArrowRight'?1:-1),true);
      } else if(event.key==='Escape')hide();
    });
  });
}
