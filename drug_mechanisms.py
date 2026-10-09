"""Evidence-labeled mechanism identification from explicitly named interventions.

Classification is only for named ingredients. It never identifies the lead
investigational asset in a multi-agent trial, and never determines drug approval.
"""
import re

# Ingredient, class, evidence for the ingredient's pharmacologic class.
KNOWN = (
    ("semaglutide", "GLP-1 receptor agonist",
     "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/209637s025lbl.pdf"),
    ("liraglutide", "GLP-1 receptor agonist",
     "https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=liraglutide"),
    ("dulaglutide", "GLP-1 receptor agonist",
     "https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=dulaglutide"),
    ("tirzepatide", "Dual GIP/GLP-1 receptor agonist",
     "https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/215866s009lbl.pdf"),
    ("somatropin", "Recombinant human growth hormone",
     "https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=somatropin"),
    ("insulin detemir", "Insulin analogue replacement",
     "https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=insulin%20detemir"),
    ("insulin degludec", "Insulin analogue replacement",
     "https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=insulin%20degludec"),
    ("insulin glargine", "Insulin analogue replacement",
     "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=d5e07a0c-7e14-4756-9152-9fea485d654a"),
    ("insulin aspart", "Insulin analogue replacement",
     "https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=insulin%20aspart"),
    ("dupilumab", "IL-4 receptor alpha antagonist",
     "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761055s057lbl.pdf"),
    ("upadacitinib", "Janus kinase inhibitor",
     "https://nctr-crs.fda.gov/fdalabel/ui/spl-summaries/criteria/380835"),
)
REGEXES = [
    (re.compile(r"(?<![A-Za-z0-9])" + re.escape(ingredient)
                + r"(?![A-Za-z0-9])", re.IGNORECASE),
     category, source)
    for ingredient, category, source in KNOWN
]

def classify_named_interventions(raw_name):
    """Return (class, evidence_url), or ('','') if no named ingredient found.

    Multiple distinct mechanisms are marked mixed instead of falsely
    pretending the pipeline has assigned an exact mechanism to the asset.
    """
    name = str(raw_name or "").strip()
    if not name or name.lower() in {"none", "nan", "<na>"}:
        return "", ""
    found = [(category, url) for regex, category, url in REGEXES
             if regex.search(name)]
    if not found:
        return "", ""
    classes = sorted({category for category, _ in found})
    if len(classes) > 1:
        return "Multiple named intervention mechanisms — review", ""
    return classes[0] + " (named ingredient)", found[0][1]
