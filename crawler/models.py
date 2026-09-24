from dataclasses import dataclass, field, asdict
import hashlib, re
from datetime import datetime, timezone

def iso(v):
    """Normalise the many date formats job feeds use; None if unparseable."""
    if not v: return None
    v = str(v).strip()
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
        if not m: return None
        d = datetime.fromisoformat(m.group(1))
    if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
    return d.isoformat(timespec="seconds")

@dataclass
class Job:
    source: str                 # greenhouse | lever | ashby | recruitee | smartrecruiters | workable | workday | jsonld | jobtech
    source_id: str
    company: str
    title: str
    url: str
    location: str = ""
    description: str = ""       # plain text
    description_html: str = ""
    posted_at: str | None = None
    deadline: str | None = None
    employment_hint: str = ""   # e.g. "Internship", "Part-time", "FullTime"
    remote_hint: str = ""       # e.g. "hybrid", "remote", "onsite"
    pay: str | None = None
    industry: str = ""
    company_slug: str = ""
    # filled by the pipeline
    city: str = ""
    country: str = ""
    type: str = ""
    mode: str = ""
    level: str = "B"
    min_year: int = 1
    langs: list = field(default_factory=lambda: ["English"])
    skills: list = field(default_factory=list)
    fields: list = field(default_factory=list)
    about: str = ""
    bullets: list = field(default_factory=list)
    enriched: bool = False

    @property
    def id(self) -> str:
        return hashlib.sha1(f"{self.source}|{self.company_slug or self.company}|{self.source_id}".encode()).hexdigest()[:16]

    @property
    def content_hash(self) -> str:
        return hashlib.sha1(f"{self.title}|{self.location}|{self.description[:4000]}".encode()).hexdigest()[:16]

    def row(self) -> dict:
        d = asdict(self)
        d.pop("description_html", None); d.pop("employment_hint", None); d.pop("remote_hint", None); d.pop("location", None)
        d["id"] = self.id
        d["content_hash"] = self.content_hash
        d["description"] = self.description[:6000]
        d["posted_at"], d["deadline"] = iso(self.posted_at), iso(self.deadline)
        return d
