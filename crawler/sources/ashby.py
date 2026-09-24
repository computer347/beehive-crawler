from ..http import get_json
from ..models import Job

def endpoint(slug): return f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"

def fetch(c) -> list[Job] | None:
    d = get_json(endpoint(c["slug"]))
    if d is None or "jobs" not in d: return None
    out = []
    for j in d["jobs"]:
        if j.get("isListed") is False: continue
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations", []) or []]
        comp = (j.get("compensation") or {}).get("compensationTierSummary")
        out.append(Job(source="ashby", source_id=j["id"], company=c["name"], company_slug=c["slug"], title=j.get("title", ""),
            url=j.get("jobUrl", ""), location=" / ".join(l for l in locs if l), description=j.get("descriptionPlain", ""),
            description_html=j.get("descriptionHtml", ""), posted_at=j.get("publishedAt"), employment_hint=j.get("employmentType", ""),
            remote_hint=j.get("workplaceType", "") or ("remote" if j.get("isRemote") else ""), pay=comp, industry=c.get("industry", "")))
    return out
