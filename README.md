# apmw

Cross-platform wrapper for the [apm](https://github.com/GravionLabs) CLI.

`apm install` and `apm update` deploy platform-neutral skills cleanly, but
agent files carry platform-specific frontmatter (`permission`, `mode`,
`tools`, etc.) that each target — Claude Code, OpenCode, GitHub Copilot,
Cursor, Codex — interprets differently. `apmw` runs the real `apm` command
and then sanitizes the installed agent frontmatter for the target platform
you specify.

## Install

```bash
pipx install apmw
# or
uvx apmw install -p claude
```

## Usage

```bash
apmw install -p claude      # apm install + sanitize for Claude Code
apmw install -p opencode    # apm install + sanitize for OpenCode
apmw update  -p copilot     # apm update + sanitize for GitHub Copilot
```

Flags:

- `-p, --platform` — target platform: `opencode` (default), `copilot`, `claude`, `cursor`, `codex`
- `-g, --global` — sanitize the platform's global agent install directory instead of the current project
- `-s, --source` — also add explicit `permission` blocks to source agent files under `packages/*/.apm/agents/`
- `update` only: `-y, --yes` (skip consent prompt), `--dry-run` (preview only, skips sanitization)

`apmw` requires `apm` to already be installed and on `PATH`.

## Development

```bash
uv sync
uv run pytest
```
