"""Offline FDA bytes provenance audit: fingerprint != adjudicated FDA truth."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_hop_fda_pdf_bytes.py"
spec = spec_from_file_location("fda_pdf_bytes_test", SCRIPT)
mod = module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic_pdf():
    # Not an authentic PDF; this tests header/EOF/size/hash behavior only.
    return b"%PDF-1.7\n" + b"A" * 1100 + b"\n%%EOF\n"


def test_synthetic_bytes_hash_never_certifies_original():
    x = mod.inspect_local_pdf(synthetic_pdf())
    assert len(x["sha256"]) == 64
    assert x["byteLength"] == len(synthetic_pdf())
    assert x["status"] == "BYTES_HASHED_NEEDS_IDENTITY_AND_CHRONOLOGY_REVIEW"
    assert x["originalLetterIndependentlyAdjudicated"] is False
    assert x["modelEligible"] is False
    assert x["approvalProbability"] is None


@pytest.mark.parametrize("broken", [
    b"",
    b"%PDF-1.7" + b"A" * 1000,
    b"A" * 3000 + b"%%EOF",
    b"%PDF-1.7" + b"A" * 50 + b"%%EOF",
    b"%PDF-1.7" + b"A" * (51 * 1024 * 1024) + b"%%EOF",
])
def test_invalid_local_source_files_rejected(broken):
    with pytest.raises(ValueError):
        mod.inspect_local_pdf(broken)


def test_a_local_filename_or_fake_pdf_cannot_certify_official_origin(tmp_path):
    f = tmp_path / "CRL_BLA761303Original1_20240322.pdf"
    f.write_bytes(synthetic_pdf())
    x = mod.audit_file("BLA761303_ORIGINAL_1_20240322_CRL", f)
    assert x["expectedOfficialUrl"].startswith("https://download.open.fda.gov/crl/")
    assert x["sourceFileClaimsOfficialOrigin"] is False
    assert x["downloadOriginProvenByByteHash"] is False
    assert x["originalLetterIndependentlyAdjudicated"] is False
    assert x["modelEligible"] is False


def test_unknown_identity_rejected(tmp_path):
    f = tmp_path / "letter.pdf"
    f.write_bytes(synthetic_pdf())
    with pytest.raises(ValueError, match="Unknown"):
        mod.audit_file("BLA999999_ORIGINAL_1_20240322_CRL", f)


def test_symlink_not_accepted_as_direct_evidence(tmp_path):
    original = tmp_path / "letter.pdf"
    original.write_bytes(synthetic_pdf())
    linked = tmp_path / "alias.pdf"
    linked.symlink_to(original)
    with pytest.raises(ValueError, match="regular"):
        mod.audit_file("NDA213973_ORIGINAL_1_20200515_APPROVED", linked)
