from pathlib import Path

from apmw import build_parser, main


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
    (agents_dir / "dev-workflow.md").write_text(
        "---\nname: dev-workflow\nmodel: deepseek-v4-flash-free\n---\n\nBody.\n"
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["apmw", "sanitize", "-p", "claude"])

    main()

    fm = (agents_dir / "dev-workflow.md").read_text()
    assert "model:" not in fm
    assert "name: dev-workflow" in fm


def test_sanitize_command_no_platform_hits_all_targets(tmp_path: Path, monkeypatch):
    claude_dir = tmp_path / ".claude" / "agents"
    opencode_dir = tmp_path / ".opencode" / "agents"
    claude_dir.mkdir(parents=True)
    opencode_dir.mkdir(parents=True)
    claude_dir_content = "---\nname: dev-workflow\nmodel: deepseek-v4-flash-free\n---\n\nBody.\n"
    opencode_content = "---\nname: dev-workflow\ntools: ['agent', 'read']\n---\n\nBody.\n"
    (claude_dir / "dev-workflow.md").write_text(claude_dir_content)
    (opencode_dir / "dev-workflow.md").write_text(opencode_content)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["apmw", "sanitize"])

    main()

    assert "model:" not in (claude_dir / "dev-workflow.md").read_text()
    assert "tools:" not in (opencode_dir / "dev-workflow.md").read_text()
