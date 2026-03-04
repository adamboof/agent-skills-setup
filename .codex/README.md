# Codex Overlay Configuration

This directory is the Codex overlay surface for repository-local Codex settings.

- Canonical Claude configuration remains under `.claude/`.
- Codex-specific config and generated artifacts live under `.codex/`.
- This folder is managed by `scripts/codexify.py`.

If upstream `.claude/**` changes, run `python scripts/codexify.py` to sync overlay scaffolding and `python scripts/codexify.py check` to verify deterministic state.
