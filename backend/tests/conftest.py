import os
from pathlib import Path

import pytest

from app.config import settings

db_path = Path(__file__).resolve().parents[1] / "chainguard_test.db"
if db_path.exists():
    try:
        db_path.unlink()
    except (PermissionError, OSError):
        pass

os.environ["DATABASE_URL"] = "sqlite:///./chainguard_test.db"


@pytest.fixture(autouse=True)
def reset_environment_and_database(monkeypatch):
    from app.database import Base, engine

    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "environment", "demo")
    monkeypatch.setattr(settings, "blockchain_provider", "demo")
    monkeypatch.setattr(settings, "ai_provider", "none")
    monkeypatch.setattr(settings, "ai_model", None)
    monkeypatch.setattr(settings, "ai_api_key", None)
    monkeypatch.setattr(settings, "ai_base_url", None)
    monkeypatch.setattr(settings, "database_url", "sqlite:///./chainguard_test.db")

    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)
    yield
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)
