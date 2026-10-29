import argparse
import difflib
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

# Which frontmatter fields to drop per target platform; the JSON file next to
# this module is the only source of truth.
#
# Note on "claude": Claude Code accepts only name/description/tools/model;
# source `tools` arrays use Copilot names and `model` values are rarely
# valid Anthropic ids, so both are stripped — Claude then inherits the
# session model.
_STRIP_FIELDS_PATH = Path(__file__).resolve().parent / "data" / "agent-strip-fields.json"


def _load_target_strip_fields() -> dict[str, list[str]]:
    if _STRIP_FIELDS_PATH.is_file():
        return json.loads(_STRIP_FIELDS_PATH.read_text(encoding="utf-8"))
    return {
        "opencode": ["tools", "user-invocable", "agents", "disable-model-invocation"],
        "copilot": ["mode", "steps", "color", "permission", "task"],
        "claude": ["mode", "steps", "color", "tools", "permission", "user-invocable", "agents", "model", "disable-model-invocation"],
        "cursor": ["mode", "steps", "color", "permission", "disable-model-invocation"],
        "codex": ["mode", "steps", "color", "permission", "disable-model-invocation"],
    }


TARGET_STRIP_FIELDS = _load_target_strip_fields()

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

TOOLS_ARRAY_RE = re.compile(r'^tools:\s*\[')
TOOLS_BLOCK_RE = re.compile(r'^tools:\s*$')
PERMISSION_RE = re.compile(r'^permission:')
METADATA_RE = re.compile(r'^metadata\s*:')

# Copilot tool aliases -> Claude Code tool names / OpenCode permission keys.
CLAUDE_TOOLS = {
    "execute": ["Bash"],
    "read": ["Read"],
    "edit": ["Edit", "Write"],
    "search": ["Grep", "Glob"],
    "agent": ["Agent"],
    "web": ["WebFetch", "WebSearch"],
    "todo": ["TodoWrite"],
}
OPENCODE_PERMISSIONS = {
    "execute": ["bash"],
    "read": ["read"],
    "edit": ["edit"],
    "search": ["glob", "grep"],
    "agent": ["task"],
    "web": ["webfetch", "websearch"],
    "todo": ["todowrite"],
}
OPENCODE_PERMISSION_ORDER = ["read", "glob", "grep", "edit", "bash", "task", "webfetch", "websearch", "todowrite"]
TOOL_SYNONYMS = {
    "shell": "execute", "bash": "execute", "powershell": "execute",
    "notebookread": "read",
    "multiedit": "edit", "write": "edit", "notebookedit": "edit",
    "grep": "search", "glob": "search",
    "custom-agent": "agent", "task": "agent", "runsubagent": "agent",
    "websearch": "web", "webfetch": "web",
    "todowrite": "todo",
}


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
    sanitize_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a diff per file instead of writing",
    )

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


def parse_tools(fm_lines: list[str]) -> list[str]:
    names: list[str] = []
    in_block = False
    for line in fm_lines:
        if in_block:
            m = re.match(r'^\s+-\s+(.+)$', line)
            if not m:
                break
            names.append(m.group(1).strip().strip("'\""))
        elif TOOLS_ARRAY_RE.match(line):
            rest = line[TOOLS_ARRAY_RE.match(line).end():].rstrip()
            if rest.endswith("]"):
                rest = rest[:-1]
            return [n.strip().strip("'\"") for n in rest.split(",") if n.strip()]
        elif TOOLS_BLOCK_RE.match(line):
            in_block = True
    return names


def tool_aliases(fm_lines: list[str]) -> tuple[list[str], list[str]]:
    aliases: list[str] = []
    unmapped: list[str] = []
    for name in parse_tools(fm_lines):
        key = TOOL_SYNONYMS.get(name.lower(), name.lower())
        if key not in CLAUDE_TOOLS:
            unmapped.append(name)
        elif key not in aliases:
            aliases.append(key)
    return aliases, unmapped


CLAUDE_MODEL_RE = re.compile(r'^model\s*:\s*(inherit|sonnet|opus|haiku|claude-[\w.\-]+)\s*$')


def native_claude_fields(fm_lines: list[str], platform: str | None) -> set[str]:
    if platform != "claude":
        return set()
    native: set[str] = set()
    names = parse_tools(fm_lines)
    if names and all(n[:1].isupper() for n in names):
        native.add("tools")
    if any(CLAUDE_MODEL_RE.match(l) for l in fm_lines):
        native.add("model")
    return native


def effective_fields(fm_lines: list[str], fields: list[str], platform: str | None) -> list[str]:
    native = native_claude_fields(fm_lines, platform)
    return [f for f in fields if f not in native]


def derive_platform_fields(
    fm_lines: list[str], platform: str | None, meta_lines: list[str]
) -> tuple[list[str], list[str]]:
    defined = {m.group(1) for l in meta_lines if (m := re.match(r'^(\S+)\s*:', l))}
    aliases, unmapped = tool_aliases(fm_lines)
    if platform == "claude" and "tools" not in defined | native_claude_fields(fm_lines, platform) and aliases:
        names = [n for a in aliases for n in CLAUDE_TOOLS[a]]
        return [f"tools: [{', '.join(names)}]"], unmapped
    if platform == "opencode" and "permission" not in defined and not any(PERMISSION_RE.match(l) for l in fm_lines):
        allowed = {p for a in aliases for p in OPENCODE_PERMISSIONS.get(a, [])}
        extra: list[str] = []
        for name in parse_tools(fm_lines):
            key = name.lower()
            if key == "skill":
                extra.append("skill")
            elif "/" in name:
                extra.append(name.replace("/", "_", 1))
        if allowed or extra:
            # Copilot `tools` is an allowlist; "*" must come first because the last matching rule wins.
            lines = ["permission:", '  "*": deny']
            lines += [f"  {p}: {'allow' if p in allowed else 'deny'}" for p in OPENCODE_PERMISSION_ORDER]
            lines += [f"  {p}: allow" for p in dict.fromkeys(extra)]
            return lines, []
    return [], []


def add_permission_block(fm_lines: list[str]) -> list[str] | None:
    for line in fm_lines:
        if PERMISSION_RE.match(line):
            return None

    tool_names = parse_tools(fm_lines)

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
    path.write_text(text, encoding="utf-8")


def sanitize_frontmatter(fm_lines: list[str], fields: list[str], platform: str | None = None) -> list[str]:
    platform_meta = extract_platform_metadata(fm_lines, platform) if platform else []
    derived, _ = derive_platform_fields(fm_lines, platform, platform_meta)
    stripped = strip_fields(fm_lines, effective_fields(fm_lines, fields, platform))
    new_fm = stripped if stripped is not None else list(fm_lines)
    if platform_meta or derived:
        new_fm = inject_metadata_fields(new_fm, platform_meta + derived)
    return new_fm


def sanitize_installed(
    agents_dir: Path, fields: list[str], platform: str | None = None, dry_run: bool = False
) -> int:
    if not agents_dir.is_dir():
        return 0

    changed = 0
    for f in sorted(agents_dir.glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        fm = find_frontmatter(lines)
        if fm is None:
            continue
        _, fm_end = fm
        fm_lines = lines[1:fm_end]

        platform_meta = extract_platform_metadata(fm_lines, platform) if platform else []
        derived, unmapped = derive_platform_fields(fm_lines, platform, platform_meta)
        new_fm = sanitize_frontmatter(fm_lines, fields, platform)

        if new_fm == fm_lines:
            continue

        if dry_run:
            diff = difflib.unified_diff(fm_lines, new_fm, fromfile=str(f), tofile=f"{f} (sanitized)", lineterm="")
            print("\n".join(diff))
        else:
            rewrite_file(f, new_fm, lines, fm_end)
        changed += 1
        name = f.stem
        removed = [k for k in effective_fields(fm_lines, fields, platform) if any(re.match(r'^' + re.escape(k) + r'\s*:', l) for l in fm_lines)]
        injected = [m.group(1) for l in platform_meta if (m := re.match(r'^(\S+)\s*:', l))]
        parts = []
        if removed:
            parts.append(f"removed {', '.join(removed)}")
        if injected:
            parts.append(f"injected {', '.join(injected)}")
        if derived:
            note = f" (unmapped: {', '.join(unmapped)})" if unmapped else ""
            parts.append(f"derived {derived[0].split(':')[0]}{note}")
        print(f"  [strip]   {name} — {'; '.join(parts)}")

    return changed


def sanitize_source(packages_dir: Path) -> int:
    if not packages_dir.is_dir():
        return 0

    changed = 0
    for f in sorted(packages_dir.glob("*/.apm/agents/*.agent.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
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


def place_opencode_plugin(global_: bool, dry_run: bool = False) -> int:
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
        if not dry_run:
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            except OSError as e:
                print(f"  [plugin]  {src.name} — skipped, {e}")
                continue
        placed += 1
        print(f"  [plugin]  {src.name} — {'would place' if dry_run else 'placed'} in {dest_dir}")
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


def do_sanitize(platform_name: str | None, global_: bool, source: bool, dry_run: bool = False) -> None:
    if platform_name is None:
        for name in TARGET_STRIP_FIELDS:
            print(f"[{name}]")
            do_sanitize(name, global_, source, dry_run)
        return

    fields = TARGET_STRIP_FIELDS.get(platform_name, [])
    packages_dir = Path.cwd() / "packages"

    changed_installed = 0

    if global_:
        dirs = get_global_agents_dirs(platform_name)
        for d in dirs:
            cnt = sanitize_installed(d, fields, platform_name, dry_run)
            if cnt:
                print(f"  ({d})")
            changed_installed += cnt
    else:
        target_subdir = TARGET_DIRS.get(platform_name, f".{platform_name}")
        target_dir = Path.cwd() / target_subdir
        changed_installed = sanitize_installed(target_dir / "agents", fields, platform_name, dry_run)

    placed_plugins = place_opencode_plugin(global_, dry_run) if platform_name == "opencode" else None

    changed_source = 0
    if source and not dry_run:
        changed_source = sanitize_source(packages_dir)

    verb = "would be sanitized" if dry_run else "sanitized"
    parts = [f"{changed_installed} {'global ' if global_ else ''}installed files {verb}"]
    if placed_plugins is not None:
        parts.append(f"{placed_plugins} plugin files {'would be placed' if dry_run else 'placed'}")
    if source:
        parts.append(f"{changed_source} source files updated")
    print(f"\nDone: {', '.join(parts)}")


def main() -> None:
    parser = build_parser()
    ns, apm_args = parser.parse_known_args(sys.argv[1:])

    if ns.command == "sanitize":
        do_sanitize(ns.platform, ns.global_, ns.source, ns.dry_run)
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
