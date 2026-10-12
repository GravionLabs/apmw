# Development

Working on `apmw` itself.

```bash
uv sync
uv run pytest
```

No linter or formatter is configured — don't introduce one speculatively.

## Documentation site

The guide in `docs/` is published with VitePress (`apps/site`):

```bash
pnpm install
pnpm --filter @apmw/site dev     # preview with hot reload
pnpm --filter @apmw/site test    # sidebar list matches the pages on disk
pnpm --filter @apmw/site build   # fails on dead links
```
