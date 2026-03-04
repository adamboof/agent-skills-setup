#!/usr/bin/env python3
"""Create and verify minimal Codex overlay scaffolding.

This script intentionally creates directories only. File creation/rewrites are
handled separately to keep diffs small and deterministic.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_DIRECTORIES: tuple[Path, ...] = (
    REPO_ROOT / ".agents",
    REPO_ROOT / ".agents" / "skills",
    REPO_ROOT / ".codex",
)


def ensure_directories() -> int:
    """Create required overlay directories if missing."""
    for directory in REQUIRED_DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
    return 0


def check_directories() -> int:
    """Validate required overlay directories exist."""
    missing = [str(path.relative_to(REPO_ROOT)) for path in REQUIRED_DIRECTORIES if not path.is_dir()]

    if missing:
        print("Missing required overlay directories:")
        for item in missing:
            print(f"- {item}")
        return 1

    print("Overlay directory check passed.")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=("check",),
        help="Run validation instead of creating directories.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.command == "check":
        return check_directories()
    return ensure_directories()


if __name__ == "__main__":
    raise SystemExit(main())
