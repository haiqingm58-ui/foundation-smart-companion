from __future__ import annotations

from sqlalchemy import text


def test_database_session_uses_isolated_database(database_url: str) -> None:
    from server.application.database import create_database

    database = create_database(database_url)
    with database.session() as session:
        session.execute(text("CREATE TABLE marker (value TEXT NOT NULL)"))
        session.execute(text("INSERT INTO marker (value) VALUES ('isolated')"))
        session.commit()

    with database.session() as session:
        assert session.execute(text("SELECT value FROM marker")).scalar_one() == "isolated"
