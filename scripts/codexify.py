#!/usr/bin/env python3
"""codexify: sync Codex skills from .claude/skills and .codex/overrides.

Usage:
  python scripts/codexify.py
      Create or update `.agents/skills/<skill>` so each skill is routed as:
      - If `.codex/overrides/skills/<skill>/` exists: copy override directory
      - Otherwise: symlink to `../../.claude/skills/<skill>`
      Also ensure required overlay directories exist.

  python scripts/codexify.py --check
      Validate that all expected skills are routed correctly:
      - Override skills are real directories matching override contents
      - Non-override skills are symlinks with expected relative targets
      Also verify required overlay directories exist, without mutating the
      filesystem.

  python scripts/codexify.py check
      Alias for `--check` for compatibility with repository docs.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path


REQUIRED_DIRS = (".agents", ".agents/skills", ".codex")
OVERRIDES_ROOT = ".codex/overrides/skills"


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


def ensure_dir_copy(dest: Path, source: Path) -> str:
    if dest.exists() or dest.is_symlink():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()

    shutil.copytree(source, dest, symlinks=False)
    return f"UPDATED: {dest} (copied from {source})"


def validate_link(path: Path, target: str) -> str | None:
    if not path.exists() and not path.is_symlink():
        return f"MISSING: {path} (expected symlink to {target})"

    if not path.is_symlink():
        return f"INCORRECT: {path} exists but is not a symlink"

    actual = path.readlink().as_posix()
    if actual != target:
        return f"INCORRECT: {path} -> {actual} (expected {target})"

    return None


def compare_directories(expected: Path, actual: Path) -> list[str]:
    """Return deterministic list of mismatch messages for two directories."""
    issues: list[str] = []

    comparison = filecmp.dircmp(expected, actual)

    for name in sorted(comparison.left_only):
        issues.append(f"MISMATCH: Missing in destination: {actual / name}")
    for name in sorted(comparison.right_only):
        issues.append(f"MISMATCH: Unexpected in destination: {actual / name}")
    for name in sorted(comparison.funny_files):
        issues.append(f"MISMATCH: Problem comparing file: {actual / name}")

    _, mismatch, errors = filecmp.cmpfiles(
        expected,
        actual,
        sorted(comparison.common_files),
        shallow=False,
    )
    for name in sorted(mismatch):
        issues.append(f"MISMATCH: File content differs: {actual / name}")
    for name in sorted(errors):
        issues.append(f"MISMATCH: File compare error: {actual / name}")

    for subdir in sorted(comparison.common_dirs):
        issues.extend(compare_directories(expected / subdir, actual / subdir))

    return issues


def validate_override_copy(path: Path, override_source: Path) -> list[str]:
    if not path.exists() and not path.is_symlink():
        return [f"MISSING: {path} (expected directory copy of {override_source})"]

    if path.is_symlink():
        return [f"INCORRECT: {path} is a symlink (expected real directory copy)"]

    if not path.is_dir():
        return [f"INCORRECT: {path} exists but is not a directory"]

    return compare_directories(override_source, path)


def main() -> int:
    args = parse_args()
    check_mode = args.check or args.command == "check"

    repo_root = Path(__file__).resolve().parent.parent
    source_root = repo_root / ".claude" / "skills"
    dest_root = repo_root / ".agents" / "skills"
    overrides_root = repo_root / OVERRIDES_ROOT

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
        override_dir = overrides_root / skill_name

        if override_dir.is_dir():
            if check_mode:
                override_issues = validate_override_copy(link_path, override_dir)
                if override_issues:
                    issues.extend(override_issues)
                else:
                    print(f"OK: {link_path} (override copy from {override_dir})")
            else:
                print(ensure_dir_copy(link_path, override_dir))
        else:
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
        print("CHECK PASSED: skills routing is in sync")
        return 0

    if issues:
        for issue in issues:
            print(issue)
        print(f"SYNC PARTIAL: Completed with {len(issues)} issue(s)")
        return 1

    print("SYNC COMPLETE: skills routing is in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
