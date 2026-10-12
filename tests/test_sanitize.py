from pathlib import Path

import pytest

from apmw import (
    TARGET_STRIP_FIELDS,
    extract_platform_metadata,
    inject_metadata_fields,
    sanitize_installed,
    strip_fields,
)


AGENT = """---
name: lead
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

AGENT_WITH_METADATA = """---
name: lead
description: "Orchestrator agent."
mode: all
steps: 40
color: primary
tools: ['agent', 'read', 'search']
user-invocable: true
agents: ['planning', 'verify']
metadata:
  opencode:
    permission:
      read: allow
      edit: deny
      bash:
        "*": deny
      task: allow
      skill: allow
  claude:
    model: claude-sonnet-4-5
---

Body stays untouched.
"""


@pytest.fixture
def agents_dir(tmp_path: Path) -> Path:
    d = tmp_path / "agents"
    d.mkdir()
    (d / "lead.md").write_text(AGENT)
    return d


@pytest.fixture
def agents_dir_meta(tmp_path: Path) -> Path:
    d = tmp_path / "agents"
    d.mkdir()
    (d / "lead.md").write_text(AGENT_WITH_METADATA)
    return d


def frontmatter(path: Path) -> str:
    text = path.read_text()
    return text.split("---\n")[1]


def test_claude_strips_permission_block_and_model(agents_dir: Path):
    changed = sanitize_installed(agents_dir, TARGET_STRIP_FIELDS["claude"])
    assert changed == 1
    fm = frontmatter(agents_dir / "lead.md")
    for forbidden in ("permission:", "model:", "mode:", "steps:", "color:",
                      "tools:", "user-invocable:", "agents:", "bash:", "gh issue"):
        assert forbidden not in fm
    assert "name: lead" in fm
    assert "description:" in fm


def test_opencode_strips_tools_but_keeps_permission(agents_dir: Path):
    changed = sanitize_installed(agents_dir, TARGET_STRIP_FIELDS["opencode"])
    assert changed == 1
    fm = frontmatter(agents_dir / "lead.md")
    assert "tools:" not in fm
    assert "user-invocable:" not in fm
    assert "agents:" not in fm
    assert "permission:" in fm
    assert '"gh issue*": allow' in fm


@pytest.mark.parametrize("target", ["cursor", "codex"])
def test_cursor_codex_strip_steps_and_color(agents_dir: Path, target: str):
    changed = sanitize_installed(agents_dir, TARGET_STRIP_FIELDS[target])
    assert changed == 1
    fm = frontmatter(agents_dir / "lead.md")
    for forbidden in ("mode:", "steps:", "color:", "permission:"):
        assert forbidden not in fm


def test_body_preserved(agents_dir: Path):
    sanitize_installed(agents_dir, TARGET_STRIP_FIELDS["claude"])
    assert "Body stays untouched." in (agents_dir / "lead.md").read_text()


def test_file_without_frontmatter_untouched(tmp_path: Path):
    d = tmp_path / "agents"
    d.mkdir()
    (d / "plain.md").write_text("no frontmatter here\n")
    assert sanitize_installed(d, TARGET_STRIP_FIELDS["claude"]) == 0
    assert (d / "plain.md").read_text() == "no frontmatter here\n"


def test_missing_dir_returns_zero(tmp_path: Path):
    assert sanitize_installed(tmp_path / "nope", TARGET_STRIP_FIELDS["claude"]) == 0


# --- extract_platform_metadata ---

def _fm_lines(agent_text: str) -> list[str]:
    parts = agent_text.split("---\n")
    return parts[1].splitlines()


def test_extract_opencode_metadata():
    fm = _fm_lines(AGENT_WITH_METADATA)
    result = extract_platform_metadata(fm, "opencode")
    assert result != []
    joined = "\n".join(result)
    assert "permission:" in joined
    assert "read: allow" in joined
    assert "task: allow" in joined
    assert "skill: allow" in joined
    # must be de-indented: no leading spaces on top-level key
    assert result[0].startswith("permission:")


def test_extract_claude_metadata():
    fm = _fm_lines(AGENT_WITH_METADATA)
    result = extract_platform_metadata(fm, "claude")
    assert result == ["model: claude-sonnet-4-5"]


def test_extract_unknown_platform_returns_empty():
    fm = _fm_lines(AGENT_WITH_METADATA)
    assert extract_platform_metadata(fm, "cursor") == []


def test_extract_no_metadata_block_returns_empty():
    fm = _fm_lines(AGENT)
    assert extract_platform_metadata(fm, "opencode") == []


# --- inject_metadata_fields ---

def test_inject_appends_when_no_conflict():
    fm = ["name: agent", "description: test"]
    meta = ["permission:", "  read: allow"]
    result = inject_metadata_fields(fm, meta)
    assert result == ["name: agent", "description: test", "permission:", "  read: allow"]


def test_inject_overrides_existing_field():
    fm = ["name: agent", "permission:", "  read: deny"]
    meta = ["permission:", "  read: allow", "  edit: allow"]
    result = inject_metadata_fields(fm, meta)
    # old permission stripped, new one appended
    assert "  read: deny" not in result
    assert "permission:" in result
    assert "  read: allow" in result
    assert "  edit: allow" in result
    assert result.index("permission:") > result.index("name: agent")


def test_inject_empty_meta_is_noop():
    fm = ["name: agent", "description: test"]
    assert inject_metadata_fields(fm, []) == fm


# --- full pipeline with metadata ---

def test_opencode_pipeline_injects_metadata_and_strips_tools(agents_dir_meta: Path):
    changed = sanitize_installed(agents_dir_meta, TARGET_STRIP_FIELDS["opencode"], platform="opencode")
    assert changed == 1
    fm = frontmatter(agents_dir_meta / "lead.md")
    # tools/user-invocable/agents/metadata stripped
    assert "tools:" not in fm
    assert "user-invocable:" not in fm
    assert "agents:" not in fm
    assert "metadata:" not in fm
    # opencode metadata injected
    assert "permission:" in fm
    assert "task: allow" in fm
    assert "skill: allow" in fm


def test_metadata_absent_from_all_output(agents_dir_meta: Path):
    sanitize_installed(agents_dir_meta, TARGET_STRIP_FIELDS["opencode"], platform="opencode")
    text = (agents_dir_meta / "lead.md").read_text()
    assert "metadata:" not in text


def test_claude_pipeline_injects_model_from_metadata(agents_dir_meta: Path):
    changed = sanitize_installed(agents_dir_meta, TARGET_STRIP_FIELDS["claude"], platform="claude")
    assert changed == 1
    fm = frontmatter(agents_dir_meta / "lead.md")
    assert "model: claude-sonnet-4-5" in fm
    assert "metadata:" not in fm
    assert "tools: [Agent, Read, Grep, Glob]" in fm


def test_pipeline_no_metadata_platform_still_strips(agents_dir_meta: Path):
    # cursor has no metadata block in AGENT_WITH_METADATA — should still strip normally
    changed = sanitize_installed(agents_dir_meta, TARGET_STRIP_FIELDS["cursor"], platform="cursor")
    assert changed == 1
    fm = frontmatter(agents_dir_meta / "lead.md")
    assert "mode:" not in fm
    assert "steps:" not in fm
    assert "color:" not in fm
    assert "metadata:" not in fm


def test_body_preserved_with_metadata(agents_dir_meta: Path):
    sanitize_installed(agents_dir_meta, TARGET_STRIP_FIELDS["opencode"], platform="opencode")
    assert "Body stays untouched." in (agents_dir_meta / "lead.md").read_text()

