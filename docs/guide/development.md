# Development

Working on `apmw` itself.

```bash
uv sync
uv run pytest
```

## Tests

`uv run pytest` is offline. The golden tests (`tests/test_fixtures.py`) sanitize a pinned set of
five agents in `tests/fixtures/agents` and compare against `tests/fixtures/expected/<platform>/`.
When the sanitize format changes, regenerate the goldens with `sanitize_installed`.

`uv run pytest -m network` runs the contract test (`tests/test_apm_hub_contract.py`), which
fetches the agents of the latest published apm-hub release and checks platform invariants. Set
`APM_HUB_REF` to test another tag and `GITHUB_TOKEN` to avoid GitHub API rate limits. CI runs it
nightly.

No linter or formatter is configured — don't introduce one speculatively.

## Documentation site

The guide in `docs/` is published with VitePress (`apps/site`):

```bash
pnpm install
pnpm --filter @apmw/site dev     # preview with hot reload
pnpm --filter @apmw/site test    # sidebar list matches the pages on disk
pnpm --filter @apmw/site build   # fails on dead links
```
