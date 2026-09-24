"""Usage:
  python -m crawler run [--limit N] [--only slug ...] [--no-enrich]
  python -m crawler discover [--from candidates.txt]        probe public ATS feeds for company names
  python -m crawler detect https://company.com/careers      identify a careers page's ATS
  python -m crawler add "Company Name" https://company.com/careers [--industry X]
  python -m crawler export [--out jobs.json]                write app-ready JSON
"""
import argparse, sys, yaml
from .config import COMPANIES_FILE, CANDIDATES_FILE

def _load():
    return yaml.safe_load(COMPANIES_FILE.read_text()) if COMPANIES_FILE.exists() else {"companies": [], "feeds": []}

def _save(data):
    data["companies"].sort(key=lambda c: c["name"].lower())
    COMPANIES_FILE.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

def main(argv=None):
    ap = argparse.ArgumentParser(prog="crawler")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--limit", type=int); r.add_argument("--only", nargs="*"); r.add_argument("--no-enrich", action="store_true")
    d = sub.add_parser("discover"); d.add_argument("--from", dest="src", default=str(CANDIDATES_FILE))
    t = sub.add_parser("detect"); t.add_argument("url")
    a = sub.add_parser("add"); a.add_argument("name"); a.add_argument("url"); a.add_argument("--industry", default="")
    e = sub.add_parser("export"); e.add_argument("--out", default="jobs.json")
    args = ap.parse_args(argv)

    if args.cmd == "run":
        from .pipeline import run
        run(limit=args.limit, only=args.only, enrich=not args.no_enrich)
    elif args.cmd == "discover":
        from .detect import discover
        from .config import ROOT
        tried_file = ROOT / "data" / "discover_tried.txt"; tried_file.parent.mkdir(exist_ok=True)
        tried = set(tried_file.read_text(encoding="utf-8").splitlines()) if tried_file.exists() else set()
        data = _load(); known = {c["name"].lower() for c in data["companies"]}
        names = [l.split("#")[0].strip() for l in open(args.src, encoding="utf-8")]
        names = [n for n in names if n and n.lower() not in known and n not in tried]
        found = 0
        with open(tried_file, "a", encoding="utf-8") as log:
            for name, hit in discover(names):
                if hit:
                    found += 1; print(f"  ✓ {name:<28} {hit['ats']:<15} {hit['slug']:<22} {hit['nordic_jobs']} Nordic ads", flush=True)
                    data["companies"].append({"name": name, "ats": hit["ats"], "slug": hit["slug"]}); _save(data)
                else:
                    print(f"  · {name}", flush=True)
                log.write(name + "\n"); log.flush()
        print(f"\nAdded {found} companies to {COMPANIES_FILE.name}. {len(names)} names probed; rerun to resume if interrupted.")
    elif args.cmd == "detect":
        from .detect import detect
        print(*detect(args.url))
    elif args.cmd == "add":
        from .detect import detect
        ats, ref = detect(args.url)
        entry = {"name": args.name, "ats": ats, "slug": ref if ats not in ("workday", "jsonld") else args.name.lower().replace(" ", "-")}
        if ats in ("workday", "jsonld"): entry["careers_url"] = ref
        if args.industry: entry["industry"] = args.industry
        data = _load(); data["companies"].append(entry); _save(data)
        print(f"Added {args.name} ({ats}).")
    elif args.cmd == "export":
        from .export import export
        p = export(args.out); print(f"Wrote {p['count']} jobs to {args.out}")

if __name__ == "__main__":
    sys.exit(main())
