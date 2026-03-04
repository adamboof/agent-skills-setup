---
name: implement
description: "Execute a phased plan using Codex-native multi-agent orchestration. Pipeline: group-based implementation → per-phase validation → per-group audit → triage and continue."
argument-hint: "[plan-folder]"
---

# Implement Plan (Codex Override)

Implement the plan at: **$ARGUMENTS**

This override keeps the original grouped execution and quality gates while replacing Claude Task/Team APIs with Codex role-based thread orchestration.

## Orchestration Model (Codex)

Use roles defined in `.codex/config.toml`.

- **Orchestrator (you):** parse plan, schedule groups, coordinate checkpoints, decide retries/escalation
- **Builder role:** implement code for one phase at a time
- **Validator role:** run tests/review against phase acceptance criteria
- **Auditor role:** perform group-level regression/deviation audit
- **Reviewer role (optional):** targeted code review support on risky phases

Spawn separate threads for each role responsibility and keep context isolated per phase/group.

## Inputs and Artifacts

- Input plan: `$ARGUMENTS/plan.md`
- Phase specs: `$ARGUMENTS/phase-*.md`
- Reviews folder: `$ARGUMENTS/reviews/implementation/`
- Group audit report path: `$ARGUMENTS/reviews/implementation/group-<group-name>-audit.md`

Before execution, read the `references/` folder inside this skill (if present) for process conventions.

## Required Pipeline

1. **Load and validate plan structure**
   - Parse phases and groups from `plan.md`.
   - Confirm every phase has acceptance criteria and a valid group.

2. **Execute by group (dependency order)**
   - For each group, process phases in numeric order.

3. **Per-phase build + validate cycle**
   - Spawn **builder** thread for the phase.
   - On completion, spawn **validator** thread to verify:
     - acceptance criteria
     - relevant tests/checks
     - no unintended regressions in touched areas
   - Retry bounded number of times for fix-forward iterations; escalate when blocked.

4. **Per-group audit**
   - After all phases in a group pass validation, spawn **auditor** thread.
   - Auditor produces a written report at:
     - `$ARGUMENTS/reviews/implementation/group-<group-name>-audit.md`
   - Include severity, impacted files, unresolved risks, and recommendation.

5. **Triage findings**
   - **Low/no issues:** continue to next group.
   - **Medium:** auto-fix with builder + revalidate.
   - **High/Critical:** checkpoint with user before applying fixes.

6. **Completion report**
   - Summarize completed groups/phases, audit outcomes, unresolved items, and verification status.

## Safety and Consistency Rules

- Never skip validation for a completed phase.
- Never skip audit for a completed group.
- Keep retry limits explicit and deterministic.
- Record deviations so later group audits can consider earlier compromises.
