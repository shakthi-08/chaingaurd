from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from fastapi.testclient import TestClient

from app.database import engine
from app.main import app
from app.services.attribution_service import AttributionService
from app.services.evidence_service import EvidenceService
from app.services.risk_analysis_service import RiskAnalysisService
from app.services.transaction_graph_service import TransactionGraphService
from app.services.wallet_ingestion_service import WalletIngestionService

CASE_ID = "CASE-SQLITE-CONCURRENCY"
SEED_WALLET = "0x1111111111111111111111111111111111111111"


def test_sqlite_uses_wal_and_busy_timeout():
    if engine.dialect.name != "sqlite":
        return
    with engine.connect() as connection:
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar()
        busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar()
    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) >= 30000


def _read_investigation_views() -> None:
    WalletIngestionService().get_case_wallets(CASE_ID)
    WalletIngestionService().get_case_transactions(CASE_ID)
    EvidenceService().list_case(CASE_ID)
    TransactionGraphService().trace_case_paths(CASE_ID, SEED_WALLET)


def _write_investigation_views() -> None:
    TransactionGraphService().build_case_graph(CASE_ID)
    RiskAnalysisService().analyze_case(CASE_ID)
    AttributionService().attribute_case(CASE_ID)
    EvidenceService().collect_case(CASE_ID)


def test_parallel_case_reads_do_not_lock():
    WalletIngestionService().ingest_wallet(CASE_ID, SEED_WALLET, "ethereum")
    _write_investigation_views()

    errors: list[str] = []

    def run(task):
        try:
            task()
        except OperationalError as exc:
            errors.append(str(exc))
            raise

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(run, _read_investigation_views) for _ in range(8)]
        futures.extend(pool.submit(run, _write_investigation_views) for _ in range(4))
        for future in as_completed(futures):
            future.result()

    assert errors == []


def test_parallel_attribution_requests_do_not_lock():
    WalletIngestionService().ingest_wallet(CASE_ID, SEED_WALLET, "ethereum")
    AttributionService().attribute_case(CASE_ID)

    errors: list[str] = []

    def run():
        try:
            AttributionService().attribute_case(CASE_ID)
        except OperationalError as exc:
            errors.append(str(exc))
            raise

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run) for _ in range(8)]
        for future in as_completed(futures):
            future.result()

    assert errors == []
    results = AttributionService().attribute_case(CASE_ID)
    assert isinstance(results, list)


def test_parallel_live_attribution_requests_do_not_lock():
    WalletIngestionService().ingest_wallet(CASE_ID, SEED_WALLET, "ethereum")
    test_client = TestClient(app)
    assert test_client.post(f"/cases/{CASE_ID}/analyze").status_code == 200

    def get_attributions():
        return test_client.get(f"/cases/{CASE_ID}/attributions")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(get_attributions) for _ in range(8)]
        responses = [future.result() for future in as_completed(futures)]

    assert all(response.status_code == 200 for response in responses)
