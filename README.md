# Beehive crawler

Collects student jobs (internships, summer jobs, thesis roles, graduate programmes and part-time
student roles) from Nordic employers, scores them into Beehive's matching fields, and publishes
the Beehive app with fresh listings every day.

```
companies.yaml ──► ATS feeds (Greenhouse, Lever, Ashby, Recruitee, SmartRecruiters, Workable, Workday)
                   + schema.org JobPosting pages + Sweden's JobTech API
                          │
                  student-role filter (5 languages) → fields, skills, study year, languages
                          │            (optional) Claude enrichment for new/changed ads
                          ▼
            Supabase `jobs` table  +  data/jobs.json (crawl state, committed daily)
                          │
            site/jobs.json → site/index.html (Beehive with listings inlined) → GitHub Pages
```

## Setup (about 15 minutes)

1. **Supabase.** Create a project at supabase.com. Open *SQL editor → New query*, paste
   `schema.sql`, run it. From *Project settings → API* copy the project URL and the
   secret key (`sb_secret_...`, or the legacy `service_role` key). The service role key can write everything: keep it in GitHub secrets
   and `.env` only, never in the browser.
2. **GitHub.** Create a repository and push this folder. In *Settings → Secrets and variables → Actions* add:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
   - `ANTHROPIC_API_KEY` (optional, turns on Claude enrichment)
   - a variable `CRAWLER_CONTACT` with an email, so sites know who is crawling
3. **Pages.** *Settings → Pages → Source: GitHub Actions.*
4. **First run.** *Actions → Crawl jobs → Run workflow.* When it finishes, Beehive is live at
   your Pages URL with the day's listings. It then runs daily at 04:00 UTC.

Supabase is optional for the site itself: the crawl state in `data/jobs.json` is committed each
run, so the Pages build works without it. Use Supabase as the store for the Next.js version.

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in what you have; everything is optional locally
python -m crawler run           # crawl, filter, (enrich), store
python -m crawler export --out site/jobs.json
python scripts/build_app.py     # site/index.html with listings inlined
python -m http.server -d site   # open http://localhost:8000
python -m pytest tests
```

## Growing coverage

- `python -m crawler add "Company" https://company.com/careers` detects the careers system
  and adds the company. Workday and custom sites are stored with their `careers_url`.
- Add names to `candidates.txt`, then `python -m crawler discover` probes public ATS feeds for them.
  It resumes where it stopped if interrupted.
- `python -m crawler detect <url>` just reports which system a careers page uses.
- For companies on custom sites, point `careers_url` at the page that lists the jobs (not the
  careers landing page). The JSON-LD reader follows links that look like student roles.

Timing: Nordic summer and trainee roles mostly open between January and March, some large
employers from October. Expect few Finnish results in late summer and a surge in winter.

## Reading from Supabase in the app

Beehive reads listings in this order: data inlined by `build_app.py`, then `jobs.json` next to
the page, then Supabase if configured before the app script:

```html
<script>window.BEEHIVE_CONFIG = { supabaseUrl: "https://YOUR.supabase.co", supabaseAnonKey: "sb_publishable_... or legacy anon key" };</script>
```

The anon key is safe to publish: row level security only allows reading open jobs.

## Being a good crawler

- ATS endpoints are public feeds meant for embedding job boards; they are paced at 4 requests a second per provider.
- HTML pages respect `robots.txt` and are paced at one request a second per site.
- The crawler identifies itself with `CRAWLER_CONTACT`.
- It does not store recruiter names, emails or phone numbers, and it does not scrape
  LinkedIn, Indeed or Duunitori (their terms forbid it). Link out to them instead.

## More sources worth adding

- Norway: NAV's public job feed on arbeidsplassen.no (free token).
- Finland: Työmarkkinatori's job data interface (check access terms first).
- The Jobs section of https://github.com/public-apis/public-apis lists aggregator APIs
  (Jooble, Arbeitnow and others) that can fill gaps.
