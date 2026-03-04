# Codex in This Repository

This repository keeps `.claude/**` as canonical source-of-truth and generates Codex overlay artifacts under `.codex/**` and `.agents/**`.

## 1) Trust the repository so Codex loads `.codex/config.toml`

Codex only applies project config when the repo is trusted.

- Open this repository in Codex.
- Mark the project as **trusted** in the Codex UI/CLI flow you use.
- After trust is enabled, Codex will load `.codex/config.toml` from this repo.

If trust is not enabled, role and MCP settings in `.codex/config.toml` will not be applied.

## 2) Where MCP servers are configured

MCP source-of-truth for this repo is:

- `.mcp.json.example` (input manifest)

Generated Codex config is:

- `.codex/config.toml` under `[mcp_servers.*]`

Do not hand-edit generated MCP blocks; regenerate through `scripts/codexify.py`.

## 3) How to verify MCP + agents config

From the repo root:

```bash
python scripts/codexify.py --check
```

This validates that:

- `.codex/config.toml` matches generated output from `.mcp.json.example` and `.claude/agents/**/*.md`
- `.codex/agents/**/*.toml` files are present and in sync
- `.agents/skills/*` symlinks are in sync with `.claude/skills/*`

You can also inspect generated role wiring directly in `.codex/config.toml`:

- `[agents]` includes `max_threads` and `max_depth`
- `[agents.<role>]` entries point to `config_file = "agents/..."`

## 4) Multi-agent workflows (high-level)

When trusted config is loaded, Codex can use the generated role catalog under `[agents.*]` in `.codex/config.toml`.

High-level flow:

1. Choose the role that matches the task (for example: architect, builder, validator, auditor).
2. Let Codex load role-specific instructions from `config_file` under `.codex/agents/**`.
3. Execute work in small, scoped steps; use validator/auditor roles for verification.

Role instruction content comes from `.claude/agents/**/*.md` and is copied into generated `developer_instructions` fields.

## 5) Regenerate overlay artifacts

After upstream pulls or `.claude/**` / `.mcp.json.example` changes, regenerate:

```bash
python scripts/codexify.py
python scripts/codexify.py --check
```

This updates:

- `.codex/config.toml`
- `.codex/agents/**/*.toml`
- `.agents/skills/*` symlinks

Keep generated files deterministic and committed so teammates get consistent Codex behavior.
