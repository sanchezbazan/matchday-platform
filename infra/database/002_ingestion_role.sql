begin;

-- A login just for the Lambda (password is set separately, never in git)
create role matchday_ingest with login;

-- Let it see the matchday schema
grant usage on schema matchday to matchday_ingest;

-- Let it read, add, and update rows (no delete)
grant select, insert, update on all tables in schema matchday to matchday_ingest;

-- RLS is on, so this role also needs policies that let it through
create policy ingest_all on matchday.leagues for all to matchday_ingest using (true) with check (true);
create policy ingest_all on matchday.teams   for all to matchday_ingest using (true) with check (true);
create policy ingest_all on matchday.matches for all to matchday_ingest using (true) with check (true);

commit;