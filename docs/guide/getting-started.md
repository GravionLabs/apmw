# Getting started

Install `apmw`, run it once, and know its flags.

## Install

```bash
pipx install apmw           # or: uv tool install apmw
apmw install -p claude
```

To run it once without installing, use `uvx`; nothing stays on your `PATH`:

```bash
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
apmw install -p opencode    # apm install + place OpenCode plugins
apmw update  -p opencode    # apm update + place OpenCode plugins
apmw install -g -p opencode # global install, plugins go to ~/.config/opencode/plugins
apmw install                # plugins for every platform that has them
```

**Flags:**

| Flag | Description |
| :--- | :---------- |
| `-p, --platform` | Target: `opencode`, `copilot`, `claude`, `cursor`, `codex`; omit to run for all (only OpenCode has plugins) |
| `-g, --global` | Forwarded to `apm`; plugins go to the global OpenCode directory |
| `-y, --yes` | (`update` only) Skip consent prompt |
| `--dry-run` | (`update` only) Preview apm changes without writing; skips plugin placement |

`apmw` requires `apm` to be installed and on `PATH`.

Arguments `apmw` does not know are passed on to `apm`, so packages and any other `apm` option work
as usual (`-g` is forwarded too):

```bash
apmw install all@apm-hub -g -p claude   # runs: apm install -g all@apm-hub, then places plugins
```
