#!/usr/bin/env python3
"""codexify: sync Codex overlay artifacts from .claude sources."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_DIRS = (".agents", ".agents/skills", ".codex", ".codex/agents")
MCP_SOURCE_FILE = ".mcp.json.example"
CODEX_CONFIG_FILE = ".codex/config.toml"
CLAUDE_AGENTS_DIR = ".claude/agents"
CODEX_AGENTS_DIR = ".codex/agents"

WORKSPACE_WRITE_ROLES = {"builder", "planner", "validator", "auditor"}
ROLE_DESCRIPTIONS = {
    "architect": "Architecture planning and technical design.",
    "code-quality-reviewer": "Code quality review for correctness and maintainability.",
    "security-reviewer": "Security review for vulnerabilities and hardening.",
    "tdd-guide": "Test-driven development guidance and test strategy.",
    "doc-updater": "Documentation updates and codemap maintenance.",
    "builder": "Implementation-focused engineer for scoped tasks.",
    "planner": "Planning specialist for phased execution plans.",
    "validator": "Validation specialist for verification and compliance.",
    "auditor": "Audit specialist for cross-phase consistency checks.",
}


@dataclass(frozen=True)
class AgentConfig:
    role_name: str
    source_relpath: str
    config_relpath: str
    generated_content: str
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Codex overlay artifacts from .claude")
    parser.add_argument("command", nargs="?", choices=("check",), help="Optional positional alias for --check")
    parser.add_argument("--check", action="store_true", help="Validate overlay state only (no filesystem changes)")
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


def toml_string(value: str) -> str:
    return json.dumps(value)


def toml_key(key: str) -> str:
    if key.replace("_", "").isalnum() and "-" not in key:
        return key
    return toml_string(key)


def render_toml_array(values: list[str]) -> str:
    return "[" + ", ".join(toml_string(value) for value in values) + "]"


def render_toml_inline_table(items: dict[str, str]) -> str:
    if not items:
        return "{}"
    pairs = [f"{toml_key(key)} = {toml_string(value)}" for key, value in sorted(items.items())]
    return "{" + ", ".join(pairs) + "}"


def load_mcp_servers(source_file: Path) -> dict[str, dict[str, Any]]:
    with source_file.open("r", encoding="utf-8") as file:
        source_data = json.load(file)
    if not isinstance(source_data, dict):
        raise ValueError(f"{source_file} must contain a JSON object")
    servers = source_data.get("mcpServers")
    if not isinstance(servers, dict):
        raise ValueError(f"{source_file} must contain an object field 'mcpServers'")

    normalized: dict[str, dict[str, Any]] = {}
    for server_name, server_cfg in servers.items():
        if not isinstance(server_name, str):
            raise ValueError("MCP server names must be strings")
        if not isinstance(server_cfg, dict):
            raise ValueError(f"MCP server '{server_name}' must be an object")

        command = server_cfg.get("command")
        args = server_cfg.get("args", [])
        env = server_cfg.get("env", {})

        if not isinstance(command, str) or not command:
            raise ValueError(f"MCP server '{server_name}' must define a non-empty string command")
        if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
            raise ValueError(f"MCP server '{server_name}' args must be an array of strings")
        if not isinstance(env, dict) or not all(isinstance(key, str) and isinstance(val, str) for key, val in env.items()):
            raise ValueError(f"MCP server '{server_name}' env must be an object of string values")

        normalized[server_name] = {"command": command, "args": args, "env": env}
    return normalized


def strip_yaml_frontmatter(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return markdown.strip()
    end_index = markdown.find("\n---\n", 4)
    if end_index == -1:
        return markdown.strip()
    return markdown[end_index + len("\n---\n") :].strip()


def resolve_sandbox_mode(role_name: str) -> str:
    if role_name in WORKSPACE_WRITE_ROLES:
        return "workspace-write"
    return "read-only"


def render_agent_toml(role_name: str, source_relpath: str, markdown: str) -> str:
    instructions = strip_yaml_frontmatter(markdown)
    return "\n".join(
        [
            "# Generated by scripts/codexify.py. DO NOT EDIT MANUALLY.",
            f"# Source: {source_relpath}",
            "",
            f"sandbox_mode = {toml_string(resolve_sandbox_mode(role_name))}",
            'developer_instructions = """',
            instructions,
            '"""',
            "",
        ]
    )


def collect_agent_sources(agents_root: Path) -> list[Path]:
    return sorted((path for path in agents_root.rglob("*.md") if path.is_file()), key=lambda path: path.as_posix())


def build_expected_agents(repo_root: Path) -> list[AgentConfig]:
    agents_root = repo_root / CLAUDE_AGENTS_DIR
    role_names: set[str] = set()
    expected_agents: list[AgentConfig] = []

    for source_file in collect_agent_sources(agents_root):
        role_name = source_file.stem
        if role_name in role_names:
            raise ValueError(f"Duplicate role name discovered in {CLAUDE_AGENTS_DIR}: {role_name}")
        role_names.add(role_name)

        rel_source = source_file.relative_to(repo_root).as_posix()
        target_rel = (Path(CODEX_AGENTS_DIR) / source_file.relative_to(agents_root)).with_suffix(".toml")
        config_relpath = target_rel.relative_to(".codex").as_posix()
        description = ROLE_DESCRIPTIONS.get(role_name, f"{role_name.replace('-', ' ').title()} specialist.")

        expected_agents.append(
            AgentConfig(
                role_name=role_name,
                source_relpath=rel_source,
                config_relpath=config_relpath,
                generated_content=render_agent_toml(role_name, rel_source, source_file.read_text(encoding="utf-8")),
                description=description,
            )
        )

    return sorted(expected_agents, key=lambda item: item.role_name)


def render_codex_config(servers: dict[str, dict[str, Any]], agents: list[AgentConfig]) -> str:
    lines = [
        "# Generated by scripts/codexify.py. DO NOT EDIT MANUALLY.",
        "# Source: .mcp.json.example, .claude/agents/**/*.md",
        "",
        "version = 1",
        "",
        "[features]",
        "multi_agent = true",
        "",
        "[agents]",
        "max_threads = 6",
        "max_depth = 1",
    ]

    for agent in agents:
        lines.extend(
            [
                "",
                f"[agents.{toml_key(agent.role_name)}]",
                f"description = {toml_string(agent.description)}",
                f"config_file = {toml_string(agent.config_relpath)}",
            ]
        )

    for server_name in sorted(servers):
        server_cfg = servers[server_name]
        lines.extend(
            [
                "",
                f"[mcp_servers.{toml_key(server_name)}]",
                f"command = {toml_string(server_cfg['command'])}",
                f"args = {render_toml_array(server_cfg['args'])}",
                f"env = {render_toml_inline_table(server_cfg['env'])}",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def sync_or_check_agents(repo_root: Path, check_mode: bool, expected_agents: list[AgentConfig], issues: list[str]) -> None:
    codex_agents_root = repo_root / CODEX_AGENTS_DIR
    expected_by_path = {repo_root / Path(".codex") / Path(agent.config_relpath): agent.generated_content for agent in expected_agents}

    if check_mode:
        for path, expected_content in expected_by_path.items():
            if not path.exists() or not path.is_file():
                issues.append(f"MISSING: {path} (run without --check to create it)")
                continue
            actual_content = path.read_text(encoding="utf-8")
            if actual_content != expected_content:
                issues.append(f"INCORRECT: {path} does not match generated output")
            else:
                print(f"OK: {path} is generated and in sync")

        actual_files = sorted(codex_agents_root.rglob("*.toml")) if codex_agents_root.exists() else []
        expected_full_paths = set(expected_by_path)
        for actual_file in actual_files:
            if actual_file not in expected_full_paths:
                issues.append(f"UNEXPECTED: {actual_file} is not generated from {CLAUDE_AGENTS_DIR}")
        return

    for path, expected_content in expected_by_path.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8") == expected_content:
            print(f"OK: {path} is generated and in sync")
        else:
            path.write_text(expected_content, encoding="utf-8")
            print(f"UPDATED: {path}")

    expected_full_paths = set(expected_by_path)
    for actual_file in sorted(codex_agents_root.rglob("*.toml")):
        if actual_file not in expected_full_paths:
            actual_file.unlink()
            print(f"REMOVED: {actual_file} (not generated from {CLAUDE_AGENTS_DIR})")


def main() -> int:
    args = parse_args()
    check_mode = args.check or args.command == "check"

    repo_root = Path(__file__).resolve().parent.parent
    source_root = repo_root / ".claude" / "skills"
    dest_root = repo_root / ".agents" / "skills"
    mcp_source = repo_root / MCP_SOURCE_FILE
    codex_config = repo_root / CODEX_CONFIG_FILE
    claude_agents_root = repo_root / CLAUDE_AGENTS_DIR

    if not source_root.exists() or not source_root.is_dir():
        print(f"ERROR: Source skills directory not found: {source_root}")
        return 2
    if not mcp_source.exists() or not mcp_source.is_file():
        print(f"ERROR: MCP source file not found: {mcp_source}")
        return 2
    if not claude_agents_root.exists() or not claude_agents_root.is_dir():
        print(f"ERROR: Claude agents directory not found: {claude_agents_root}")
        return 2

    skill_dirs = iter_skill_dirs(source_root)
    if not skill_dirs:
        print(f"ERROR: No skill directories found in {source_root}")
        return 2

    try:
        mcp_servers = load_mcp_servers(mcp_source)
        expected_agents = build_expected_agents(repo_root)
        expected_config = render_codex_config(mcp_servers, expected_agents)
    except ValueError as err:
        print(f"ERROR: {err}")
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
        if not codex_config.exists() or not codex_config.is_file():
            issues.append(f"MISSING: {codex_config} (run without --check to create it)")
        else:
            actual_config = codex_config.read_text(encoding="utf-8")
            if actual_config != expected_config:
                issues.append(f"INCORRECT: {codex_config} does not match generated output")
            else:
                print(f"OK: {codex_config} is in sync with generated output")
    else:
        if codex_config.exists() and codex_config.read_text(encoding="utf-8") == expected_config:
            print(f"OK: {codex_config} is in sync with generated output")
        else:
            codex_config.write_text(expected_config, encoding="utf-8")
            print(f"UPDATED: {codex_config}")

    sync_or_check_agents(repo_root, check_mode, expected_agents, issues)

    if check_mode:
        if issues:
            for issue in issues:
                print(issue)
            print(f"CHECK FAILED: {len(issues)} issue(s) found")
            return 1
        print("CHECK PASSED: Codex overlay is in sync")
        return 0

    if issues:
        for issue in issues:
            print(issue)
        print(f"SYNC PARTIAL: Completed with {len(issues)} issue(s)")
        return 1

    print("SYNC COMPLETE: Codex overlay is in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
