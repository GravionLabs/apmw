import argparse
import os
import platform as _platform
import shutil
import subprocess
import sys
from pathlib import Path


TARGET_DIRS = {
    "opencode": ".opencode",
    "copilot": ".github",
    "claude": ".claude",
    "cursor": ".cursor",
    "codex": ".codex",
}

# Verified against apm 0.33 `apm install -g` (sandboxed HOME, 2026-10-11): it writes
# ~/.claude/agents, ~/.config/opencode/agents and ~/.copilot/agents on every OS;
# the older vendor-specific dirs stay as fallbacks for hand-made installs.
GLOBAL_PATHS: dict[str, dict[str, list[str]]] = {
    "opencode": {
        "Linux": ["~/.config/opencode/agents"],
        "Darwin": ["~/.config/opencode/agents", "~/Library/Application Support/opencode/agents"],
        "Windows": ["%USERPROFILE%\\.config\\opencode\\agents", "%APPDATA%\\opencode\\agents"],
    },
    "copilot": {
        "Linux": ["~/.copilot/agents", "~/.config/github-copilot/agents"],
        "Darwin": ["~/.copilot/agents", "~/Library/Application Support/github-copilot/agents"],
        "Windows": ["%USERPROFILE%\\.copilot\\agents", "%APPDATA%\\GitHub Copilot\\agents"],
    },
    "claude": {
        "Linux": ["~/.claude/agents", "~/.config/claude/agents"],
        "Darwin": ["~/.claude/agents", "~/Library/Application Support/claude/agents"],
        "Windows": ["%USERPROFILE%\\.claude\\agents", "%APPDATA%\\Claude\\agents"],
    },
    "cursor": {
        "Linux": ["~/.cursor/agents", "~/.config/cursor/agents"],
        "Darwin": ["~/Library/Application Support/cursor/agents"],
        "Windows": ["%APPDATA%\\Cursor\\agents"],
    },
    "codex": {
        "Linux": ["~/.codex/agents"],
        "Darwin": ["~/.codex/agents"],
        "Windows": ["%APPDATA%\\Codex\\agents"],
    },
}

OPENCODE_PLUGIN_GLOB = "apm_modules/**/opencode/plugins/*.[tj]s"

def resolve_path(raw: str) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(raw))
    return Path(expanded)


def get_global_agents_dirs(target: str) -> list[Path]:
    system = _platform.system()
    dirs = GLOBAL_PATHS.get(target, {}).get(system, [])
    return [resolve_path(d) for d in dirs]


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-p", "--platform",
        default=None,
        choices=list(TARGET_DIRS.keys()),
        help="Target platform (default: all known platforms)",
    )
    parser.add_argument(
        "-g", "--global",
        action="store_true",
        dest="global_",
        help="Use global installation paths instead of CWD",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apmw",
        description="Wrapper for the apm CLI that places OpenCode plugins after install and update.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser(
        "install", help="Run apm install then place OpenCode plugins."
    )
    _add_common_args(install_parser)

    update_parser = subparsers.add_parser(
        "update", help="Run apm update then place OpenCode plugins."
    )
    _add_common_args(update_parser)
    update_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip the consent prompt (passed as --yes to apm update)",
    )
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing (passed to apm update, skips plugin placement)",
    )

    return parser


def place_opencode_plugin(global_: bool) -> int:
    if global_:
        root = resolve_path("~/.apm")
        dirs = get_global_agents_dirs("opencode")
        if not dirs:
            return 0
        dest_dir = dirs[0].parent / "plugins"
    else:
        root = Path.cwd()
        dest_dir = Path.cwd() / TARGET_DIRS["opencode"] / "plugins"

    placed = 0
    seen: set[str] = set()
    for src in sorted(root.glob(OPENCODE_PLUGIN_GLOB)):
        if src.is_symlink() or not src.is_file() or src.name.endswith((".d.ts", ".test.ts", ".test.js")):
            continue
        if src.name in seen:
            print(f"  [plugin]  {src} — skipped, name already taken by an earlier match")
            continue
        seen.add(src.name)
        dest = dest_dir / src.name
        if dest.is_symlink() or (dest.exists() and not dest.is_file()):
            print(f"  [plugin]  {src.name} — skipped, {dest} is not a regular file")
            continue
        data = src.read_bytes()
        if dest.is_file() and dest.read_bytes() == data:
            continue
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        except OSError as e:
            print(f"  [plugin]  {src.name} — skipped, {e}")
            continue
        placed += 1
        print(f"  [plugin]  {src.name} — placed in {dest_dir}")
    return placed


def run_apm(subcommand: str, args: list[str]) -> int:
    apm_exe = shutil.which("apm")
    if apm_exe is None:
        print("error: 'apm' command not found in PATH", file=sys.stderr)
        return 1

    cmd = [apm_exe, subcommand] + args
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def do_plugins(platform_name: str | None, global_: bool) -> None:
    if platform_name not in (None, "opencode"):
        return
    placed = place_opencode_plugin(global_)
    print(f"\nDone: {placed} plugin files placed")


def main() -> None:
    parser = build_parser()
    ns, apm_args = parser.parse_known_args(sys.argv[1:])

    apm_extra: list[str] = []
    if ns.global_:
        apm_extra.append("-g")

    if ns.command == "install":
        rc = run_apm("install", apm_extra + apm_args)
        if rc != 0:
            sys.exit(rc)
        do_plugins(ns.platform, ns.global_)
        return

    if ns.command == "update":
        if ns.yes:
            apm_extra.insert(0, "--yes")
        if ns.dry_run:
            apm_extra.insert(0, "--dry-run")
        rc = run_apm("update", apm_extra + apm_args)
        if rc != 0:
            sys.exit(rc)
        if not ns.dry_run:
            do_plugins(ns.platform, ns.global_)
