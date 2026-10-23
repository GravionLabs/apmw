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
| `disable-model-invocation` |    ✅    |    ❌     |      ❌      |       ❌        |
| `model`          |    ✅    |    ✅     |      ❌ *    |       ✅        |
| `agents`         |    ✅    |    ❌     |      ❌      |       ✅        |
| `skills`         |    ✅    |    ✅     |      ✅      |       ✅        |

\* Claude Code uses different tool identifiers and model ids than Copilot (`Bash` vs
`run_in_terminal`), so `tools` and `model` come only from `metadata.claude`.
† OpenCode rejects list-form `tools` at load time, so `tools` is always stripped.

Whether a platform actually supports a kept field is up to the platform. To give one platform a
field the table strips (for example `tools` or `model` for Claude Code, `permission` for
OpenCode), put it under `metadata.<platform>`.

The nine agents shipped by apm-hub (`explorer`, `implementer`, `issue-reader`, `orchestrator`,
`pbi-runner`, `planner`, `pr-writer`, `review-lead`, `reviewer`) are the
reference fixtures: [`tests/fixtures/agents/*.agent.md`](https://github.com/GravionLabs/apmw/tree/main/tests/fixtures/agents) with the expected output per platform under
`tests/fixtures/expected/<platform>/`. `apmw sanitize --dry-run -p <platform>` prints the diff
without writing.

## `metadata:` — platform-specific overrides

Add a `metadata:` block to supply fields that only apply to a specific
platform. `apmw` extracts the block for the target platform, injects the
lines into the sanitized frontmatter, and strips `metadata:` itself from all
outputs. **Metadata wins on conflict** — if both the top level and
`metadata.opencode` define `permission:`, the metadata version is used.

The example is the `orchestrator` fixture (description shortened):

```yaml
---
name: orchestrator
description: Issue orchestrator. Modes plan|implement|full|next|loop|status <issue>. …
tools: ['agent', 'read', 'search', 'execute']
user-invocable: true
disable-model-invocation: true
metadata:
  claude:
    tools: [Agent, Read, Grep, Glob, Bash, Skill, AskUserQuestion, SendMessage]
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

## Derived fields when metadata is missing

For Claude Code and OpenCode, `apmw` decides per field in this order:

1. `metadata.<platform>` defines the field → that value is used.
2. A top-level field the platform keeps (OpenCode `permission`, Claude Code `tools` or `model` that
   already use Claude names) → it stays as it is. This also makes a second `apmw sanitize` run on
   an already sanitized directory a no-op.
3. Otherwise the field is **derived from the Copilot `tools:` list**.
4. No `tools:` in the source → nothing is added.

The Copilot aliases map like this (the Claude and OpenCode names of a tool are accepted as synonyms):

| Copilot `tools` | Claude Code `tools` | OpenCode `permission` |
| :-------------- | :------------------ | :-------------------- |
| `read`          | `Read`              | `read`                |
| `search`        | `Grep`, `Glob`      | `grep`, `glob`        |
| `edit`          | `Edit`, `Write`     | `edit`                |
| `execute`       | `Bash`              | `bash`                |
| `agent`         | `Agent`             | `task`                |
| `web`           | `WebFetch`, `WebSearch` | `webfetch`        |
| `todo`          | `TodoWrite`         | —                     |

Claude Code gets `tools: [Agent, Read, Grep, Glob, Bash]` for `['agent', 'read', 'search', 'execute']`.
`model` is never derived; Claude inherits the session model. OpenCode gets a `permission:` block
that lists `read`, `glob`, `grep`, `edit`, `bash`, `task` and `webfetch`: listed tools `allow`, the
rest `deny`, because the Copilot list is an allowlist. Entries without a mapping, such as MCP tools
(`github/*`), are skipped and named in the output line (`derived tools (unmapped: github/*)`).
Anything these tables cannot express, such as `skill` or `question` permissions or extra Claude
tools like `Skill`, belongs in `metadata.<platform>`.

## What each platform receives

**`.github/agents/orchestrator.agent.md`** — Copilot output (`metadata:` stripped, all else kept):
```yaml
---
name: orchestrator
description: Issue orchestrator. Modes plan|implement|full|next|loop|status <issue>. …
tools: ['agent', 'read', 'search', 'execute']
user-invocable: true
disable-model-invocation: true
---
```

**`.opencode/agents/orchestrator.md`** — `mode` and `permission` injected from `metadata.opencode`; Copilot-only fields (`tools`, `user-invocable`, `disable-model-invocation`) stripped:
```yaml
---
name: orchestrator
description: Issue orchestrator. Modes plan|implement|full|next|loop|status <issue>. …
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

**`.claude/agents/orchestrator.md`** — Claude-native `tools` and `model` injected from `metadata.claude`; all incompatible fields stripped:
```yaml
---
name: orchestrator
description: Issue orchestrator. Modes plan|implement|full|next|loop|status <issue>. …
tools: [Agent, Read, Grep, Glob, Bash, Skill, AskUserQuestion, SendMessage]
model: inherit
---
```
