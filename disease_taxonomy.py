"""Conservative disease grouping and source-attributed population context.

The registry indication is always retained; group labels are navigation only.
Disease-wide counts are NOT estimates of trial eligibility or peak drug sales.
"""
import re

# Only explicit diseases are grouped. More specific disorders come before broad
# keywords to avoid classifying, e.g., pulmonary arterial hypertension as
# ordinary hypertension or diabetes insipidus as diabetes mellitus.
PATTERNS = (
    ("Epidermolysis bullosa", r"\bepidermolysis bullosa\b|\brdeb\b"),
    ("Mucopolysaccharidosis type III", r"\bmucopolysaccharidosis\s*(?:type\s*)?(?:iii[\s-]?[ab]|3[\s-]?[ab])\b"),
    ("Autism spectrum disorder", r"\bautism spectrum\b|\bautistic disorder\b"),
    ("Menopausal vasomotor symptoms", r"\bvasomotor symptoms\b|\bmenopaus(?:al|e) hot flash"),
    ("Onychomycosis", r"\bonychomycosis\b"),
    ("Prader-Willi syndrome", r"\bprader[\s-]*willi\b"),
    ("Duchenne muscular dystrophy", r"\bduchenne\b|\bdmd\b"),
    ("Amyotrophic lateral sclerosis (ALS)", r"\bamyotrophic lateral sclerosis\b|\bals\b|\blou gehrig"),
    ("Cystic fibrosis", r"\bcystic fibrosis\b"),
    ("Sickle cell disease", r"\bsickle[\s-]*cell\b"),
    ("Hemophilia", r"\bha?emophilia\b"),
    ("IgA nephropathy", r"\biga nephropathy\b|\bberger.?s disease\b"),
    ("Focal segmental glomerulosclerosis", r"\bfsgs\b|\bfocal segmental glomerulosclerosis\b"),
    ("Pulmonary arterial hypertension", r"\bpulmonary arterial hypertension\b|\bpah\b"),
    ("Intracranial hypertension", r"\bintracranial hypertension\b"),
    ("Diabetes insipidus", r"\bdiabetes insipidus\b"),
    ("Congenital adrenal hyperplasia", r"\bcongenital adrenal hyperplasia\b"),
    ("Idiopathic pulmonary fibrosis", r"\bidiopathic pulmonary fibrosis\b|\bipf\b"),
    ("Spinal muscular atrophy", r"\bspinal muscular atrophy\b"),
    ("Multiple sclerosis", r"\bmultiple sclerosis\b"),
    ("Parkinson's disease", r"\bparkinson"),
    ("Alzheimer's disease", r"\balzheimer"),
    ("Epilepsy", r"\bepileps|\bseizure"),
    ("Schizophrenia", r"\bschizophren"),
    ("Major depression", r"\bdepressi|\bmajor depressive\b|\bmdd\b"),
    ("Anxiety disorders", r"\banxiety\b|\bgeneralized anxiety\b"),
    ("Bipolar disorder", r"\bbipolar\b"),
    ("Migraine", r"\bmigraine"),
    ("Obesity", r"\bobes\b|\bobesity\b"),
    ("Overweight", r"\boverweight\b"),
    ("Weight management (unspecified)", r"\bweight management\b"),
    ("Type 1 diabetes", r"\btype[ -]?1[ -]?(?:diabetes|diabetic|dm)\b|\bdiabetes(?: mellitus)?[ ,]+type[ -]?1\b|\bt1dm\b"),
    ("Type 2 diabetes", r"\btype[ -]?2[ -]?(?:diabetes|diabetic|dm)\b|\bdiabetes(?: mellitus)?[ ,]+type[ -]?2\b|\bt2dm\b"),
    ("Diabetes", r"\bdiabetes\b|\bdiabetic\b"),
    ("Hypertension", r"\bhypertension\b|\bhigh blood pressure\b"),
    ("Heart failure", r"\bheart failure\b|\bcardiac failure\b"),
    ("Atrial fibrillation", r"\batrial fibrillation\b"),
    ("Coronary artery disease", r"\bcoronary artery disease\b"),
    ("Hypercholesterolemia / dyslipidemia", r"\bhypercholesterol\b|\bdyslipid|\bhyperlipid"),
    ("Chronic kidney disease", r"\bchronic kidney disease\b|\bchronic renal disease\b|\brenal insufficiency\b|\bckd\b"),
    ("Chronic obstructive pulmonary disease (COPD)", r"\bchronic obstructive pulmonary\b|\bcopd\b|\bemphysema\b"),
    ("Asthma", r"\basthma"),
    ("Atopic dermatitis", r"\batopic dermatitis\b|\beczema\b|\bdermatitis atopic\b"),
    ("Psoriasis", r"\bpsoriasis\b|\bplaque psorias"),
    ("Rheumatoid arthritis", r"\brheumatoid arthritis\b"),
    ("Osteoarthritis", r"\bosteoarthritis\b"),
    ("Psoriatic arthritis", r"\bpsoriatic arthritis\b"),
    ("Crohn's disease", r"\bcrohn"),
    ("Ulcerative colitis", r"\bulcerative colitis\b"),
    ("Inflammatory bowel disease", r"\binflammatory bowel disease\b"),
    ("MASH / fatty liver disease", r"\bmash\b|\bnash\b|\bsteatohepatitis\b|\bmetabolic dysfunction.associated steatotic liver\b|\bfatty liver"),
    ("Hepatitis B", r"\bhepatitis b\b|\bhepatitis b virus\b|\bhbv\b"),
    ("Hepatitis C", r"\bhepatitis c\b|\bhepatitis c virus\b|\bhcv\b"),
    ("HIV", r"\bhiv\b|\baids\b"),
    ("COVID-19", r"\bcovid[\s-]*19\b|\bsars[\s-]*cov[\s-]*2\b"),
    ("Influenza", r"\binfluenza\b"),
    ("Urinary tract infection", r"\burinary tract infection\b|\bpyelonephritis\b|\bcuti\b"),
    ("Breast cancer", r"\bbreast cancer\b|\bbreast neoplasm"),
    ("Non-small cell lung cancer", r"\bnon[\s-]*small[\s-]*cell lung\b|\bnsclc\b|\bcarcinoma, non.small.cell lung\b"),
    ("Small cell lung cancer", r"(?<!non-)(?<!non )\bsmall[\s-]*cell lung cancer\b|\bsclc\b"),
    ("Prostate cancer", r"\bprostate cancer\b|\bprostate neoplasm"),
    ("Colorectal cancer", r"\bcolorectal\b|\bcolon cancer\b|\brectal cancer\b"),
    ("Pancreatic cancer", r"\bpancreatic cancer\b|\bpancreatic adenocarcinoma\b"),
    ("Melanoma", r"\bmelanoma\b"),
    ("Multiple myeloma", r"\bmultiple myeloma\b"),
    ("Acute myeloid leukemia", r"\bacute myeloid leuk"),
    ("Chronic lymphocytic leukemia", r"\bchronic lymphocytic leuk"),
    ("Hepatocellular carcinoma", r"\bhepatocellular carcinoma\b|\bcarcinoma,?\s*hepatocellular\b"),
    ("Ovarian cancer", r"\bovarian cancer\b|\bovarian neoplasm"),
    ("Cancer — other / multi-tumor", r"\bsolid tumors?\b|\bmalignant neoplasm\b|\badvanced cancer\b|\boncolog"),
    ("Pain / neuropathy", r"\bneuropathic pain\b|\bperipheral neuropath\b|\bchronic pain\b|\bacute pain\b"),
    ("Healthy volunteers / no disease", r"^healthy\b|^normal volunteers?\b|^healthy participants?\b"),
)
COMPILED = [(name, re.compile(rx, re.I)) for name, rx in PATTERNS]

# Numbers refer to the WHO/CDC population DEFINITION and vintage specified here,
# not patients eligible for any one investigational agent. Empty == not verified.
# For obesity, the US source is a percentage, not a headcount.
BURDEN = {
    "Hypertension": {
        "world_people": 1400000000, "us_people": 119900000,
        "year": "Worldwide 2024; US 2021–2023",
        "definition": "Adults; different WHO and CDC hypertension thresholds",
        "source": "https://www.who.int/news-room/fact-sheets/detail/hypertension",
        "us_source": "https://www.cdc.gov/high-blood-pressure/data-research/facts-stats/",
    },
    "Obesity": {
        "world_people": 890000000, "us_percent": "40.3% of US adults",
        "year": "Worldwide 2022; US Aug 2021–Aug 2023",
        "definition": "Adults with obesity (not everyone eligible for treatment)",
        "source": "https://www.who.int/news-room/fact-sheets/detail/malnutrition",
        "us_source": "https://www.cdc.gov/nchs/products/databriefs/db508.htm",
    },
    "Diabetes": {
        "world_people": 830000000, "us_people": 40100000,
        "year": "Worldwide 2022; US 2023",
        "definition": "All diabetes types combined, not type 2 alone",
        "source": "https://www.who.int/en/news-room/fact-sheets/detail/diabetes",
        "us_source": "https://www.cdc.gov/diabetes/php/data-research/",
    },
    "Osteoarthritis": {
        "world_people": 528000000, "year": "Worldwide 2019",
        "definition": "All osteoarthritis sites, not one joint/indication",
        "source": "https://www.who.int/news-room/fact-sheets/detail/osteoarthritis",
    },
    "Anxiety disorders": {
        "world_people": 359000000, "year": "Worldwide 2021",
        "definition": "All anxiety disorders, not a single subtype",
        "source": "https://www.who.int/en/news-room/fact-sheets/detail/anxiety-disorders",
    },
    "Major depression": {
        "world_people": 332000000, "year": "Worldwide (WHO 2025)",
        "definition": "Broad depression estimate, not limited to trial-defined MDD",
        "source": "https://www.who.int/westernpacific/newsroom/fact-sheets/detail/depression",
    },
    "Asthma": {
        "world_people": 262000000, "us_people": 27807000,
        "year": "Worldwide 2019; US 2023",
        "definition": "Current asthma, all severities and ages",
        "source": "https://www.who.int/groups/global-alliance-against-chronic-respiratory-diseases-%28gard%29/terms-of-reference",
        "us_source": "https://www.cdc.gov/asthma/most_recent_data.htm",
    },
    "Hepatitis B": {
        "world_people": 254000000, "year": "Worldwide 2022",
        "definition": "Chronic hepatitis B infection only",
        "source": "https://www.who.int/teams/global-hiv-hepatitis-and-stis-programmes/hepatitis/testing-and-diagnostics",
    },
    "Chronic obstructive pulmonary disease (COPD)": {
        "world_people": 212000000, "us_people": 16000000,
        "year": "Worldwide 2019; US CDC 2024 publication",
        "definition": "COPD; US figure approximately diagnosed adults",
        "source": "https://www.who.int/groups/global-alliance-against-chronic-respiratory-diseases-%28gard%29/terms-of-reference",
        "us_source": "https://www.cdc.gov/copd/about/index.html",
    },
    "Hepatitis C": {
        "world_people": 50000000, "year": "Worldwide 2022",
        "definition": "Chronic hepatitis C infection",
        "source": "https://www.who.int/teams/global-hiv-hepatitis-and-stis-programmes/hepatitis/testing-and-diagnostics",
    },
    "HIV": {
        "world_people": 40800000, "year": "Worldwide 2024",
        "definition": "People living with HIV, all ages",
        "source": "https://www.who.int/data/gho/data/themes/hiv-aids/GHO/hiv-aids",
    },
    "Chronic kidney disease": {
        "us_people": 35500000, "year": "US 2023",
        "definition": "All CKD stages; not any single renal indication",
        "source": "https://www.cdc.gov/cdi/indicator-definitions/chronic-kidney-disease.html",
    },
    "Type 1 diabetes": {
        "us_people": 2100000, "year": "US 2023",
        "definition": "Diagnosed type 1 diabetes, all ages; not all trial-eligible",
        "us_source": "https://usdss.cdc.gov/diabetes/report.html",
    },
    "Heart failure": {
        "us_people": 6700000, "year": "CDC summary published 2024",
        "definition": "U.S. adults age 20+ with heart failure",
        "us_source": "https://www.cdc.gov/heart-disease/about/heart-failure.html",
    },
    "Rheumatoid arthritis": {
        "world_people": 18000000, "year": "Worldwide 2019",
        "definition": "All rheumatoid arthritis",
        "source": "https://www.who.int/news-room/fact-sheets/detail/rheumatoid-arthritis",
    },
}

# These are disease categories commonly considered rare; not evidence of a
# particular drug's FDA Orphan Drug Designation.
RARE_CATEGORIES = {
    "Prader-Willi syndrome", "Duchenne muscular dystrophy",
    "Amyotrophic lateral sclerosis (ALS)", "Cystic fibrosis",
    "Sickle cell disease", "Hemophilia", "IgA nephropathy",
    "Focal segmental glomerulosclerosis", "Congenital adrenal hyperplasia",
    "Spinal muscular atrophy",
}


def group_indication(indication, curated_issue=""):
    """Return a useful disease group without discarding the exact indication."""
    raw = str(indication or "").strip()
    if raw.lower() in {"nan", "none", "<na>"}:
        raw = ""
    curated = str(curated_issue or "").strip()
    # Registry condition first; curated issue is fallback for missing indications.
    for source in (raw, curated):
        if not source:
            continue
        for label, pattern in COMPILED:
            if pattern.search(source):
                return label
    if not raw and not curated:
        return "Indication not recorded"
    # Keep unrecognized diseases findable; never lump everything into an
    # undifferentiated "Other" bucket.
    first = (raw or curated).split("|", 1)[0].strip()
    first = re.sub(r"\s+", " ", first).strip()
    return first[:105] if first else "Indication not recorded"


def group_indications(indication, curated_issue=""):
    """List all explicit disease groups on one registered trial, uniquely.

    A trial can legitimately study multiple conditions: group associations
    may exceed trial counts, but no source records are created or deleted.
    Specific diabetes types supersede broad untyped diabetes; a healthy
    control does not become a patient indication when disease is also listed.
    """
    raw = str(indication or "").strip()
    if raw.lower() in {"nan", "none", "<na>"}:
        raw = ""
    # Capture explicit matches across the full free-text indication first.
    # Use them instead of thousands of differing pipe-separated synonyms.
    seen = []
    for label, pattern in COMPILED:
        if pattern.search(raw) and label not in seen:
            seen.append(label)
    specifics = {"Type 1 diabetes", "Type 2 diabetes", "Diabetes insipidus"}
    if seen and "Diabetes" in seen and specifics.intersection(seen):
        seen.remove("Diabetes")
    if "Hypertension" in seen and (
        "Pulmonary arterial hypertension" in seen
        or "Intracranial hypertension" in seen
    ):
        seen.remove("Hypertension")
    specific_cancers = {"Breast cancer", "Non-small cell lung cancer",
        "Small cell lung cancer", "Prostate cancer", "Colorectal cancer",
        "Pancreatic cancer", "Melanoma", "Multiple myeloma",
        "Acute myeloid leukemia", "Chronic lymphocytic leukemia",
        "Hepatocellular carcinoma", "Ovarian cancer"}
    if "Cancer — other / multi-tumor" in seen and specific_cancers.intersection(seen):
        seen.remove("Cancer — other / multi-tumor")
    if "Healthy volunteers / no disease" in seen and len(seen) > 1:
        seen.remove("Healthy volunteers / no disease")
    if "Weight management (unspecified)" in seen and (
        "Obesity" in seen or "Overweight" in seen
    ):
        seen.remove("Weight management (unspecified)")
    if seen:
        return tuple(seen)
    return (group_indication(raw, curated_issue),)


def burden_for(issue):
    return BURDEN.get(issue, {})


def population_label(value):
    if not value:
        return "Not verified"
    if value >= 1000000000:
        return f"{value/1000000000:g}B"
    if value >= 1000000:
        return f"{value/1000000:g}M"
    return f"{value:,}"
