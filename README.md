# apmw

Cross-platform wrapper for the [apm](https://github.com/GravionLabs) CLI.

`apm install` and `apm update` deploy platform-neutral skills cleanly, but
agent files carry platform-specific frontmatter (`permission`, `mode`,
`tools`, etc.) that each target — Claude Code, OpenCode, GitHub Copilot,
Cursor, Codex — interprets differently. `apmw` runs the real `apm` command
and then sanitizes the installed agent frontmatter for the target platform
you specify.

---

## Install

```bash
pipx install apmw
# or
uvx apmw install -p claude
```

Prebuilt single-file executables (linux, macOS-arm64, windows) that need no Python environment
are attached to each [GitHub Release](https://github.com/GravionLabs/apmw/releases).

### Local development install

To install the local checkout (editable — picks up source edits immediately):

```bash
./install.sh       # Linux / macOS
.\install.ps1      # Windows
```

Uses `uv tool install` if `uv` is on `PATH`, falling back to `pipx`.

---

## Usage

```bash
apmw install -p claude      # apm install + sanitize for Claude Code
apmw install -p opencode    # apm install + sanitize for OpenCode
apmw update  -p copilot     # apm update + sanitize for GitHub Copilot
apmw sanitize -p claude     # sanitize an already-installed local agent dir (no apm call)
apmw sanitize -g -p claude  # sanitize the global Claude Code agent dir
apmw sanitize               # sanitize for every known platform
```

**Flags:**

| Flag | Description |
| :--- | :---------- |
| `-p, --platform` | Target: `opencode`, `copilot`, `claude`, `cursor`, `codex`; omit to run for all |
| `-g, --global` | Sanitize the platform's global agent install directory instead of the project dir |
| `-s, --source` | Also inject `permission:` blocks into source agent files under `packages/` |
| `-y, --yes` | (`update` only) Skip consent prompt |
| `--dry-run` | (`update` only) Preview changes without writing |

`apmw install`/`update` require `apm` to be installed and on `PATH`.  
`apmw sanitize` operates only on local files and does not invoke `apm`.

---

## Global install — all packages

Install the full apm-hub skill set into the global agent directories so every
repository on the machine benefits without a per-project `apm install`:

```bash
# 1. Register the marketplace (once per machine)
apm marketplace add GravionLabs/apm-hub

# 2. Install the meta-package globally
apmw install all@apm-hub -g -p opencode
apmw install all@apm-hub -g -p claude
apmw install all@apm-hub -g -p copilot
```

`apmw install` calls `apm install -g` (which deploys to global paths) and then
sanitizes all agent files in those paths for the target platform.

**Global agent paths per platform** (where `apm install -g` writes, verified with apm 0.33;
the second entry is a fallback for hand-made installs):

| Platform       | Linux / macOS                                               | Windows                                                        |
| :------------- | :---------------------------------------------------------- | :------------------------------------------------------------- |
| OpenCode       | `~/.config/opencode/agents/`                                | `%USERPROFILE%\.config\opencode\agents\` · `%APPDATA%\opencode\agents\` |
| Claude Code    | `~/.claude/agents/` · `~/.config/claude/agents/`            | `%USERPROFILE%\.claude\agents\` · `%APPDATA%\Claude\agents\`   |
| GitHub Copilot | `~/.copilot/agents/` · `~/.config/github-copilot/agents/`   | `%USERPROFILE%\.copilot\agents\` · `%APPDATA%\GitHub Copilot\agents\` |
| Cursor         | `~/.cursor/agents/`                                         | `%APPDATA%\Cursor\agents\`                                     |
| Codex          | `~/.codex/agents/`                                          | `%APPDATA%\Codex\agents\`                                      |

### Transitive MCP server definitions

When a package declares MCP server entries in its `apm.yml`, `apm install`
propagates those definitions to consuming projects transitively. For example,
the `github` package may ship an MCP server configuration for the GitHub API:

```yaml
# packages/github/apm.yml
name: github
version: 1.0.0
mcp:
  servers:
    - name: github
      command: npx
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
```

When you run `apmw install all@apm-hub -g -p opencode`, the `all` meta-package
pulls in `github` (and every other package) transitively. `apm` writes the MCP
server entries to the platform's agent config file (e.g.
`~/.config/opencode/mcp.json`) so every project on the machine can use GitHub
MCP tools without any per-project setup.

---

## Multi-target agent authoring

Agent source files (`*.agent.md`) are written in **GitHub Copilot style** as
the primary format. Each platform understands only a subset of frontmatter
fields — `apmw` strips the incompatible ones and can also inject
platform-specific additions via a reserved `metadata:` key.

### Field compatibility

| Field            | Copilot | OpenCode | Claude Code | Cursor / Codex |
| :--------------- | :-----: | :------: | :---------: | :------------: |
| `name`           |    ✅    |    ✅     |      ✅      |       ✅        |
| `description`    |    ✅    |    ✅     |      ✅      |       ✅        |
| `tools`          |    ✅    |    ❌     |      ✅ *    |       ✅        |
| `mode`           |    ✅    |    ❌     |      ❌      |       ❌        |
| `steps`          |    ✅    |    ❌     |      ❌      |       ❌        |
| `color`          |    ✅    |    ❌     |      ❌      |       ❌        |
| `permission`     |    ❌    |    ✅     |      ❌      |       ❌        |
| `user-invocable` |    ✅    |    ❌     |      ❌      |       ❌        |
| `model`          |    ✅    |    ✅     |      ❌      |       ✅        |
| `agents`         |    ✅    |    ❌     |      ❌      |       ✅        |

*Claude Code uses different tool identifiers than Copilot (`Bash` vs `run_in_terminal`, etc.).

### `metadata:` — platform-specific overrides

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

### What each platform receives

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

### Strip rules

The strip rules are loaded from `src/apmw/data/agent-strip-fields.json` and
must be kept in sync with `apm-hub`'s `config/agent-strip-fields.json`:

```json
{
  "opencode":  ["tools", "user-invocable", "agents", "metadata"],
  "copilot":   ["mode", "steps", "color", "permission", "task", "metadata"],
  "claude":    ["mode", "steps", "color", "tools", "permission", "user-invocable", "agents", "model", "metadata"],
  "cursor":    ["mode", "steps", "color", "permission", "metadata"],
  "codex":     ["mode", "steps", "color", "permission", "metadata"]
}
```

`metadata` appears in every platform's list — it is always stripped after extraction.

### Processing pipeline

For each `*.md` file in the target agent directory, `apmw` runs:

1. **Extract** — find `metadata.<platform>` and de-indent its content lines.
2. **Strip** — remove fields in the platform's strip list (including `metadata`).
3. **Inject** — if step 1 produced lines: strip any conflicting top-level fields, then append the extracted lines. Metadata wins.
4. **Rewrite** — write the file only if the frontmatter changed.

### OpenCode `permission:` reference

```yaml
permission:
  read: allow          # file read
  edit: deny           # file write/edit
  glob: allow          # file glob search
  grep: allow          # content search
  bash:
    "*": deny          # deny all shell commands by default
    "git *": allow     # allow specific patterns
    "gh *": allow
  task: allow          # spawn sub-agents
  skill: allow         # load skills
  webfetch: allow      # HTTP fetch
  question: allow      # interactive prompts
```

### Claude Code `tools:` reference

```yaml
tools:
  - Bash        # shell commands
  - Read        # read files
  - Write       # create/overwrite files
  - Edit        # patch existing files
  - Glob        # file pattern search
  - Grep        # content search
  - WebFetch    # HTTP fetch
  - Task        # spawn sub-agents
  - TodoWrite   # task list management
```

---

## Development

```bash
uv sync
uv run pytest
```

No linter or formatter is configured — don't introduce one speculatively.
