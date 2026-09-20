from __future__ import annotations

import pytest

from evalforge.db import configure_database, create_tables, session_factory


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    configure_database(f"sqlite:///{tmp_path / 'evalforge-test.db'}")
    create_tables()
    yield


@pytest.fixture
def db_session():
    session = session_factory()()
    try:
        yield session
    finally:
        session.close()
