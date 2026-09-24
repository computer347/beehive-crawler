from ..http import get_json
from ..models import Job
from ..text import html_to_text

def endpoint(slug): return f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true"

def fetch(c) -> list[Job] | None:
    d = get_json(endpoint(c["slug"]))
    if d is None or "jobs" not in d: return None
    out = []
    for j in d["jobs"]:
        html_src = (j.get("description") or "") + (j.get("requirements") or "")
        loc = ", ".join(filter(None, [j.get("city"), j.get("country")]))
        out.append(Job(source="workable", source_id=j.get("shortcode") or j.get("id", ""), company=c["name"], company_slug=c["slug"],
            title=j.get("title", ""), url=j.get("url") or j.get("shortlink", ""), location=loc, description=html_to_text(html_src),
            description_html=html_src, posted_at=j.get("published_on") or j.get("created_at"), employment_hint=j.get("employment_type", ""),
            remote_hint="remote" if j.get("telecommuting") else "", industry=c.get("industry", "")))
    return out
