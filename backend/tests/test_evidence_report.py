from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models import Evidence
from app.services.demo_case_seeder import seed_demo_case
from app.services.evidence_service import EvidenceService
from app.services.report_service import ReportService
from app.services.wallet_ingestion_service import WalletIngestionService

client = TestClient(app)


def setup_case():
    ingestion = WalletIngestionService()
    ingestion.ingest_wallet("CASE-REPORT-01", "0x1111111111111111111111111111111111111111", "ethereum")


def test_evidence_collection_is_traceable_and_deduplicated():
    setup_case()
    EvidenceService().collect_case("CASE-REPORT-01")
    first = EvidenceService().list_case("CASE-REPORT-01")
    EvidenceService().collect_case("CASE-REPORT-01")
    second = EvidenceService().list_case("CASE-REPORT-01")

    assert first
    assert second == first
    assert any(item["type"] == "transaction" for item in first)
    assert all(item["evidence_id"].startswith("EV-") for item in first)


def test_manual_evidence_creation_validates_references_and_is_idempotent():
    setup_case()
    payload = {
        "type": "investigator_note",
        "source": "manual_review",
        "timestamp": "2024-01-05T00:00:00Z",
        "description": "Reviewed synthetic transaction evidence.",
        "transaction_ref": "demo-eth-001",
        "wallet_ref": "0x1111111111111111111111111111111111111111",
        "reference": "review-001",
    }
    first = client.post("/cases/CASE-REPORT-01/evidence", json=payload)
    repeat = client.post("/cases/CASE-REPORT-01/evidence", json=payload)
    invalid = client.post("/cases/CASE-REPORT-01/evidence", json={**payload, "transaction_ref": "missing-tx"})

    assert first.status_code == 200
    assert repeat.status_code == 200
    assert first.json() == repeat.json()
    assert invalid.status_code == 400
    assert len(EvidenceService().list_case("CASE-REPORT-01")) == 1


def test_evidence_api_retrieves_case_evidence():
    setup_case()
    created = client.post(
        "/cases/CASE-REPORT-01/evidence",
        json={
            "type": "note",
            "source": "manual",
            "timestamp": "2024-01-05T00:00:00Z",
            "description": "Synthetic review note.",
            "wallet_ref": "0x1111111111111111111111111111111111111111",
        },
    )

    response = client.get("/cases/CASE-REPORT-01/evidence")
    assert created.status_code == 200
    assert response.status_code == 200
    assert response.json()[0]["description"] == "Synthetic review note."


def test_demo_report_is_valid_pdf_and_metadata_is_listed(tmp_path):
    seed_demo_case()
    service = ReportService(output_dir=tmp_path)
    output_path, metadata = service.generate("CASE-DEMO-001")

    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")
    reports = service.list_reports("CASE-DEMO-001")
    assert reports[0]["report_id"] == metadata["report_id"]
    assert reports[0]["filename"].endswith(".pdf")


def test_report_api_returns_pdf_and_missing_cases_are_rejected():
    setup_case()
    response = client.post("/cases/CASE-REPORT-01/report")
    missing_report = client.post("/cases/NO-SUCH-CASE/report")
    reports = client.get("/cases/CASE-REPORT-01/reports")
    missing_evidence = client.get("/cases/NO-SUCH-CASE/evidence")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert missing_report.status_code == 404
    assert reports.status_code == 200
    assert reports.json()
    assert missing_evidence.status_code == 404
