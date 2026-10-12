"""Read-only PDUFA tables with a real CSS-drawn circled question-mark per header.

Native Streamlit grids render column titles on a canvas; U+20DD enclosing
circle is not supported by every font and can appear as a boxed X. These
three dashboard sheets use ordinary HTML, keeping headings and help icons
on one line and using the existing pandas Styler cell colors.
"""
import html
import json
import re

import pandas as pd
import streamlit.components.v1 as components

from pdufa_display_columns import finance_style
from pdufa_table_headers import column_help, style_countdown_cells


_HEADER = re.compile(r'(<th\b[^>]*class="col_heading[^"]*"[^>]*>)(.*?)(</th>)', re.S)


def dashboard_sheet_html(data: pd.DataFrame, columns: list[str], height: int = 310, *,
                         ticker_controls=False, watchlist=(), trading_tickers=()) -> str:
    """Create a sortable, scrollable HTML table with actual CSS circle icons."""
    visible_columns = [col for col in columns if col in data.columns]
    visible = data.loc[:, visible_columns].copy()
    styled = style_countdown_cells(finance_style(visible))
    # Keep existing countdown and financing Styler colors, plus safe text data.
    markup = styled.hide(axis="index").format(escape="html").to_html()
    markup = re.sub(r'<table\b', '<table class="pdufa-help-grid"', markup, count=1)

    # Inline controls are embedded in the actual Ticker column, never in a
    # duplicate ticker list. Preserve row ordering and existing styled cells.
    if ticker_controls and "Ticker" in visible_columns:
        ticker_index = visible_columns.index("Ticker")
        tickers = visible["Ticker"].fillna("").astype(str).str.strip().str.upper().tolist()
        cell_pattern = re.compile(
            r'(<td\b[^>]*class="[^"]*\brow(\d+)\s+col'
            + str(ticker_index) + r'\b[^"]*"[^>]*>)(.*?)(</td>)',
            re.S,
        )

        def insert_inline_controls(match):
            row = int(match.group(2))
            if row >= len(tickers):
                return match.group(0)
            symbol = tickers[row]
            if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,12}", symbol):
                return match.group(0)
            safe = html.escape(symbol, quote=True)
            contents = (
                '<span class="ticker-inline-controls">'
                f'<button type="button" class="ticker-inline-toggle" data-category="watch" data-ticker="{safe}">+</button>'
                f'<button type="button" class="ticker-inline-toggle" data-category="trade" data-ticker="{safe}">+</button>'
                f'<strong class="ticker-inline-symbol">{safe}</strong>'
                '</span>'
            )
            return match.group(1) + contents + match.group(4)

        markup, converted = cell_pattern.subn(insert_inline_controls, markup)
        if converted != len(tickers):
            raise ValueError("Inline ticker button count differs from visible ticker rows")

    counter = iter(enumerate(visible_columns))
    def decorate(match):
        index, name = next(counter)
        title = html.escape(
            "W / T · Ticker" if ticker_controls and name == "Ticker" else
            "Days to PDUFA" if name.casefold().replace("_", " ") in
            ("days to pdufa", "days left") else str(name)
        )
        explanation = html.escape(column_help(name), quote=True)
        # Question mark itself is ASCII, with its circle drawn by CSS.
        # No unsupported enclosing Unicode marks or emoji fonts required.
        return (match.group(1)
                + f'<span class="pdufa-th-content">'
                + f'<button class="pdufa-th-sort" type="button" data-index="{index}"'
                + f' title="Sort by {html.escape(str(name), quote=True)}">'
                + f'<span class="pdufa-th-label">{title}</span>'
                + '<span class="pdufa-th-arrow" aria-hidden="true">⇅</span>'
                + '</button>'
                + f'<span class="pdufa-circled-help" tabindex="0" role="img"'
                + f' aria-label="{explanation}" title="{explanation}">?</span>'
                + '</span>'
                + match.group(3))

    markup, found = _HEADER.subn(decorate, markup)
    if found != len(visible_columns):
        raise ValueError("PDUFA HTML headers did not match the displayed columns")

    styles = """
    <style>
      html,body{margin:0;background:#fff;color:#111;font-family:Arial,Helvetica,sans-serif}
      .pdufa-grid-scroll{overflow:auto;max-height:__HEIGHT__px;border:2px solid #111;
                         border-radius:9px;background:#fff}
      .pdufa-help-grid{border-collapse:separate;border-spacing:0;width:max-content;
                       table-layout:auto;font-size:13px;color:#111;background:#fff}
      .pdufa-help-grid th,.pdufa-help-grid td{
        border-bottom:1px solid #aaa;border-right:1px solid #bbb;
        text-align:left;padding:6px 9px;white-space:nowrap;max-width:none;min-width:0}
      .pdufa-help-grid th{position:sticky;top:0;z-index:2;
                          background:#f4f4f4;font-weight:700}
      .pdufa-help-grid td{background:#fff}
      .pdufa-th-content{display:inline-flex;flex-flow:row nowrap;
                        align-items:center;gap:5px;white-space:nowrap}
      .pdufa-th-sort{display:inline-flex;flex-flow:row nowrap;align-items:center;
                     gap:4px;border:0;background:transparent;color:#111;
                     padding:0;font:inherit;font-weight:700;cursor:pointer}
      .pdufa-th-label{white-space:nowrap}
      .pdufa-th-arrow{font-size:12px;color:#444}
      .pdufa-circled-help{
        display:inline-flex;align-items:center;justify-content:center;
        box-sizing:border-box;flex:0 0 17px;width:17px;height:17px;
        font-family:Arial,sans-serif;font-size:12px;font-weight:700;
        line-height:1;background:#fff;color:#111;border:1.5px solid #333;
        border-radius:50%;cursor:help}
      .pdufa-circled-help:hover,.pdufa-circled-help:focus{
        outline:none;color:#fff;background:#111;border-color:#111}
      .pdufa-help-grid a{color:#0b57d0;text-decoration:underline}
      .ticker-inline-controls{display:inline-flex;align-items:center;gap:3px;white-space:nowrap}
      .ticker-inline-toggle{display:inline-flex;align-items:center;justify-content:center;
        width:23px;height:23px;min-width:23px;padding:0;margin:0;border:1px solid #777;
        border-radius:4px;background:#fff;color:#111;cursor:pointer;
        font:800 16px/1 Arial,Helvetica,sans-serif}
      .ticker-inline-toggle[data-active="true"]{background:#22863a;color:#fff;border-color:#18632c}
      .ticker-inline-toggle:focus-visible{outline:2px solid #1d4ed8;outline-offset:1px}
      .ticker-inline-symbol{padding-left:3px;font-weight:700}
    </style>
    """.replace("__HEIGHT__", str(int(height)))
    script = r"""
    <script>
    (() => {
      const table = document.querySelector('.pdufa-help-grid');
      if (!table) return;
      const body = table.tBodies[0];
      let active = -1, ascending = true;
      const buttons = Array.from(table.querySelectorAll('.pdufa-th-sort'));
      buttons.forEach(button => {
        button.addEventListener('click', () => {
          const index = Number(button.dataset.index);
          ascending = index !== active ? true : !ascending;
          active = index;
          const rows = Array.from(body.rows);
          const numeric = value => {
            const raw = value.replace(/[$,%\\s]/g, '');
            return raw && /^[-+]?(?:\\d*\\.)?\\d+$/.test(raw) ? Number(raw) : null;
          };
          rows.sort((left, right) => {
            const a = (left.cells[index]?.querySelector('.ticker-inline-symbol') ||
              left.cells[index])?.textContent.trim() ?? '';
            const b = (right.cells[index]?.querySelector('.ticker-inline-symbol') ||
              right.cells[index])?.textContent.trim() ?? '';
            if (!a || !b) return (!a === !b) ? 0 : !a ? 1 : -1;
            const an = numeric(a), bn = numeric(b);
            const difference = an !== null && bn !== null
              ? an - bn : a.localeCompare(b, undefined, {numeric:true,sensitivity:'base'});
            return ascending ? difference : -difference;
          });
          rows.forEach(row => body.appendChild(row));
          buttons.forEach(btn => {
            const icon = btn.querySelector('.pdufa-th-arrow');
            icon.textContent = btn === button ? (ascending ? '▲' : '▼') : '⇅';
          });
        });
      });
    })();
    </script>
    """
    # Keep the exact existing localStorage schema used by native ticker controls.
    # Inline buttons update immediately and synchronize between all three tables.
    if ticker_controls and "Ticker" in visible_columns:
        initial = {
            "version": 1,
            "watch": [str(v).upper() for v in watchlist if isinstance(v, str)],
            "trade": [str(v).upper() for v in trading_tickers if isinstance(v, str)],
        }
        initial_json = json.dumps(initial).replace("<", "\\u003c")
        script += """
        <script>
        (() => {
          const storageKey = 'pdufa_watch_trading_v1';
          const buttons = [...document.querySelectorAll('.ticker-inline-toggle')];
          const initial = __INITIAL__;
          const clean = x => [...new Set((Array.isArray(x) ? x : [])
            .filter(t => typeof t === 'string' && /^[A-Z][A-Z0-9.\-]{0,12}$/.test(t)))];
          const normalize = x => x && x.version === 1 && Array.isArray(x.watch) && Array.isArray(x.trade)
            ? {version:1, watch:clean(x.watch), trade:clean(x.trade)} : null;
          function read() {
            try { return normalize(JSON.parse(localStorage.getItem(storageKey))) || initial; }
            catch (e) { return initial; }
          }
          let state = read();
          function paint() {
            for (const b of buttons) {
              const on = state[b.dataset.category].includes(b.dataset.ticker);
              b.textContent = on ? '−' : '+';
              b.dataset.active = String(on);
              b.setAttribute('aria-pressed', String(on));
              b.setAttribute('aria-label', (on ? 'Remove ' : 'Add ') + b.dataset.ticker +
                (b.dataset.category === 'watch' ? ' from Watchlist' : ' from Trading list'));
              b.title = (b.dataset.category === 'watch' ? 'Watchlist' : 'Trading list (no broker order)')
                + ': ' + b.dataset.ticker;
            }
          }
          let broadcast = null;
          try {
            broadcast = new BroadcastChannel('pdufa_watch_trading_sync_v1');
            broadcast.onmessage = e => { const next = normalize(e.data); if (next) {state = next; paint();} };
          } catch (e) {}
          window.addEventListener('storage', e => {
            if (e.key === storageKey) {state = read(); paint();}
          });
          for (const b of buttons) b.addEventListener('click', () => {
            const kind = b.dataset.category, symbol = b.dataset.ticker;
            if (!['watch','trade'].includes(kind)) return;
            const members = new Set(state[kind]);
            if (members.has(symbol)) members.delete(symbol); else members.add(symbol);
            state[kind] = [...members].sort();
            paint();
            try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch (e) {}
            if (broadcast) broadcast.postMessage(state);
          });
          paint();
        })();
        </script>
        """.replace("__INITIAL__", initial_json)
    return styles + '<div class="pdufa-grid-scroll">' + markup + '</div>' + script


def render_dashboard_sheet(data: pd.DataFrame, columns: list[str], height: int = 310, *,
                           ticker_controls=False, watchlist=(), trading_tickers=()):
    """Render sortable table with optional inline Watch / Trade +/- ticker buttons."""
    components.html(
        dashboard_sheet_html(data, columns, height, ticker_controls=ticker_controls,
                             watchlist=watchlist, trading_tickers=trading_tickers),
        height=height + 30, scrolling=False,
    )
