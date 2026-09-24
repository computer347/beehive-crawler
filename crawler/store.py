"""Writes to Supabase (when configured) and always to a local JSON store,
which also drives `export` for static builds of the app."""
import json
from datetime import datetime, timezone
from .config import LOCAL_STORE, SUPABASE_URL, SUPABASE_SERVICE_KEY, supabase_enabled
from .http import _client

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

class LocalStore:
    def __init__(self):
        try: self.jobs = json.loads(LOCAL_STORE.read_text())
        except (OSError, ValueError): self.jobs = {}

    def upsert(self, rows, run_at):
        for r in rows:
            old = self.jobs.get(r["id"])
            r["first_seen"] = old["first_seen"] if old else run_at
            r["last_seen"], r["is_open"] = run_at, True
            self.jobs[r["id"]] = r

    def close_missing(self, crawled_slugs: set, run_at):
        n = 0
        for r in self.jobs.values():
            if r["is_open"] and r["company_slug"] in crawled_slugs and r["last_seen"] < run_at:
                r["is_open"], n = False, n + 1
        return n

    def open_jobs(self): return [r for r in self.jobs.values() if r["is_open"]]

    def save(self):
        LOCAL_STORE.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_STORE.write_text(json.dumps(self.jobs, ensure_ascii=False, indent=1))

class SupabaseStore:
    def __init__(self):
        self.base = f"{SUPABASE_URL}/rest/v1"
        # New-style keys (sb_secret_...) go in the apikey header only; legacy JWT keys also as a bearer token.
        self.h = {"apikey": SUPABASE_SERVICE_KEY, "Content-Type": "application/json"}
        if SUPABASE_SERVICE_KEY.startswith("eyJ"):
            self.h["Authorization"] = f"Bearer {SUPABASE_SERVICE_KEY}"

    def upsert(self, rows, run_at):
        rows = [{**r, "last_seen": run_at, "is_open": True} for r in rows]
        for i in range(0, len(rows), 200):
            r = _client.post(f"{self.base}/jobs?on_conflict=id", headers={**self.h, "Prefer": "resolution=merge-duplicates,return=minimal"}, json=rows[i:i+200])
            if r.status_code >= 300: raise RuntimeError(f"Supabase upsert failed: {r.status_code} {r.text[:300]}")

    def close_missing(self, crawled_slugs: set, run_at):
        if not crawled_slugs: return 0
        slugs = ",".join('"' + s.replace('"', '') + '"' for s in crawled_slugs)
        r = _client.patch(f"{self.base}/jobs?is_open=eq.true&last_seen=lt.{run_at}&company_slug=in.({slugs})", headers={**self.h, "Prefer": "return=representation"}, json={"is_open": False})
        return len(r.json()) if r.status_code < 300 else 0

    def log_run(self, stats: dict):
        _client.post(f"{self.base}/crawl_runs", headers={**self.h, "Prefer": "return=minimal"}, json=stats)

def stores():
    s = [LocalStore()]
    if supabase_enabled(): s.append(SupabaseStore())
    return s
