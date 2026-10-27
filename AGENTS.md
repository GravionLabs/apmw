# apmw

Cross-platform wrapper CLI for [apm](https://github.com/microsoft/apm). `apmw install`/`apmw update`
run the real `apm` command and then place the OpenCode plugins of the installed packages into the
OpenCode `plugins` directory (project or global). Agent frontmatter sanitization (`apmw sanitize`)
was removed because apm-hub no longer ships agent source files.

## Repo layout

- `docs/guide/*.md` — the user guide (one page per topic, order given by the numbered list in
  `docs/guide/README.md`); the README keeps only intro, install, usage and links. Move user-facing
  documentation here, not into the README.
- `apps/site/` — the documentation site (VitePress, `srcDir` is `docs/`), published on GitHub Pages
  by `.github/workflows/pages.yml`. `pnpm --filter @apmw/site dev` to preview, `build` fails on dead
  links, `test` checks that the sidebar list in `docs/guide/README.md` matches the pages on disk.
- `src/apmw/__init__.py` — the entire package: argument parsing, OpenCode plugin placement, and `apm`
  subprocess invocation all live in this single file.
- `tests/test_cli.py` — CLI-level tests: argument parsing, `main()` dispatch, global paths, OpenCode plugin
  placement (fixture project in `tests/fixtures/plugins`).

## Key concepts

- `TARGET_DIRS` — local (CWD-relative) install dir per platform, e.g. `opencode` → `.opencode`.
- `GLOBAL_PATHS` — per-OS global agent install dirs per platform, used when `-g/--global` is passed.
- `place_opencode_plugin(global_)` — copies `apm_modules/**/opencode/plugins/*.[tj]s` into the
  OpenCode `plugins` dir.
- Subcommands (`build_parser()` in `src/apmw/__init__.py`): `install` and `update` run the real
  `apm` binary via `run_apm()` and then call `do_plugins()`.

## Dev workflow

```bash
uv sync
uv run pytest
```

No linter or formatter is configured in `pyproject.toml` — don't introduce one speculatively.

## Style

The codebase has no docstrings and minimal comments (only where a non-obvious rationale needs
capturing, e.g. the `claude` strip-fields comment). Keep additions flat and terse — match what's
already there rather than adding documentation blocks.
