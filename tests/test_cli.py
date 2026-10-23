from pathlib import Path

import pytest

from apmw import build_parser, get_global_agents_dirs, main


@pytest.mark.parametrize(
    ("system", "target", "first"),
    [
        ("Linux", "copilot", "~/.copilot/agents"),
        ("Darwin", "copilot", "~/.copilot/agents"),
        ("Linux", "claude", "~/.claude/agents"),
        ("Darwin", "claude", "~/.claude/agents"),
        ("Linux", "opencode", "~/.config/opencode/agents"),
        ("Darwin", "opencode", "~/.config/opencode/agents"),
    ],
)
def test_global_agents_dirs_match_apm_install_g(monkeypatch, system: str, target: str, first: str):
    monkeypatch.setattr("apmw._platform.system", lambda: system)
    dirs = get_global_agents_dirs(target)
    assert dirs[0] == Path(first).expanduser()


def test_global_agents_dirs_windows_copilot(monkeypatch):
    # %VAR% only expands on Windows; on POSIX the raw entry must still name the apm location.
    monkeypatch.setattr("apmw._platform.system", lambda: "Windows")
    first = str(get_global_agents_dirs("copilot")[0])
    assert first.endswith("\\.copilot\\agents")
    assert first.startswith(("%USERPROFILE%", "C:", "D:")) or "\\Users\\" in first


def test_global_agents_dirs_unknown_target_is_empty(monkeypatch):
    monkeypatch.setattr("apmw._platform.system", lambda: "Linux")
    assert get_global_agents_dirs("nope") == []


def test_sanitize_parser_defaults():
    ns = build_parser().parse_args(["sanitize", "-p", "claude"])
    assert ns.command == "sanitize"
    assert ns.platform == "claude"
    assert ns.global_ is False
    assert ns.source is False


def test_sanitize_parser_no_platform_defaults_to_none():
    ns = build_parser().parse_args(["sanitize"])
    assert ns.platform is None


def test_sanitize_parser_global_flag():
    ns = build_parser().parse_args(["sanitize", "-g", "-p", "claude"])
    assert ns.command == "sanitize"
    assert ns.global_ is True


def test_sanitize_command_runs_without_apm(tmp_path: Path, monkeypatch):
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "orchestrator.md").write_text(
        "---\nname: orchestrator\nmodel: deepseek-v4-flash-free\n---\n\nBody.\n"
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["apmw", "sanitize", "-p", "claude"])

    main()

    fm = (agents_dir / "orchestrator.md").read_text()
    assert "model:" not in fm
    assert "name: orchestrator" in fm


def test_sanitize_command_no_platform_hits_all_targets(tmp_path: Path, monkeypatch):
    claude_dir = tmp_path / ".claude" / "agents"
    opencode_dir = tmp_path / ".opencode" / "agents"
    claude_dir.mkdir(parents=True)
    opencode_dir.mkdir(parents=True)
    claude_dir_content = "---\nname: orchestrator\nmodel: deepseek-v4-flash-free\n---\n\nBody.\n"
    opencode_content = "---\nname: orchestrator\ntools: ['agent', 'read']\n---\n\nBody.\n"
    (claude_dir / "orchestrator.md").write_text(claude_dir_content)
    (opencode_dir / "orchestrator.md").write_text(opencode_content)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["apmw", "sanitize"])

    main()

    assert "model:" not in (claude_dir / "orchestrator.md").read_text()
    assert "tools:" not in (opencode_dir / "orchestrator.md").read_text()
