# Codex/Claude Skill Compatibility Matrix

This repository keeps Claude setup files as the canonical source-of-truth, while allowing a small Codex-native overlay for skills that need different orchestration mechanics.

## Compatibility Matrix

| Category | Source path(s) | Deployment in `.agents/skills/**` |
|---|---|---|
| Claude-native | `.claude/skills/create-plan`<br>`.claude/skills/implement` | **Overridden** by Codex-native versions listed below |
| Codex-native override | `.codex/overrides/skills/create-plan`<br>`.codex/overrides/skills/implement` | Copied as real directories |
| Everything else | `.claude/skills/*` (all other skills) | Symlinked to `.claude/skills/*` |

## Rationale

- Claude-native orchestrator skills use Claude-specific task/team primitives that do not map directly to Codex execution.
- Codex-native overrides provide equivalent intent using Codex role/thread orchestration, without modifying canonical `.claude/**` sources.
- Keeping only a minimal override set reduces merge friction with upstream Claude changes and preserves a clear layering model.

## Generation Rule

`python scripts/codexify.py` generates `.agents/skills/**` by routing each skill as:

1. copy from `.codex/overrides/skills/<skill>/` when an override exists;
2. otherwise symlink to `.claude/skills/<skill>`.
