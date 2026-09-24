"""Rule-based classification. Fast, free and good enough to filter;
Claude enrichment (enrich.py) refines skills, fields, study year and languages."""
import re
from .text import summary_sentence, list_items

# ---------- geography ----------
COUNTRY_NAMES = {
    "FI": ["finland", "suomi", "finland"], "SE": ["sweden", "sverige"], "NO": ["norway", "norge", "noreg"],
    "DK": ["denmark", "danmark"], "IS": ["iceland", "ísland", "island"],
}
CITIES = {
    "FI": "helsinki helsingfors espoo esbo vantaa tampere tammerfors turku åbo oulu uleåborg jyväskylä lahti kuopio vaasa vasa lappeenranta pori joensuu rovaniemi seinäjoki kotka hämeenlinna salo otaniemi keilaniemi kajaani kokkola porvoo hyvinkää",
    "SE": "stockholm göteborg gothenburg goteborg malmö malmo uppsala linköping linkoping lund västerås vasteras örebro orebro norrköping norrkoping helsingborg umeå umea luleå lulea jönköping jonkoping kista solna sundbyberg södertälje sodertalje karlskrona sundsvall gävle gavle karlstad växjö vaxjo trollhättan halmstad skellefteå borås eskilstuna",
    "NO": "oslo bergen trondheim stavanger kristiansand tromsø tromso drammen fornebu lysaker sandvika kongsberg bodø bodo ålesund alesund sandnes asker bærum baerum horten moss fredrikstad sarpsborg haugesund molde",
    "DK": "copenhagen københavn kobenhavn aarhus århus odense aalborg ålborg esbjerg kolding lyngby billund vejle horsens herning roskilde hillerød hillerod ballerup søborg soborg bagsværd bagsvaerd hørsholm horsholm glostrup nordborg bjerringbro randers silkeborg",
    "IS": "reykjavík reykjavik akureyri kópavogur kopavogur hafnarfjörður hafnarfjordur garðabær",
}
_CITY_INDEX = {c: cc for cc, s in CITIES.items() for c in s.split()}
ISO = {"fi": "FI", "se": "SE", "no": "NO", "dk": "DK", "is": "IS", "fin": "FI", "swe": "SE", "nor": "NO", "dnk": "DK", "isl": "IS"}

def country_city(location: str) -> tuple[str, str]:
    loc = (location or "").lower()
    for word in re.findall(r"[a-zà-ÿæøåäöðþ]+", loc):
        if word in _CITY_INDEX:
            city = next((w for w in re.split(r"[,/;|()-]", location) if word in w.lower()), word).strip()
            return _CITY_INDEX[word], city.title() if city.islower() else city
    for cc, names in COUNTRY_NAMES.items():
        if any(re.search(rf"\b{n}\b", loc) for n in names):
            return cc, ""
    m = re.search(r"\b(fi|se|no|dk|is|fin|swe|nor|dnk|isl)\b", loc)
    if m and len(loc) <= 40:
        return ISO[m.group(1)], ""
    return "", ""

# ---------- student roles ----------
PATTERNS = [  # (type, regex on title)
    ("Thesis", r"\b(thesis|master'?s thesis|diplomityö|diplomityöntekijä|opinnäytetyö|gradu|examensarbete|exjobb|masteroppgave|bacheloroppgave|speciale|specialestuderende|bachelorprojekt)\b"),
    ("Summer job", r"\b(summer|kesä\w*|sommar\w*|sommer\w*|sumar\w*)\b"),
    ("Internship", r"\b(intern|interns|internship|internships|harjoittelija\w*|harjoittelu\w*|praktikant\w*|praktik\w*|praksis\w*|trainee ?ship|co-?op|stagiaire)\b"),
    ("Part-time", r"\b(working student|student worker|student assistant|student job|studentjobb|extrajobb|studentmedarbetare|studentermedhjælper\w*|studentmedhjælper\w*|deltidsstudent|student ?assistent|osa-aikainen opiskelija|opiskelijatyö|tuntityö)\b"),
    ("Graduate", r"\b(graduate|graduates|trainee|traineeship|new grad|nyexaminerad|nyutdannet|nyuddannet|vastavalmistunut|graduate programme|graduate program|early careers?|junior associate programme)\b"),
]
EXCLUDE = r"\b(senior|sr\.?|lead|principal|head of|director|manager(?! trainee)|chief|vp|staff engineer|architect|professor|postdoc|phd position|doctoral)\b"
EXCLUDE_FALSE = r"\b(internal|international|interna|internet)\b|\bintern(?=\s+(service|kontroll|revision|kommunikation|rekrytering|verksamhet|it|tjänst|stöd|handläggare))|\btill intern\b"
# roles for vocational workers rather than university students
VOCATIONAL = r"\b(svetsare|svejser|sveiser|hitsaaja|snickare|tømrer|snekker|puuseppä|cnc|operatör|operatør|lagerarbet|lagermedarbet|varasto|hjullastar|truckförare|förare|chaufför|sjåfør|kuljettaja|vaktmäst|städ|lokalvård|siivo|rengøring|butik|kassa|kassør|myyjä|servering|servitör|kock|kokk|barista|montör|montør|asentaja|fysiskt arbete|undersköterska|vårdbiträde|personlig assistent|barnskötare|lärarvikarie)"


def student_type(title: str, description: str = "", employment_hint: str = "") -> str | None:
    t = title.lower()
    if re.search(EXCLUDE, t) and not re.search(r"\b(trainee|intern|summer|thesis)\b", t):
        return None
    if re.search(VOCATIONAL, t):
        return None
    t_clean = re.sub(EXCLUDE_FALSE, " ", t)
    for typ, rx in PATTERNS:
        if re.search(rx, t_clean):
            return typ
    hint = employment_hint.lower()
    if "intern" in hint:
        return "Internship"
    if re.search(r"\b(this is a|we offer a|for a) (summer job|summer internship|kesätyö|sommarjobb)\b", description.lower()):
        return "Summer job"
    return None

def work_mode(location: str, description: str, hint: str) -> str:
    s = f"{hint} {location}".lower()
    if "hybrid" in s: return "Hybrid"
    if "remote" in s or "etä" in s or "distans" in s: return "Remote"
    d = description.lower()
    if re.search(r"\bhybrid\b", d): return "Hybrid"
    if re.search(r"\b(fully remote|remote-first|100% remote)\b", d): return "Remote"
    return "On-site"

# ---------- language ----------
STOP = {
    "Finnish": " ja on että tai sekä voit meillä sinulla tehtävä työ opiskelija kanssa ",
    "Swedish": " och att det som för med är på vi dig du har eller inom arbete ",
    "Norwegian": " og at det som for med er på vi deg du har eller innen jobb ikke ",
    "Danish": " og at det som for med er på vi dig du har eller inden job ikke ",
}
def text_language(text: str) -> str:
    words = re.findall(r"[a-zà-ÿæøåäöð]+", text.lower()[:3000])
    if len(words) < 25: return "English"
    score = {lang: sum(1 for w in words if f" {w} " in stop) / len(words) for lang, stop in STOP.items()}
    en = sum(1 for w in words if w in {"and","the","to","of","you","we","with","for","in","our","your","is"}) / len(words)
    best = max(score, key=score.get)
    return best if score[best] > max(en, 0.06) else "English"

LANG_RX = {
    "Finnish": r"\b(finnish|suomen kiel\w*|suomea)\b", "Swedish": r"\b(swedish|svenska|ruotsi\w*)\b",
    "Norwegian": r"\b(norwegian|norsk)\b", "Danish": r"\b(danish|dansk)\b", "Icelandic": r"\b(icelandic|íslensk\w*)\b",
    "German": r"\b(german|deutsch)\b",
}
def required_languages(description: str) -> list[str]:
    langs = ["English"]
    local = text_language(description)
    if local != "English":
        langs.append(local)
    d = description.lower()
    for lang, rx in LANG_RX.items():
        for m in re.finditer(rx, d):
            ctx = d[max(0, m.start()-80): m.end()+80]
            if re.search(r"(fluent|required|must|excellent|good command|native|proficien|sujuva|erinomai|hyvä|flytande|goda kunskaper|krav|flytende|flydende|skal)", ctx) and not re.search(r"(plus|merit|advantage|nice to have|eduksi|meriitti|meriterande|fördel|en fordel)", ctx):
                if lang not in langs: langs.append(lang)
                break
    return langs

# ---------- study phase ----------
def level_and_year(title: str, description: str, typ: str) -> tuple[str, int]:
    s = f"{title}\n{description}".lower()
    if typ == "Thesis" or re.search(r"\b(master'?s (degree )?student|master'?s level|diplomi-insinööri|di-opiskelija|civilingenjör|sivilingeniør)\b", s):
        return "M", 4
    m = re.search(r"\b(?:at least|minimum|min\.?)\s*(?:your\s*)?([1-5])(?:st|nd|rd|th)?[\s-]*year", s) or re.search(r"\b([2-5])(?:nd|rd|th)[\s-]*year (?:student|of (?:your|their) studies)", s)
    if m: return "B", int(m.group(1))
    if typ == "Graduate": return "B", 3
    if re.search(r"\b(final year|last year of|graduating (in|by)|nearing graduation)\b", s): return "B", 3
    return "B", 2

# ---------- fields and skills (same vocabulary as the Beehive app) ----------
FIELDS = [
    ("Electrical Engineering", r"electrical|electronics|embedded|firmware|hardware engineer|power systems|power grid|sähkö\w*|elektro\w*|elteknik|elkraft|elnät|strømnett"),
    ("Computer Science", r"computer science|software|developer|full[- ]?stack|backend|frontend|devops|cyber ?security|tietotekniikka|ohjelmisto\w*|kehittäjä|datateknik|mjukvara|systemutveckl\w*|utvecklare|utvikler|programvare|udvikler|informatik|sikkerhetsutvikl\w*"),
    ("Data Science", r"data scien|machine learning|analytics|data analy|data engineer|\bai\b|artificial intelligence|data og analyse|dataanalys|analytiikka"),
    ("Mechanical Engineering", r"mechanical|mechatronic|konetekniikka|maskinteknik|maskiningeniør|mekanik|\bcad\b|solidworks|cfd|produktutveckling"),
    ("Energy & Environment", r"renewable|energy (sector|system|transition|company|storage)|environmental|climate|wind (power|energy|turbine)|solar|battery|hydrogen|nuclear|kärnkraft|vattenkraft|energiteknik|ympäristötekniikka|miljöteknik"),
    ("Health Technology", r"biomedical|medical device|health ?tech|medtech|clinical|life science|lääketiede|bioteknik|medicinteknik"),
    ("Physics & Mathematics", r"physics|mathemat|quantum|optics|fysiikka|matematiikka|fysik|teknisk fysik"),
    ("Industrial Engineering", r"industrial engineering|supply chain|logistics|operations|procurement|production planning|tuotantotalous|industriell ekonomi|lean"),
    ("Economics & Business", r"economics|business|finance|financial|accounting|marketing|controller|kauppatiet|ekonomi|økonomi|consult|forretning\w*|strategy|investment"),
    ("Design", r"\bux\b|\bui\b|user experience|figma|visual design|graphic design|grafisk design|product design|interaction design|ux-designer"),
]
SKILL_RX = [
    ("Python", r"python|pandas|numpy"), ("C/C++", r"\bc\+\+|\bc/c\+\+|\bc programming|\bc and c\+\+"), ("Embedded C", r"embedded|firmware|microcontroller|stm32|esp32|\bmcu\b"),
    ("TypeScript", r"typescript|javascript"), ("React", r"\breact\b"), ("SQL", r"\bsql\b|postgres|mysql"), ("Git", r"\bgit\b|github|gitlab"),
    ("Docker", r"docker|kubernetes|container"), ("ROS", r"\bros\b|ros ?2"), ("RTOS", r"\brtos\b|freertos|zephyr"),
    ("PCB design", r"\bpcb\b|schematic|altium|kicad|circuit design"), ("Lab measurements", r"oscilloscope|measurement|laboratory|test bench|lab work"),
    ("Power electronics", r"power electronics|converter|inverter|motor drive"), ("PLC programming", r"\bplc\b|codesys|tia portal|scada"),
    ("CAD (SolidWorks)", r"\bcad\b|solidworks|creo|catia|inventor|nx\b"), ("MATLAB", r"matlab|simulink"), ("Signal processing", r"signal processing|\bdsp\b|signal analysis"),
    ("Control systems", r"control systems|control engineering|automation|control theory|\bpid\b"), ("Statistics", r"statistic|probabilit"),
    ("Data analysis", r"data analy|analytics|power bi|tableau|excel analysis"), ("Data visualisation", r"visuali[sz]|dashboards?|power bi|tableau"),
    ("Machine learning", r"machine learning|deep learning|pytorch|tensorflow|scikit|neural net"), ("Computer vision", r"computer vision|image processing|opencv"),
    ("LLM applications", r"\bllms?\b|large language model|generative ai|genai|\brag\b|langchain|openai|anthropic|prompt engineering"),
    ("AI-assisted coding", r"copilot|cursor|claude code|ai[- ]assisted (coding|development)|ai coding tools"),
    ("Cloud (AWS)", r"\baws\b|azure|gcp|google cloud|cloud"), ("Excel modelling", r"excel|financial model"), ("Finance", r"finance|financial|accounting|valuation"),
    ("Product management", r"product management|product owner|roadmap"), ("Figma", r"figma"), ("User research", r"user research|usability|interviews with users|ux research"),
]
def fields_for(title: str, description: str) -> list[str]:
    t, d = title.lower(), description.lower()
    scored = sorted(((3 * len(re.findall(rx, t)) + len(re.findall(rx, d)), f) for f, rx in FIELDS), reverse=True)
    top = scored[0][0] if scored else 0
    return [f for n, f in scored if n >= 2 and n >= top / 3][:3]

def skills_for(title: str, description: str) -> list[str]:
    s = f"{title}\n{description}".lower()
    found = [(len(re.findall(rx, s)), name) for name, rx in SKILL_RX]
    return [n for c, n in sorted(found, reverse=True) if c > 0][:6]

def CITIES_HAS(word: str) -> bool:
    return word.lower() in _CITY_INDEX

def apply_rules(job) -> bool:
    """Fill classification fields. Returns False if the job is not a Nordic student role."""
    typ = student_type(job.title, job.description, job.employment_hint)
    if not typ:
        return False
    cc, city = country_city(job.location)
    if not cc:
        return False
    fallback = job.location.split(",")[0].strip()
    job.type, job.country, job.city = typ, cc, city or ("" if country_city(fallback)[0] and not CITIES_HAS(fallback) else fallback)
    job.mode = work_mode(job.location, job.description, job.remote_hint)
    job.level, job.min_year = level_and_year(job.title, job.description, typ)
    job.langs = required_languages(job.description)
    job.fields = fields_for(job.title, job.description)
    job.skills = skills_for(job.title, job.description)
    job.about = job.about or summary_sentence(job.description, job.company)
    job.bullets = job.bullets or list_items(job.description_html, job.description)
    return True
