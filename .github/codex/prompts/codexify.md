You are updating the Codex overlay after upstream sync and `python scripts/codexify.py` regeneration.

Hard constraints:
- Never edit `.claude/**`.
- Only modify these paths when necessary:
  - `AGENTS.md`
  - `.codex/config.toml`
  - `.codex/overrides/**`
  - docs describing the Codex overlay (for example `README.md` Codex sections)

Change policy:
- Keep diffs minimal and deterministic.
- Preserve existing comments, placeholders, and structure unless a change is required.
- Do not reformat unrelated files.
- Do not introduce secrets.

Goal:
- Make only targeted, mechanical adjustments needed to keep the Codex overlay aligned with canonical Claude sources.
