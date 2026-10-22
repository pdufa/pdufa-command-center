"""Read-only reconciliation evidence validation regressions."""
import unittest
from datetime import date, timedelta

from sqlalchemy import create_engine, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.reconciliation_review import ReviewItem, ReviewPackage, validate_review_package


class Base(DeclarativeBase):
    pass


class Identity(Base):
    __tablename__ = "identities_test"
    source_key: Mapped[str] = mapped_column(String(512), primary_key=True)


class ReconciliationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def validate(self, url="https://clinicaltrials.gov/study/NCT00000001", reviewed=None, key="missing"):
        payload = ReviewPackage(
            schemaVersion=1, kind="pdufa-reconciliation-review-export",
            records=[ReviewItem(programKey="TEST|drug|indication", status="confirmed",
                                evidenceUrl=url, reviewedOn=reviewed or date.today().isoformat(),
                                exactSourceKey=key)],
        )
        return validate_review_package(payload, self.engine, Identity)

    def test_unmapped_identity_cannot_be_approved(self):
        self.assertEqual(self.validate()["records"][0]["outcome"], "UNMAPPED_EXACT_IDENTITY")

    def test_future_date_is_invalid(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(self.validate(reviewed=tomorrow)["records"][0]["outcome"], "INVALID_EVIDENCE")

    def test_whitespace_url_is_invalid(self):
        self.assertEqual(self.validate(url="https://clinicaltrials.gov/study/NCT00000001 extra")["records"][0]["outcome"], "INVALID_EVIDENCE")

    def test_http_url_is_invalid(self):
        self.assertEqual(self.validate(url="http://clinicaltrials.gov/study/NCT00000001")["records"][0]["outcome"], "INVALID_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
