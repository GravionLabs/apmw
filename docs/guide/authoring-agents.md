# Authoring multi-target agents

Write one agent source file in Copilot style and let `apmw` derive the OpenCode and Claude Code variants from a `metadata:` block.

Agent source files (`*.agent.md`) are written in **GitHub Copilot style** as
the primary format. Each platform understands only a subset of frontmatter
fields — `apmw` strips the incompatible ones and can also inject
platform-specific additions via a reserved `metadata:` key.

## Field compatibility

✅ means `apmw` keeps the top-level field for that platform, ❌ means it strips it (rules in
[Platform reference](platform-reference.md)). Fields not listed are never stripped.

| Field            | Copilot | OpenCode | Claude Code | Cursor / Codex |
| :--------------- | :-----: | :------: | :---------: | :------------: |
| `name`           |    ✅    |    ✅     |      ✅      |       ✅        |
| `description`    |    ✅    |    ✅     |      ✅      |       ✅        |
| `tools`          |    ✅    |    ❌ †   |      ❌ *    |       ✅        |
| `mode`           |    ❌    |    ✅     |      ❌      |       ❌        |
| `steps`          |    ❌    |    ✅     |      ❌      |       ❌        |
| `color`          |    ❌    |    ✅     |      ❌      |       ❌        |
| `permission`     |    ❌    |    ✅     |      ❌      |       ❌        |
| `task`           |    ❌    |    ✅     |      ✅      |       ✅        |
| `user-invocable` |    ✅    |    ❌     |      ❌      |       ✅        |
| `model`          |    ✅    |    ✅     |      ❌ *    |       ✅        |
| `agents`         |    ✅    |    ❌     |      ❌      |       ✅        |
| `skills`         |    ✅    |    ✅     |      ✅      |       ✅        |

\* Claude Code uses different tool identifiers and model ids than Copilot (`Bash` vs
`run_in_terminal`), so `tools` and `model` come only from `metadata.claude`.
† OpenCode rejects list-form `tools` at load time, so `tools` is always stripped.

Whether a platform actually supports a kept field is up to the platform. To give one platform a
field the table strips (for example `tools` or `model` for Claude Code, `permission` for
OpenCode), put it under `metadata.<platform>`.

The four agents shipped by apm-hub (`dev-workflow`, `explorer`, `reviewer`, `implementer`) are the
reference fixtures: [`tests/fixtures/agents/*.agent.md`](https://github.com/GravionLabs/apmw/tree/main/tests/fixtures/agents) with the expected output per platform under
`tests/fixtures/expected/<platform>/`. `apmw sanitize --dry-run -p <platform>` prints the diff
without writing.

## `metadata:` — platform-specific overrides

Add a `metadata:` block to supply fields that only apply to a specific
platform. `apmw` extracts the block for the target platform, injects the
lines into the sanitized frontmatter, and strips `metadata:` itself from all
outputs. **Metadata wins on conflict** — if both the top level and
`metadata.opencode` define `permission:`, the metadata version is used.

The example is the `dev-workflow` fixture (description shortened):

```yaml
---
name: dev-workflow
description: Issue orchestrator. Modes plan|implement|full <issue>. …
tools: ['agent', 'read', 'search', 'execute']
user-invocable: true
metadata:
  claude:
    tools: [Agent, Read, Grep, Glob, Bash, Skill, AskUserQuestion]
    model: inherit
  opencode:
    mode: primary
    permission:
      read: allow
      glob: allow
      grep: allow
      edit: deny
      task: allow
      skill: allow
      question: allow
      bash:
        "git *": allow
        "gh *": allow
        "*": ask
---

Agent body — unchanged across all platforms.
```

## What each platform receives

**`.github/agents/dev-workflow.agent.md`** — Copilot output (`metadata:` stripped, all else kept):
```yaml
---
name: dev-workflow
description: Issue orchestrator. Modes plan|implement|full <issue>. …
tools: ['agent', 'read', 'search', 'execute']
user-invocable: true
---
```

**`.opencode/agents/dev-workflow.md`** — `mode` and `permission` injected from `metadata.opencode`; Copilot-only fields stripped:
```yaml
---
name: dev-workflow
description: Issue orchestrator. Modes plan|implement|full <issue>. …
mode: primary
permission:
  read: allow
  glob: allow
  grep: allow
  edit: deny
  task: allow
  skill: allow
  question: allow
  bash:
    "git *": allow
    "gh *": allow
    "*": ask
---
```

**`.claude/agents/dev-workflow.md`** — Claude-native `tools` and `model` injected from `metadata.claude`; all incompatible fields stripped:
```yaml
---
name: dev-workflow
description: Issue orchestrator. Modes plan|implement|full <issue>. …
tools: [Agent, Read, Grep, Glob, Bash, Skill, AskUserQuestion]
model: inherit
---
```
