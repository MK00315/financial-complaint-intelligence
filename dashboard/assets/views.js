import {icon} from './icons.js';
import {e,n,pct,shortProduct,rangeLabel,weekLabel,FIRST,LAST,params,issueMatches} from './utils.js';
import {chartMarkup} from './charts.js';

export const pages = [
  {key:'overview',label:'Overview',icon:'overview'},
  {key:'issues',label:'Issue explorer',icon:'search'},
  {key:'classify',label:'Classify complaint',icon:'tag'},
  {key:'model',label:'Model & Data',icon:'database'},
];

export function route(screen,filters={}) {
  const query=params({product:filters.product,start:filters.start===FIRST?'':filters.start,end:filters.end===LAST?'':filters.end});
  return `#/${screen}${query?`?${query}`:''}`;
}

export function navigation(screen,filters) {
  return pages.map(page=>`<a class="nav-link" id="nav-${page.key}" href="${e(route(page.key,filters))}" ${screen===page.key?'aria-current="page"':''}>${icon(page.icon)}<span>${page.label}</span></a>`).join('');
}

export function kpi(label,value,note,iconName,unit='') {
  return `<article class="panel kpi view-enter"><p class="kpi-label">${e(label)}${icon(iconName)}</p><p class="kpi-value">${e(value)}${unit?`<span class="unit">${e(unit)}</span>`:''}</p><p class="kpi-note">${note}</p></article>`;
}

function filterControls(ctx) {
  const f=ctx.filters;
  return `<div class="toolbar">
    <label class="sr-only" for="product-filter">Filter by product</label>
    <select class="select" id="product-filter" title="${e(f.product || 'All products')}"><option value="">All products</option>${ctx.data.analytics.products.map(row=>`<option value="${e(row.product)}" ${f.product===row.product?'selected':''}>${e(shortProduct(row.product))}</option>`).join('')}</select>
    <details class="date-control" id="date-control"><summary class="button secondary" title="Change the date range">${icon('calendar')}Date range${icon('chevron')}</summary>
      <form class="date-popover" id="date-form"><h3>Choose a date range</h3><p>Available: January 1–February 28, 2025.</p><div class="date-fields">
        <label><span class="field-label">From</span><input class="date-input" type="date" name="start" id="start-date" value="${f.start}" min="${FIRST}" max="${LAST}" required></label>
        <label><span class="field-label">To</span><input class="date-input" type="date" name="end" id="end-date" value="${f.end}" min="${FIRST}" max="${LAST}" required></label></div>
        <p class="inline-error" id="date-error" role="alert" hidden></p><div class="date-actions"><button class="button ghost small" type="button" data-action="reset-dates">Full period</button><button class="button small" type="submit">Apply dates</button></div>
      </form>
    </details>
    ${ctx.screen==='overview'?`<a class="button" href="${e(route('classify',f))}">${icon('plus')}Classify a complaint</a>`:`<a class="button secondary" href="${e(route('overview',f))}">${icon('overview')}Overview</a>`}
  </div>`;
}

export function heading(title,subtitle,badge='Historical snapshot',controls='') {
  return `<header class="page-head"><div><div class="heading-line"><h1 id="page-heading" tabindex="-1">${e(title)}</h1>${badge?`<span class="eyebrow">${e(badge)}</span>`:''}</div><p class="subtitle">${subtitle}</p></div>${controls}</header>`;
}

function filterContext(f) {
  if(!f.product && f.start===FIRST && f.end===LAST)return '';
  return `<div class="filter-context"><span>Showing:</span>${f.product?`<span class="chip">${e(f.product)}</span>`:''}<span class="chip">${rangeLabel(f.start,f.end)}</span><button class="clear-link" data-action="reset-filters">Reset filters</button></div>`;
}

export function dailyPanel(ctx) {
  const mode=ctx.metric || 'complaints';
  return `<section class="panel panel-padding chart-panel span-8" aria-labelledby="volume-heading"><div class="panel-title-row"><h2 id="volume-heading">Daily reporting volume</h2><div class="segmented" role="group" aria-label="Daily chart measure"><button data-action="chart-metric" data-metric="complaints" aria-pressed="${mode==='complaints'}">Complaints</button><button data-action="chart-metric" data-metric="narratives" aria-pressed="${mode==='narratives'}">With narrative</button></div></div>
    ${chartMarkup(ctx.analytics.daily,{id:'daily-volume',metric:mode})}
  </section>`;
}

export function productPanel(ctx) {
  const rows=ctx.analytics.products;
  const top=rows.slice(0,5),other=rows.slice(5);
  const total=ctx.analytics.totals.complaints;
  const otherCount=other.reduce((sum,r)=>sum+r.complaints,0);
  return `<section class="panel panel-padding span-4" aria-labelledby="mix-heading"><div class="panel-title-row"><h2 id="mix-heading">Product mix</h2><span class="legend">Share of selected</span></div><div class="product-list">
    ${top.map((row,i)=>`<button class="product-item" data-action="filter-product" data-product="${e(row.product)}" title="Explore ${e(row.product)}"><span class="product-label"><span class="product-name">${e(shortProduct(row.product))}</span><span class="numeric">${pct(row.share_pct)}</span></span><span class="track"><span style="width:${row.share_pct.toFixed(3)}%;opacity:${1-i*.13}"></span></span><span class="product-count numeric">${n(row.complaints)}</span></button>`).join('')}
    ${other.length?`<div class="product-other"><div class="product-label"><span class="product-name">Other products (${other.length})</span><span class="numeric muted">${pct(otherCount/total*100)}</span></div><div class="track"><span style="width:${otherCount/total*100}%"></span></div><p class="product-count numeric">${n(otherCount)}</p></div>`:''}
    ${!rows.length?'<p class="empty-note">No complaints in this selection.</p>':''}
  </div></section>`;
}

export function signalPanel(ctx,detailed=false) {
  const history=ctx.data.analytics.signal_history || [ctx.data.analytics.signals];
  const latest=history[history.length-1];
  const signal=history.find(row=>row.week_start===ctx.signalWeek) || latest;
  const count=signal.items.length;
  return `<section class="panel signal-panel span-4" id="signal-panel" aria-labelledby="signal-heading"><div class="panel-head"><div><h2 id="signal-heading">Weekly signals</h2><p>${detailed?'Selected complete week':'Latest complete week'}: ${weekLabel(signal.week_start)}</p>
    ${detailed?`<label class="sr-only" for="signal-week">Signal week</label><select class="select select-block" id="signal-week">${[...history].reverse().map(row=>`<option value="${row.week_start}" ${row.week_start===signal.week_start?'selected':''}>${weekLabel(row.week_start)}</option>`).join('')}</select>`:''}
    <p class="scope-note">Archive-wide · independent of date/product filters</p></div></div>
    ${count?`<div>${signal.items.map(row=>`<div class="signal-item"><span class="route-badge review">${icon('alert')}Investigate</span><h3>${e(row.issue)}</h3><p>${e(shortProduct(row.product))} · ${n(row.current)} complaints · ${row.volume_ratio}× baseline</p></div>`).join('')}</div>`:`<div class="signal-empty"><span class="empty-icon">${icon('check')}</span><h3>No issues crossed the signal thresholds</h3><p>Compared against the baseline mean of four preceding complete weeks.</p></div>`}
    ${detailed?`<div class="signal-stats"><div><strong class="numeric">${n(signal.current_week_total)}</strong><span>Selected week · all products</span></div><div><strong class="numeric">${n(signal.baseline_four_week_total/4)}</strong><span>Baseline weekly mean</span></div></div>`:''}
    <div class="signal-foot"><details class="rule-details"><summary>How signals are checked</summary><div class="rule-list"><div><strong>≥ 30 complaints</strong>Current complete week</div><div><strong>≥ 5 complaints</strong>Baseline weekly mean</div><div><strong>≥ 1.5× volume</strong>Relative to baseline</div><div><strong>≥ 0.5 pp</strong>Archive-wide share increase</div></div><p>All four rules must hold. Baseline weeks begin ${signal.baseline_weeks.map(w=>e(w.slice(5).replace('-','/'))).join(', ')}. Partial weeks are excluded.</p></details><p class="scope-note">Exploratory signals, not confirmed anomalies or proof of misconduct. Only seven complete weeks are available.</p></div>
  </section>`;
}

function issueButton(row) {
  return `<button class="table-button" data-action="issue-detail" data-product="${e(row.product)}" data-issue="${e(row.issue)}">${e(row.issue)}</button>`;
}

export function overview(ctx) {
  const t=ctx.analytics.totals,m=ctx.data.model;
  return `<div class="view-enter">${heading('Complaint overview',`${icon('calendar')}Observed: ${rangeLabel(ctx.filters.start,ctx.filters.end)}`,'Historical snapshot',filterControls(ctx))}${filterContext(ctx.filters)}
    <div class="kpi-grid" aria-label="Complaint summary">
      ${kpi('Total complaints',n(t.complaints),'Archived records','files')}
      ${kpi('Narrative coverage',t.narrative_coverage_pct.toFixed(2),`<strong>${n(t.narratives)}</strong> written complaints`,'text','%')}
      ${kpi('Product categories',n(t.products),'Distinct product categories','layers')}
      <article class="panel kpi view-enter"><p class="kpi-label model-label">${icon('cpu')}Model: Logistic Reg.<span class="tag mono">TEST SET</span></p><p class="kpi-value">${(m.test.accuracy*100).toFixed(2)}<span class="unit">%</span></p><p class="kpi-note">Accuracy on <strong>${n(ctx.model.split.splits.test.rows)}</strong> held-out complaints</p></article>
    </div>
    <div class="grid-12">${dailyPanel(ctx)}${productPanel(ctx)}</div>
    <div class="grid-12"><section class="panel span-8" aria-labelledby="issues-heading"><div class="panel-head"><h2 id="issues-heading">Top reported issues</h2></div><div class="table-scroll"><table class="issue-table"><caption class="sr-only">Five leading product and issue combinations in the selected period</caption><thead><tr><th scope="col">Issue</th><th scope="col">Product source</th><th scope="col" class="text-right">Count</th></tr></thead><tbody>${ctx.analytics.issues.slice(0,5).map(row=>`<tr><td class="issue-col">${issueButton(row)}</td><td class="source-col">${e(row.product)}</td><td class="text-right numeric">${n(row.complaints)}</td></tr>`).join('') || '<tr><td colspan="3" class="no-results">No reported issues in this selection.</td></tr>'}</tbody></table></div><div class="table-bottom"><span>${n(t.issues)} product/issue combinations</span><a class="button ghost small" href="${e(route('issues',ctx.filters))}">Explore all issues ${icon('arrow')}</a></div></section>${signalPanel({...ctx,signalWeek:''})}</div>
  </div>`;
}

export function explorerResults(ctx) {
  const rows=issueMatches(ctx.analytics.issues,ctx.issueSearch,ctx.issueSort);
  const pageSize=10, page=Math.max(1,Math.min(ctx.issuePage,Math.ceil(rows.length/pageSize) || 1));
  const from=(page-1)*pageSize;
  const items=rows.slice(from,from+pageSize);
  return `<div class="table-scroll"><table class="explorer-table"><caption class="sr-only">Reported product and issue combinations; share is relative to all complaints in the selected period and products.</caption><thead><tr><th scope="col">Reported issue</th><th scope="col">Product</th><th scope="col" class="text-right">Complaints</th><th scope="col" class="text-right" title="Share of complaints in the selected period/product, before search">Share</th></tr></thead><tbody>
    ${items.map(row=>`<tr><td class="issue-col">${issueButton(row)}</td><td class="source-col" title="${e(row.product)}">${e(shortProduct(row.product))}</td><td class="text-right numeric">${n(row.complaints)}</td><td class="text-right numeric">${pct(row.share_pct)}<div class="mini-bar"><span style="width:${row.share_pct}%"></span></div></td></tr>`).join('') || `<tr><td colspan="4"><div class="no-results">${icon('search')}<h3>No matching issues</h3><p>Try another search or reset the date and product filters.</p><button class="button ghost small" data-action="clear-search">Clear search</button></div></td></tr>`}
    </tbody></table></div><div class="table-bottom"><span id="search-result-count" role="status">${rows.length?`${from+1}–${Math.min(from+pageSize,rows.length)} of ${n(rows.length)} issues`:'0 issues'}${ctx.issueSearch?' matched':''}</span><div class="pagination"><button class="button secondary small icon-only" data-action="issue-page" data-page="${page-1}" aria-label="Previous issue page" ${page===1?'disabled':''}>${icon('left')}</button><span>Page ${page} of ${Math.ceil(rows.length/pageSize) || 1}</span><button class="button secondary small icon-only" data-action="issue-page" data-page="${page+1}" aria-label="Next issue page" ${from+pageSize>=rows.length?'disabled':''}>${icon('right')}</button></div></div>`;
}

export function explorer(ctx) {
  const t=ctx.analytics.totals;
  const largest=ctx.analytics.issues[0];
  return `<div class="view-enter">${heading('Issue explorer',`${icon('calendar')}Observed: ${rangeLabel(ctx.filters.start,ctx.filters.end)}`,'Historical snapshot',filterControls(ctx))}${filterContext(ctx.filters)}
    <div class="kpi-grid">${kpi('Selected complaints',n(t.complaints),'All archived records in this selection','files')}${kpi('Reported issues',n(t.issues),'Distinct product/issue combinations','search')}${kpi('Largest issue share',largest?largest.share_pct.toFixed(1):'0.0',largest?e(shortProduct(largest.product)):'No reported issues','chart','%')}${kpi('Narrative coverage',t.narrative_coverage_pct.toFixed(2),`<strong>${n(t.narratives)}</strong> written complaints`,'text','%')}</div>
    <div class="grid-12 explorer-layout"><section class="panel span-8" aria-labelledby="explorer-heading"><div class="panel-head"><div><h2 id="explorer-heading">Reported issues</h2><p>Select an issue to inspect its daily trend. Shares use the full selected population.</p></div></div>
      <div class="explorer-tools"><label class="search-field">${icon('search')}<span class="sr-only">Search issues or products</span><input class="input" type="search" id="issue-search" placeholder="Search issues or products…" maxlength="300" value="${e(ctx.issueSearch)}"></label><label><span class="sr-only">Sort reported issues</span><select class="select" id="issue-sort" aria-label="Sort reported issues"><option value="count_desc" ${ctx.issueSort==='count_desc'?'selected':''}>Most complaints</option><option value="count_asc" ${ctx.issueSort==='count_asc'?'selected':''}>Fewest complaints</option><option value="issue_asc" ${ctx.issueSort==='issue_asc'?'selected':''}>Issue A–Z</option></select></label><button class="button secondary small" data-action="export-issues">${icon('download')}Export CSV</button></div>
      <div id="issue-results">${explorerResults(ctx)}</div>
    </section>${signalPanel(ctx,true)}</div>
  </div>`;
}

export function issueDialogContent(row,ctx,detail=null,error='') {
  const f=ctx.filters;
  return `<div class="dialog-heading"><div><span class="eyebrow">Reported issue</span><h2 id="issue-dialog-title" style="margin-top:12px">${e(row.issue)}</h2><p>${e(row.product)} · ${rangeLabel(f.start,f.end)}</p></div><button class="button ghost icon-only" data-action="close-dialog" aria-label="Close issue details">${icon('close')}</button></div><div class="dialog-body"><div class="detail-metrics"><div class="detail-metric"><span>Complaints</span><strong>${n(row.complaints)}</strong></div><div class="detail-metric"><span>Share of selection</span><strong>${pct(row.share_pct)}</strong></div><div class="detail-metric"><span>Narrative coverage</span><strong>${pct(row.narrative_coverage_pct)}</strong></div></div>
    ${error?`<p class="inline-error" role="alert">${e(error)}</p><button class="button secondary small" data-action="retry-dialog">Try again</button>`:detail?`${chartMarkup(detail.daily,{id:'issue-daily',title:'Selected issue daily reporting volume'})}<div class="dialog-actions"><p class="small muted">${n(row.narratives)} complaints include a narrative.</p><button class="button secondary small" data-action="export-issue-detail">${icon('download')}Export daily CSV</button></div>`:'<div class="loading-screen" style="min-height:230px" role="status"><span class="spinner"></span>Loading issue trend…</div>'}
    </div><div class="dialog-note">Counts reflect reported complaints. They do not establish company failure rates or proven misconduct. This view uses the selected date range and the issue’s source product.</div>`;
}
