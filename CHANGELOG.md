# Changelog

All notable changes to apmw are documented here.
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.1] — 2026-10-11

Planned as 0.2.0; GitVersion published the merge of `release/0.2` as 0.1.1 because `next-version` still said 0.1.0.

### Bug Fixes
- Correct the Copilot global agent path and verify global deploy paths (#7) (#9)


### Features
- Inject Claude and OpenCode metadata for the apm-hub agents and add fixture tests (#8) (#10)


## [0.1.0] — 2026-09-05

### Bug Fixes
- Migrate GitVersion config to v6.x workflow syntax
- Revert to mode: ContinuousDeployment and remove tag-prefix to fix GitVersion 6.x crash on empty tag repo
- Remove double /agents append in get_global_agents_dirs
- Add pytest-cov dependency to fix CI test coverage step
- Publish apmw to real PyPI via Trusted Publishing instead of GitHub Packages


### Documentation
- Document multi-target agent authoring, global install, and MCP example


### Features
- Support platform-specific metadata in agent frontmatter



