from pathlib import Path

import pytest

from apmw import TARGET_STRIP_FIELDS, derive_platform_fields, parse_tools, sanitize_installed


def agent(frontmatter: str) -> str:
    return f"---\nname: a\ndescription: d\n{frontmatter}---\n\nBody.\n"


def run(tmp_path: Path, text: str, platform: str) -> str:
    d = tmp_path / "agents"
    d.mkdir(exist_ok=True)
    (d / "a.md").write_text(text)
    sanitize_installed(d, TARGET_STRIP_FIELDS[platform], platform)
    return (d / "a.md").read_text().split("---\n")[1]


def test_parse_tools_inline_and_block():
    assert parse_tools(["tools: ['read', \"edit\"]"]) == ["read", "edit"]
    assert parse_tools(["tools:", "  - read", "  - 'search'", "model: x"]) == ["read", "search"]
    assert parse_tools(["name: a"]) == []


def test_claude_tools_derived_from_copilot(tmp_path: Path):
    fm = run(tmp_path, agent("tools: ['agent', 'read', 'search', 'execute']\n"), "claude")
    assert "tools: [Agent, Read, Grep, Glob, Bash]" in fm


def test_claude_tools_derived_from_block_list_and_synonyms(tmp_path: Path):
    fm = run(tmp_path, agent("tools:\n  - shell\n  - write\n  - grep\n"), "claude")
    assert "tools: [Bash, Edit, Write, Grep, Glob]" in fm


def test_claude_metadata_tools_win(tmp_path: Path):
    text = agent("tools: ['read']\nmetadata:\n  claude:\n    tools: [Skill]\n")
    fm = run(tmp_path, text, "claude")
    assert "tools: [Skill]" in fm
    assert "Read" not in fm


def test_claude_without_tools_adds_nothing(tmp_path: Path):
    fm = run(tmp_path, agent("model: gpt-5\n"), "claude")
    assert "tools" not in fm


def test_opencode_permission_derived_from_copilot(tmp_path: Path):
    fm = run(tmp_path, agent("tools: ['read', 'search']\n"), "opencode")
    assert "tools:" not in fm
    assert fm.split("permission:\n")[1].splitlines()[:7] == [
        "  read: allow", "  glob: allow", "  grep: allow",
        "  edit: deny", "  bash: deny", "  task: deny", "  webfetch: deny",
    ]


def test_opencode_existing_permission_is_kept(tmp_path: Path):
    top = run(tmp_path, agent("tools: ['read']\npermission:\n  read: allow\n"), "opencode")
    assert top.count("permission:") == 1 and "edit: deny" not in top
    meta = run(tmp_path, agent("tools: ['read']\nmetadata:\n  opencode:\n    permission:\n      bash: allow\n"), "opencode")
    assert meta.count("permission:") == 1 and "bash: allow" in meta and "read: allow" not in meta


def test_unmapped_tools_are_reported_not_derived():
    fm = ["tools: ['read', 'github/*']"]
    assert derive_platform_fields(fm, "claude", []) == (["tools: [Read]"], ["github/*"])
    assert derive_platform_fields(["tools: ['github/*']"], "claude", []) == ([], [])
    assert derive_platform_fields(["tools: ['github/*']"], "opencode", []) == ([], [])


def test_unmapped_tools_named_in_console_line(tmp_path: Path, capsys):
    run(tmp_path, agent("tools: ['read', 'github/*']\n"), "claude")
    assert "derived tools (unmapped: github/*)" in capsys.readouterr().out


@pytest.mark.parametrize("platform", ["claude", "opencode"])
def test_derived_output_is_stable_on_second_run(tmp_path: Path, platform: str):
    first = run(tmp_path, agent("tools: ['agent', 'read', 'search']\n"), platform)
    d = tmp_path / "agents"
    assert sanitize_installed(d, TARGET_STRIP_FIELDS[platform], platform) == 0
    assert (d / "a.md").read_text().split("---\n")[1] == first


@pytest.mark.parametrize("platform", ["copilot", "cursor", "codex"])
def test_other_platforms_derive_nothing(platform: str):
    assert derive_platform_fields(["tools: ['read']"], platform, []) == ([], [])


def test_second_run_keeps_native_claude_tools_and_model(tmp_path: Path):
    text = agent("tools: [Agent, Read, Skill, AskUserQuestion]\nmodel: inherit\n")
    fm = run(tmp_path, text, "claude")
    assert "tools: [Agent, Read, Skill, AskUserQuestion]" in fm and "model: inherit" in fm


def test_non_claude_model_is_still_stripped(tmp_path: Path):
    fm = run(tmp_path, agent("model: GPT-5\ntools: ['read']\n"), "claude")
    assert "model" not in fm and "tools: [Read]" in fm
