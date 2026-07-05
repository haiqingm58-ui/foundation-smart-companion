from __future__ import annotations

import argparse
import json
from pathlib import Path

from server.application.config import load_settings
from server.application.database import create_database
from server.application.legacy_import import import_legacy_sqlite
from server.application.migrations import upgrade_database
from server.application.services.demo_accounts import create_demo_accounts


def main() -> None:
    parser = argparse.ArgumentParser(description="Foundation Smart Companion server maintenance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Upgrade the configured database to the latest revision")
    legacy = subparsers.add_parser("import-legacy", help="Import the previous SQLite database idempotently")
    legacy.add_argument("path", type=Path)
    demo = subparsers.add_parser("seed-demo-accounts", help="Create idempotent demo accounts for all roles")
    demo.add_argument("--count", type=int, default=6, choices=range(1, 51))
    args = parser.parse_args()

    settings = load_settings()
    if args.command == "migrate":
        upgrade_database(settings.database_url)
        print("Database migrations completed.")
        return

    if args.command == "seed-demo-accounts":
        upgrade_database(settings.database_url)
        result = create_demo_accounts(create_database(settings.database_url), count=args.count)
        print(json.dumps(result, ensure_ascii=False))
        return

    upgrade_database(settings.database_url)
    result = import_legacy_sqlite(args.path, create_database(settings.database_url))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
