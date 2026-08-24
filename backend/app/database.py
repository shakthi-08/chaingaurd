from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    from app.models import (
        Attribution,
        Case,
        Entity,
        Evidence,
        Finding,
        GraphEdge,
        Report,
        RiskIndicator,
        Transaction,
        Wallet,
    )

    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            migrations = {
                "transactions": {
                    "chain": "VARCHAR(64) NOT NULL DEFAULT 'ethereum'",
                },
                "graph_edges": {
                    "chain": "VARCHAR(64) NOT NULL DEFAULT 'ethereum'",
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
                "reports": {
                    "file_path": "VARCHAR(500)",
                },
            }
            for table_name, columns in migrations.items():
                existing_columns = {column["name"] for column in inspect(connection).get_columns(table_name)}
                for column_name, column_definition in columns.items():
                    if column_name not in existing_columns:
                        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
