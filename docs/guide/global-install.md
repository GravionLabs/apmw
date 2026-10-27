# Global install

Install the whole apm-hub skill set globally so every repository on the machine benefits without a
per-project `apm install`:

```bash
# 1. Register the marketplace (once per machine)
apm marketplace add GravionLabs/apm-hub

# 2. Install the meta-package globally
apmw install all@apm-hub -g -p opencode
apmw install all@apm-hub -g -p claude
apmw install all@apm-hub -g -p copilot
```

`apmw install` calls `apm install -g` (which deploys to global paths) and then places the OpenCode
plugin for `-p opencode`.

**OpenCode hooks plugin.** With `-p opencode -g`, `apmw` globs `~/.apm/apm_modules/**/opencode/plugins/*.ts|js`
and copies each match to the `plugins` directory next to the first OpenCode agents path
(`~/.config/opencode/plugins` on Linux and macOS). Identical files are skipped and a missing plugin is a no-op.
