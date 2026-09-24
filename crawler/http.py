"""Polite HTTP: one client, per-host pacing, retries on 429/5xx, robots.txt for HTML pages."""
import threading, time
from urllib.parse import urlparse
from urllib import robotparser
import httpx
from .config import USER_AGENT

_client = httpx.Client(timeout=httpx.Timeout(15, connect=8), follow_redirects=True, headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/html;q=0.9"})
_last: dict[str, float] = {}
_lock = threading.Lock()
_robots: dict[str, robotparser.RobotFileParser | None] = {}
MIN_INTERVAL = 1.0      # seconds between requests to the same website
API_INTERVAL = 0.25     # public ATS APIs are built for this traffic
API_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "recruitee.com", "smartrecruiters.com", "workable.com", "jobtechdev.se")

def _pace(host: str):
    gap = API_INTERVAL if host.endswith(API_HOSTS) else MIN_INTERVAL
    key = next((h for h in API_HOSTS if host.endswith(h)), host)
    with _lock:
        wait = _last.get(key, 0) + gap - time.monotonic()
        _last[key] = max(time.monotonic(), _last.get(key, 0) + gap)
    if wait > 0:
        time.sleep(wait)

def allowed(url: str) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = robotparser.RobotFileParser()
        try:
            r = _client.get(base + "/robots.txt", timeout=10)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except httpx.HTTPError:
            rp.parse([])
        _robots[base] = rp
    rp = _robots[base]
    return rp.can_fetch(USER_AGENT, url) if rp else True

def request(method: str, url: str, *, check_robots=False, retries=2, **kw) -> httpx.Response | None:
    if check_robots and not allowed(url):
        return None
    host = urlparse(url).netloc
    for attempt in range(retries + 1):
        _pace(host)
        try:
            r = _client.request(method, url, **kw)
        except httpx.HTTPError:
            if attempt == retries:
                return None
            time.sleep(2 * (attempt + 1)); continue
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(float(r.headers.get("Retry-After", 3 * (attempt + 1)))); continue
        return r
    return None

def get_json(url: str, **kw):
    r = request("GET", url, **kw)
    if r is None or r.status_code != 200:
        return None
    try:
        return r.json()
    except ValueError:
        return None

def get_text(url: str, **kw) -> str | None:
    r = request("GET", url, check_robots=True, **kw)
    return r.text if r is not None and r.status_code == 200 else None
