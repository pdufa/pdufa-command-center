"""Compact column tabs shared by the dashboard's tables and editors."""
from collections import OrderedDict
from hashlib import sha1
import inspect
import re

import pandas as pd
import streamlit as st
from stages import StageIndex, STAGE_HELP, DAYS_HELP, add_stage_column


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
        if "STAGE" in columns:
            ticker = next((c for c in columns if _name(c) == "ticker"), None)
            if ticker:
                columns.remove("STAGE")
                columns.insert(columns.index(ticker) + 1, "STAGE")
                if "DAYS TO PDUFA" in columns:
                    columns.remove("DAYS TO PDUFA")
                    columns.insert(columns.index("STAGE") + 1, "DAYS TO PDUFA")
        return OrderedDict([("Overview", [("Overview", columns)])])
    named = {_name(c): c for c in columns}
    controls = [c for c in columns if _name(c) in CONTROL_COLUMNS]
    identity = [named[n] for n in ("ticker", "stage", "days to pdufa", "drug") if n in named]
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


def _stage_sort_rank(value):
    """Approximate workflow order; the displayed label remains evidence-based."""
    label = str(value).upper()
    if label.startswith("FDA APPROVED") or label.startswith("FDA CRL"): return 110
    if "FDA DECISION PENDING" in label: return 100
    if "PDUFA / FDA REVIEW" in label: return 90
    if "FDA APPLICATION ACCEPTED" in label: return 80
    if "NDA/BLA SUBMITTED" in label: return 75
    if "2ND FINANCING CLOSED" in label: return 70
    if "FINANCING IN PROGRESS" in label: return 60
    if "FINANCING ANNOUNCED" in label: return 55
    if "PHASE 3 RESULTS" in label or "PHASE 3 COMPLETED" in label: return 50
    if "PHASE 3 ONGOING" in label: return 40
    if "PHASE 3" in label: return 35
    if "PHASE 2 COMPLETED" in label: return 20
    if "PHASE 2" in label: return 10
    return 999


def stage_filter_panel(data, key, source=None):
    """Select any combination of stages and sort without losing underlying rows."""
    staged = staged_table(data, source=source)
    if staged.empty or "STAGE" not in staged:
        return staged
    stages = staged["STAGE"].fillna("STAGE UNKNOWN — REVIEW").astype(str)
    options = sorted(stages.unique().tolist(), key=lambda value: (_stage_sort_rank(value), value))
    with st.expander("STAGE — MULTI-SELECT & SORT", expanded=True):
        selected = st.multiselect(
            "Show one or more stages", options, key=key + "_selected_stages",
            help="Select several stages together; leave blank to display every stage.",
        )
        order = st.selectbox(
            "Sort stage rows",
            ("Workflow: early to late", "Workflow: late to early", "Stage: A to Z", "Stage: Z to A",
             "Days to PDUFA: soonest first", "Days to PDUFA: latest first"),
            key=key + "_stage_order",
        )
        st.caption("Stages are evidence-based. Financing may overlap with clinical and FDA milestones. Select multiple stages to combine them.")
    result = staged.loc[stages.isin(selected)].copy() if selected else staged.copy()
    if result.empty:
        st.info("No rows match the selected stages.")
        return result
    if order.startswith("Workflow"):
        ranking = result["STAGE"].map(_stage_sort_rank)
        result = result.assign(_stage_rank=ranking).sort_values(
            ["_stage_rank", "STAGE"], ascending=[order.endswith("early to late"), True], kind="stable"
        ).drop(columns="_stage_rank")
    elif order.startswith("Stage"):
        result = result.sort_values("STAGE", ascending=order.endswith("A to Z"), kind="stable")
    elif "DAYS TO PDUFA" in result:
        result = result.sort_values(
            "DAYS TO PDUFA", ascending=order.endswith("soonest first"), na_position="last", kind="stable"
        )
    st.caption(f"Showing {len(result):,} of {len(staged):,} rows across {result['STAGE'].nunique():,} stage labels.")
    return result


def begin_table_render():
    st.session_state["_column_table_counts"] = {}


def set_stage_sources(records):
    st.session_state["_program_stage_index"] = StageIndex(records)


def staged_table(data, source=None):
    return add_stage_column(data, st.session_state.get("_program_stage_index"), source)


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
        if column == "STAGE":
            entry.update({"label": "STAGE", "help": STAGE_HELP})
        if column == "DAYS TO PDUFA":
            entry.update(st.column_config.NumberColumn("DAYS TO PDUFA", help=DAYS_HELP, format="%d", width="small"))
        entry["width"] = "small" if _name(column) in CONTROL_COLUMNS | {"ticker", "days to pdufa", "order", "n", "b", "p", "p%"} else "medium"
        result[column] = entry
    return result


def grouped_dataframe(data, **kwargs):
    data = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    data = staged_table(data, kwargs.pop("stage_source", None))
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
    data = staged_table(data, kwargs.pop("stage_source", None))
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
    blocked.update(c for c in ("STAGE", "DAYS TO PDUFA") if c in data)
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
