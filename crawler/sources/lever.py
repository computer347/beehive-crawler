from datetime import datetime, timezone
from ..http import get_json
from ..models import Job
from ..text import html_to_text

def endpoint(slug, eu=False): return f"https://api{'.eu' if eu else ''}.lever.co/v0/postings/{slug}?mode=json"

def fetch(c) -> list[Job] | None:
    d = get_json(endpoint(c["slug"], c.get("eu", False)))
    if d is None and not c.get("eu"):
        d = get_json(endpoint(c["slug"], True))       # EU-hosted Lever accounts
    if not isinstance(d, list): return None
    out = []
    for j in d:
        cat = j.get("categories") or {}
        lists = j.get("lists") or []
        lists_html = "".join(f"<h3>{l.get('text','')}</h3><ul>{l.get('content','')}</ul>" for l in lists)
        desc = "\n".join(filter(None, [j.get("descriptionPlain", "")] + [f"{l.get('text','')}\n{html_to_text(l.get('content',''))}" for l in lists] + [j.get("additionalPlain", "")]))
        created = j.get("createdAt")
        out.append(Job(source="lever", source_id=j["id"], company=c["name"], company_slug=c["slug"], title=j.get("text", ""),
            url=j.get("hostedUrl", ""), location=" / ".join(cat.get("allLocations") or [cat.get("location") or ""]),
            description=desc, description_html=lists_html,
            posted_at=datetime.fromtimestamp(created / 1000, timezone.utc).isoformat() if created else None,
            employment_hint=cat.get("commitment", ""), remote_hint=j.get("workplaceType", ""), industry=c.get("industry", "")))
    return out
