import os
from pathlib import Path

import pytest

db_path = Path(__file__).resolve().parents[1] / "chainguard_test.db"
if db_path.exists():
	db_path.unlink()

os.environ["DATABASE_URL"] = "sqlite:///./chainguard_test.db"


@pytest.fixture(autouse=True)
def reset_database():
	from app.database import Base, engine

	Base.metadata.drop_all(bind=engine)
	Base.metadata.create_all(bind=engine)
	yield
	Base.metadata.drop_all(bind=engine)
	Base.metadata.create_all(bind=engine)
