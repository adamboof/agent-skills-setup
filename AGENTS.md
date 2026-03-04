# Codex Working Guide (Repo Root)

This repository keeps **Claude setup files as the canonical source-of-truth**.

## Source-of-truth and overlay rules
- **Canonical (do not edit unless explicitly requested):** `.claude/**`
- **Codex overlay / generated surface:** `AGENTS.md`, `.agents/**`, `.codex/**`

If a Codex task conflicts with existing Claude setup, preserve `.claude/**` and apply changes in the overlay paths.

## How to work in this repo with Codex
- Read `CLAUDE.md` for deeper project rules and conventions.
- Keep Codex-specific guidance in `AGENTS.md` and Codex assets under `.agents/` and `.codex/`.
- After upstream pulls or `.claude/**` updates, regenerate/sync the overlay:
  - `python scripts/codexify.py`

## Verification
Run deterministic checks before committing:
- `python scripts/codexify.py check`

If checks fail, regenerate with `python scripts/codexify.py` and re-run the check.

## Scope note
Codex discovers `AGENTS.md` by walking up directories; this root file is the primary repo-wide guide.
