from ..http import get_json
from ..models import Job
from ..text import html_to_text

def endpoint(slug): return f"https://{slug}.recruitee.com/api/offers/"

def fetch(c) -> list[Job] | None:
    d = get_json(endpoint(c["slug"]))
    if d is None or "offers" not in d: return None
    out = []
    for j in d["offers"]:
        html_src = (j.get("description") or "") + (j.get("requirements") or "")
        loc = ", ".join(filter(None, [j.get("city"), j.get("country")])) or j.get("location", "")
        out.append(Job(source="recruitee", source_id=str(j["id"]), company=c["name"], company_slug=c["slug"], title=j.get("title", ""),
            url=j.get("careers_url", ""), location=loc, description=html_to_text(html_src), description_html=html_src,
            posted_at=j.get("published_at"), deadline=j.get("close_at"), employment_hint=j.get("employment_type_code", ""),
            remote_hint="remote" if j.get("remote") else ("hybrid" if j.get("hybrid") else ""), industry=c.get("industry", "")))
    return out
