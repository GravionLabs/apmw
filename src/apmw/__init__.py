import argparse
import json
import os
import platform as _platform
import re
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

# Which frontmatter fields to drop per target platform. GravionLabs/apm-hub
# keeps an equivalent copy at config/agent-strip-fields.json (shared with
# src/generators/agent-target-generator.ts there) — update both if the set
# of fields per platform changes.
#
# Note on "claude": Claude Code accepts only name/description/tools/model;
# source `tools` arrays use Copilot names and `model` values are rarely
# valid Anthropic ids, so both are stripped — Claude then inherits the
# session model.
_STRIP_FIELDS_PATH = Path(__file__).resolve().parent / "data" / "agent-strip-fields.json"


def _load_target_strip_fields() -> dict[str, list[str]]:
    if _STRIP_FIELDS_PATH.is_file():
        return json.loads(_STRIP_FIELDS_PATH.read_text())
    return {
        "opencode": ["tools", "user-invocable", "agents"],
        "copilot": ["mode", "steps", "color", "permission", "task"],
        "claude": ["mode", "steps", "color", "tools", "permission", "user-invocable", "agents", "model"],
        "cursor": ["mode", "steps", "color", "permission"],
        "codex": ["mode", "steps", "color", "permission"],
    }


TARGET_STRIP_FIELDS = _load_target_strip_fields()

GLOBAL_PATHS: dict[str, dict[str, list[str]]] = {
    "opencode": {
        "Linux": ["~/.config/opencode/agents"],
        "Darwin": ["~/Library/Application Support/opencode/agents"],
        "Windows": ["%APPDATA%\\opencode\\agents"],
    },
    "copilot": {
        "Linux": ["~/.config/github-copilot/agents"],
        "Darwin": ["~/Library/Application Support/github-copilot/agents"],
        "Windows": ["%APPDATA%\\GitHub Copilot\\agents"],
    },
    "claude": {
        "Linux": ["~/.claude/agents", "~/.config/claude/agents"],
        "Darwin": ["~/Library/Application Support/claude/agents"],
        "Windows": ["%APPDATA%\\Claude\\agents"],
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

TOOLS_ARRAY_RE = re.compile(r'^tools:\s*\[')
TOOLS_BLOCK_RE = re.compile(r'^tools:\s*$')
PERMISSION_RE = re.compile(r'^permission:')
METADATA_RE = re.compile(r'^metadata\s*:')


def resolve_path(raw: str) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(raw))
    return Path(expanded)


def get_global_agents_dirs(target: str) -> list[Path]:
    system = _platform.system()
    dirs = GLOBAL_PATHS.get(target, {}).get(system, [])
    return [resolve_path(d) for d in dirs]


def _add_sanitize_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-p", "--platform",
        default=None,
        choices=list(TARGET_STRIP_FIELDS.keys()),
        help="Target platform (default: all known platforms)",
    )
    parser.add_argument(
        "-s", "--source",
        action="store_true",
        help="Also add permission block to source agent files under packages/",
    )
    parser.add_argument(
        "-g", "--global",
        action="store_true",
        dest="global_",
        help="Sanitize global installation paths instead of CWD",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apmw",
        description="Wrapper for the apm CLI that sanitizes agent frontmatter per target platform.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser(
        "install", help="Run apm install then sanitize agent frontmatter per target."
    )
    _add_sanitize_args(install_parser)

    sanitize_parser = subparsers.add_parser(
        "sanitize", help="Sanitize an already-installed agent directory without running apm."
    )
    _add_sanitize_args(sanitize_parser)

    update_parser = subparsers.add_parser(
        "update", help="Run apm update then sanitize agent frontmatter per target."
    )
    _add_sanitize_args(update_parser)
    update_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip the consent prompt (passed as --yes to apm update)",
    )
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing (passed to apm update, skips sanitization)",
    )

    return parser


def find_frontmatter(lines: list[str]) -> tuple[int, int] | None:
    if len(lines) < 3 or lines[0].strip() != "---":
        return None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return (0, i)
    return None


def has_array_tools(fm_lines: list[str]) -> bool:
    for line in fm_lines:
        if TOOLS_ARRAY_RE.match(line) or TOOLS_BLOCK_RE.match(line):
            return True
    return False


def strip_fields(fm_lines: list[str], fields: list[str]) -> list[str] | None:
    patterns = [re.compile(r'^' + re.escape(f) + r'\s*:') for f in fields]

    new_lines: list[str] = []
    skip_indent = False
    skip_indent_level = 0

    for line in fm_lines:
        if skip_indent:
            if line and not line[0].isspace():
                skip_indent = False
            elif line and line[0].isspace():
                indent = len(line) - len(line.lstrip())
                if indent <= skip_indent_level:
                    skip_indent = False
                else:
                    continue
            else:
                skip_indent = False

        matched = False
        for pat in patterns:
            if pat.match(line):
                matched = True
                skip_indent = True
                skip_indent_level = len(line) - len(line.lstrip()) if line else 0
                break

        if not matched:
            new_lines.append(line)

    if len(new_lines) == len(fm_lines):
        return None
    return new_lines


def add_permission_block(fm_lines: list[str]) -> list[str] | None:
    for line in fm_lines:
        if PERMISSION_RE.match(line):
            return None

    tool_names: list[str] = []
    in_block = False
    for line in fm_lines:
        if in_block:
            m = re.match(r'^\s+-\s+(.+)$', line)
            if m:
                tool_names.append(m.group(1).strip())
            else:
                break
        elif TOOLS_ARRAY_RE.match(line):
            m = TOOLS_ARRAY_RE.match(line)
            rest = line[m.end():]
            if rest.endswith("]"):
                rest = rest[:-1]
            tool_names = [t.strip().strip("'\"") for t in rest.split(",") if t.strip()]
            break
        elif TOOLS_BLOCK_RE.match(line):
            in_block = True

    if not tool_names:
        return None

    insert_at = None
    for i, line in enumerate(fm_lines):
        if line.strip().startswith("# Copilot/APM fields") or line.strip().startswith("# Copilot"):
            insert_at = i
            break

    perm_block = ["permission:"]
    for name in tool_names:
        perm_block.append(f"  {name}: allow")

    if insert_at is not None:
        return fm_lines[:insert_at] + perm_block + fm_lines[insert_at:]
    else:
        return fm_lines + perm_block


def extract_platform_metadata(fm_lines: list[str], platform: str) -> list[str]:
    platform_re = re.compile(r'^(\s+)' + re.escape(platform) + r'\s*:')

    in_metadata = False
    platform_indent: int | None = None
    content_base_indent: int | None = None
    result: list[str] = []

    for line in fm_lines:
        if not in_metadata:
            if METADATA_RE.match(line):
                in_metadata = True
            continue

        if platform_indent is None:
            if not line or not line[0].isspace():
                break
            m = platform_re.match(line)
            if m:
                platform_indent = len(m.group(1))
            continue

        if not line or not line[0].isspace():
            break
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= platform_indent:
            break
        if content_base_indent is None:
            content_base_indent = current_indent
        result.append(line[content_base_indent:])

    return result


def inject_metadata_fields(fm_lines: list[str], meta_lines: list[str]) -> list[str]:
    if not meta_lines:
        return fm_lines

    meta_fields = []
    for line in meta_lines:
        if line and not line[0].isspace():
            m = re.match(r'^(\S+)\s*:', line)
            if m:
                meta_fields.append(m.group(1))

    stripped = strip_fields(fm_lines, meta_fields)
    base = stripped if stripped is not None else list(fm_lines)
    return base + meta_lines


def rewrite_file(path: Path, new_fm_lines: list[str], original_lines: list[str], fm_end: int) -> None:
    body = original_lines[fm_end + 1:]
    result = ["---"] + new_fm_lines + ["---"] + body
    text = "\n".join(result)
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text)


def sanitize_installed(agents_dir: Path, fields: list[str], platform: str | None = None) -> int:
    if not agents_dir.is_dir():
        return 0

    changed = 0
    for f in sorted(agents_dir.glob("*.md")):
        lines = f.read_text().splitlines()
        fm = find_frontmatter(lines)
        if fm is None:
            continue
        _, fm_end = fm
        fm_lines = lines[1:fm_end]

        platform_meta = extract_platform_metadata(fm_lines, platform) if platform else []

        stripped = strip_fields(fm_lines, fields)
        new_fm = stripped if stripped is not None else list(fm_lines)

        if platform_meta:
            new_fm = inject_metadata_fields(new_fm, platform_meta)

        if new_fm == fm_lines:
            continue

        rewrite_file(f, new_fm, lines, fm_end)
        changed += 1
        name = f.stem
        removed = [k for k in fields if any(re.match(r'^' + re.escape(k) + r'\s*:', l) for l in fm_lines)]
        injected = [m.group(1) for l in platform_meta if (m := re.match(r'^(\S+)\s*:', l))]
        parts = []
        if removed:
            parts.append(f"removed {', '.join(removed)}")
        if injected:
            parts.append(f"injected {', '.join(injected)}")
        print(f"  [strip]   {name} — {'; '.join(parts)}")

    return changed


def sanitize_source(packages_dir: Path) -> int:
    if not packages_dir.is_dir():
        return 0

    changed = 0
    for f in sorted(packages_dir.glob("*/.apm/agents/*.agent.md")):
        lines = f.read_text().splitlines()
        fm = find_frontmatter(lines)
        if fm is None:
            continue
        _, fm_end = fm
        fm_lines = lines[1:fm_end]

        if not has_array_tools(fm_lines):
            continue

        new_fm = add_permission_block(fm_lines)
        if new_fm is None:
            continue

        rewrite_file(f, new_fm, lines, fm_end)
        changed += 1
        name = f.stem
        tools = [l.split(":")[0].strip() for l in new_fm if l.startswith("  ") and ":" in l and l.strip() != "permission:"]
        print(f"  [convert] {name} — added permission ({', '.join(tools)})")

    return changed


def run_apm(subcommand: str, args: list[str]) -> int:
    apm_exe = shutil.which("apm")
    if apm_exe is None:
        print("error: 'apm' command not found in PATH", file=sys.stderr)
        return 1

    cmd = [apm_exe, subcommand] + args
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def do_sanitize(platform_name: str | None, global_: bool, source: bool) -> None:
    if platform_name is None:
        for name in TARGET_STRIP_FIELDS:
            print(f"[{name}]")
            do_sanitize(name, global_, source)
        return

    fields = TARGET_STRIP_FIELDS.get(platform_name, [])
    packages_dir = Path.cwd() / "packages"

    changed_installed = 0

    if global_:
        dirs = get_global_agents_dirs(platform_name)
        for d in dirs:
            cnt = sanitize_installed(d, fields, platform_name)
            if cnt:
                print(f"  ({d})")
            changed_installed += cnt
    else:
        target_subdir = TARGET_DIRS.get(platform_name, f".{platform_name}")
        target_dir = Path.cwd() / target_subdir
        changed_installed = sanitize_installed(target_dir / "agents", fields, platform_name)

    changed_source = 0
    if source:
        changed_source = sanitize_source(packages_dir)

    parts = [f"{changed_installed} {'global ' if global_ else ''}installed files sanitized"]
    if source:
        parts.append(f"{changed_source} source files updated")
    print(f"\nDone: {', '.join(parts)}")


def main() -> None:
    parser = build_parser()
    ns, apm_args = parser.parse_known_args(sys.argv[1:])

    if ns.command == "sanitize":
        do_sanitize(ns.platform, ns.global_, ns.source)
        return

    apm_extra: list[str] = []
    if ns.global_:
        apm_extra.append("-g")

    if ns.command == "install":
        rc = run_apm("install", apm_extra + apm_args)
        if rc != 0:
            sys.exit(rc)
        do_sanitize(ns.platform, ns.global_, ns.source)
        return

    if ns.command == "update":
        if ns.yes:
            apm_extra.insert(0, "--yes")
        if ns.dry_run:
            apm_extra.insert(0, "--dry-run")
        rc = run_apm("update", apm_extra + apm_args)
        if rc != 0 or ns.dry_run:
            if rc != 0:
                sys.exit(rc)
            return
        do_sanitize(ns.platform, ns.global_, ns.source)
