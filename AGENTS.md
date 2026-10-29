# apmw

Cross-platform wrapper CLI for [apm](https://github.com/microsoft/apm). `apm install`/`apm update`
deploy platform-neutral skills cleanly, but agent files carry platform-specific frontmatter
(`permission`, `mode`, `tools`, `model`, etc.) that each target — Claude Code, OpenCode, GitHub
Copilot, Cursor, Codex — interprets differently. `apmw` runs the real `apm` command and then
strips/rewrites the installed agent frontmatter for the target platform. `apmw sanitize` exposes
the stripping step standalone, for re-sanitizing an already-installed agent directory without
invoking `apm` at all.

## Repo layout

- `docs/guide/*.md` — the user guide (one page per topic, order given by the numbered list in
  `docs/guide/README.md`); the README keeps only intro, install, usage and links. Move user-facing
  documentation here, not into the README.
- `apps/site/` — the documentation site (VitePress, `srcDir` is `docs/`), published on GitHub Pages
  by `.github/workflows/pages.yml`. `pnpm --filter @apmw/site dev` to preview, `build` fails on dead
  links, `test` checks that the sidebar list in `docs/guide/README.md` matches the pages on disk.
- `src/apmw/__init__.py` — the entire package: argument parsing, sanitization logic, and `apm`
  subprocess invocation all live in this single file.
- `src/apmw/data/agent-strip-fields.json` — per-platform list of frontmatter fields to strip.
  This file is the only source of truth; apm-hub no longer carries a copy (its agent generator was
  removed with the agents-to-skills migration).
- `tests/test_sanitize.py` — unit tests for the frontmatter-stripping logic (`sanitize_installed`,
  `strip_fields`, `add_permission_block`).
- `tests/test_cli.py` — CLI-level tests: argument parsing, `main()` dispatch, global paths.
- `tests/fixtures/agents/*.agent.md` — a pinned set of five apm-hub agents for golden/format
  tests; `tests/fixtures/expected/<platform>/` holds the sanitized golden output and
  `tests/test_fixtures.py` compares against it. When the sanitize format changes, regenerate the
  goldens with `sanitize_installed` (see the test module).
- `tests/test_apm_hub_contract.py` — checks the agents of a published apm-hub release (network,
  marked `network`, run nightly by `.github/workflows/contract.yml`; excluded from `uv run pytest`).

## Key concepts

- `TARGET_DIRS` — local (CWD-relative) agent install dir per platform, e.g. `claude` → `.claude`.
- `GLOBAL_PATHS` — per-OS global agent install dirs per platform, used when `-g/--global` is passed.
- `TARGET_STRIP_FIELDS` — loaded from `agent-strip-fields.json`; which frontmatter keys to drop
  per platform.
- `do_sanitize(platform, global_, source)` — the core operation: sanitizes either the local or
  global agent dir for a platform, optionally also sanitizing source files under `packages/`.
- `sanitize_installed` / `sanitize_source` — the actual file-rewriting functions `do_sanitize`
  calls.
- Subcommands (`build_parser()` in `src/apmw/__init__.py`): `install` and `update` run the real
  `apm` binary via `run_apm()` and then call `do_sanitize()`; `sanitize` calls `do_sanitize()`
  directly with no `apm` invocation.

## Dev workflow

```bash
uv sync
uv run pytest
```

No linter or formatter is configured in `pyproject.toml` — don't introduce one speculatively.

## Issues

The title of an issue starts with its level: `[Epic]`, `[Feature]`, `[PBI]`, `[Task]` or `[Bug]`, then the summary (`[PBI] feat: short summary`).

## Style

The codebase has no docstrings and minimal comments (only where a non-obvious rationale needs
capturing, e.g. the `claude` strip-fields comment). Keep additions flat and terse — match what's
already there rather than adding documentation blocks.
