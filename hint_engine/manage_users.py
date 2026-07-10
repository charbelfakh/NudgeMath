"""CLI to manage NudgeMath admin accounts — keeps credentials out of code/git.

    python -m hint_engine.manage_users add <username> [--password PW]
    python -m hint_engine.manage_users list
    python -m hint_engine.manage_users remove <username>

``add`` prompts for the password interactively (via getpass) unless ``--password``
is given for scripting. Accounts persist to ``NUDGEMATH_USERS_PATH`` (default
``.nudgemath/users.json``, gitignored).
"""

from __future__ import annotations

import argparse
import getpass
import sys
import time

from hint_engine.auth import hash_password
from hint_engine.user_store import (
    UserRecord,
    UserStore,
    build_user_store,
    default_users_path,
    normalize_username,
)


def _add(args: argparse.Namespace, store: UserStore) -> int:
    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Confirm password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
    if not password:
        print("Password must not be empty.", file=sys.stderr)
        return 1
    username = normalize_username(args.username)
    existed = store.get(username) is not None
    store.put(
        UserRecord(
            username=username,
            password_hash=hash_password(password),
            role="admin",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
    )
    print(f"{'Updated' if existed else 'Created'} admin '{username}' in {default_users_path()}")
    return 0


def _list(args: argparse.Namespace, store: UserStore) -> int:
    names = store.list_usernames()
    if not names:
        print(f"No admin accounts yet ({default_users_path()}).")
        return 0
    for name in names:
        print(name)
    return 0


def _remove(args: argparse.Namespace, store: UserStore) -> int:
    username = normalize_username(args.username)
    if not store.delete(username):
        print(f"No such admin: {username}", file=sys.stderr)
        return 1
    print(f"Removed admin '{username}'.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hint_engine.manage_users")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="create or update an admin account")
    add.add_argument("username")
    add.add_argument("--password", help="set non-interactively (else prompt)")
    add.set_defaults(func=_add)

    lst = sub.add_parser("list", help="list admin usernames")
    lst.set_defaults(func=_list)

    rem = sub.add_parser("remove", help="remove an admin account")
    rem.add_argument("username")
    rem.set_defaults(func=_remove)

    args = parser.parse_args(argv)
    return args.func(args, build_user_store())


if __name__ == "__main__":
    raise SystemExit(main())
