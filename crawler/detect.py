"""Find which ATS a careers page uses, and discover companies on public ATS feeds by name."""
import re, unicodedata
from concurrent.futures import ThreadPoolExecutor
from .http import get_text, get_json
from .classify import country_city
from .sources import greenhouse, lever, ashby, recruitee, smartrecruiters, workable

FINGERPRINTS = [
    ("greenhouse", r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)"),
    ("lever", r"jobs(?:\.eu)?\.lever\.co/([\w-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/([\w.-]+)"),
    ("recruitee", r"([\w-]+)\.recruitee\.com"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)"),
    ("workable", r"apply\.workable\.com/([\w-]+)"),
    ("workday", r"(https://[\w.-]+\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?[\w-]+)"),
]

def detect(careers_url: str) -> tuple[str, str]:
    """Returns (ats, slug_or_url). Falls back to ('jsonld', careers_url)."""
    for ats, rx in FINGERPRINTS:
        m = re.search(rx, careers_url)
        if m: return ats, m.group(1)
    page = get_text(careers_url) or ""
    for ats, rx in FINGERPRINTS:
        m = re.search(rx, page)
        if m and m.group(1).lower() not in ("embed", "js", "static", "api"):
            return ats, m.group(1)
    return "jsonld", careers_url

def slugs(name: str) -> list[str]:
    base = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"\b(oy|oyj|ab|asa|as|a/s|aps|hf|ehf|group|inc|ltd)\b", "", base).strip()
    words = re.findall(r"[a-z0-9]+", base)
    out = ["".join(words), "-".join(words)]
    return list(dict.fromkeys(s for s in out if s))

def _lever(s):
    d = get_json(lever.endpoint(s))
    if not isinstance(d, list): d = get_json(lever.endpoint(s, True))
    return d if isinstance(d, list) else None

PROBES = {
    "greenhouse": lambda s: (get_json(greenhouse.endpoint(s)) or {}).get("jobs"),
    "lever": lambda s: _lever(s),
    "ashby": lambda s: (get_json(ashby.endpoint(s)) or {}).get("jobs"),
    "recruitee": lambda s: (get_json(recruitee.endpoint(s)) or {}).get("offers"),
    "smartrecruiters": lambda s: (get_json(smartrecruiters.endpoint(s)) or {}).get("content"),
    "workable": lambda s: (get_json(workable.endpoint(s).replace("?details=true", "")) or {}).get("jobs"),
}
LOC = {
    "greenhouse": lambda j: (j.get("location") or {}).get("name", ""),
    "lever": lambda j: " / ".join((j.get("categories") or {}).get("allLocations") or [(j.get("categories") or {}).get("location") or ""]),
    "ashby": lambda j: " / ".join([j.get("location", "")] + [x.get("location", "") for x in j.get("secondaryLocations") or []]),
    "recruitee": lambda j: f"{j.get('city','')}, {j.get('country','')}",
    "smartrecruiters": lambda j: f"{(j.get('location') or {}).get('city','')}, {((j.get('location') or {}).get('country') or '').upper()}",
    "workable": lambda j: f"{j.get('city','')}, {j.get('country','')}",
}

def probe(name: str) -> dict | None:
    for ats, fn in PROBES.items():
        for s in slugs(name):
            try:
                jobs = fn(s)
            except Exception:
                jobs = None
            if jobs:
                nordic = sum(1 for j in jobs if country_city(LOC[ats](j))[0])
                if nordic:
                    return {"name": name, "ats": ats, "slug": s, "jobs": len(jobs), "nordic_jobs": nordic}
    return None

def discover(names: list[str], workers=8):
    with ThreadPoolExecutor(workers) as ex:
        for name, hit in zip(names, ex.map(probe, names)):
            yield name, hit
