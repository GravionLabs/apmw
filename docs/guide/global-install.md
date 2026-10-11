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

**Global agent paths per platform** (where `apm install -g` writes, verified with apm 0.33;
the second entry is a fallback for hand-made installs):

| Platform       | Linux / macOS                                               | Windows                                                        |
| :------------- | :---------------------------------------------------------- | :------------------------------------------------------------- |
| OpenCode       | `~/.config/opencode/agents/`                                | `%USERPROFILE%\.config\opencode\agents\` · `%APPDATA%\opencode\agents\` |
| Claude Code    | `~/.claude/agents/` · `~/.config/claude/agents/`            | `%USERPROFILE%\.claude\agents\` · `%APPDATA%\Claude\agents\`   |
| GitHub Copilot | `~/.copilot/agents/` · `~/.config/github-copilot/agents/`   | `%USERPROFILE%\.copilot\agents\` · `%APPDATA%\GitHub Copilot\agents\` |
| Cursor         | `~/.cursor/agents/`                                         | `%APPDATA%\Cursor\agents\`                                     |
| Codex          | `~/.codex/agents/`                                          | `%APPDATA%\Codex\agents\`                                      |

## Transitive MCP server definitions

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
