from __future__ import annotations

import argparse
import json
from pathlib import Path

from server.application.config import load_settings
from server.application.database import create_database
from server.application.legacy_import import import_legacy_sqlite
from server.application.migrations import upgrade_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Foundation Smart Companion server maintenance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Upgrade the configured database to the latest revision")
    legacy = subparsers.add_parser("import-legacy", help="Import the previous SQLite database idempotently")
    legacy.add_argument("path", type=Path)
    args = parser.parse_args()

    settings = load_settings()
    if args.command == "migrate":
        upgrade_database(settings.database_url)
        print("Database migrations completed.")
        return

    upgrade_database(settings.database_url)
    result = import_legacy_sqlite(args.path, create_database(settings.database_url))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
