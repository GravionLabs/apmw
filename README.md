# apmw

[![PyPI](https://img.shields.io/pypi/v/apmw)](https://pypi.org/project/apmw/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-gravionlabs.github.io%2Fapmw-informational)](https://gravionlabs.github.io/apmw/)

**[Documentation](https://gravionlabs.github.io/apmw/)** · [User guide on GitHub](docs/guide/README.md) · [Changelog](CHANGELOG.md)

Cross-platform wrapper for the [apm](https://github.com/microsoft/apm) CLI.

`apm install` and `apm update` deploy platform-neutral skills cleanly, but do not place the
OpenCode plugins that packages ship. `apmw` runs the real `apm` command and then copies those
plugins into the OpenCode `plugins` directory.

## Install

```bash
pipx install apmw           # or: uv tool install apmw
apmw install -p claude
```

To run it once without installing, use `uvx`; nothing stays on your `PATH`:

```bash
uvx apmw install -p claude
```

Prebuilt single-file executables (Linux, macOS arm64, Windows) that need no Python environment are
attached to each [GitHub release](https://github.com/GravionLabs/apmw/releases).

## Usage

```bash
apmw install -p opencode    # apm install + place OpenCode plugins
apmw update  -p opencode    # apm update + place OpenCode plugins
apmw install -g -p opencode # same for the global install
```

Everything else — flags and the global install of the apm-hub packages — is in the
[user guide](docs/guide/README.md).

## Development

```bash
uv sync
uv run pytest
```

See [docs/guide/development.md](docs/guide/development.md) and [AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE)
