# apmw user guide

`apmw` wraps the [apm](https://github.com/GravionLabs/apm-hub) CLI: it runs the real `apm install`
or `apm update` and then rewrites the installed agent frontmatter for the platform you target, so
one agent source file serves Claude Code, OpenCode, GitHub Copilot, Cursor and Codex.

The numbered list is the order of the guide and the sidebar of the documentation site.

1. [Getting started](getting-started.md): install `apmw`, the commands and their flags.
2. [Global install](global-install.md): the whole apm-hub skill set in every platform's global agent directory.
3. [Authoring multi-target agents](authoring-agents.md): one Copilot-style source file, a `metadata:` block per platform.
4. [Platform reference](platform-reference.md): strip rules, processing pipeline, OpenCode `permission:` and Claude Code `tools:`.
5. [Development](development.md): working on `apmw` itself.

Releases and prebuilt executables: [GitHub Releases](https://github.com/GravionLabs/apmw/releases) ·
changes: [CHANGELOG](https://github.com/GravionLabs/apmw/blob/main/CHANGELOG.md).
