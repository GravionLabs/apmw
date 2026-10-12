# apmw

[![PyPI](https://img.shields.io/pypi/v/apmw)](https://pypi.org/project/apmw/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-gravionlabs.github.io%2Fapmw-informational)](https://gravionlabs.github.io/apmw/)

**[Documentation](https://gravionlabs.github.io/apmw/)** · [User guide on GitHub](docs/guide/README.md) · [Changelog](CHANGELOG.md)

Cross-platform wrapper for the [apm](https://github.com/GravionLabs/apm-hub) CLI.

`apm install` and `apm update` deploy platform-neutral skills cleanly, but agent files carry
platform-specific frontmatter (`permission`, `mode`, `tools`, …) that each target — Claude Code,
OpenCode, GitHub Copilot, Cursor, Codex — interprets differently. `apmw` runs the real `apm`
command and then sanitizes the installed agent frontmatter for the platform you specify.

## Install

```bash
pipx install apmw
# or
uvx apmw install -p claude
```

Prebuilt single-file executables (Linux, macOS arm64, Windows) that need no Python environment are
attached to each [GitHub release](https://github.com/GravionLabs/apmw/releases).

## Usage

```bash
apmw install -p claude      # apm install + sanitize for Claude Code
apmw update  -p copilot     # apm update + sanitize for GitHub Copilot
apmw sanitize -g -p opencode  # sanitize the global OpenCode agent dir, no apm call
```

Everything else — flags, global install of the apm-hub packages, authoring agents for several
platforms from one source file, strip rules and per-platform references — is in the
[user guide](docs/guide/README.md).

## Development

```bash
uv sync
uv run pytest
```

See [docs/guide/development.md](docs/guide/development.md) and [AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE)
