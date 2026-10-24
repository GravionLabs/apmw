import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from apmw import TARGET_STRIP_FIELDS, sanitize_installed

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
        if e.code == 429 or (e.code == 403 and e.headers.get("X-RateLimit-Remaining") == "0"):
            pytest.skip(f"apm-hub rate limited (HTTP {e.code}) for {url}; set GITHUB_TOKEN")
        hint = "; check APM_HUB_REF" if e.code == 404 and "?ref=" in url else ""
        pytest.fail(f"apm-hub request failed: HTTP {e.code} for {url}{hint}")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
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
    m = re.match(r"---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.S)
    assert m, f"{name} ({platform}): frontmatter missing or not closed"
    return m.group(1)


def _has(fm: str, key: str) -> bool:
    return re.search(rf"^{re.escape(key)}\s*:", fm, re.M) is not None


@pytest.mark.network
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


class _Resp:
    def __init__(self, body: bytes = b"ok"):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.body


def _http_error(code: int, headers: dict[str, str] | None = None):
    return urllib.error.HTTPError("u", code, "msg", headers or {}, None)  # type: ignore[arg-type]


def _raises(exc):
    def urlopen(req, timeout=None):
        raise exc

    return urlopen


def test_get_skips_on_rate_limit(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _raises(_http_error(403, {"X-RateLimit-Remaining": "0"})))
    with pytest.raises(pytest.skip.Exception, match="rate limited"):
        _get("https://api.github.com/x")
    monkeypatch.setattr(urllib.request, "urlopen", _raises(_http_error(429)))
    with pytest.raises(pytest.skip.Exception, match="rate limited"):
        _get("https://api.github.com/x")


def test_get_fails_on_plain_403(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _raises(_http_error(403, {"X-RateLimit-Remaining": "5"})))
    with pytest.raises(pytest.fail.Exception, match="HTTP 403"):
        _get("https://api.github.com/x")


def test_get_404_hints_ref_only_for_ref_urls(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _raises(_http_error(404)))
    with pytest.raises(pytest.fail.Exception, match="APM_HUB_REF"):
        _get("https://api.github.com/contents?ref=nope")
    with pytest.raises(pytest.fail.Exception) as e:
        _get("https://api.github.com/releases/latest")
    assert "APM_HUB_REF" not in str(e.value)


@pytest.mark.parametrize("exc", [urllib.error.URLError("down"), TimeoutError("slow"), ConnectionResetError("reset")])
def test_get_skips_on_connection_errors(monkeypatch, exc):
    monkeypatch.setattr(urllib.request, "urlopen", _raises(exc))
    with pytest.raises(pytest.skip.Exception, match="unreachable"):
        _get("https://api.github.com/x")


@pytest.mark.parametrize(
    "url, sent",
    [("https://api.github.com/x", True), ("https://raw.githubusercontent.com/x", False)],
)
def test_get_sends_token_only_to_api_github(monkeypatch, url, sent):
    seen = []
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: seen.append(req) or _Resp())
    assert _get(url) == b"ok"
    assert (seen[0].get_header("Authorization") == "Bearer tok") == sent


@pytest.mark.parametrize("text", ["---\r\na: 1\r\n---\r\nbody", "---\na: 1\n---"])
def test_frontmatter_handles_crlf_and_eof_fence(text):
    assert _frontmatter(text, "a", "claude").strip() == "a: 1"


def test_frontmatter_unclosed_names_agent_and_platform():
    with pytest.raises(AssertionError, match=r"a \(claude\)"):
        _frontmatter("---\na: 1\nbody", "a", "claude")
