# Getting started

Install `apmw`, run it once, and know its flags.

## Install

```bash
pipx install apmw
# or
uvx apmw install -p claude
```

Prebuilt single-file executables (linux, macOS-arm64, windows) that need no Python environment
are attached to each [GitHub Release](https://github.com/GravionLabs/apmw/releases).

## Local development install

To install the local checkout (editable — picks up source edits immediately):

```bash
./install.sh       # Linux / macOS
.\install.ps1      # Windows
```

Uses `uv tool install` if `uv` is on `PATH`, falling back to `pipx`.

---

## Usage

```bash
apmw install -p claude      # apm install + sanitize for Claude Code
apmw install -p opencode    # apm install + sanitize for OpenCode
apmw update  -p copilot     # apm update + sanitize for GitHub Copilot
apmw sanitize -p claude     # sanitize an already-installed local agent dir (no apm call)
apmw sanitize -g -p claude  # sanitize the global Claude Code agent dir
apmw sanitize               # sanitize for every known platform
```

**Flags:**

| Flag | Description |
| :--- | :---------- |
| `-p, --platform` | Target: `opencode`, `copilot`, `claude`, `cursor`, `codex`; omit to run for all |
| `-g, --global` | Sanitize the platform's global agent install directory instead of the project dir |
| `-s, --source` | Also inject `permission:` blocks into source agent files under `packages/` |
| `-y, --yes` | (`update` only) Skip consent prompt |
| `--dry-run` | `update`: preview apm changes without writing; `sanitize`: print a diff per agent file instead of writing |

`apmw install`/`update` require `apm` to be installed and on `PATH`.  
`apmw sanitize` operates only on local files and does not invoke `apm`.
