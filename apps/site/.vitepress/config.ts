import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitepress';
import { sidebarOf } from './sidebar';

const REPO_URL = 'https://github.com/GravionLabs/apmw';
const repoRoot = resolve(fileURLToPath(new URL('../../..', import.meta.url)));
const base = process.env['SITE_BASE'] ?? '/';
const readme = readFileSync(resolve(repoRoot, 'docs/guide/README.md'), 'utf8');

export default defineConfig({
  title: 'apmw',
  description:
    'Cross-platform wrapper for the apm CLI: one agent source file, sanitized frontmatter for Claude Code, OpenCode, GitHub Copilot, Cursor and Codex.',
  lang: 'en',
  // `/<repository>/` on GitHub Pages; the workflow sets SITE_BASE.
  base,
  // The site is the documentation of the repository: its pages are the files of `docs`.
  srcDir: '../../docs',
  // `docs/guide/README.md` is what GitHub shows for the folder, and the home of the guide here.
  rewrites: { 'guide/README.md': 'guide/index.md' },
  cleanUrls: true,
  lastUpdated: false,
  // A link that leads nowhere fails the build.
  ignoreDeadLinks: [/^https?:\/\/localhost(:\d+)?(\/|$)/],
  themeConfig: {
    siteTitle: 'apmw',
    nav: [
      { text: 'Guide', link: '/guide/' },
      { text: 'PyPI', link: 'https://pypi.org/project/apmw/' },
      { text: 'GitHub', link: REPO_URL },
    ],
    sidebar: sidebarOf(readme),
    search: { provider: 'local' },
    editLink: {
      pattern: `${REPO_URL}/edit/main/docs/:path`,
      text: 'Edit this page on GitHub',
    },
    socialLinks: [{ icon: 'github', link: REPO_URL }],
    footer: { message: 'Released under the MIT license.' },
  },
});
