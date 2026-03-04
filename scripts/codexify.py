#!/usr/bin/env python3
"""codexify: sync Codex skill symlinks from .claude/skills.

Usage:
  python scripts/codexify.py
      Create or update `.agents/skills/<skill>` symlinks so each points to
      `../../.claude/skills/<skill>`, and ensure `.codex/` exists.

  python scripts/codexify.py --check
      Validate that all expected symlinks exist and point to the expected
      relative target, and verify required overlay directories exist,
      without mutating the filesystem.

  python scripts/codexify.py check
      Alias for `--check` for compatibility with repository docs.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


REQUIRED_DIRS = (".agents", ".agents/skills", ".codex")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Codex skills symlinks from .claude/skills")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("check",),
        help="Optional positional alias for --check",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate symlink state only (no filesystem changes)",
    )
    return parser.parse_args()


def iter_skill_dirs(skills_root: Path) -> list[Path]:
    return sorted((path for path in skills_root.iterdir() if path.is_dir()), key=lambda path: path.name)


def ensure_link(path: Path, target: str) -> str:
    if path.is_symlink() and path.readlink().as_posix() == target:
        return f"OK: {path} -> {target}"

    if path.exists() or path.is_symlink():
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()

    path.symlink_to(target)
    return f"UPDATED: {path} -> {target}"


def validate_link(path: Path, target: str) -> str | None:
    if not path.exists() and not path.is_symlink():
        return f"MISSING: {path} (expected symlink to {target})"

    if not path.is_symlink():
        return f"INCORRECT: {path} exists but is not a symlink"

    actual = path.readlink().as_posix()
    if actual != target:
        return f"INCORRECT: {path} -> {actual} (expected {target})"

    return None


def main() -> int:
    args = parse_args()
    check_mode = args.check or args.command == "check"

    repo_root = Path(__file__).resolve().parent.parent
    source_root = repo_root / ".claude" / "skills"
    dest_root = repo_root / ".agents" / "skills"

    if not source_root.exists() or not source_root.is_dir():
        print(f"ERROR: Source skills directory not found: {source_root}")
        return 2

    skill_dirs = iter_skill_dirs(source_root)
    if not skill_dirs:
        print(f"ERROR: No skill directories found in {source_root}")
        return 2

    issues: list[str] = []

    for rel_dir in REQUIRED_DIRS:
        directory = repo_root / rel_dir
        if check_mode:
            if not directory.exists() or not directory.is_dir():
                issues.append(f"MISSING: {directory} (run without --check to create it)")
        else:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"ENSURED: {directory}")

    if check_mode and (not dest_root.exists() or not dest_root.is_dir()):
        for issue in issues:
            print(issue)
        print(f"CHECK FAILED: {len(issues)} issue(s) found")
        return 1

    for skill_dir in skill_dirs:
        skill_name = skill_dir.name
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            issues.append(f"INVALID: {skill_dir} missing required SKILL.md")
            continue

        link_path = dest_root / skill_name
        target = f"../../.claude/skills/{skill_name}"

        if check_mode:
            issue = validate_link(link_path, target)
            if issue:
                issues.append(issue)
            else:
                print(f"OK: {link_path} -> {target}")
        else:
            print(ensure_link(link_path, target))

    if check_mode:
        if issues:
            for issue in issues:
                print(issue)
            print(f"CHECK FAILED: {len(issues)} issue(s) found")
            return 1
        print("CHECK PASSED: skills symlinks are in sync")
        return 0

    if issues:
        for issue in issues:
            print(issue)
        print(f"SYNC PARTIAL: Completed with {len(issues)} issue(s)")
        return 1

    print("SYNC COMPLETE: skills symlinks are in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
