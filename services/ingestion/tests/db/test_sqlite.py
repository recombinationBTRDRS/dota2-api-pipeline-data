#services/ingestion/tests/db/test_sqlite.py
from services.ingestion.db.sqlite import init_db


def test_init_db():
    init_db()
    assert True