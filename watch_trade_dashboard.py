"""Watchlist above Trading, with one auto-loading stock chart per selected ticker.

Selections are the same W/T flags set in the #2, #3 and #4 ticker cells.
This is a research tag dashboard, NOT a broker trading interface.
"""
import streamlit.components.v1 as components


def render_watch_trade_dashboard():
    """Render responsive charts and buttons, backed by per-browser selections."""
    page = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#dff5e1;color:#111;font-family:Arial,Helvetica,sans-serif}
main{padding:8px 10px 30px}
.description{font-size:13px;color:#24422e;line-height:1.45;margin:0 0 10px}
section{background:white;border:2px solid black;border-radius:12px;padding:12px;margin:10px 0 18px}
.title{display:flex;align-items:center;gap:10px;justify-content:space-between;flex-wrap:wrap}
h2{font-size:20px;margin:0 0 8px}
.count{font-size:12px;background:#f4f4f4;border:1px solid #111;border-radius:8px;padding:4px 9px}
.header{font-weight:700;background:#edf2ed;border-bottom:1px solid #aaa;
        display:grid;grid-template-columns:minmax(165px,210px) minmax(0,1fr);padding:8px;gap:8px}
.stock{display:grid;grid-template-columns:minmax(165px,210px) minmax(0,1fr);
       border-bottom:1px solid #aaa;gap:8px;align-items:stretch;padding:9px 6px}
.stock:last-child{border-bottom:0}
.identity{display:flex;flex-direction:column;gap:9px;padding-top:6px}
.symbol{font-weight:800;font-size:20px}
.started{font-size:12px;color:#474747;line-height:1.4}
.actions{display:flex;gap:5px;flex-wrap:wrap}
button{cursor:pointer;border:1px solid #222;background:white;color:#111;
       border-radius:5px;font-weight:700;padding:6px 9px;font-size:12px}
button:hover{background:#e6f4e8}
button.active{background:#22863a;color:white}
.chart{position:relative;height:235px;min-width:0;background:#fff;
       border:1px solid #ccc;border-radius:7px;overflow:hidden}
.chart .tradingview-widget-container{height:100%;width:100%}
.chart .tradingview-widget-container__widget{height:calc(100% - 18px);width:100%}
.chart small{font-size:10px;padding-left:4px}
.chart a{color:#1456aa}
.pending{padding:25px 12px;font-size:13px;color:#555}
.empty{font-size:14px;padding:25px 8px;color:#555;text-align:center}
.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.controls button{background:#fff}
.note{font-size:11px;color:#555;margin:9px 3px;line-height:1.4}
@media (max-width:520px){
  main{padding:5px}
  section{padding:8px}
  .header{display:none}
  .stock{grid-template-columns:minmax(0,1fr)}
  .identity{flex-direction:row;justify-content:space-between;align-items:center;flex-wrap:wrap}
  .chart{height:235px}
}
</style>
</head>
<body>
<main>
  <p class="description">Press <b>W</b> or <b>T</b> before a ticker in #2 PIPELINE, #3 PRE3 or #4 POST3. It appears here automatically when this tab opens. Charts launch when the stock is added or appears on screen.</p>
  <div class="controls"><button id="refresh" type="button">↻ Sync lists</button><span id="sync-status" aria-live="polite"></span></div>
  <section aria-label="Watchlist">
    <div class="title"><h2>WATCHLIST</h2><span class="count" id="watch-count">0 tickers</span></div>
    <div class="header"><span>Ticker / Actions</span><span>Attached Stock Chart</span></div>
    <div id="watch-rows" aria-live="polite"></div>
  </section>
  <section aria-label="Trade screen">
    <div class="title"><h2>TRADING</h2><span class="count" id="trade-count">0 tickers</span></div>
    <div class="header"><span>Ticker / Actions</span><span>Attached Stock Chart</span></div>
    <div id="trade-rows" aria-live="polite"></div>
  </section>
  <p class="note">W and T are independent research tags; adding T does not place an order or erase W. Start times are saved locally in this browser, not as verified execution timestamps. TradingView data may be delayed; its default chart range is the closest supported window to the selection date, not a precise point-in-time backtest. No chart data is invented if the quote provider is unavailable.</p>
</main>
<script>
(() => {
  'use strict';
  const KEY = 'pdufa_watch_trading_v1';
  const START_KEY = 'pdufa_watch_trading_since_v1';
  const CHANNEL = 'pdufa_watch_trading_sync_v1';
  const CHART_URL = 'https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js';
  const tickerPattern = /^[A-Z][A-Z0-9.\-]{0,12}$/;
  const unique = values => [...new Set((Array.isArray(values) ? values : [])
      .filter(t => typeof t === 'string' && tickerPattern.test(t)))].sort();
  const normalize = value =>
    value && value.version === 1 && Array.isArray(value.watch) && Array.isArray(value.trade)
      ? {version:1,watch:unique(value.watch),trade:unique(value.trade)} : null;
  function get(key) {
    try {return JSON.parse(localStorage.getItem(key));} catch (e) {return null;}
  }
  function save(key, value) {
    try {localStorage.setItem(key, JSON.stringify(value));} catch (e) {}
  }
  function parseStarts() {
    const raw = get(START_KEY);
    const result = {watch:{},trade:{}};
    if (!raw || typeof raw !== 'object') return result;
    for (const group of ['watch','trade']) {
      const entries = raw[group];
      if (!entries || typeof entries !== 'object' || Array.isArray(entries)) continue;
      for (const [symbol, stamp] of Object.entries(entries)) {
        if (tickerPattern.test(symbol) && typeof stamp === 'string' &&
            !Number.isNaN(Date.parse(stamp))) result[group][symbol] = stamp;
      }
    }
    return result;
  }
  let selected = normalize(get(KEY)) || {version:1,watch:[],trade:[]};
  let started = parseStarts();
  let channel = null;
  try { channel = new BroadcastChannel(CHANNEL); } catch (e) {}
  const section = {
    watch: document.getElementById('watch-rows'),
    trade: document.getElementById('trade-rows')
  };
  // Rendered chart widgets are keyed by (list, ticker, start time).
  // A new W/T selection re-mounts its own chart automatically.
  const chartMounted = new Set();
  const createdRows = new Map();
  let observer = null;
  if ('IntersectionObserver' in window) {
    observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          mountChart(entry.target);
          observer.unobserve(entry.target);
        }
      }
    }, {rootMargin:'150px 0px'});
  }
  function trackingWindow(stamp) {
    if (!stamp) return '1m|30';
    const days = Math.max(0,(Date.now()-Date.parse(stamp))/86400000);
    if (days <= 2) return '1d|1';
    if (days <= 32) return '1m|30';
    if (days <= 96) return '3m|60';
    if (days <= 380) return '12m|1D';
    return '60m|1W';
  }
  function localDate(stamp) {
    if (!stamp) return 'Start time unavailable';
    try {return new Date(stamp).toLocaleString(undefined,{year:'numeric',month:'short',
      day:'numeric',hour:'numeric',minute:'2-digit'});}
    catch (e) {return 'Start time unavailable';}
  }
  function mountChart(target) {
    if (!target || !target.isConnected) return;
    const ticker = target.dataset.ticker, kind = target.dataset.kind;
    const stamp = target.dataset.started || '';
    if (!tickerPattern.test(ticker) || !['watch','trade'].includes(kind)) return;
    const signature = kind+'|'+ticker+'|'+stamp;
    if (chartMounted.has(signature)) return;
    chartMounted.add(signature);
    const container = document.createElement('div');
    container.className = 'tradingview-widget-container';
    const widget = document.createElement('div');
    widget.className = 'tradingview-widget-container__widget';
    const credit = document.createElement('small');
    const anchor = document.createElement('a');
    anchor.href = 'https://www.tradingview.com/symbols/'+encodeURIComponent(ticker)+'/';
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    anchor.textContent = ticker+' chart via TradingView';
    credit.append(anchor);
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = CHART_URL;
    script.async = true;
    script.textContent = JSON.stringify({
      autosize:true, width:'100%', height:'100%', symbol: ticker, locale:'en',
      colorTheme:'light', backgroundColor:'#ffffff', chartType:'area',
      isTransparent:false, hideDateRanges:true,
      dateRanges:[trackingWindow(stamp)],
      symbols:[[ticker,ticker+'|'+trackingWindow(stamp).split('|')[0]]],
      valuesTracking:'1', fontSize:'10'
    });
    container.append(widget,credit,script);
    target.replaceChildren(container);
  }
  function makeButton(text,label,onClick,active=false) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = text;
    btn.setAttribute('aria-label',label);
    btn.className = active ? 'active' : '';
    btn.addEventListener('click',onClick);
    return btn;
  }
  function makeRow(kind,ticker) {
    const startTime = started[kind][ticker] || '';
    const row = document.createElement('div');
    row.className = 'stock';
    const identity = document.createElement('div');
    identity.className = 'identity';
    const symbol = document.createElement('strong');
    symbol.className = 'symbol';
    symbol.textContent = ticker;
    const time = document.createElement('div');
    time.className = 'started';
    time.textContent = 'Tracking since '+localDate(startTime);
    const actions = document.createElement('div');
    actions.className = 'actions';
    if (kind === 'watch') {
      actions.append(
        makeButton(selected.trade.includes(ticker) ? 'T SELECTED' : '+ TRADE',
          'Add '+ticker+' to Trading',()=>toggle('trade',ticker), selected.trade.includes(ticker)),
        makeButton('REMOVE W','Remove '+ticker+' from Watchlist',()=>toggle('watch',ticker))
      );
    } else {
      if (!selected.watch.includes(ticker))
        actions.append(makeButton('+ WATCH','Add '+ticker+' to Watchlist',
          ()=>toggle('watch',ticker)));
      actions.append(makeButton('REMOVE T','Remove '+ticker+' from Trading list',
        ()=>toggle('trade',ticker)));
    }
    identity.append(symbol,time,actions);
    const chart = document.createElement('div');
    chart.className = 'chart';
    chart.dataset.kind = kind;
    chart.dataset.ticker = ticker;
    chart.dataset.started = startTime;
    const waiting = document.createElement('div');
    waiting.className = 'pending';
    waiting.textContent = 'Loading '+ticker+' stock chart…';
    chart.append(waiting);
    row.append(identity,chart);
    if (observer) observer.observe(chart);
    else window.setTimeout(() => mountChart(chart), 0);
    return row;
  }
  function render() {
    for (const kind of ['watch','trade']) {
      const list = selected[kind];
      const bucket = section[kind];
      const next = new Set(list.map(t => kind+'|'+t+'|'+(started[kind][t] || '')));
      for (const [key,object] of [...createdRows]) {
        if (key.startsWith(kind+'|') && !next.has(key)) {
          if (observer) observer.unobserve(object.lastElementChild);
          object.remove();createdRows.delete(key);chartMounted.delete(key);
        }
      }
      const replacement = document.createDocumentFragment();
      for (const ticker of list) {
        const key = kind+'|'+ticker+'|'+(started[kind][ticker] || '');
        let row = createdRows.get(key);
        if (row) {
          // Recreate action buttons to reflect current Watch/Trade membership.
          row.querySelector('.actions').replaceWith(
            makeRowActions(kind,ticker)
          );
        } else {
          row = makeRow(kind,ticker);
          createdRows.set(key,row);
        }
        replacement.append(row);
      }
      if (!list.length) {
        const empty = document.createElement('div');
        empty.className = 'empty';
        empty.textContent = kind === 'watch'
          ? 'No watchlist tickers. Press W beside a ticker in #2, #3 or #4.'
          : 'No trade tickers. Press T in #2, #3 or #4, or + TRADE beside a watchlist ticker.';
        replacement.append(empty);
      }
      bucket.replaceChildren(replacement);
      document.getElementById(kind+'-count').textContent = list.length+' ticker'+(list.length===1?'':'s');
      // Start the newest chart immediately even if it is below the fold.
      const newest = [...list].sort((a,b) => Date.parse(started[kind][b]||0)
        - Date.parse(started[kind][a]||0))[0];
      if (newest) {
        const key = kind+'|'+newest+'|'+(started[kind][newest]||'');
        const latestRow = createdRows.get(key);
        if (latestRow) mountChart(latestRow.lastElementChild);
      }
    }
    document.getElementById('sync-status').textContent = 'Watch '+selected.watch.length+' · Trade '+selected.trade.length;
  }
  function makeRowActions(kind,ticker) {
    const actions = document.createElement('div');
    actions.className = 'actions';
    if (kind === 'watch') {
      actions.append(
        makeButton(selected.trade.includes(ticker) ? 'T SELECTED' : '+ TRADE',
          (selected.trade.includes(ticker) ? 'Remove ' : 'Add ')+ticker+' from/to Trading',
          ()=>toggle('trade',ticker),selected.trade.includes(ticker)),
        makeButton('REMOVE W','Remove '+ticker+' from Watchlist',()=>toggle('watch',ticker))
      );
    } else {
      if (!selected.watch.includes(ticker))
        actions.append(makeButton('+ WATCH','Add '+ticker+' to Watchlist',()=>toggle('watch',ticker)));
      actions.append(makeButton('REMOVE T','Remove '+ticker+' from Trading list',()=>toggle('trade',ticker)));
    }
    return actions;
  }
  function ensureStamps() {
    let dirty = false;
    for (const kind of ['watch','trade']) {
      for (const ticker of selected[kind]) {
        if (!started[kind][ticker]) {started[kind][ticker] = new Date().toISOString();dirty=true;}
      }
    }
    if (dirty) save(START_KEY,started);
  }
  function adoptSelection(incoming) {
    const candidate = normalize(incoming);
    if (!candidate) return;
    const existing = selected;
    selected = candidate;
    // The source buttons may update both localStorage keys. Re-read first.
    started = parseStarts();
    for (const kind of ['watch','trade']) {
      for (const ticker of selected[kind]) {
        if (!existing[kind].includes(ticker) && !started[kind][ticker])
          started[kind][ticker] = new Date().toISOString();
      }
    }
    ensureStamps();
    save(START_KEY,started);
    render();
  }
  function toggle(kind,ticker) {
    if (!tickerPattern.test(ticker)) return;
    // Always merge the freshest same-browser state before toggling.
    const current = normalize(get(KEY));
    if (current) selected = current;
    started = parseStarts();
    const list = new Set(selected[kind]);
    if (list.has(ticker)) {
      list.delete(ticker);
      delete started[kind][ticker];
    } else {
      list.add(ticker);
      started[kind][ticker] = new Date().toISOString();
    }
    selected[kind] = [...list].sort();
    save(START_KEY,started);
    save(KEY,selected);
    render();
    // Trade promotion or Watch addition mounts the new chart right away.
    if (list.has(ticker)) {
      const key = kind+'|'+ticker+'|'+started[kind][ticker];
      const row = createdRows.get(key);
      if (row) mountChart(row.lastElementChild);
    }
    if (channel) channel.postMessage(selected);
  }
  document.getElementById('refresh').addEventListener('click',()=>{
    adoptSelection(normalize(get(KEY)) || {version:1,watch:[],trade:[]});
  });
  window.addEventListener('storage', e => {
    if (e.key === KEY || e.key === START_KEY) adoptSelection(normalize(get(KEY)));
  });
  if (channel) channel.onmessage = e => adoptSelection(e.data);
  ensureStamps();
  render();
  // Some browsers suppress storage events in embedded views. Cheap fallback
  // keeps list membership current even while another app tab is active.
  window.setInterval(()=>{
    const current=normalize(get(KEY));
    if (current && (JSON.stringify(current.watch)!==JSON.stringify(selected.watch)
        || JSON.stringify(current.trade)!==JSON.stringify(selected.trade))) adoptSelection(current);
  },3000);
})();
</script>
</body></html>
"""
    # Two vertically stacked scrolling sections; charts load on first visibility
    # and use the same browser-backed W/T tag store as the three source tables.
    components.html(page, height=1450, scrolling=True)
