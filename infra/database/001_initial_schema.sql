begin;

-- Separate schema, kept apart from Django's tables in public
create schema matchday;

-- Leagues we track
create table matchday.leagues (
  slug  text primary key,          -- ESPN's code: 'esp.1', 'mex.1'
  name  text not null
);

insert into matchday.leagues (slug, name) values
  ('esp.1', 'La Liga'),
  ('mex.1', 'Liga MX');

-- Teams, stored once each
create table matchday.teams (
  espn_id       text primary key,  -- ESPN team id, e.g. '231'
  name          text not null,
  abbreviation  text not null,
  logo_url      text
);

-- One row per match, updated while it's live
create table matchday.matches (
  espn_id        text primary key,                    -- ESPN event id
  league_slug    text not null references matchday.leagues (slug),
  season_year    int  not null,                       -- 2026
  season_slug    text,                                -- 'torneo-apertura'
  kickoff_at     timestamptz not null,
  home_team_id   text not null references matchday.teams (espn_id),
  away_team_id   text not null references matchday.teams (espn_id),
  home_score     int,
  away_score     int,
  state          text not null check (state in ('pre', 'in', 'post')),
  status_name    text,                                -- 'STATUS_HALFTIME', etc.
  display_clock  text,                                -- "67'"
  venue          text,
  updated_at     timestamptz not null default now()
);

-- Speeds up the Lambda's "is anything live?" check
create index matches_kickoff_idx on matchday.matches (kickoff_at);

-- Defense in depth: block Supabase's API roles even if this schema is ever exposed
alter table matchday.leagues enable row level security;
alter table matchday.teams   enable row level security;
alter table matchday.matches enable row level security;
revoke all on schema matchday from anon, authenticated;

commit;