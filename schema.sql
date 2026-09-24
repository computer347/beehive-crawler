-- Beehive job store. Run once in Supabase: SQL editor > New query > paste > Run.

create table if not exists public.jobs (
  id            text primary key,              -- stable hash of source + company + source id
  source        text not null,                 -- greenhouse, lever, ashby, recruitee, smartrecruiters, workable, workday, jsonld, jobtech
  source_id     text not null,
  company       text not null,
  company_slug  text,
  title         text not null,
  url           text,                          -- where students apply
  city          text,
  country       text not null check (country in ('FI','SE','NO','DK','IS')),
  type          text not null check (type in ('Internship','Summer job','Thesis','Part-time','Graduate')),
  mode          text,
  level         text default 'B',              -- B: bachelor's students can apply, M: master's level
  min_year      int  default 1,
  langs         text[] default '{English}',
  skills        text[] default '{}',
  fields        text[] default '{}',
  about         text,
  bullets       jsonb default '[]',
  description   text,
  pay           text,
  industry      text,
  posted_at     timestamptz,
  deadline      timestamptz,
  enriched      boolean default false,
  content_hash  text,
  first_seen    timestamptz default now(),
  last_seen     timestamptz default now(),
  is_open       boolean default true
);
create index if not exists jobs_open_country on public.jobs (country) where is_open;
create index if not exists jobs_open_type    on public.jobs (type) where is_open;
create index if not exists jobs_skills       on public.jobs using gin (skills);

create table if not exists public.crawl_runs (
  id bigserial primary key, run_at timestamptz, companies int, errors int,
  ads_seen int, student_roles int, closed int
);

-- Security: the browser (anon key) may only read open jobs. The crawler writes with the
-- service role key, which bypasses row level security and must stay server-side.
alter table public.jobs enable row level security;
alter table public.crawl_runs enable row level security;
drop policy if exists "Anyone can read open jobs" on public.jobs;
create policy "Anyone can read open jobs" on public.jobs for select to anon, authenticated using (is_open);

-- What the app reads: open, not past deadline, without the long description.
create or replace view public.open_jobs with (security_invoker = on) as
  select id, title, company, industry, city, country, type, mode, pay, fields, skills, level, min_year,
         langs, about, bullets, url, source, posted_at, deadline, first_seen
  from public.jobs
  where is_open and (deadline is null or deadline > now());
grant select on public.open_jobs to anon, authenticated;
