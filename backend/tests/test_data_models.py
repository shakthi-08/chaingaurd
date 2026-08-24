from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Case, Wallet, Transaction, GraphEdge, Entity, Attribution, RiskIndicator, Finding, Evidence, Report


def test_models_can_be_created_and_persisted():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        case = Case(
            case_id="CASE-001",
            complaint_ref="COMP-123",
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        wallet = Wallet(
            address="0xabc",
            chain="ethereum",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            labels=["exchange", "suspicious"],
            case=case,
        )
        tx = Transaction(
            tx_hash="0xhash",
            from_address="0xsender",
            to_address="0xrecipient",
            value="1000000000000000000",
            token="ETH",
            timestamp=datetime.now(timezone.utc),
            block=123456,
        )
        edge = GraphEdge(
            source="0xsender",
            destination="0xrecipient",
            tx_ref="0xhash",
            value="1000000000000000000",
            timestamp=datetime.now(timezone.utc),
        )
        entity = Entity(entity_id="entity-1", type="exchange", name="Demo Exchange", source="manual")
        attribution = Attribution(
            wallet=wallet,
            entity=entity,
            confidence=0.82,
            reasons=["shared cluster"],
            source="manual_review",
        )
        risk = RiskIndicator(type="high_risk", score=0.75, evidence_ref="ev-1")
        finding = Finding(title="Suspicious flow", severity="high", confidence=0.8, evidence="evidence-1")
        evidence = Evidence(id="ev-1", type="transaction", source="manual", hash="abc123", timestamp=datetime.now(timezone.utc))
        report = Report(report_id="report-1", case=case, generated_at=datetime.now(timezone.utc), version="1.0")

        session.add_all([case, wallet, tx, edge, entity, attribution, risk, finding, evidence, report])
        session.commit()

        assert session.query(Case).count() == 1
        assert session.query(Wallet).count() == 1
        assert session.query(Transaction).count() == 1
        assert session.query(GraphEdge).count() == 1
        assert session.query(Entity).count() == 1
        assert session.query(Attribution).count() == 1
        assert session.query(RiskIndicator).count() == 1
        assert session.query(Finding).count() == 1
        assert session.query(Evidence).count() == 1
        assert session.query(Report).count() == 1
