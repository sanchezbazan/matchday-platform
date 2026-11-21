"""Fetch La Liga and Liga MX scores from ESPN's public scoreboard."""

import sys

import requests

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard"
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


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    for league in LEAGUES:
        for event in fetch_scoreboard(league, date):
            m = parse_event(event, league)
            home, away = m["home_team"]["abbreviation"], m["away_team"]["abbreviation"]
            hs = "-" if m["home_score"] is None else m["home_score"]
            aws = "-" if m["away_score"] is None else m["away_score"]
            print(f"{league}  {home} {hs}–{aws} {away}  [{m['state']}] {m['display_clock']}  {m['kickoff_at']}")