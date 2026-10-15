import shutil
from pathlib import Path

import pytest

from apmw import TARGET_STRIP_FIELDS, main, sanitize_installed

FIXTURES = Path(__file__).parent / "fixtures"
AGENTS = ["dev-workflow", "explorer", "implementer", "reviewer", "issue-reader"]
PLATFORMS = ["claude", "copilot", "opencode"]
# installed file name per platform; apm keeps the Copilot suffix only for .github/.copilot
INSTALLED_NAME = {"claude": "{name}.md", "copilot": "{name}.agent.md", "opencode": "{name}.md"}


def _install(tmp_path: Path, platform: str) -> Path:
    d = tmp_path / platform / "agents"
    d.mkdir(parents=True)
    for name in AGENTS:
        shutil.copy(FIXTURES / "agents" / f"{name}.agent.md", d / INSTALLED_NAME[platform].format(name=name))
    return d


def _frontmatter(path: Path) -> str:
    return path.read_text().split("---\n")[1]


@pytest.mark.parametrize("platform", PLATFORMS)
def test_sanitized_output_matches_golden(tmp_path: Path, platform: str):
    d = _install(tmp_path, platform)
    assert sanitize_installed(d, TARGET_STRIP_FIELDS[platform], platform) == len(AGENTS)
    for name in AGENTS:
        installed = d / INSTALLED_NAME[platform].format(name=name)
        golden = FIXTURES / "expected" / platform / installed.name
        assert installed.read_text() == golden.read_text(), f"{platform}/{installed.name} differs from golden"


@pytest.mark.parametrize("platform", PLATFORMS)
def test_metadata_never_survives(tmp_path: Path, platform: str):
    d = _install(tmp_path, platform)
    sanitize_installed(d, TARGET_STRIP_FIELDS[platform], platform)
    for f in d.iterdir():
        assert "metadata:" not in f.read_text()


def test_claude_gets_tools_model_and_skills(tmp_path: Path):
    d = _install(tmp_path, "claude")
    sanitize_installed(d, TARGET_STRIP_FIELDS["claude"], "claude")
    explorer = _frontmatter(d / "explorer.md")
    assert "tools: [Read, Grep, Glob]" in explorer
    assert "model: haiku" in explorer
    assert "user-invocable:" not in explorer
    implementer = _frontmatter(d / "implementer.md")
    assert "skills: [implementation]" in implementer
    assert "model: inherit" in implementer
    assert "AskUserQuestion" in _frontmatter(d / "dev-workflow.md")


def test_opencode_gets_mode_model_permission_and_no_tools(tmp_path: Path):
    d = _install(tmp_path, "opencode")
    sanitize_installed(d, TARGET_STRIP_FIELDS["opencode"], "opencode")
    for name in AGENTS:
        fm = _frontmatter(d / f"{name}.md")
        assert "tools:" not in fm
        assert "user-invocable:" not in fm
        assert "permission:" in fm
    assert "mode: primary" in _frontmatter(d / "dev-workflow.md")
    assert "mode: subagent" in _frontmatter(d / "explorer.md")
    assert "model: anthropic/claude-haiku-4-5" in _frontmatter(d / "explorer.md")
    assert '"git diff*": allow' in _frontmatter(d / "reviewer.md")


def test_copilot_keeps_tools_and_user_invocable(tmp_path: Path):
    d = _install(tmp_path, "copilot")
    sanitize_installed(d, TARGET_STRIP_FIELDS["copilot"], "copilot")
    fm = _frontmatter(d / "explorer.agent.md")
    assert "tools: ['read', 'search']" in fm
    assert "user-invocable: false" in fm
    assert "permission:" not in fm


def test_bodies_untouched(tmp_path: Path):
    d = _install(tmp_path, "claude")
    before = {n: (d / f"{n}.md").read_text().split("\n---\n", 1)[1] for n in AGENTS}
    sanitize_installed(d, TARGET_STRIP_FIELDS["claude"], "claude")
    for n in AGENTS:
        assert (d / f"{n}.md").read_text().split("\n---\n", 1)[1] == before[n]


def test_sanitize_dry_run_prints_diff_and_writes_nothing(tmp_path: Path, monkeypatch, capsys):
    d = tmp_path / ".opencode" / "agents"
    d.mkdir(parents=True)
    shutil.copy(FIXTURES / "agents" / "explorer.agent.md", d / "explorer.md")
    before = (d / "explorer.md").read_text()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["apmw", "sanitize", "-p", "opencode", "--dry-run"])
    main()

    out = capsys.readouterr().out
    assert "-tools: ['read', 'search']" in out
    assert "+mode: subagent" in out
    assert "would be sanitized" in out
    assert (d / "explorer.md").read_text() == before
