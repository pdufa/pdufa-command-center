"""Optional Streamlit scientific assessment panel; no mutation of GEM presets."""
import streamlit as st
from scientific_assessment import DOMAINS, assess

def render_scientific_assessment(trial_id: str, evidence: dict | None = None):
    """Render trial-specific scientific evidence without inferring values from ticker."""
    st.subheader("Scientific Assessment")
    if not trial_id or not str(trial_id).strip():
        st.warning("A verified trial identity is required.")
        return
    st.caption(f"Trial: {trial_id} · Evidence-based assessment, not FDA approval probability")
    result = assess(evidence or {})
    st.info("Complete" if result["status"] == "complete" else "Insufficient verified evidence — no overall score")
    for domain, fields in DOMAINS.items():
        data = result["domains"][domain]
        with st.expander(f"{domain.replace('_', ' ').title()} · {data['verified_fields']}/{data['required_fields']} verified"):
            st.write("Domain score:", data["score"] if data["score"] is not None else "Not available")
            for field in fields:
                item = (evidence or {}).get(f"{domain}.{field}", {})
                st.write(field.replace("_", " ").title(), "—", item.get("status", "missing"))
                if item.get("source_url"):
                    st.caption(item["source_url"])
                if item.get("rationale"):
                    st.caption(item["rationale"])
    st.caption("Scientific assessments remain separate from PIPELINE, GEM JR and GEM preset restrictions.")
