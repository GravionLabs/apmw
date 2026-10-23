import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from apmw import TARGET_STRIP_FIELDS, sanitize_installed

pytestmark = pytest.mark.network

REPO = "GravionLabs/apm-hub"
PLATFORMS = ["claude", "copilot", "opencode"]
INSTALLED_NAME = {"claude": "{name}.md", "copilot": "{name}.agent.md", "opencode": "{name}.md"}


def _get(url: str) -> bytes:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "apmw-contract-test"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and urllib.parse.urlparse(url).hostname == "api.github.com":
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            pytest.skip(f"apm-hub rate limited (HTTP {e.code}) for {url}; set GITHUB_TOKEN")
        if e.code == 404:
            pytest.fail(f"apm-hub not found (HTTP 404) for {url}; check APM_HUB_REF")
        pytest.fail(f"apm-hub request failed: HTTP {e.code} for {url}")
    except urllib.error.URLError as e:
        pytest.skip(f"apm-hub unreachable: {e}")


@pytest.fixture(scope="module")
def hub_agents() -> dict[str, str]:
    ref = os.environ.get("APM_HUB_REF") or json.loads(
        _get(f"https://api.github.com/repos/{REPO}/releases/latest")
    )["tag_name"]
    url = f"https://api.github.com/repos/{REPO}/contents/packages/agents/.apm/agents?ref={urllib.parse.quote(ref, safe='')}"
    listing = json.loads(_get(url))
    assert isinstance(listing, list), f"apm-hub listing at ref {ref} is not a directory list: {str(listing)[:200]}"
    agents = {
        e["name"].removesuffix(".agent.md"): _get(e["download_url"]).decode()
        for e in listing
        if e["name"].endswith(".agent.md")
    }
    assert agents, f"no agents found in apm-hub at ref {ref}"
    return agents


def _frontmatter(text: str, name: str, platform: str) -> str:
    parts = text.split("---\n")
    assert len(parts) >= 3 and parts[0] == "", f"{name} ({platform}): frontmatter does not parse"
    return parts[1]


def _has(fm: str, key: str) -> bool:
    return re.search(rf"^{re.escape(key)}\s*:", fm, re.M) is not None


@pytest.mark.parametrize("platform", PLATFORMS)
def test_published_agents_sanitize_per_platform(tmp_path: Path, hub_agents: dict[str, str], platform: str):
    d = tmp_path / platform / "agents"
    d.mkdir(parents=True)
    for name, text in hub_agents.items():
        (d / INSTALLED_NAME[platform].format(name=name)).write_text(text)

    changed = sanitize_installed(d, TARGET_STRIP_FIELDS[platform], platform)
    assert changed == len(hub_agents), f"{platform}: sanitized {changed} of {len(hub_agents)} agents"

    for name in hub_agents:
        fm = _frontmatter((d / INSTALLED_NAME[platform].format(name=name)).read_text(), name, platform)

        def has(key: str) -> bool:
            return _has(fm, key)

        assert not has("metadata"), f"{name} ({platform}): metadata survived"
        if platform != "copilot":
            assert not has("disable-model-invocation"), f"{name} ({platform}): disable-model-invocation present"
        if platform == "opencode":
            assert has("mode"), f"{name} (opencode): mode missing"
            assert has("permission"), f"{name} (opencode): permission missing"
            assert not has("tools"), f"{name} (opencode): tools present"
        elif platform == "claude":
            assert has("tools"), f"{name} (claude): tools missing"
            assert not has("user-invocable"), f"{name} (claude): user-invocable present"
        else:
            assert has("tools"), f"{name} (copilot): tools missing"
            assert not has("permission"), f"{name} (copilot): permission present"
