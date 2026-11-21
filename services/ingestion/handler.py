"""Fetch La Liga and Liga MX scores from ESPN's public scoreboard."""

import functools
import os
import sys
from datetime import UTC, datetime, timedelta

import psycopg
import requests

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
)
LEAGUES = ["esp.1", "mex.1"]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "matchday-platform/1.0"})


def fetch_scoreboard(league: str, date: str | None = None) -> list[dict]:
    """Return ESPN's raw events for one league: today, or a YYYYMMDD date."""
    params = {"dates": date} if date else {}
    resp = SESSION.get(ESPN_SCOREBOARD.format(league=league), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("events", [])


def parse_team(competitor: dict) -> dict:
    """Shape one ESPN competitor like a row in our teams table."""
    team = competitor["team"]
    return {
        "espn_id": team["id"],
        "name": team["displayName"],
        "abbreviation": team["abbreviation"],
        "logo_url": team.get("logo"),
    }


def parse_event(event: dict, league: str) -> dict:
    """Shape one ESPN event like a row in our matches table."""
    competition = event["competitions"][0]
    sides = {c["homeAway"]: c for c in competition["competitors"]}
    home, away = sides["home"], sides["away"]
    status = event["status"]
    state = status["type"]["state"]

    def score(side: dict) -> int | None:
        # ESPN says "0" before kickoff; we store no score until the match starts
        return None if state == "pre" else int(side.get("score") or 0)

    return {
        "espn_id": event["id"],
        "league_slug": league,
        "season_year": event["season"]["year"],
        "season_slug": event["season"].get("slug"),
        "kickoff_at": event["date"],
        "home_team": parse_team(home),
        "away_team": parse_team(away),
        "home_score": score(home),
        "away_score": score(away),
        "state": state,
        "status_name": status["type"]["name"],
        "display_clock": status.get("displayClock"),
        "venue": competition.get("venue", {}).get("fullName"),
    }


UPSERT_TEAM = """
    insert into matchday.teams (espn_id, name, abbreviation, logo_url)
    values (%(espn_id)s, %(name)s, %(abbreviation)s, %(logo_url)s)
    on conflict (espn_id) do update set
        name         = excluded.name,
        abbreviation = excluded.abbreviation,
        logo_url     = excluded.logo_url
"""

UPSERT_MATCH = """
    insert into matchday.matches (
        espn_id, league_slug, season_year, season_slug, kickoff_at,
        home_team_id, away_team_id, home_score, away_score,
        state, status_name, display_clock, venue
    )
    values (
        %(espn_id)s, %(league_slug)s, %(season_year)s, %(season_slug)s, %(kickoff_at)s,
        %(home_team_id)s, %(away_team_id)s, %(home_score)s, %(away_score)s,
        %(state)s, %(status_name)s, %(display_clock)s, %(venue)s
    )
    on conflict (espn_id) do update set
        kickoff_at    = excluded.kickoff_at,
        home_score    = excluded.home_score,
        away_score    = excluded.away_score,
        state         = excluded.state,
        status_name   = excluded.status_name,
        display_clock = excluded.display_clock,
        venue         = excluded.venue,
        updated_at    = now()
"""


def save_matches(conn, matches: list[dict]) -> None:
    """Upsert teams first (matches reference them), then matches."""
    teams = {}
    for m in matches:
        for team in (m["home_team"], m["away_team"]):
            teams[team["espn_id"]] = team

    rows = [
        {
            **m,
            "home_team_id": m["home_team"]["espn_id"],
            "away_team_id": m["away_team"]["espn_id"],
        }
        for m in matches
    ]

    with conn.cursor() as cur:
        cur.executemany(UPSERT_TEAM, list(teams.values()))
        cur.executemany(UPSERT_MATCH, rows)


LIVE_WINDOW_SQL = """
    select distinct
        league_slug,
        to_char(kickoff_at at time zone 'America/New_York', 'YYYYMMDD') as espn_date
    from matchday.matches
    where state <> 'post'
      and kickoff_at between now() - interval '140 minutes' and now() + interval '5 minutes'
"""


def find_live_scoreboards(conn) -> list[tuple[str, str]]:
    """Return (league, ESPN date) pairs that have a match in the live window."""
    with conn.cursor() as cur:
        cur.execute(LIVE_WINDOW_SQL)
        return cur.fetchall()


@functools.cache
def get_dsn() -> str:
    """Local runs use DATABASE_URL; in Lambda, read it from SSM Parameter Store."""
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]

    import boto3  # included in the Lambda runtime; not needed locally

    ssm = boto3.client("ssm")
    param = ssm.get_parameter(
        Name=os.environ["DATABASE_URL_PARAM"], WithDecryption=True
    )
    return param["Parameter"]["Value"]


def run(mode: str) -> int:
    """Fetch the scoreboards this mode needs and save them. Returns matches saved."""
    dsn = get_dsn()

    if mode == "fixtures":
        today = datetime.now(UTC).date()
        targets = [
            (league, (today + timedelta(days=offset)).strftime("%Y%m%d"))
            for league in LEAGUES
            for offset in range(-1, 8)
        ]
    elif mode == "live":
        with psycopg.connect(dsn, prepare_threshold=None) as conn:
            targets = find_live_scoreboards(conn)
        if not targets:
            print("live: nothing in the window, skipping ESPN.")
            return 0
    else:
        raise ValueError(f"Unknown mode: {mode!r}")

    matches = [
        parse_event(e, league)
        for league, date in targets
        for e in fetch_scoreboard(league, date)
    ]

    with psycopg.connect(dsn, prepare_threshold=None) as conn:
        save_matches(conn, matches)

    print(f"{mode}: saved {len(matches)} matches from {len(targets)} scoreboard(s).")
    return len(matches)


def handler(event, context):
    """AWS Lambda entry point. EventBridge sends {"mode": "fixtures"} or {"mode": "live"}."""
    mode = event.get("mode", "live")
    saved = run(mode)
    return {"mode": mode, "saved": saved}


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "live")
