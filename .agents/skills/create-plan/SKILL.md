---
name: create-plan
description: "Create phased implementation plans for new features or projects using Codex-native multi-agent orchestration. Pipeline: clarify requirements → explore codebase → produce plan + phases → validate plan artifacts."
argument-hint: "[feature-name] [description]"
---

# Create Complete Plan (Codex Override)

Create a complete phased plan for: **$ARGUMENTS**

This override preserves the original planning intent while replacing Claude-only task APIs with Codex multi-agent mechanics.

## Orchestration Model (Codex)

Use roles defined in `.codex/config.toml` for all delegation.

- **Orchestrator (you):** manage checkpoints, ensure artifacts are created, route PASS/FAIL
- **Explorer role:** gather technical grounding from codebase
- **Planner role:** draft `plan.md` and phase files
- **Reviewer/Validator roles:** review plan quality and template compliance

When delegating, spawn focused threads per role (e.g., explorer, planner, validator) and keep each thread scoped to one objective.

## Artifact Paths

- Plan folder: `plans/<YYMMDD>-<feature-name>/`
- Plan file: `plans/<YYMMDD>-<feature-name>/plan.md`
- Phase files: `plans/<YYMMDD>-<feature-name>/phase-<NN>-<slug>.md`

## Required Pipeline

1. **Clarify requirements**
   - Resolve ambiguity before planning (problem, scope, users, integrations, data, UI).
   - Ask concise follow-up questions when assumptions would impact architecture or phase count.

2. **Explore codebase (explorer role)**
   - Spawn an explorer thread.
   - Produce a concise grounding summary:
     - affected files/modules
     - existing patterns/conventions
     - reusable components/utilities
     - integration points
     - risk/complexity hotspots

3. **Create plan artifacts (planner role)**
   - Spawn a planner thread with clarified requirements + exploration summary.
   - Instruct planner to read the `references/` folder inside this skill before writing artifacts.
   - Generate:
     - `plan.md`
     - all phase files needed for a complete delivery plan
   - Preserve group-based phase structure so implementation can be executed/audited by group.

4. **Checkpoint: user review of plan summary**
   - Present a short summary of goals, phase count, group layout, and key risks.
   - Incorporate user adjustments before finalizing phases.

5. **Validate plan quality (reviewer/validator roles)**
   - Spawn independent validation thread(s):
     - one for `plan.md`
     - one per phase (or batched deterministically)
   - Ensure template compliance, realistic sequencing, and explicit acceptance criteria.

6. **Finalize and report**
   - Report final artifact list, open risks, and next command (`/implement <plan-folder>`).

## Determinism Rules

- Use stable ordering (phases sorted numerically, groups in dependency order).
- Keep section headers and tables consistent across files.
- Avoid non-deterministic wording like "maybe" where decisions are required.
