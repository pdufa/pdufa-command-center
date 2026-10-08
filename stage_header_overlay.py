"""Keep the native Streamlit STAGE checkbox popover on the visible grid header.

Streamlit does not offer a native custom data_editor header menu. Its cells
and headers are rendered on a canvas, so the existing Streamlit popover must
be visually anchored over the STAGE header without changing the editable grid.
Requires Streamlit >=1.52 for safe, explicitly opted-in st.html scripts.
"""
import json

import streamlit as st

_SCRIPT = r"""
<script>
(() => {
  const marker = __MARKER__;
  const stageOffset = __STAGE_OFFSET__;
  const id = 'stage-header-' + marker;
  const previous = window.__pdufaStageHeaders?.[id];
  if (previous) previous();
  window.__pdufaStageHeaders = window.__pdufaStageHeaders || {};

  let scheduled = false;
  const selector = '.st-key-' + marker;
  const gridSelector = '[data-testid="stDataFrame"],[data-testid="stDataEditor"],iframe[title]';

  function findGrid(anchor) {
    const candidates = Array.from(document.querySelectorAll(gridSelector));
    const nextAnchor = Array.from(document.querySelectorAll('[class*="st-key-stageheader_"]'))
      .find(other => other !== anchor &&
        (anchor.compareDocumentPosition(other) & Node.DOCUMENT_POSITION_FOLLOWING));
    return candidates.find(candidate => {
      if (!(anchor.compareDocumentPosition(candidate) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
      if (nextAnchor && !(candidate.compareDocumentPosition(nextAnchor) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
      const rect = candidate.getBoundingClientRect();
      return rect.width > 180 && rect.height > 90 &&
        window.getComputedStyle(candidate).visibility !== 'hidden';
    });
  }

  function align() {
    const anchor = document.querySelector(selector);
    if (!anchor) {
      // Tear down observers when the user navigates to a different tab/page.
      window.__pdufaStageHeaders?.[id]?.();
      delete window.__pdufaStageHeaders?.[id];
      return;
    }
    const grid = findGrid(anchor);
    if (!grid) {
      // Preserve access to Select all if no rows remain to show.
      anchor.style.cssText = '';
      const emptySlot = anchor.closest('[data-testid="stElementContainer"]');
      if (emptySlot) emptySlot.style.cssText = '';
      return;
    }
    const rect = grid.getBoundingClientRect();
    // Account for native grid horizontal scrolling if an exposed scroller exists.
    const scrollport = Array.from(grid.querySelectorAll('*')).find(node =>
      node.clientWidth > 180 && node.scrollWidth > node.clientWidth + 10 &&
      window.getComputedStyle(node).overflowX !== 'hidden');
    const horizontalScroll = scrollport?.scrollLeft || 0;
    // Canvas heading: STAGE follows controls and Ticker.
    // Place the compact chevron just to the right of the word STAGE.
    const left = rect.left + stageOffset + 53 - horizontalScroll;
    const isIframe = grid.tagName === 'IFRAME';
    const top = rect.top + (isIframe ? 132 : 5);
    anchor.style.position = 'fixed';
    anchor.style.left = left + 'px';
    anchor.style.top = top + 'px';
    anchor.style.width = '31px';
    anchor.style.height = '28px';
    anchor.style.minHeight = '0';
    anchor.style.padding = '0';
    anchor.style.margin = '0';
    anchor.style.zIndex = '900';
    anchor.style.overflow = 'visible';
    const button = anchor.querySelector('button');
    if (button) {
      button.style.minHeight = '25px';
      button.style.height = '25px';
      button.style.padding = '0 3px';
      button.style.fontSize = '15px';
      button.style.border = '1px solid #222';
      button.title = 'Filter or sort the STAGE column';
    }
    const slot = anchor.closest('[data-testid="stElementContainer"]');
    if (slot) {
      slot.style.minHeight = '0px';
      slot.style.height = '0px';
      slot.style.margin = '0px';
      slot.style.padding = '0px';
      slot.style.overflow = 'visible';
    }
    // If a table is scrolled out of view, do not cover unrelated controls.
    anchor.style.visibility = (rect.bottom < 0 || rect.top > window.innerHeight ||
      left < rect.left || left + 31 > rect.right) ? 'hidden' : 'visible';
  }

  const schedule = () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled = false; align(); });
  };
  const observer = new MutationObserver(schedule);
  observer.observe(document.body, {
    childList: true, subtree: true, attributes: true,
    attributeFilter: ['aria-selected', 'hidden', 'aria-hidden']
  });
  window.addEventListener('scroll', schedule, true);
  window.addEventListener('resize', schedule);
  document.addEventListener('click', schedule, true);
  window.__pdufaStageHeaders[id] = () => {
    observer.disconnect();
    window.removeEventListener('scroll', schedule, true);
    window.removeEventListener('resize', schedule);
    document.removeEventListener('click', schedule, true);
  };
  schedule();
})();
</script>
"""


def position_stage_filter(marker, stage_offset):
    """Move the *real* checkboxes popover onto the native STAGE header."""
    script = (_SCRIPT.replace('__MARKER__', json.dumps(marker))
                     .replace('__STAGE_OFFSET__', str(int(stage_offset))))
    st.html(script, unsafe_allow_javascript=True)
