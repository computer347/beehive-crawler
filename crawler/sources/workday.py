"""Workday career sites (common at large Nordic employers). Configure with the public careers URL,
e.g. https://company.wd3.myworkdayjobs.com/en-US/Careers. This uses the same JSON the careers page loads."""
import re
from ..http import request, get_json
from ..models import Job
from ..text import html_to_text
from ..classify import student_type

SEARCH = ["intern", "summer", "trainee", "thesis", "harjoittelija", "kesä", "praktikant", "sommar", "sommer", "student"]

def parse(url):
    m = re.match(r"https://([\w.-]+\.myworkdayjobs\.com)/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)", url)
    if not m: return None
    host, site = m.groups()
    return host, host.split(".")[0], site

def fetch(c) -> list[Job] | None:
    p = parse(c.get("careers_url", ""))
    if not p: return None
    host, tenant, site = p
    base = f"https://{host}/wday/cxs/{tenant}/{site}"
    seen, out = set(), []
    ok = False
    for term in SEARCH:
        r = request("POST", f"{base}/jobs", json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": term})
        if r is None or r.status_code != 200: continue
        ok = True
        for j in r.json().get("jobPostings", []):
            path = j.get("externalPath")
            if not path or path in seen or not student_type(j.get("title", "")): continue
            seen.add(path)
            info = (get_json(base + path) or {}).get("jobPostingInfo", {})
            html_src = info.get("jobDescription", "")
            out.append(Job(source="workday", source_id=info.get("jobReqId") or path, company=c["name"], company_slug=c["slug"],
                title=j.get("title", ""), url=info.get("externalUrl") or f"https://{host}/{site}{path}",
                location=info.get("location") or j.get("locationsText", ""), description=html_to_text(html_src), description_html=html_src,
                posted_at=info.get("startDate"), employment_hint=info.get("timeType", ""), industry=c.get("industry", "")))
    return out if ok else None
