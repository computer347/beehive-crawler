import time, yaml
from concurrent.futures import ThreadPoolExecutor
from .config import COMPANIES_FILE
from .sources import ATS, FEEDS
from .classify import apply_rules
from .enrich import Enricher
from .store import stores, now

def load_companies():
    data = yaml.safe_load(COMPANIES_FILE.read_text()) or {}
    return [c for c in data.get("companies", []) if c.get("active", True)], data.get("feeds", [])

def crawl_company(c):
    t = time.time()
    try:
        jobs = ATS[c["ats"]].fetch(c)
    except Exception as e:
        return c, None, f"{type(e).__name__}: {e}", time.time() - t
    return c, jobs, None if jobs is not None else "no response", time.time() - t

def run(limit=None, only=None, enrich=True, workers=6, verbose=True):
    run_at = now()
    companies, feeds = load_companies()
    if only: companies = [c for c in companies if c["slug"] in only or c["name"] in only]
    if limit: companies = companies[:limit]
    enricher = Enricher() if enrich else None
    kept, crawled, errors, seen = [], set(), [], 0

    with ThreadPoolExecutor(workers) as ex:
        for c, jobs, err, secs in ex.map(crawl_company, companies):
            if err:
                errors.append((c["name"], err)); verbose and print(f"  ✗ {c['name']:<28} {err}"); continue
            crawled.add(c["slug"]); seen += len(jobs)
            mine = [j for j in jobs if apply_rules(j)]
            kept += mine
            verbose and print(f"  ✓ {c['name']:<28} {len(jobs):>4} ads, {len(mine):>3} student roles  ({secs:.1f}s)")

    for f in feeds:
        if f.get("active", True) and f["source"] in FEEDS:
            jobs = FEEDS[f["source"]].fetch(f)
            mine = [j for j in jobs if apply_rules(j) and j.fields]   # feeds are broad: keep degree-relevant roles only
            kept += mine; seen += len(jobs)
            crawled |= {j.company_slug for j in mine}
            verbose and print(f"  ✓ feed {f['source']:<23} {len(jobs):>4} ads, {len(mine):>3} student roles")

    if enricher:
        if enricher.enabled: print(f"Enriching with {enricher.client and 'Claude'}…")
        for j in kept: enricher.apply(j)
        enricher.save()

    rows = [j.row() for j in {j.id: j for j in kept}.values()]
    closed = 0
    for st in stores():
        st.upsert(rows, run_at)
        closed = st.close_missing(crawled, run_at)
        if hasattr(st, "save"): st.save()
        if hasattr(st, "log_run"):
            try: st.log_run({"run_at": run_at, "companies": len(companies), "errors": len(errors), "ads_seen": seen, "student_roles": len(rows), "closed": closed})
            except Exception: pass
    print(f"\nDone: {len(rows)} open student roles from {len(crawled)} employers, {seen} ads scanned, {closed} closed, {len(errors)} errors.")
    return rows, errors
