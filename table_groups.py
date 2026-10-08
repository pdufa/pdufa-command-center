"""Compact column tabs shared by the dashboard's tables and editors."""
from collections import OrderedDict
from hashlib import sha1
import inspect
import re

import pandas as pd
import streamlit as st


MAX_COLUMNS = 7
CONTROL_COLUMNS = {"watchlist", "add to analysis", "add to invest", "move to master table", "in master table"}
GROUP_ORDER = ("Overview", "Clinical", "FDA", "Financing", "Market", "Trading", "Evidence", "Tasks", "Schedule", "Actions")
TOPIC_ORDER = {
    "Clinical": ("Trial registry & stage", "Milestone dates", "Clinical results"),
    "FDA": ("Application & dates", "Predictions", "Review gates", "Statistics", "Safety & benefit-risk", "CMC", "Facilities & inspections", "Designations", "Regulatory monitoring", "Directional assessment", "Facility registry", "Outcomes & validation"),
}


def _name(column):
    return re.sub(r"[^a-z0-9%]+", " ", str(column).lower()).strip()


def column_topic(column):
    """Keep evidence from the same discipline and source family together."""
    name = _name(column)
    has = lambda *terms: any(term in name for term in terms)
    if name.startswith("historical predictions "):
        _, topic = column_topic(str(column).split("·", 1)[-1])
        return "Evidence", "Historical · " + topic
    if name.startswith("fda backfill ") or has("backfill", "missing components", "source targets"):
        return "Evidence", "Backfill"
    if name.startswith("fda freezes ") or has("freeze id", "frozen at", "prediction frozen"):
        return "Evidence", "Prediction freezes"
    if name.startswith("fda directional "):
        return "FDA", "Directional assessment"
    if name.startswith("fda monitor "):
        return "FDA", "Regulatory monitoring"
    if name.startswith("fda facilities "):
        return "FDA", "Facility registry"
    if name in {"area", "task", "order"}:
        return "Tasks", "Tasks"
    if name in {"cadence", "priority", "status"}:
        return "Schedule", "Schedule"
    if name in {"next action", "notes"}:
        return "Actions", "Actions"
    if has("trade score", "trade pdufa score"):
        return "Trading", "Signals & scores"
    if has("financ", "offering", "dilution", "atm", "proceeds", "cash", "runway") or name in {"announced", "running", "closed"}:
        if has("source", "evidence", "audit", "verified", "verification"):
            return "Financing", "Verification"
        if has("cash", "runway", "dilution", "atm", "proceeds"):
            return "Financing", "Cash & dilution"
        if has("summary"):
            return "Financing", "Summary"
        return "Financing", "Timeline & status"
    if has("market cap", "cap bucket", "valuation", "revenue"):
        return "Market", "Valuation"
    if has("ownership", "shares", "float", "short interest", "short ratio", "short %"):
        return "Market", "Ownership & shorts"
    if has("source", "evidence", "last checked", "last updated", "generated at", "verified as of", "cutoff", "record source", "review reason", "conflict", "recoverability", "audit"):
        if has("source", "url", "link"):
            return "Evidence", "Sources"
        if has("checked", "updated", "generated", "as of", "cutoff"):
            return "Evidence", "Freshness"
        return "Evidence", "Review & provenance"
    if has("primary endpoint", "multiplicity", "missing data", "effect size", "replication", "statistics"):
        return "FDA", "Statistics"
    if has("cmc", "process validation", "stability", "analytical", "comparability", "supplier", "cmo"):
        return "FDA", "CMC"
    if has("facility", "site ", "inspection", "warning letter", "import alert", "form483", "form 483", "remediation", "fei"):
        return "FDA", "Facilities & inspections"
    if has("safety", "clinical pharmacology", "nonclinical", "immunogenicity", "benefit risk", "bimo", "data integrity"):
        return "FDA", "Safety & benefit-risk"
    if has("orphan", "no available therapy", "serious condition", "life threatening", "fast track", "breakthrough", "priority review", "accelerated approval", "rmat", "qidp", "rare pediatric", "rolling review", "rtor", "orbis") or name in {"spa", "o", "l", "s", "ft", "bt", "pr", "aa", "rm", "rp", "pv", "rr"}:
        return "FDA", "Designations"
    if has("decision", "outcome", "match", "correct", "actual binary", "predicted binary") or re.search(r"\bmiss\b", name):
        return "FDA", "Outcomes & validation"
    if has("pdufa", "nda", "bla", "acceptance", "application", "extension", "deficiency", "late cycle") or name in {"n", "b", "days left"}:
        return "FDA", "Application & dates"
    if has("prediction", "probability", "approval", "poa", "direction", "confidence", "model", "p%") or name in {"p approval", "suggestion", "p direction", "i direction"}:
        return "FDA", "Predictions"
    if has("fda", "regulatory", "labeling", "crl", "hard gate", "gate reason", "adcom", "blindspot"):
        return "FDA", "Review gates"
    if has("phase", "trial", "nct", "readout", "completion", "start date", "started", "results", "registered", "graduation", "moved to master"):
        if has("date", "start", "completion", "readout", "results", "moved"):
            return "Clinical", "Milestone dates"
        return "Clinical", "Trial registry & stage"
    if has("p value", "endpoint", "science", "clinical score") or name == "p":
        return "Clinical", "Clinical results"
    if has("entry", "watchlist", "funnel", "position", "gate", "eligibility", "universe"):
        return "Trading", "Entry & eligibility"
    if has("price", "return", "volume", "momentum"):
        return "Trading", "Price & volume"
    if has("iv ", "iv 30", "volatility", "risk"):
        return "Trading", "Risk"
    if has("trade", "trading", "signal", "score"):
        return "Trading", "Signals & scores"
    return "Overview", "Details"


def column_groups(columns, max_columns=MAX_COLUMNS):
    """Every field has one home; identifiers and action checkboxes repeat."""
    columns = list(columns)
    if len(columns) <= max_columns:
        return OrderedDict([("Overview", [("Overview", columns)])])
    named = {_name(c): c for c in columns}
    controls = [c for c in columns if _name(c) in CONTROL_COLUMNS]
    identity = [named[n] for n in ("ticker", "drug") if n in named]
    if not identity:
        identity = [named[n] for n in ("order", "task") if n in named]
    if not identity:
        identity = [columns[0]]
    pinned = list(dict.fromkeys(controls + identity))
    capacity = max_columns - len(pinned)
    if capacity < 1:
        raise ValueError("Too many shared columns for a compact table")
    preferred = ("indication", "current stage", "next milestone", "evidence status", "pdufa date", "current evidence", "graduation status", "company")
    overview = [named[n] for n in preferred if n in named and named[n] not in pinned][:capacity]
    buckets = OrderedDict()
    if overview:
        buckets[("Overview", "Overview")] = overview
    for column in columns:
        if column not in pinned and column not in overview:
            buckets.setdefault(column_topic(column), []).append(column)
    grouped = OrderedDict()
    for group in GROUP_ORDER:
        panes = []
        topics = TOPIC_ORDER.get(group, ())
        family_buckets = [(pair, fields) for pair, fields in buckets.items() if pair[0] == group]
        family_buckets.sort(key=lambda item: topics.index(item[0][1]) if item[0][1] in topics else len(topics))
        for (family, topic), fields in family_buckets:
            if family != group:
                continue
            chunks = [fields[i:i + capacity] for i in range(0, len(fields), capacity)]
            for i, chunk in enumerate(chunks):
                label = topic if len(chunks) == 1 else f"{topic} · {i + 1}"
                panes.append((label, pinned + chunk))
        if panes:
            grouped[group] = panes
    return grouped


def begin_table_render():
    st.session_state["_column_table_counts"] = {}


def _table_key(data, key):
    if key:
        return str(key)
    caller = inspect.currentframe().f_back.f_back
    base = f"{caller.f_code.co_filename}:{caller.f_lineno}:{list(data.columns)}"
    base = "column_table_" + sha1(base.encode()).hexdigest()[:12]
    counts = st.session_state.setdefault("_column_table_counts", {})
    occurrence = counts.get(base, 0)
    counts[base] = occurrence + 1
    return f"{base}_{occurrence}"


def render_column_tabs(data, key, render):
    groups = column_groups(data.columns)
    if sum(len(panes) for panes in groups.values()) == 1:
        return [render(next(iter(groups.values()))[0][1], "overview")]
    results = []
    for tab, (group, panes) in zip(st.tabs(list(groups)), groups.items()):
        with tab:
            labels = [label for label, _ in panes]
            selected = labels[0]
            if len(panes) > 1:
                selected = st.selectbox(f"{group} fields", labels, key=f"{key}_fields_{group}")
            fields = dict(panes)[selected]
            token = sha1(f"{group}:{selected}".encode()).hexdigest()[:10]
            results.append(render(fields, token))
    return results


def _compact_config(fields, config):
    result = {}
    for column in fields:
        original = (config or {}).get(column)
        if original is None and column in (config or {}):
            result[column] = None
            continue
        entry = dict(original) if isinstance(original, dict) else {"label": original or str(column)}
        entry.setdefault("help", str(column))
        entry["width"] = "small" if _name(column) in CONTROL_COLUMNS | {"ticker", "order", "n", "b", "p", "p%"} else "medium"
        result[column] = entry
    return result


def grouped_dataframe(data, **kwargs):
    data = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    key = _table_key(data, kwargs.pop("key", None))
    config = kwargs.pop("column_config", None)
    kwargs.pop("column_order", None)
    first = True

    def render(fields, token):
        nonlocal first
        panel_key = key if first else f"{key}_{token}"
        first = False
        return st.dataframe(data[fields], key=panel_key, column_config=_compact_config(fields, config), **kwargs)

    results = render_column_tabs(data, key, render)
    return next((result for result in results if getattr(getattr(result, "selection", None), "rows", [])), results[0])


def frame_signature(data):
    payload = pd.util.hash_pandas_object(data.astype(str), index=True).values.tobytes()
    return sha1(str(list(data.columns)).encode() + payload).hexdigest()


def apply_editor_changes(data, changes, editable, dynamic=False):
    """Apply a pane's edits to the complete records, including hidden fields."""
    result = data.copy()
    for row_number, values in changes.get("edited_rows", {}).items():
        position = int(row_number)
        if 0 <= position < len(result):
            for field, value in values.items():
                if field in editable:
                    result.iat[position, result.columns.get_loc(field)] = value
    if dynamic:
        deleted = {int(i) for i in changes.get("deleted_rows", [])}
        result = result.iloc[[i for i in range(len(result)) if i not in deleted]]
        added = [{field: row.get(field, pd.NA) if field in editable else pd.NA for field in data.columns}
                 for row in changes.get("added_rows", [])]
        if added:
            result = pd.concat([result, pd.DataFrame(added, columns=data.columns)], ignore_index=True)
        result = result.reset_index(drop=True)
    return result


def _commit_pane(state_key, widget_key, snapshot, editable, dynamic):
    state = st.session_state[state_key]
    edited = apply_editor_changes(snapshot, st.session_state.get(widget_key, {}), editable, dynamic)
    state["data"] = edited
    state["epoch"] += 1


def grouped_editor(data, **kwargs):
    """One shared draft makes edits survive switching tabs and adding rows."""
    data = data.copy()
    key = _table_key(data, kwargs.pop("key", None))
    config = kwargs.pop("column_config", None)
    disabled = kwargs.pop("disabled", False)
    dynamic = kwargs.pop("num_rows", "fixed") == "dynamic"
    kwargs.pop("column_order", None)
    state_key = "_column_draft_" + key
    signature = frame_signature(data)
    state = st.session_state.get(state_key)
    if state is None or state["source"] != signature:
        epoch = 0 if state is None else state["epoch"] + 1
        state = {"source": signature, "data": data.copy(), "epoch": epoch}
        st.session_state[state_key] = state
    groups = column_groups(data.columns)
    shared = set.intersection(*(set(fields) for panes in groups.values() for _, fields in panes))
    blocked = set(data.columns) if disabled is True else set(disabled or [])
    controls = {c for c in data.columns if _name(c) in CONTROL_COLUMNS}
    first = True

    def render(fields, token):
        nonlocal first
        primary = first
        first = False
        snapshot = state["data"].copy()
        allowed = set(fields) - blocked
        if not primary:
            allowed -= shared - controls
        pane_dynamic = dynamic and primary
        suffix = "" if primary else "_" + token
        widget_key = key + suffix + (f"_v{state['epoch']}" if state["epoch"] else "")
        pane_config = _compact_config(fields, config)
        pane_input = snapshot if pane_dynamic else snapshot[fields]
        if pane_dynamic:
            pane_config.update({c: None for c in data.columns if c not in fields})
        edited = st.data_editor(
            pane_input, key=widget_key, column_order=fields, column_config=pane_config,
            disabled=[c for c in pane_input.columns if c not in allowed],
            num_rows="dynamic" if pane_dynamic else "fixed", on_change=_commit_pane,
            args=(state_key, widget_key, snapshot, allowed, pane_dynamic), **kwargs,
        )
        # Also consume the returned value for programmatic edit events and tests.
        if not edited.equals(pane_input):
            if pane_dynamic:
                state["data"] = edited
            else:
                for column in allowed:
                    state["data"][column] = edited[column]
            state["epoch"] += 1
        return edited

    if dynamic:
        st.caption("Add or remove rows in the first tab. Changes in every tab are included when you save or download.")
    render_column_tabs(data, key, render)
    return state["data"].copy()
