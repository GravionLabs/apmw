# Global install

Install the whole apm-hub skill set into the global agent directories of every platform on a machine.

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

**Global agent paths per platform.** `apmw sanitize -g` visits every listed directory. For OpenCode,
Claude Code and Copilot the first entry is where `apm install -g` writes (verified with apm 0.33);
the others are fallbacks for hand-made installs.

| Platform | Linux | macOS | Windows |
| :------- | :---- | :---- | :------ |
| OpenCode | `~/.config/opencode/agents` | `~/.config/opencode/agents` · `~/Library/Application Support/opencode/agents` | `%USERPROFILE%\.config\opencode\agents` · `%APPDATA%\opencode\agents` |
| Claude Code | `~/.claude/agents` · `~/.config/claude/agents` | `~/.claude/agents` · `~/Library/Application Support/claude/agents` | `%USERPROFILE%\.claude\agents` · `%APPDATA%\Claude\agents` |
| GitHub Copilot | `~/.copilot/agents` · `~/.config/github-copilot/agents` | `~/.copilot/agents` · `~/Library/Application Support/github-copilot/agents` | `%USERPROFILE%\.copilot\agents` · `%APPDATA%\GitHub Copilot\agents` |
| Cursor | `~/.cursor/agents` · `~/.config/cursor/agents` | `~/Library/Application Support/cursor/agents` | `%APPDATA%\Cursor\agents` |
| Codex | `~/.codex/agents` | `~/.codex/agents` | `%APPDATA%\Codex\agents` |

**OpenCode hooks plugin.** With `-p opencode -g`, `apmw` globs `~/.apm/apm_modules/**/opencode/plugins/*.ts|js`
and copies each match to the `plugins` directory next to the first OpenCode agents path
(`~/.config/opencode/plugins` on Linux and macOS). Identical files are skipped and a missing plugin is a no-op.
