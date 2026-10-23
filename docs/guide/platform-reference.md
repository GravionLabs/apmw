# Platform reference

Strip rules, the processing pipeline, and the frontmatter each platform accepts.

## Strip rules

The strip rules are loaded from `src/apmw/data/agent-strip-fields.json`, the only source of truth:

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

## Processing pipeline

For each `*.md` file in the target agent directory, `apmw` runs:

1. **Extract** — find `metadata.<platform>` and de-indent its content lines.
2. **Strip** — remove fields in the platform's strip list (including `metadata`).
3. **Inject** — if step 1 produced lines: strip any conflicting top-level fields, then append the extracted lines. Metadata wins.
   Missing `tools` (Claude Code) or `permission` (OpenCode) are derived from the Copilot `tools:` list, see [Authoring multi-target agents](authoring-agents.md#derived-fields-when-metadata-is-missing).
4. **Rewrite** — write the file only if the frontmatter changed.

For OpenCode only, `apmw` also places the hooks plugin: it globs `apm_modules/**/opencode/plugins/*.ts|js`
in the working directory and copies each match to `.opencode/plugins/`. The copy is skipped when the content
is identical, a missing plugin is silently ignored, `--dry-run` writes nothing, and the count appears in the
`Done:` line. Other platforms are untouched.

## OpenCode `permission:` reference

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

## Claude Code `tools:` reference

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
