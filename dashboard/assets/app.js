import {icon} from './icons.js';
import {e,n,FIRST,LAST,params,getJSON} from './utils.js';
import {pages,route,navigation,overview,explorer,explorerResults,dailyPanel,signalPanel,issueDialogContent} from './views.js';
import {examples,classifyView,classificationResult} from './views-classify.js';
import {modelView,performanceRows,confusionMatrix,matrixDetail} from './views-model.js';
import {bindCharts} from './charts.js';

const main=document.getElementById('main-content');
const nav=document.getElementById('navigation');
const dialog=document.getElementById('issue-dialog');
const state={data:null,model:null,analytics:null,screen:'overview',filters:{product:'',start:FIRST,end:LAST},metric:'complaints',issueSearch:'',issueSort:'count_desc',issuePage:1,signalWeek:'',narrative:'',exampleLabel:'',prediction:null,classifying:false,classificationError:'',matrixMode:'percent',matrixSelection:null,performanceSort:'name'};
let analyticsController,classificationController,dialogController;
let routeGeneration=0,classificationGeneration=0,toastTimer,pendingFocus='',activeDialog=null;

function readRoute() {
  const [path,query='']=location.hash.replace(/^#\/?/,'').split('?');
  const screen=pages.some(page=>page.key===path)?path:'overview';
  const values=new URLSearchParams(query);
  const start=values.get('start') || FIRST,end=values.get('end') || LAST;
  return {screen,filters:{product:values.get('product') || '',start,end}};
}

function toast(message) {
  const target=document.getElementById('toast');
  clearTimeout(toastTimer); target.textContent=message; target.hidden=false;
  toastTimer=setTimeout(()=>{target.hidden=true;},4500);
}

function friendlyError(error) {
  return error instanceof TypeError?'Could not connect to the workspace. Wait a moment, check your connection and try again.':error.message;
}

function errorPage(error,selection=false) {
  main.innerHTML=`<section class="error-box" role="alert">${icon('alert')}<h1 style="font-size:24px;margin:12px 0">${selection?'This selection could not be loaded':'The workspace could not be opened'}</h1><p>${e(friendlyError(error))}</p><button class="button" data-action="${selection?'reset-filters':'retry-bootstrap'}">${icon('refresh')}${selection?'Reset filters':'Try again'}</button></section>`;
}

function render({focus=false}={}) {
  nav.innerHTML=navigation(state.screen,state.filters);
  const view={overview,issues:explorer,classify:classifyView,model:modelView}[state.screen];
  main.innerHTML=view(state);
  main.removeAttribute('aria-busy');
  document.title=`${pages.find(page=>page.key===state.screen).label} · Financial Complaint Intelligence`;
  bindCharts(main);
  if(pendingFocus){main.querySelector(pendingFocus)?.focus({preventScroll:true});pendingFocus='';}
  else if(focus){main.querySelector('#page-heading')?.focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});}
}

async function bootstrap() {
  const initial=readRoute();
  Object.assign(state,initial);
  nav.innerHTML=navigation(state.screen,state.filters);
  main.innerHTML='<div class="loading-screen" role="status"><span class="spinner"></span>Opening the analyst workspace…</div>';
  try {
    const [data,model]=await Promise.all([getJSON('/api/summary'),getJSON('/api/model')]);
    state.data=data;state.model=model;
    await syncRoute(false);
  } catch(error){errorPage(error);}
}

async function syncRoute(focus=true) {
  if(!state.data)return;
  const next=readRoute(),changed=next.screen!==state.screen;
  state.screen=next.screen;state.filters=next.filters;
  const generation=++routeGeneration;
  if(dialog.open)dialog.close();
  analyticsController?.abort();
  nav.innerHTML=navigation(state.screen,state.filters);
  const scope=state.analytics?.scope;
  const mustLoad=['overview','issues'].includes(state.screen) && (!scope || ['product','start','end'].some(key=>scope[key]!==state.filters[key]));
  if(mustLoad) {
    analyticsController=new AbortController();
    main.setAttribute('aria-busy','true');
    main.firstElementChild?.classList.add('loading-overlay');
    try {
      const analytics=await getJSON(`/api/analytics?${params(state.filters)}`,{signal:analyticsController.signal});
      if(generation!==routeGeneration)return;
      state.analytics=analytics;state.issuePage=1;
    } catch(error){
      if(error.name==='AbortError' || generation!==routeGeneration)return;
      main.removeAttribute('aria-busy');errorPage(error,true);return;
    }
  }
  if(generation===routeGeneration)render({focus:focus&&changed});
}

function setFilters(update) {
  const filters={...state.filters,...update};
  const target=route(state.screen,filters);
  if(location.hash===target){syncRoute(false);return;}
  location.hash=target;
}

function updateIssueResults() {
  const target=document.getElementById('issue-results');
  if(target)target.innerHTML=explorerResults(state);
}

function updateClassification() {
  if(state.screen!=='classify')return;
  const result=document.getElementById('classification-result');
  if(result)result.innerHTML=classificationResult(state);
  const button=document.getElementById('classify-submit');
  if(button){button.disabled=state.classifying || !state.narrative.trim();button.innerHTML=`${state.classifying?'<span class="spinner"></span>':icon('tag')}${state.classifying?'Analyzing…':'Classify complaint'}`;}
  const error=document.getElementById('narrative-error');
  if(error){error.hidden=!state.classificationError;error.textContent=state.classificationError;}
  document.getElementById('complaint-text')?.setAttribute('aria-invalid',String(!!state.classificationError));
  const clear=document.querySelector('[data-action="clear-narrative"]');if(clear)clear.disabled=!state.narrative;
}

function narrativeChanged(text,exampleLabel='') {
  classificationGeneration++;
  classificationController?.abort();
  Object.assign(state,{narrative:text,exampleLabel,prediction:null,classifying:false,classificationError:''});
  const count=document.getElementById('character-count');if(count)count.textContent=`${n(text.length)} / 12,000`;
  const hint=document.getElementById('narrative-hint');if(hint)hint.textContent=exampleLabel?`Illustrative example · ${exampleLabel}`:'Remove names, account numbers and other personal details.';
  updateClassification();
}

async function classifyComplaint() {
  const text=state.narrative.trim();
  if(text.length<30 || text.split(/\s+/).length<12) {
    state.classificationError='Enter a financial complaint with at least 12 meaningful words. Remove personal details first.';
    updateClassification();document.getElementById('complaint-text')?.focus();return;
  }
  classificationController?.abort();classificationController=new AbortController();
  const generation=++classificationGeneration;
  state.classifying=true;state.prediction=null;state.classificationError='';updateClassification();
  try {
    const prediction=await getJSON('/api/classify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text}),signal:classificationController.signal});
    if(generation!==classificationGeneration)return;
    state.prediction=prediction;
  } catch(error){
    if(error.name==='AbortError' || generation!==classificationGeneration)return;
    state.classificationError=friendlyError(error);
  } finally {
    if(generation===classificationGeneration){
      state.classifying=false;updateClassification();
      if(state.screen==='classify' && document.activeElement===document.body)document.getElementById('classify-submit')?.focus({preventScroll:true});
      const announce=document.getElementById('classification-announcement');
      if(announce && state.prediction)announce.textContent=`Suggested product: ${state.prediction.category}. Model score ${state.prediction.score.toFixed(3)}. ${state.prediction.human_review?'Human review recommended.':'Review the suggestion before routing.'}`;
    }
  }
}

async function exportCSV(kind,extra={}) {
  const url=`/api/export?${params({...state.filters,kind,...extra})}`;
  try {
    const response=await fetch(url);
    if(!response.ok){const value=await response.json();throw new Error(value.detail || 'The export could not be prepared.');}
    const blob=await response.blob();
    const filename=(response.headers.get('content-disposition') || '').match(/filename="([^"]+)"/)?.[1] || 'Financial_Complaints.csv';
    const blobURL=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=blobURL;link.download=filename;document.body.appendChild(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(blobURL),2000);
    toast('CSV export prepared for your current selection.');
  } catch(error){toast(friendlyError(error));}
}

async function openIssue(product,issue) {
  const row=state.analytics.issues.find(item=>item.product===product && item.issue===issue);
  if(!row)return;
  dialogController?.abort();dialogController=new AbortController();
  const snapshot={filters:{...state.filters}},controller=dialogController;
  activeDialog={row,snapshot};
  dialog.innerHTML=issueDialogContent(row,snapshot);
  if(!dialog.open)dialog.showModal();
  try {
    const detail=await getJSON(`/api/analytics?${params({...snapshot.filters,product,issue})}`,{signal:controller.signal});
    if(controller.signal.aborted || !dialog.open)return;
    dialog.innerHTML=issueDialogContent(row,snapshot,detail);bindCharts(dialog);
    dialog.querySelector('[data-action="close-dialog"]')?.focus({preventScroll:true});
  } catch(error){
    if(error.name==='AbortError' || !dialog.open)return;
    dialog.innerHTML=issueDialogContent(row,snapshot,null,friendlyError(error));
  }
}

document.addEventListener('click',event=>{
  const skip=event.target.closest('.skip-link');
  if(skip){event.preventDefault();main.focus();return;}
  const dateControl=document.getElementById('date-control');
  if(dateControl?.open && !dateControl.contains(event.target))dateControl.open=false;
  const target=event.target.closest('[data-action]');
  if(!target || target.disabled)return;
  event.preventDefault();
  const action=target.dataset.action;
  if(action==='retry-bootstrap')bootstrap();
  if(action==='reset-filters'){state.issueSearch='';state.issuePage=1;setFilters({product:'',start:FIRST,end:LAST});}
  if(action==='reset-dates'){pendingFocus='#date-control summary';setFilters({start:FIRST,end:LAST});}
  if(action==='filter-product'){pendingFocus='#product-filter';setFilters({product:target.dataset.product});}
  if(action==='chart-metric'){
    state.metric=target.dataset.metric;
    const panel=document.querySelector('.chart-panel');panel.outerHTML=dailyPanel(state);
    const replacement=document.querySelector('.chart-panel');bindCharts(replacement);
    replacement.querySelector(`[data-metric="${state.metric}"]`)?.focus({preventScroll:true});
  }
  if(action==='clear-search'){state.issueSearch='';state.issuePage=1;document.getElementById('issue-search').value='';updateIssueResults();document.getElementById('issue-search').focus();}
  if(action==='issue-page'){state.issuePage=Math.max(1,Number(target.dataset.page));updateIssueResults();document.getElementById('issue-results')?.scrollIntoView({block:'nearest'});document.querySelector('[data-action="issue-page"]:not(:disabled)')?.focus({preventScroll:true});}
  if(action==='export-issues')exportCSV('issues',{q:state.issueSearch,sort:state.issueSort});
  if(action==='issue-detail')openIssue(target.dataset.product,target.dataset.issue);
  if(action==='close-dialog')dialog.close();
  if(action==='retry-dialog' && activeDialog)openIssue(activeDialog.row.product,activeDialog.row.issue);
  if(action==='export-issue-detail' && activeDialog)exportCSV('daily',{...activeDialog.snapshot.filters,product:activeDialog.row.product,issue:activeDialog.row.issue});
  if(action==='load-example'){
    const example=examples.find(item=>item.key===target.dataset.example);if(!example)return;
    const textarea=document.getElementById('complaint-text');textarea.value=example.text;narrativeChanged(example.text,example.label);textarea.focus();textarea.setSelectionRange(0,0);
  }
  if(action==='clear-narrative'){
    const textarea=document.getElementById('complaint-text');textarea.value='';narrativeChanged('');textarea.focus();
  }
  if(action==='matrix-mode'){
    state.matrixMode=target.dataset.mode;
    document.getElementById('matrix-table').innerHTML=confusionMatrix(state);
    document.querySelectorAll('[data-action="matrix-mode"]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.mode===state.matrixMode)));
  }
  if(action==='matrix-cell'){
    state.matrixSelection={r:Number(target.dataset.row),c:Number(target.dataset.col)};
    document.querySelectorAll('[data-action="matrix-cell"]').forEach(cell=>cell.setAttribute('aria-pressed',String(cell===target)));
    document.getElementById('matrix-detail').innerHTML=matrixDetail(state);
  }
});

document.addEventListener('input',event=>{
  if(event.target.id==='issue-search'){state.issueSearch=event.target.value;state.issuePage=1;updateIssueResults();}
  if(event.target.id==='complaint-text')narrativeChanged(event.target.value);
});

document.addEventListener('change',event=>{
  if(event.target.id==='product-filter'){pendingFocus='#product-filter';setFilters({product:event.target.value});}
  if(event.target.id==='issue-sort'){state.issueSort=event.target.value;state.issuePage=1;updateIssueResults();}
  if(event.target.id==='signal-week'){
    state.signalWeek=event.target.value;document.getElementById('signal-panel').outerHTML=signalPanel(state,true);document.getElementById('signal-week').focus({preventScroll:true});
  }
  if(event.target.id==='performance-sort'){state.performanceSort=event.target.value;document.getElementById('performance-body').innerHTML=performanceRows(state);}
});

document.addEventListener('submit',event=>{
  if(event.target.id==='classify-form'){event.preventDefault();classifyComplaint();}
  if(event.target.id==='date-form'){
    event.preventDefault();
    const values=new FormData(event.target),start=values.get('start'),end=values.get('end');
    if(start>end || start<FIRST || end>LAST){const error=document.getElementById('date-error');error.textContent='Choose an ordered range between January 1 and February 28, 2025.';error.hidden=false;return;}
    pendingFocus='#date-control summary';setFilters({start,end});
  }
});

dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});
dialog.addEventListener('close',()=>{dialogController?.abort();activeDialog=null;});
document.addEventListener('keydown',event=>{if(event.key==='Escape'){const control=document.getElementById('date-control');if(control?.open){control.open=false;control.querySelector('summary').focus();}}});
window.addEventListener('hashchange',()=>syncRoute(true));
if(!location.hash)history.replaceState(null,'',route('overview',state.filters));
bootstrap();
