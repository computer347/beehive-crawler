from ..http import get_json
from ..models import Job
from ..text import html_to_text

def endpoint(slug): return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"

def fetch(c) -> list[Job] | None:
    d = get_json(endpoint(c["slug"]))
    if d is None or "jobs" not in d: return None
    out = []
    for j in d["jobs"]:
        html_src = j.get("content") or ""
        locs = [j.get("location", {}).get("name", "")] + [o.get("location") or o.get("name", "") for o in j.get("offices", [])]
        out.append(Job(source="greenhouse", source_id=str(j["id"]), company=c["name"], company_slug=c["slug"],
            title=j.get("title", ""), url=j.get("absolute_url", ""), location=" / ".join(l for l in locs if l),
            description=html_to_text(html_src), description_html=html_src, posted_at=j.get("first_published") or j.get("updated_at"),
            industry=c.get("industry", "")))
    return out
