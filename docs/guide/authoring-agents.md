# Authoring multi-target agents

Write one agent source file in Copilot style and let `apmw` derive the OpenCode and Claude Code variants from a `metadata:` block.

Agent source files (`*.agent.md`) are written in **GitHub Copilot style** as
the primary format. Each platform understands only a subset of frontmatter
fields — `apmw` strips the incompatible ones and can also inject
platform-specific additions via a reserved `metadata:` key.

## Field compatibility

| Field            | Copilot | OpenCode | Claude Code | Cursor / Codex |
| :--------------- | :-----: | :------: | :---------: | :------------: |
| `name`           |    ✅    |    ✅     |      ✅      |       ✅        |
| `description`    |    ✅    |    ✅     |      ✅      |       ✅        |
| `tools`          |    ✅    |    ❌ †   |      ✅ *    |       ✅        |
| `mode`           |    ✅    |    ✅ †   |      ❌      |       ❌        |
| `steps`          |    ✅    |    ❌     |      ❌      |       ❌        |
| `color`          |    ✅    |    ❌     |      ❌      |       ❌        |
| `permission`     |    ❌    |    ✅ †   |      ❌      |       ❌        |
| `user-invocable` |    ✅    |    ❌     |      ❌      |       ❌        |
| `model`          |    ✅    |    ✅ †   |      ✅ *    |       ✅        |
| `skills`         |    ❌    |    ❌     |      ✅ *    |       ❌        |
| `agents`         |    ✅    |    ❌     |      ❌      |       ✅        |

\* Claude Code reads `tools`, `model` and `skills` from `metadata.claude` (the top-level Copilot
values are stripped because the tool names and model ids differ).
† OpenCode reads `mode`, `model` and `permission` from `metadata.opencode`; its list-form `tools`
is rejected at load time, so `tools` is always stripped.

The four agents shipped by apm-hub (`dev-workflow`, `explorer`, `reviewer`, `implementer`) are the
reference fixtures: [`tests/fixtures/agents/*.agent.md`](https://github.com/GravionLabs/apmw/tree/main/tests/fixtures/agents) with the expected output per platform under
`tests/fixtures/expected/<platform>/`. `apmw sanitize --dry-run -p <platform>` prints the diff
without writing.

*Claude Code uses different tool identifiers than Copilot (`Bash` vs `run_in_terminal`, etc.).

## `metadata:` — platform-specific overrides

Add a `metadata:` block to supply fields that only apply to a specific
platform. `apmw` extracts the block for the target platform, injects the
lines into the sanitized frontmatter, and strips `metadata:` itself from all
outputs. **Metadata wins on conflict** — if both the top level and
`metadata.opencode` define `permission:`, the metadata version is used.

```yaml
---
name: dev-workflow
description: "Dev workflow orchestrator."
# Copilot-native fields — kept as-is in the Copilot output
mode: all
steps: 40
color: primary
tools: ['agent', 'read', 'search']
user-invocable: true
# Platform-specific overrides (never appear in any output file)
metadata:
  opencode:
    permission:
      read: allow
      edit: deny
      glob: allow
      grep: allow
      bash:
        "*": deny
      task: allow
      skill: allow
      webfetch: allow
      question: allow
  claude:
    tools:
      - Bash
      - Read
      - Glob
      - Grep
      - WebFetch
      - Task
---

Agent body — unchanged across all platforms.
```

## What each platform receives

**`.github/agents/dev-workflow.agent.md`** — Copilot output (`metadata:` stripped, all else kept):
```yaml
---
name: dev-workflow
description: "Dev workflow orchestrator."
mode: all
steps: 40
color: primary
tools: ['agent', 'read', 'search']
user-invocable: true
---
```

**`.opencode/agents/dev-workflow.md`** — `permission:` injected from `metadata.opencode`; Copilot-only fields stripped by default:
```yaml
---
name: dev-workflow
description: "Dev workflow orchestrator."
mode: all
steps: 40
color: primary
permission:
  read: allow
  edit: deny
  glob: allow
  grep: allow
  bash:
    "*": deny
  task: allow
  skill: allow
  webfetch: allow
  question: allow
---
```

**`.claude/agents/dev-workflow.md`** — Claude-native `tools:` injected from `metadata.claude`; all incompatible fields stripped:
```yaml
---
name: dev-workflow
description: "Dev workflow orchestrator."
tools:
  - Bash
  - Read
  - Glob
  - Grep
  - WebFetch
  - Task
---
```
