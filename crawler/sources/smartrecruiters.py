from ..http import get_json
from ..models import Job
from ..text import html_to_text
from ..classify import student_type

def endpoint(slug, offset=0): return f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={offset}"

def fetch(c) -> list[Job] | None:
    first = get_json(endpoint(c["slug"]))
    if first is None or "content" not in first: return None
    items, total = list(first["content"]), first.get("totalFound", 0)
    while len(items) < min(total, 1000):
        page = get_json(endpoint(c["slug"], len(items)))
        if not page or not page.get("content"): break
        items += page["content"]
    out = []
    for j in items:
        title = j.get("name", "")
        if not student_type(title):   # descriptions cost one request each: only fetch likely student roles
            continue
        loc = j.get("location", {}) or {}
        detail = get_json(j["ref"]) if j.get("ref") else None
        sections = ((detail or {}).get("jobAd") or {}).get("sections") or {}
        html_src = "".join((sections.get(k) or {}).get("text", "") for k in ("jobDescription", "qualifications", "additionalInformation"))
        out.append(Job(source="smartrecruiters", source_id=j["id"], company=c["name"], company_slug=c["slug"], title=title,
            url=(detail or {}).get("postingUrl") or f"https://jobs.smartrecruiters.com/{c['slug']}/{j['id']}",
            location=", ".join(filter(None, [loc.get("city"), (loc.get("country") or "").upper()])),
            description=html_to_text(html_src), description_html=html_src, posted_at=j.get("releasedDate"),
            employment_hint=(j.get("typeOfEmployment") or {}).get("label", ""), remote_hint="remote" if loc.get("remote") else ("hybrid" if loc.get("hybrid") else ""),
            industry=c.get("industry", "")))
    return out
