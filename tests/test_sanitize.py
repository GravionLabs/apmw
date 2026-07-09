from pathlib import Path

import pytest

from apmw import TARGET_STRIP_FIELDS, sanitize_installed


AGENT = """---
name: dev-workflow
description: "Orchestrator agent."
model: deepseek-v4-flash-free
mode: all
steps: 40
color: primary
permission:
  read: allow
  edit: deny
  bash:
    "*": deny
    "gh issue*": allow
  task: allow
tools: ['agent', 'read', 'search']
user-invocable: true
agents: ['planning', 'verify']
---

Body stays untouched.
"""


@pytest.fixture
def agents_dir(tmp_path: Path) -> Path:
    d = tmp_path / "agents"
    d.mkdir()
    (d / "dev-workflow.md").write_text(AGENT)
    return d


def frontmatter(path: Path) -> str:
    text = path.read_text()
    return text.split("---\n")[1]


def test_claude_strips_permission_block_and_model(agents_dir: Path):
    changed = sanitize_installed(agents_dir, TARGET_STRIP_FIELDS["claude"])
    assert changed == 1
    fm = frontmatter(agents_dir / "dev-workflow.md")
    for forbidden in ("permission:", "model:", "mode:", "steps:", "color:",
                      "tools:", "user-invocable:", "agents:", "bash:", "gh issue"):
        assert forbidden not in fm
    assert "name: dev-workflow" in fm
    assert "description:" in fm


def test_opencode_strips_tools_but_keeps_permission(agents_dir: Path):
    changed = sanitize_installed(agents_dir, TARGET_STRIP_FIELDS["opencode"])
    assert changed == 1
    fm = frontmatter(agents_dir / "dev-workflow.md")
    assert "tools:" not in fm
    assert "user-invocable:" not in fm
    assert "agents:" not in fm
    assert "permission:" in fm
    assert '"gh issue*": allow' in fm


@pytest.mark.parametrize("target", ["cursor", "codex"])
def test_cursor_codex_strip_steps_and_color(agents_dir: Path, target: str):
    changed = sanitize_installed(agents_dir, TARGET_STRIP_FIELDS[target])
    assert changed == 1
    fm = frontmatter(agents_dir / "dev-workflow.md")
    for forbidden in ("mode:", "steps:", "color:", "permission:"):
        assert forbidden not in fm


def test_body_preserved(agents_dir: Path):
    sanitize_installed(agents_dir, TARGET_STRIP_FIELDS["claude"])
    assert "Body stays untouched." in (agents_dir / "dev-workflow.md").read_text()


def test_file_without_frontmatter_untouched(tmp_path: Path):
    d = tmp_path / "agents"
    d.mkdir()
    (d / "plain.md").write_text("no frontmatter here\n")
    assert sanitize_installed(d, TARGET_STRIP_FIELDS["claude"]) == 0
    assert (d / "plain.md").read_text() == "no frontmatter here\n"


def test_missing_dir_returns_zero(tmp_path: Path):
    assert sanitize_installed(tmp_path / "nope", TARGET_STRIP_FIELDS["claude"]) == 0
