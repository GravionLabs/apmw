import shutil
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


PLUGIN_FIXTURE = Path(__file__).parent / "fixtures" / "plugins"
PLUGIN_REL = Path("apm_modules/GravionLabs/apm-hub/packages/hooks/.apm/opencode/plugins/hooks.ts")


def _run_sanitize(monkeypatch, *args: str) -> None:
    monkeypatch.setattr("sys.argv", ["apmw", "sanitize", *args])
    main()


def _project(tmp_path: Path, monkeypatch) -> Path:
    shutil.copytree(PLUGIN_FIXTURE, tmp_path, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_sanitize_opencode_places_plugin_in_project(tmp_path: Path, monkeypatch, capsys):
    _project(tmp_path, monkeypatch)
    _run_sanitize(monkeypatch, "-p", "opencode")
    placed = tmp_path / ".opencode" / "plugins" / "hooks.ts"
    assert placed.read_bytes() == (PLUGIN_FIXTURE / PLUGIN_REL).read_bytes()
    assert "1 plugin files placed" in capsys.readouterr().out


def test_sanitize_opencode_plugin_is_idempotent_and_updates(tmp_path: Path, monkeypatch, capsys):
    _project(tmp_path, monkeypatch)
    _run_sanitize(monkeypatch, "-p", "opencode")
    capsys.readouterr()
    _run_sanitize(monkeypatch, "-p", "opencode")
    assert "0 plugin files placed" in capsys.readouterr().out
    (tmp_path / PLUGIN_REL).write_text("// v2\n")
    _run_sanitize(monkeypatch, "-p", "opencode")
    assert "1 plugin files placed" in capsys.readouterr().out
    assert (tmp_path / ".opencode" / "plugins" / "hooks.ts").read_text() == "// v2\n"


def test_sanitize_opencode_plugin_missing_source_is_noop(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _run_sanitize(monkeypatch, "-p", "opencode")
    assert not (tmp_path / ".opencode").exists()
    assert "0 plugin files placed" in capsys.readouterr().out


def test_sanitize_opencode_plugin_dry_run_writes_nothing(tmp_path: Path, monkeypatch, capsys):
    _project(tmp_path, monkeypatch)
    _run_sanitize(monkeypatch, "-p", "opencode", "--dry-run")
    assert not (tmp_path / ".opencode").exists()
    assert "1 plugin files would be placed" in capsys.readouterr().out


@pytest.mark.parametrize("platform", ["claude", "copilot", "cursor", "codex"])
def test_sanitize_other_platforms_place_no_plugin(tmp_path: Path, monkeypatch, platform: str):
    _project(tmp_path, monkeypatch)
    _run_sanitize(monkeypatch, "-p", platform)
    assert not (tmp_path / ".opencode").exists()
    assert not list(tmp_path.glob(".*/plugins"))


def test_sanitize_opencode_places_plugin_globally(tmp_path: Path, monkeypatch, capsys):
    home = tmp_path / "home"
    shutil.copytree(PLUGIN_FIXTURE, home / ".apm")
    work = tmp_path / "work"
    work.mkdir()
    shutil.copytree(PLUGIN_FIXTURE, work, dirs_exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr("apmw._platform.system", lambda: "Linux")
    monkeypatch.chdir(work)
    _run_sanitize(monkeypatch, "-p", "opencode", "-g")
    placed = home / ".config" / "opencode" / "plugins" / "hooks.ts"
    assert placed.read_bytes() == (PLUGIN_FIXTURE / PLUGIN_REL).read_bytes()
    assert not (work / ".opencode").exists()
    assert "1 plugin files placed" in capsys.readouterr().out


def _plugin_src(root: Path, module: str, name: str, text: str) -> Path:
    d = root / "apm_modules" / module / ".apm" / "opencode" / "plugins"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text)
    return d / name


def _home(tmp_path: Path, monkeypatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr("apmw._platform.system", lambda: "Linux")
    return home


def test_plugin_global_ignores_cwd_plugins(tmp_path: Path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    work = tmp_path / "work"
    _plugin_src(work, "a", "hooks.ts", "// cwd\n")
    _plugin_src(home / ".apm", "b", "hooks.ts", "// home\n")
    monkeypatch.chdir(work)
    _run_sanitize(monkeypatch, "-p", "opencode", "-g")
    assert (home / ".config" / "opencode" / "plugins" / "hooks.ts").read_text() == "// home\n"


def test_plugin_global_dry_run_writes_nothing(tmp_path: Path, monkeypatch, capsys):
    home = _home(tmp_path, monkeypatch)
    _plugin_src(home / ".apm", "b", "hooks.ts", "// home\n")
    monkeypatch.chdir(tmp_path)
    _run_sanitize(monkeypatch, "-p", "opencode", "-g", "--dry-run")
    assert not (home / ".config").exists()
    assert "1 plugin files would be placed" in capsys.readouterr().out


def test_plugin_global_without_known_dirs_is_noop(tmp_path: Path, monkeypatch, capsys):
    home = _home(tmp_path, monkeypatch)
    _plugin_src(home / ".apm", "b", "hooks.ts", "// home\n")
    monkeypatch.setattr("apmw._platform.system", lambda: "Plan9")
    monkeypatch.chdir(tmp_path)
    _run_sanitize(monkeypatch, "-p", "opencode", "-g")
    assert not (home / ".config").exists()
    assert "0 plugin files placed" in capsys.readouterr().out


def test_plugin_duplicate_names_first_sorted_wins_and_is_idempotent(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _plugin_src(tmp_path, "b", "hooks.ts", "// b\n")
    _plugin_src(tmp_path, "a", "hooks.ts", "// a\n")
    _run_sanitize(monkeypatch, "-p", "opencode")
    out = capsys.readouterr().out
    assert "1 plugin files placed" in out and "skipped" in out
    assert (tmp_path / ".opencode" / "plugins" / "hooks.ts").read_text() == "// a\n"
    _run_sanitize(monkeypatch, "-p", "opencode")
    assert "0 plugin files placed" in capsys.readouterr().out


def test_plugin_js_placed_and_declarations_and_tests_excluded(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _plugin_src(tmp_path, "a", "hooks.js", "// js\n")
    _plugin_src(tmp_path, "a", "hooks.d.ts", "// types\n")
    _plugin_src(tmp_path, "a", "hooks.test.ts", "// test\n")
    _run_sanitize(monkeypatch, "-p", "opencode")
    assert sorted(p.name for p in (tmp_path / ".opencode" / "plugins").iterdir()) == ["hooks.js"]


def test_plugin_symlinked_source_skipped(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    secret = tmp_path / "secret.ts"
    secret.write_text("// secret\n")
    d = tmp_path / "apm_modules" / "a" / "opencode" / "plugins"
    d.mkdir(parents=True)
    (d / "link.ts").symlink_to(secret)
    _run_sanitize(monkeypatch, "-p", "opencode")
    assert not (tmp_path / ".opencode").exists()


def test_plugin_symlinked_destination_not_written(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _plugin_src(tmp_path, "a", "hooks.ts", "// new\n")
    target = tmp_path / "elsewhere.txt"
    target.write_text("keep\n")
    dest_dir = tmp_path / ".opencode" / "plugins"
    dest_dir.mkdir(parents=True)
    (dest_dir / "hooks.ts").symlink_to(target)
    _run_sanitize(monkeypatch, "-p", "opencode")
    assert target.read_text() == "keep\n"
    assert "0 plugin files placed" in capsys.readouterr().out


def test_plugin_destination_directory_does_not_crash(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _plugin_src(tmp_path, "a", "hooks.ts", "// new\n")
    (tmp_path / ".opencode" / "plugins" / "hooks.ts").mkdir(parents=True)
    _run_sanitize(monkeypatch, "-p", "opencode")
    assert "0 plugin files placed" in capsys.readouterr().out


def test_install_places_plugin_after_apm(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _plugin_src(tmp_path, "a", "hooks.ts", "// x\n")
    monkeypatch.setattr("apmw.run_apm", lambda sub, args: 0)
    monkeypatch.setattr("sys.argv", ["apmw", "install", "-p", "opencode"])
    main()
    assert (tmp_path / ".opencode" / "plugins" / "hooks.ts").read_text() == "// x\n"
