"""Export open jobs in the exact shape the Beehive front end uses."""
import json
from datetime import datetime, timezone
from .store import LocalStore

def _days(iso):
    if not iso: return None
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days
    except ValueError:
        return None

def to_app(r: dict) -> dict:
    posted = _days(r.get("posted_at") or r.get("first_seen"))
    left = _days(r.get("deadline"))
    return {
        "id": r["id"], "t": r["title"], "c": r["company"], "ind": r.get("industry") or "", "city": r.get("city") or "",
        "cc": r["country"], "type": r["type"], "mode": r.get("mode") or "On-site", "pay": r.get("pay"),
        "fields": r.get("fields") or [], "skills": r.get("skills") or [], "lvl": r.get("level") or "B",
        "minYear": r.get("min_year") or 1, "langs": r.get("langs") or ["English"],
        "days": max(0, posted) if posted is not None else 0, "dl": (-left if left is not None and left <= 0 else None),
        "about": r.get("about") or "", "bullets": r.get("bullets") or [], "url": r.get("url"), "source": r.get("source"),
    }

def export(path, max_age_days=120):
    jobs = [to_app(r) for r in LocalStore().open_jobs()]
    jobs = [j for j in jobs if j["days"] <= max_age_days and (j["dl"] is None or j["dl"] >= 0)]
    jobs.sort(key=lambda j: (j["cc"], j["days"]))
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "count": len(jobs), "jobs": jobs}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    return payload
