from __future__ import annotations

import argparse
import json
from pathlib import Path

from alembic.util import CommandError
from sqlalchemy.exc import SQLAlchemyError

from server.application.config import load_settings
from server.application.database import create_database
from server.application.legacy_import import import_legacy_sqlite
from server.application.migrations import upgrade_database
from server.application.services.demo_accounts import create_demo_accounts
from server.application.services.question_bank_import import QuestionBankImportError, import_question_bank


def _error(code: str, message: str) -> int:
    print(json.dumps({"error": {"code": code, "message": message}}, ensure_ascii=False, sort_keys=True))
    return 2 if code == "QUESTION_BANK_IMPORT_INVALID" else 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Foundation Smart Companion server maintenance")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="Upgrade the configured database to the latest revision")
    legacy = subparsers.add_parser("import-legacy", help="Import the previous SQLite database idempotently")
    legacy.add_argument("path", type=Path)
    question_bank = subparsers.add_parser("import-question-bank", help="Import a shared question-bank manifest idempotently")
    question_bank.add_argument("manifest", type=Path)
    demo = subparsers.add_parser("seed-demo-accounts", help="Create idempotent demo accounts for all roles")
    demo.add_argument("--count", type=int, default=6, choices=range(1, 51))
    args = parser.parse_args(argv)

    settings = load_settings()
    if args.command == "migrate":
        upgrade_database(settings.database_url)
        print("Database migrations completed.")
        return 0

    if args.command == "seed-demo-accounts":
        upgrade_database(settings.database_url)
        result = create_demo_accounts(create_database(settings.database_url), count=args.count)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.command == "import-question-bank":
        try:
            upgrade_database(settings.database_url)
            result = import_question_bank(create_database(settings.database_url), args.manifest, None)
        except QuestionBankImportError as error:
            return _error("QUESTION_BANK_IMPORT_INVALID", str(error))
        except (CommandError, OSError, SQLAlchemyError):
            return _error("QUESTION_BANK_DATABASE_FAILED", "题库导入数据库操作失败")
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
        return 0

    upgrade_database(settings.database_url)
    result = import_legacy_sqlite(args.path, create_database(settings.database_url))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
