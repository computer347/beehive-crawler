"""Sweden's open JobTech JobSearch API (Arbetsförmedlingen). Free and keyless."""
from ..http import get_json
from ..models import Job
from urllib.parse import quote

QUERIES = ["sommarjobb", "praktikant", "praktik", "examensarbete", "exjobb", "trainee", "internship", "summer intern", "studentmedarbetare", "sommarpraktik"]
RELEVANT_FIELDS = ("data/it", "tekni", "naturvetensk", "ekonomi", "industriell", "bygg", "energi", "kultur, media, design", "administration")

def fetch(cfg=None) -> list[Job]:
    seen, out = set(), []
    for q in QUERIES:
        for offset in range(0, 500, 100):
            d = get_json(f"https://jobsearch.api.jobtechdev.se/search?q={quote(q)}&limit=100&offset={offset}")
            hits = (d or {}).get("hits", [])
            for h in hits:
                if h["id"] in seen: continue
                seen.add(h["id"])
                field = ((h.get("occupation_field") or {}).get("label") or "").lower()
                if field and not any(f in field for f in RELEVANT_FIELDS):
                    continue
                emp = h.get("employer") or {}
                addr = h.get("workplace_address") or {}
                desc = ((h.get("description") or {}).get("text") or "")
                app = (h.get("application_details") or {}).get("url") or h.get("webpage_url", "")
                hours = ((h.get("working_hours_type") or {}).get("label") or "")
                out.append(Job(source="jobtech", source_id=str(h["id"]), company=emp.get("name") or emp.get("workplace") or "",
                    company_slug=(emp.get("organization_number") or emp.get("name") or "").lower(), title=h.get("headline", ""), url=app,
                    location=", ".join(filter(None, [(addr.get("municipality") or addr.get("city") or "").title(), "Sweden"])),
                    description=desc, posted_at=h.get("publication_date"), deadline=h.get("application_deadline"),
                    employment_hint="Part-time" if hours == "Deltid" else "", pay=h.get("salary_description") or None,
                    industry=""))   # Platsbanken labels are Swedish occupation groups; enrichment adds an English industry
            if len(hits) < 100: break
    return out
