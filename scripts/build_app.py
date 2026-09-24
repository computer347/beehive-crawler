"""Inline the latest jobs.json into the Beehive app so the page works as one static file."""
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("--data", default=str(ROOT / "site" / "jobs.json"))
ap.add_argument("--app", default=str(ROOT / "app" / "index.html"))
ap.add_argument("--out", default=str(ROOT / "site" / "index.html"))
a = ap.parse_args()

html = Path(a.app).read_text(encoding="utf-8")
data = json.loads(Path(a.data).read_text(encoding="utf-8"))
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html, n = re.subn(r'(<script id="beehive-data" type="application/json">)(.*?)(</script>)', lambda m: m.group(1) + blob + m.group(3), html, flags=re.S)
if n != 1: raise SystemExit("beehive-data script tag not found in app")
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text(html, encoding="utf-8")
print(f"Built {a.out} with {data['count']} jobs")
