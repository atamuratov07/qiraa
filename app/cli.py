"""
uv run python -m app.cli make-admin <username>
DATABASE_URL="postgresql://..." uv run python -m app.cli make-admin <username>   # Neon
"""

import argparse
import sys
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app import models  # noqa: F401  registers every model before the first query
from app.auth.service import set_admin
from app.core.db import SessionLocal


class Args(argparse.Namespace):
    command: str = ""
    username: str = ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    make_admin = commands.add_parser(
        "make-admin", help="let a user publish and edit common content"
    )
    _ = make_admin.add_argument("username")

    return parser


def parse(argv: Sequence[str] | None = None) -> Args:
    return build_parser().parse_args(argv, namespace=Args())


def run(db: Session, args: Args) -> int:
    match args.command:
        case "make-admin":
            user = set_admin(db, args.username)
            if user is None:
                print(f"No user named {args.username!r}.", file=sys.stderr)
                return 1
            print(f"{user.username} is now an admin.")
        case _:
            raise AssertionError(f"unhandled command {args.command!r}")

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse(argv)
    with SessionLocal() as db:
        return run(db, args)


if __name__ == "__main__":
    sys.exit(main())
