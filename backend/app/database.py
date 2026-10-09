from __future__ import annotations

import threading

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url
_DB_INIT_LOCK = threading.Lock()
_DB_INITIALIZED = False


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
    # WAL is enabled once below. Changing journal_mode on every NullPool
    # connect requires an exclusive lock and causes "database is locked"
    # under concurrent FastAPI requests.
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def _enable_sqlite_wal(bind) -> None:
    with bind.connect() as connection:
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.exec_driver_sql("PRAGMA journal_mode=WAL")


if _is_sqlite(SQLALCHEMY_DATABASE_URL):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=NullPool,
        future=True,
    )
    event.listen(engine, "connect", _configure_sqlite_connection)
    try:
        _enable_sqlite_wal(engine)
    except Exception:
        pass
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, future=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)
Base = declarative_base()


def init_db() -> None:
    global _DB_INITIALIZED

    if _DB_INITIALIZED:
        return

    with _DB_INIT_LOCK:
        if _DB_INITIALIZED:
            return

        from app.models import (
            Attribution,
            Case,
            Entity,
            Evidence,
            Finding,
            GraphEdge,
            InvestigationAlert,
            LeaComplaint,
            Report,
            RiskIndicator,
            Transaction,
            Wallet,
        )

        Base.metadata.create_all(bind=engine)
        if engine.dialect.name == "sqlite":
            try:
                _enable_sqlite_wal(engine)
            except Exception:
                pass
            with engine.begin() as connection:
                migrations = {
                    "cases": {
                        "current_stage": "VARCHAR(64) NOT NULL DEFAULT 'CREATED'",
                        "progress": "INTEGER NOT NULL DEFAULT 0",
                        "error_message": "TEXT",
                    },
                    "transactions": {
                        "chain": "VARCHAR(64) NOT NULL DEFAULT 'ethereum'",
                        "contract_address": "VARCHAR(255)",
                        "tx_type": "VARCHAR(64)",
                    },
                    "graph_edges": {
                        "chain": "VARCHAR(64) NOT NULL DEFAULT 'ethereum'",
                        "relation_type": "VARCHAR(64)",
                    },
                    "entities": {
                        "known_wallet": "VARCHAR(255)",
                        "chain": "VARCHAR(64)",
                        "source_reliability": "FLOAT NOT NULL DEFAULT 0",
                        "confidence_metadata": "JSON",
                    },
                    "risk_indicators": {
                        "case_id": "VARCHAR(128)",
                        "severity": "VARCHAR(64) NOT NULL DEFAULT 'medium'",
                        "weight": "FLOAT NOT NULL DEFAULT 0",
                        "confidence": "FLOAT NOT NULL DEFAULT 0",
                        "explanation": "VARCHAR(1000)",
                        "transaction_refs": "JSON",
                        "wallet_addresses": "JSON",
                        "evidence_refs": "JSON",
                    },
                    "findings": {
                        "case_id": "VARCHAR(128)",
                        "type": "VARCHAR(128)",
                        "score": "FLOAT NOT NULL DEFAULT 0",
                        "explanation": "VARCHAR(1000)",
                        "transaction_refs": "JSON",
                        "wallet_addresses": "JSON",
                        "evidence_refs": "JSON",
                    },
                    "evidence": {
                        "case_id": "INTEGER",
                        "transaction_ref": "VARCHAR(255)",
                        "wallet_ref": "VARCHAR(255)",
                        "description": "VARCHAR(1000)",
                        "created_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
                    },
                    "attributions": {
                        "attribution_type": "VARCHAR(64)",
                        "status": "VARCHAR(64)",
                        "confidence_factors": "JSON",
                        "evidence_refs": "JSON",
                        "conflicting_evidence": "JSON",
                        "provenance": "VARCHAR(128)",
                    },
                    "reports": {
                        "file_path": "VARCHAR(500)",
                    },
                }
                for table_name, columns in migrations.items():
                    try:
                        existing_columns = {column["name"] for column in inspect(connection).get_columns(table_name)}
                    except Exception:
                        continue
                    for column_name, column_definition in columns.items():
                        if column_name not in existing_columns:
                            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))

                index_statements = [
                    "CREATE INDEX IF NOT EXISTS ix_transactions_from_address ON transactions (from_address)",
                    "CREATE INDEX IF NOT EXISTS ix_transactions_to_address ON transactions (to_address)",
                    "CREATE INDEX IF NOT EXISTS ix_graph_edges_tx_ref ON graph_edges (tx_ref)",
                    "CREATE INDEX IF NOT EXISTS ix_wallets_case_id ON wallets (case_id)",
                    "CREATE INDEX IF NOT EXISTS ix_transactions_chain ON transactions (chain)",
                    "CREATE INDEX IF NOT EXISTS ix_investigation_alerts_case_id ON investigation_alerts (case_id)",
                ]
                for statement in index_statements:
                    connection.execute(text(statement))

        _DB_INITIALIZED = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
