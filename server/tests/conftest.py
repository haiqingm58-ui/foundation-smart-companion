from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("FOUNDATION_DATABASE_URL", url)
    return url
