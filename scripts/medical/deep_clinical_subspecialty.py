"""Conservative disease-specialty dossier router for independent medical intelligence.

Routing is not clinical adjudication and never changes trial membership or predictions.
Ambiguous or unsupported indications require manual review.
"""
import re

SPECIALTIES = {
    "oncology": ("cancer", "carcinoma", "melanoma", "leukemia", "lymphoma", "myeloma", "neoplasm", "tumor"),
    "neurology": ("alzheimer", "parkinson", "multiple sclerosis", "epilepsy", "migraine", "amyotrophic lateral sclerosis"),
    "cardiology": ("heart failure", "cardiomyopathy", "atrial fibrillation", "coronary artery"),
    "hematology": ("hemophilia", "sickle cell", "thalassemia", "anemia"),
    "endocrinology": ("diabetes", "obesity", "thyroid"),
    "pulmonology": ("asthma", "copd", "pulmonary fibrosis"),
    "infectious_disease": ("hiv", "hepatitis", "influenza", "tuberculosis"),
    "rheumatology": ("rheumatoid arthritis", "lupus", "psoriatic arthritis"),
    "dermatology": ("psoriasis", "atopic dermatitis", "hidradenitis"),
    "gastroenterology": ("crohn", "ulcerative colitis", "cirrhosis"),
    "nephrology": ("chronic kidney disease", "glomerulonephritis", "iga nephropathy"),
    "ophthalmology": ("macular degeneration", "diabetic retinopathy", "glaucoma"),
    "psychiatry": ("schizophrenia", "major depressive disorder", "bipolar disorder"),
}
REVIEW_DIMENSIONS = (
    "disease_subtype_and_diagnostic_criteria",
    "current_standard_of_care_and_comparator",
    "endpoint_validity_and_clinical_meaning",
    "population_generalizability",
    "magnitude_and_durability_of_benefit",
    "specialty_specific_safety",
    "unmet_need_and_alternatives",
    "regulatory_precedent_and_uncertainties",
)

def route(indication, nct=None):
    if not isinstance(indication, str):
        raise TypeError("indication must be text")
    normalized = re.sub(r"\s+", " ", indication.casefold()).strip()
    matches = sorted(
        name for name, terms in SPECIALTIES.items()
        if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized) for term in terms)
    )
    return {
        "nct": nct,
        "indication": indication,
        "specialtyCandidates": matches,
        "routingStatus": "REQUIRES_SPECIALIST_REVIEW" if len(matches) != 1 else "PROVISIONAL_SINGLE_SPECIALTY",
        "reviewDimensions": list(REVIEW_DIMENSIONS),
        "reviewStatus": "NOT_ADJUDICATED",
        "sourceEvidence": [],
        "specialistJudgment": None,
        "fdaOutcomePrediction": None,
        "fdaTimingPrediction": None,
    }
