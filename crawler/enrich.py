"""Optional Claude enrichment: turns a raw ad into Beehive's matching fields.
Only new or changed ads are sent (cached by content hash), so daily runs stay cheap."""
import json
from .config import ANTHROPIC_API_KEY, MODEL, ENRICH_CACHE
from .classify import FIELDS, SKILL_RX

SKILLS = [s for s, _ in SKILL_RX]
FIELD_NAMES = [f for f, _ in FIELDS]
TYPES = ["Internship", "Summer job", "Thesis", "Part-time", "Graduate"]
PROMPT = """You extract structured data from a Nordic student job ad for a matching engine.
Reply with only one JSON object:
{{"type": one of {types},
 "about": "one plain sentence under 25 words on what the person will do",
 "bullets": ["up to 3 short responsibilities, under 12 words each"],
 "skills": [up to 6 from this list, only if the ad asks for or clearly uses them: {skills}],
 "fields": [up to 3 degree fields from: {fields}],
 "level": "B" if bachelor's students can apply, "M" if it needs master's-level students,
 "min_year": integer 1-5, the earliest year of study that fits,
 "langs": ["English" plus any other language the ad requires, not merely prefers],
 "mode": "On-site" | "Hybrid" | "Remote",
 "industry": "two or three word industry label",
 "pay": "pay as written in the ad, or null"}}
Write English even if the ad is in Finnish, Swedish, Norwegian, Danish or Icelandic.

Title: {title}
Company: {company}
Location: {location}
Ad:
\"\"\"{text}\"\"\""""

class Enricher:
    def __init__(self):
        self.client = None
        if ANTHROPIC_API_KEY:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            except ImportError:
                print("anthropic package not installed; skipping enrichment")
        try:
            self.cache = json.loads(ENRICH_CACHE.read_text())
        except (OSError, ValueError):
            self.cache = {}
        self.calls = 0

    @property
    def enabled(self): return self.client is not None

    def apply(self, job, max_calls=400):
        key = job.content_hash
        data = self.cache.get(key)
        if data is None and self.enabled and self.calls < max_calls:
            try:
                msg = self.client.messages.create(model=MODEL, max_tokens=700, messages=[{"role": "user", "content": PROMPT.format(
                    types=TYPES, skills=", ".join(SKILLS), fields=", ".join(FIELD_NAMES), title=job.title, company=job.company,
                    location=job.location, text=job.description[:7000])}])
                self.calls += 1
                raw = "".join(b.text for b in msg.content if b.type == "text")
                data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
                self.cache[key] = data
            except Exception as e:           # never let enrichment break a crawl
                print(f"  enrich failed for {job.title[:50]}: {e}")
                data = None
        if not data: return
        if data.get("type") in TYPES: job.type = data["type"]
        job.about = str(data.get("about") or job.about)[:220]
        job.bullets = [str(b)[:120] for b in (data.get("bullets") or job.bullets)][:3]
        job.skills = [s for s in data.get("skills", []) if s in SKILLS][:6] or job.skills
        job.fields = [f for f in data.get("fields", []) if f in FIELD_NAMES][:3] or job.fields
        job.level = "M" if data.get("level") == "M" else "B"
        try: job.min_year = max(1, min(5, int(data.get("min_year", job.min_year))))
        except (TypeError, ValueError): pass
        langs = [l for l in data.get("langs", []) if isinstance(l, str)]
        job.langs = ["English"] + [l for l in langs if l != "English"] if langs else job.langs
        if data.get("mode") in ("On-site", "Hybrid", "Remote"): job.mode = data["mode"]
        job.industry = data.get("industry") or job.industry
        job.pay = job.pay or data.get("pay")
        job.enriched = True

    def save(self):
        ENRICH_CACHE.parent.mkdir(parents=True, exist_ok=True)
        ENRICH_CACHE.write_text(json.dumps(self.cache))
