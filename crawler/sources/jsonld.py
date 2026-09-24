"""Generic fallback: schema.org JobPosting JSON-LD, which career pages publish for Google Jobs.
Works for Teamtailor, Jobylon, Varbi, ReachMee, Laura, Sympa and most custom career sites."""
import json, re
from urllib.parse import urljoin, urlparse
from ..http import get_text
from ..models import Job
from ..text import html_to_text
from ..classify import PATTERNS

LINK_HINT = re.compile("|".join(rx for _, rx in PATTERNS).replace(r"\b", ""), re.I)
JOB_HOSTS = ("teamtailor.com", "jobylon.com", "varbi.com", "reachmee.com", "laura.fi", "sympahr.net", "talentadore.com", "emply.com", "hr-manager.net")

def _jsonld(html_src: str) -> list[dict]:
    out = []
    for m in re.finditer(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html_src):
        try:
            data = json.loads(m.group(1).strip())
        except ValueError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                if d.get("@type") in ("JobPosting", ["JobPosting"]): out.append(d)
                stack += [v for k, v in d.items() if k in ("@graph", "itemListElement", "item")] 
            elif isinstance(d, list):
                stack += d
    return [d for d in out if isinstance(d, dict)]

def _loc(p: dict) -> str:
    locs = p.get("jobLocation") or []
    locs = locs if isinstance(locs, list) else [locs]
    parts = []
    for l in locs:
        a = (l or {}).get("address") or {}
        if isinstance(a, str): parts.append(a); continue
        parts.append(", ".join(filter(None, [a.get("addressLocality"), a.get("addressCountry") if isinstance(a.get("addressCountry"), str) else (a.get("addressCountry") or {}).get("name")])))
    if p.get("jobLocationType") == "TELECOMMUTE": parts.append("Remote")
    return " / ".join(filter(None, parts))

def _job(p: dict, c: dict, url: str) -> Job:
    html_src = p.get("description", "")
    org = p.get("hiringOrganization") or {}
    return Job(source="jsonld", source_id=str(p.get("identifier", {}).get("value") if isinstance(p.get("identifier"), dict) else p.get("identifier") or p.get("url") or url),
        company=c.get("name") or org.get("name", ""), company_slug=c["slug"], title=html_to_text(p.get("title", "")), url=p.get("url") or url,
        location=_loc(p), description=html_to_text(html_src), description_html=html_src, posted_at=p.get("datePosted"),
        deadline=p.get("validThrough"), employment_hint=str(p.get("employmentType", "")), industry=c.get("industry", ""))

def fetch(c, max_pages=25) -> list[Job] | None:
    root = c.get("careers_url")
    page = get_text(root) if root else None
    if page is None: return None
    jobs = [_job(p, c, root) for p in _jsonld(page)]
    host = urlparse(root).netloc
    links = []
    for m in re.finditer(r'(?is)<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', page):
        href, text = urljoin(root, m.group(1)), html_to_text(m.group(2))
        h = urlparse(href).netloc
        if (h == host or h.endswith(JOB_HOSTS)) and (LINK_HINT.search(text) or LINK_HINT.search(href)) and href not in links:
            links.append(href)
    for href in links[:max_pages]:
        sub = get_text(href)
        if sub: jobs += [_job(p, c, href) for p in _jsonld(sub)]
    return jobs
