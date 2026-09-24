import html, re

def html_to_text(s: str) -> str:
    if not s:
        return ""
    s = html.unescape(s)            # Greenhouse double-escapes its HTML
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr)>", "\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "\n• ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\u00a0]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()

def list_items(html_src: str, text: str, n=3) -> list[str]:
    items = []
    if html_src:
        for m in re.finditer(r"(?is)<li[^>]*>(.*?)</li>", html.unescape(html_src)):
            t = html_to_text(m.group(1)).strip(" •-")
            if 12 <= len(t) <= 160:
                items.append(t)
    if not items:
        items = [l.strip(" •-*") for l in text.splitlines() if l.strip().startswith(("•", "-", "*")) and 12 <= len(l.strip()) <= 160]
    return items[:n]

ROLE_CUES = re.compile(r"\b(you will|you'll|you are going to|as an? (intern|trainee|summer)|your (role|tasks|work)|in this role|during (the|your) (internship|summer)|du kommer|dina arbetsuppgifter|som (praktikant|trainee|sommarjobbare)|i rollen|du vil|dine (oppgaver|arbeidsoppgaver)|som sommerstudent|du skal|dine opgaver|tehtäviisi|pääset|työtehtäviin|tehtävässä)\b", re.I)

def summary_sentence(text: str, company: str = "", limit=200) -> str:
    """Prefer a sentence about the role over company boilerplate."""
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n", text) if 40 <= len(x.strip()) <= 400]
    pick = next((x for x in sents if ROLE_CUES.search(x)), None)
    if not pick: return ""        # better no summary than boilerplate; Claude enrichment writes a proper one
    return pick if len(pick) <= limit else pick[:limit].rsplit(" ", 1)[0] + "…"

def first_sentence(text: str, limit=180) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 40 or line.endswith(":"):
            continue
        m = re.match(r"(.{30,}?[.!?])(\s|$)", line)
        s = (m.group(1) if m else line)
        return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"
    return ""
