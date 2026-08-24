from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Case, Transaction, Wallet
from app.config import settings
from app.services.demo_case_seeder import seed_demo_case

client = TestClient(app)


def test_demo_case_seeding_creates_dashboard_data():
    assert seed_demo_case() is True

    with SessionLocal() as session:
        case = session.query(Case).filter(Case.case_id == "CASE-DEMO-001").one()
        assert case.complaint_ref == "CYBER-001-demo"
        assert len(case.wallets) == 5
        assert session.query(Transaction).count() == 4
        assert all("DEMO/SAMPLE" in wallet.labels for wallet in case.wallets)

    assert client.get("/cases/CASE-DEMO-001/transactions").json()
    assert client.get("/cases/CASE-DEMO-001/graph").json()["nodes"]


def test_demo_case_seeding_is_idempotent():
    assert seed_demo_case() is True
    with SessionLocal() as session:
        counts_before = (session.query(Case).count(), session.query(Wallet).count(), session.query(Transaction).count())

    assert seed_demo_case() is False
    with SessionLocal() as session:
        counts_after = (session.query(Case).count(), session.query(Wallet).count(), session.query(Transaction).count())

    assert counts_after == counts_before


def test_demo_seeder_does_not_overwrite_existing_case():
    with SessionLocal() as session:
        session.add(
            Case(
                case_id="CASE-DEMO-001",
                complaint_ref="USER-CREATED-REFERENCE",
                status="closed",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()

    assert seed_demo_case() is False
    with SessionLocal() as session:
        case = session.query(Case).filter(Case.case_id == "CASE-DEMO-001").one()
        assert case.complaint_ref == "USER-CREATED-REFERENCE"
        assert case.status == "closed"
        assert case.wallets == []


def test_demo_mode_startup_loads_configured_dashboard_case(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)

    with TestClient(app) as demo_client:
        transactions = demo_client.get("/cases/CASE-DEMO-001/transactions")
        graph = demo_client.get("/cases/CASE-DEMO-001/graph")

    assert transactions.status_code == 200
    assert len(transactions.json()) == 4
    assert graph.status_code == 200
    assert len(graph.json()["edges"]) == 4
