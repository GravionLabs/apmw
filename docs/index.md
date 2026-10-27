---
layout: home
title: apmw
hero:
  name: apmw
  text: apm, plus OpenCode plugins
  tagline: Runs apm install or update and then places the OpenCode plugins of the installed packages.
  actions:
    - theme: brand
      text: Read the guide
      link: /guide/
    - theme: alt
      text: GitHub
      link: https://github.com/GravionLabs/apmw
features:
  - title: Wraps the real apm
    details: apmw install and apmw update call apm and copy the OpenCode plugins of the installed packages afterwards.
  - title: Global or per project
    details: Place plugins in the global OpenCode directory of a machine, or in the .opencode folder of one repository.
  - title: Single-file executables
    details: Linux, macOS and Windows builds without a Python environment on every GitHub release; pipx, uv tool or uvx otherwise.
---

```bash
pipx install apmw
apmw install all@apm-hub -g -p claude
```
