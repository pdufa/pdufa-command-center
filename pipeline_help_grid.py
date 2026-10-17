"""Fast, paginated PIPELINE trial table with visible CSS-circled help icons.

Unlike Streamlit's canvas-based dataframe headers, these are real DOM buttons.
Rows remain fully sortable and clickable without sending selection state to server.
"""
import html
import json
import re
import pandas as pd
import streamlit.components.v1 as components

from pdufa_table_headers import column_help


_PAGE = 75
_LONG = ("note", "description", "summary", "narrative", "rationale",
         "explanation", "source", "url", "link", "factors", "gaps", "next action")


def _string(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def pipeline_grid_html(frame, *, height=550):
    """Render all filtered rows with client-side sorting and page-sized DOM work."""
    columns = [str(c) for c in frame.columns]
    # Keep the full set for sort/export. DOM draws only _PAGE rows at a time.
    rows = [[_string(value) for value in item] for item in frame.itertuples(index=False, name=None)]
    payload = json.dumps(
        {"columns": columns, "rows": rows, "help": [column_help(c) for c in columns],
         "sortable": [not any(term in c.casefold() for term in _LONG) for c in columns],
         "page_size": _PAGE},
        ensure_ascii=False, separators=(",", ":"),
    ).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    css = """
<style>
html,body{margin:0;background:#fff;color:#171717;font:14px/1.4 Arial,sans-serif}
*{box-sizing:border-box}
.pipeline-grid-shell{background:#fff;border:2px solid #161616;border-radius:10px;overflow:hidden}
.pipeline-grid-toolbar{display:flex;flex-wrap:wrap;gap:9px;align-items:center;
  padding:8px 12px;background:#f6faf7;border-bottom:1px solid #888;font-weight:700}
.pipeline-grid-toolbar button,.pipeline-detail-close{cursor:pointer;background:#fff;
  border:1px solid #555;border-radius:5px;padding:5px 9px;color:#111;font-weight:700}
.pipeline-grid-toolbar button:disabled{opacity:.4;cursor:default}
.pipeline-grid-scroll{overflow:auto;height:__GRIDHEIGHT__px;background:#fff}
.pipeline-help-table{border-collapse:separate;border-spacing:0;table-layout:auto;
  width:max-content;min-width:100%;background:#fff}
.pipeline-help-table th{position:sticky;top:0;z-index:4;background:#f1f5f1;
  border-right:1px solid #777;border-bottom:2px solid #111;padding:9px 10px;
  white-space:nowrap;color:#111;text-align:left}
.pipeline-help-table td{padding:7px 10px;border-bottom:1px solid #ddd;border-right:1px solid #e4e4e4;
  white-space:nowrap;color:#111;max-width:450px;overflow:hidden;text-overflow:ellipsis}
.pipeline-help-table td[data-long="1"]{max-width:300px}
.pipeline-help-table tr[data-row]:hover td{background:#edf8ed;cursor:pointer}
.pipeline-help-table tr[data-selected="1"] td{background:#d6eddf!important}
.pipeline-header-controls{display:inline-flex;gap:9px;align-items:center;
  justify-content:space-between;min-width:max-content;white-space:nowrap}
.pipeline-column-name{font-size:13px;font-weight:800;flex:0 0 auto}
.pipeline-header-actions{display:inline-flex;align-items:center;gap:7px;flex:0 0 auto}
.pipeline-sort-button{min-width:27px;height:25px;display:inline-flex;align-items:center;
  justify-content:center;padding:1px 5px;background:#fff;color:#111;border:1.5px solid #111;
  border-radius:4px;cursor:pointer;font-size:15px;font-weight:900}
.pipeline-sort-button:hover,.pipeline-sort-button:focus{background:#d2e5d3}
.pipeline-question{display:inline-flex!important;align-items:center;justify-content:center;
  flex:0 0 21px;width:21px;height:21px;min-width:21px;
  background:#fff!important;color:#111!important;border:2px solid #222!important;
  border-radius:50%!important;font:900 13px/1 Arial,sans-serif!important;
  cursor:pointer;padding:0!important}
.pipeline-question:hover,.pipeline-question:focus{background:#111!important;color:#fff!important;
  outline:2px solid #15703a;outline-offset:1px}
.pipeline-help-popup{position:fixed;right:12px;top:45px;max-width:min(450px,93vw);z-index:10000;
  border:2px solid #111;border-radius:9px;padding:13px 14px 14px;background:#fff;
  box-shadow:0 6px 24px #0004;color:#111;white-space:normal}
.pipeline-help-popup[hidden],.pipeline-selected-details[hidden]{display:none}
.pipeline-help-popup button{float:right;border:1px solid #777;background:white;cursor:pointer;
  padding:1px 7px;border-radius:4px;font-size:16px}
.pipeline-selected-details{border-bottom:2px solid #111;background:#f6fbf5;
  max-height:180px;overflow:auto;padding:8px 12px}
.pipeline-detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:5px 16px;font-size:12px}
.pipeline-detail-grid>div{min-width:0;overflow-wrap:anywhere}
.pipeline-selected-details a,.pipeline-help-table a{color:#0857bc!important}
.pipeline-grid-status{font-size:12px;font-weight:600}
.pipeline-help-table tbody tr:focus{outline:2px solid #00834a;outline-offset:-2px}
@media(max-width:640px){.pipeline-grid-toolbar{gap:5px;padding:7px}
  .pipeline-help-table th{padding:7px}.pipeline-help-table td{padding:6px}
  .pipeline-header-actions{gap:5px}}
</style>
""".replace("__GRIDHEIGHT__", str(max(250,int(height)-105)))
    markup = """
<div class="pipeline-grid-shell">
 <div class="pipeline-grid-toolbar" aria-label="Trial list pagination">
  <strong>TRIAL RESULTS</strong>
  <button type="button" id="pipeline-prev">◀ Previous</button>
  <span class="pipeline-grid-status" id="pipeline-page-info"></span>
  <button type="button" id="pipeline-next">Next ▶</button>
  <span style="margin-left:auto;font-size:12px">▾ Sort · ? Field explanation · Click row for details</span>
 </div>
 <section class="pipeline-selected-details" id="pipeline-detail" hidden
   aria-label="Selected trial information"><button type="button" class="pipeline-detail-close"
   id="pipeline-detail-close" style="float:right">Close ×</button>
   <strong id="pipeline-detail-title">SELECTED PROGRAM</strong>
   <div class="pipeline-detail-grid" id="pipeline-detail-grid"></div>
 </section>
 <div class="pipeline-grid-scroll">
  <table class="pipeline-help-table" aria-label="Sortable Pipeline trial programs">
   <thead id="pipeline-head"></thead><tbody id="pipeline-body"></tbody>
  </table>
 </div>
</div>
<div class="pipeline-help-popup" id="pipeline-help-popup" hidden role="dialog"
   aria-label="Column explanation">
 <button id="pipeline-help-close" type="button" aria-label="Close explanation">×</button>
 <strong id="pipeline-help-title"></strong><p id="pipeline-help-copy"></p>
</div>
"""
    script = r"""
<script>
(() => {
const dataset = __DATA__;
const cols=dataset.columns, rows=dataset.rows, helps=dataset.help,
      sortable=dataset.sortable, pageSize=dataset.page_size;
const head=document.getElementById('pipeline-head'), body=document.getElementById('pipeline-body');
const info=document.getElementById('pipeline-page-info');
const previous=document.getElementById('pipeline-prev'), next=document.getElementById('pipeline-next');
const detail=document.getElementById('pipeline-detail');
const detailGrid=document.getElementById('pipeline-detail-grid');
const popup=document.getElementById('pipeline-help-popup');
const order=rows.map((_,i)=>i);
let page=0, active=-1, ascending=true, selected=-1;
function numeric(value){
  const cleaned=value.replace(/[$,%\s,]/g,'');
  return /^[-+]?(?:\d*\.)?\d+$/.test(cleaned) ? Number(cleaned) : null;
}
function compare(a,b,index){
  const av=rows[a][index].trim(), bv=rows[b][index].trim();
  if(!av||!bv) return av===bv ? a-b : !av ? 1 : -1;
  const an=numeric(av), bn=numeric(bv);
  let v=(an!==null && bn!==null) ? an-bn :
    av.localeCompare(bv,undefined,{numeric:true,sensitivity:'base'});
  return (ascending?v:-v)||(a-b);
}
function paint(){
  body.replaceChildren();
  const offset=page*pageSize;
  const fragment=document.createDocumentFragment();
  order.slice(offset,offset+pageSize).forEach(i=>{
    const tr=document.createElement('tr');
    tr.tabIndex=0; tr.dataset.row=String(i);
    if(i===selected) tr.dataset.selected='1';
    cols.forEach((col,j)=>{
      const td=document.createElement('td'), value=rows[i][j];
      if(!sortable[j]){td.dataset.long='1';td.title=value;}
      const source=col.toLowerCase().includes('source') && /^https?:\/\//i.test(value);
      if(source){
        const a=document.createElement('a');a.href=value;a.textContent='Open source ↗';
        a.target='_blank';a.rel='noopener noreferrer';
        a.addEventListener('click',e=>e.stopPropagation());td.appendChild(a);
      } else {td.textContent=value;}
      if(col==='Days to PDUFA'){
        const n=numeric(value);
        if(n!==null && n>=0){td.style.background=n<=29?'#f87171':n<=59?'#fdba74':n<=90?'#86efac':'#4ade80';}
        else if(n!==null && n<0)td.style.background='#e5e7eb';
      }
      if(col==='F'){
        td.style.background=value.includes('CLOSED')?'#fecaca':value.includes('RUN')?'#fde68a':
          value.includes('START')?'#bbf7d0':'#eee';
      }
      tr.appendChild(td);
    });
    tr.addEventListener('click',()=>selectRow(i));
    tr.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();selectRow(i);}});
    fragment.appendChild(tr);
  });
  body.appendChild(fragment);
  info.textContent = rows.length ?
    (offset+1).toLocaleString()+'–'+Math.min(offset+pageSize,rows.length).toLocaleString()
      +' of '+rows.length.toLocaleString() : '0 matching records';
  previous.disabled=page===0;next.disabled=offset+pageSize>=rows.length;
}
function selectRow(i){
  selected=i;detail.hidden=false;
  document.getElementById('pipeline-detail-title').textContent='SELECTED PROGRAM: '+
    (rows[i][cols.indexOf('Ticker')]||rows[i][cols.indexOf('Drug')]||'TRIAL');
  detailGrid.replaceChildren();
  cols.forEach((col,j)=>{
    const value=rows[i][j];if(!value) return;
    const item=document.createElement('div');
    const key=document.createElement('strong');key.textContent=col+': ';item.appendChild(key);
    if(/^https?:\/\//i.test(value)){
      const a=document.createElement('a');a.href=value;a.textContent='Open source ↗';
      a.target='_blank';a.rel='noopener noreferrer';item.appendChild(a);
    }else{item.appendChild(document.createTextNode(value));}
    detailGrid.appendChild(item);
  });
  const nct=cols.indexOf('NCT ID');
  if(nct>=0 && /^NCT\d{8}$/i.test(rows[i][nct])){
    const item=document.createElement('div'),a=document.createElement('a');
    a.href='https://clinicaltrials.gov/study/'+rows[i][nct].toUpperCase();
    a.target='_blank';a.rel='noopener noreferrer';a.textContent='View exact ClinicalTrials.gov trial ↗';
    item.appendChild(a);detailGrid.appendChild(item);
  }
  paint();
}
cols.forEach((col,i)=>{
  const th=document.createElement('th');
  const controls=document.createElement('span');controls.className='pipeline-header-controls';
  const name=document.createElement('span');name.className='pipeline-column-name';name.textContent=col;
  const actions=document.createElement('span');actions.className='pipeline-header-actions';
  controls.appendChild(name);
  if(sortable[i]){
    const btn=document.createElement('button');btn.type='button';btn.className='pipeline-sort-button';
    btn.textContent='▾';btn.title='Sort '+col+' ascending/descending';
    btn.setAttribute('aria-label','Sort '+col);btn.dataset.col=String(i);
    btn.addEventListener('click',()=>{
      ascending=active===i?!ascending:true;active=i;order.sort((a,b)=>compare(a,b,i));page=0;
      head.querySelectorAll('.pipeline-sort-button').forEach(b=>{
        b.textContent=Number(b.dataset.col)===i?(ascending?'▲':'▼'):'▾';
      });paint();
    });
    actions.appendChild(btn);
  }
  const help=document.createElement('button');help.type='button';help.className='pipeline-question';
  help.textContent='?';help.title=helps[i];help.setAttribute('aria-label','Explain '+col);
  help.addEventListener('click',()=>{
    document.getElementById('pipeline-help-title').textContent=col;
    document.getElementById('pipeline-help-copy').textContent=helps[i];popup.hidden=false;
  });
  actions.appendChild(help);controls.appendChild(actions);th.appendChild(controls);
  head.appendChild(th);
});
document.getElementById('pipeline-help-close').addEventListener('click',()=>popup.hidden=true);
document.getElementById('pipeline-detail-close').addEventListener('click',()=>{detail.hidden=true;selected=-1;paint();});
previous.addEventListener('click',()=>{page=Math.max(0,page-1);paint();});
next.addEventListener('click',()=>{if((page+1)*pageSize<rows.length){page++;paint();}});
document.addEventListener('keydown',e=>{if(e.key==='Escape')popup.hidden=true;});
paint();
})();
</script>
""".replace("__DATA__", payload)
    return css + markup + script


def render_pipeline_grid(frame, *, height=550):
    """Show all filtered records through a paginated HTML table and real help icons."""
    components.html(pipeline_grid_html(frame, height=height), height=int(height)+45, scrolling=False)
