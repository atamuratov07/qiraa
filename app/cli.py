"""
uv run python -m app.cli make-admin <username>
uv run python -m app.cli import content/passages.yaml --common
uv run python -m app.cli import my.yaml --owner <username>   # passages or grammar
uv run python -m app.cli check content/passages.yaml   # needs no database
DATABASE_URL="postgresql://..." uv run python -m app.cli ...   # Neon
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.orm import Session

from app import models  # noqa: F401  registers every model before the first query
from app.auth.service import find_user, set_admin
from app.content import loader
from app.content.errors import ContentError, LineError, describe
from app.content.service import ImportedItem
from app.core.db import SessionLocal
from app.grammar.schemas import GrammarFile
from app.grammar.service import import_grammar
from app.passages.schemas import PassageFile
from app.passages.service import import_passages


class Args(argparse.Namespace):
    command: str = ""
    username: str = ""
    file: Path = Path()
    owner: str | None = None
    common: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    make_admin = commands.add_parser(
        "make-admin", help="let a user publish and edit common content"
    )
    make_admin.add_argument("username")

    import_ = commands.add_parser(
        "import",
        help="add the passages or grammar questions of a file, or update them by slug",
    )
    import_.add_argument("file", type=Path)
    scope = import_.add_mutually_exclusive_group(required=True)
    scope.add_argument("--owner", metavar="USERNAME", help="into this user's area")
    scope.add_argument("--common", action="store_true", help="as common content")

    check = commands.add_parser("check", help="validate a file without importing it")
    check.add_argument("file", type=Path)

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

        case "import":
            content = read(args.file)
            if content is None:
                return 1

            owner = None
            if args.owner is not None:
                owner = find_user(db, args.owner)
                if owner is None:
                    print(f"No user named {args.owner!r}.", file=sys.stderr)
                    return 1

            try:
                match content:
                    case PassageFile(passages=entries):
                        report = import_passages(
                            db, entries, owner=owner, common=args.common
                        )
                    case GrammarFile(grammar=entries):
                        report = import_grammar(
                            db, entries, owner=owner, common=args.common
                        )
            except ContentError as e:
                print_errors(args.file, e.errors)
                return 1

            print(summary("added", report.added))
            print(summary("updated", report.updated))

        case "check":
            content = read(args.file)
            if content is None:
                return 1

            match content:
                case PassageFile(passages=entries):
                    count, noun = len(entries), "passage"
                case GrammarFile(grammar=entries):
                    count, noun = len(entries), "grammar question"
            print(f"{args.file}: {count} {noun}{'' if count == 1 else 's'}, no errors")

        case _:
            raise AssertionError(f"unhandled command {args.command!r}")

    return 0


def read(path: Path) -> PassageFile | GrammarFile | None:
    try:
        return loader.parse_file(loader.decode(path.read_bytes()))
    except OSError as e:
        print(f"{path}: {e}", file=sys.stderr)
    except ContentError as e:
        print_errors(path, e.errors)
    return None


def print_errors(path: Path, errors: list[LineError]) -> None:
    """One line per error: `FILE:LINE: path: message`"""
    for error in errors:
        parts = [str(path) if error.line is None else f"{path}:{error.line}"]
        if error.path:
            parts.append(error.path)
        parts.append(describe(error))
        print(": ".join(parts), file=sys.stderr)


def summary(label: str, items: list[ImportedItem]) -> str:
    return f"{label} {len(items)}: {', '.join(i.slug for i in items) or '-'}"


def main(argv: Sequence[str] | None = None) -> int:
    args = parse(argv)
    with SessionLocal() as db:
        return run(db, args)


if __name__ == "__main__":
    sys.exit(main())
