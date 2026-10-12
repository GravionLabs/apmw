---
layout: home
title: apmw
hero:
  name: apmw
  text: One agent file, every platform
  tagline: Runs apm install or update and then rewrites the installed agent frontmatter for Claude Code, OpenCode, GitHub Copilot, Cursor or Codex.
  actions:
    - theme: brand
      text: Read the guide
      link: /guide/
    - theme: alt
      text: GitHub
      link: https://github.com/GravionLabs/apmw
features:
  - title: Wraps the real apm
    details: apmw install and apmw update call apm and sanitize afterwards; apmw sanitize works on an already-installed agent directory without apm.
  - title: Copilot style in, native out
    details: Write agents once in GitHub Copilot frontmatter. A metadata block per platform supplies tools, mode, model and permission where a target needs them.
  - title: Global or per project
    details: Sanitize the global agent directories of every platform on a machine, or the .claude, .opencode and .github folders of one repository.
  - title: Single-file executables
    details: Linux, macOS and Windows builds without a Python environment on every GitHub release; pipx, uv tool or uvx otherwise.
---

```bash
pipx install apmw
apmw install all@apm-hub -g -p claude
```
