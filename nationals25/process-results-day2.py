import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
# INPUT_SHEET_KEY = "1SnbMJVwzD9JHvhzHfjuTHEzIMpSLLalVhyNh7216nXg"
INPUT_SHEET_KEY = "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc" # test input
OUTPUT_SHEET_KEY = "1vxYF86Jh8VL6U96jHarDUqsACYr51aFzuf8fUI65AiU"

# --- AUTH ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
gc = gspread.authorize(creds)
input_sh = gc.open_by_key(INPUT_SHEET_KEY)
output_sh = gc.open_by_key(OUTPUT_SHEET_KEY)


# --- FUNCTIONS ---
def get_scores(ws_name):
    """Download match results from a sheet."""
    ws = input_sh.worksheet(ws_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)


def calculate_team_stats(df):
    """Calculate sets won, point diff, point ratio for each team."""
    teams = {}
    matches = []

    for _, row in df.iterrows():
        t1, t2 = row["Team 1 Name"], row["Team 2 Name"]
        t1s1, t2s1 = int(row["Team 1 Score"]), int(row["Team 2 Score"])
        t1s2, t2s2 = int(row.get("Team 1 Score 2", 0)), int(row.get("Team 2 Score 2", 0))

        matches.append({"t1": t1, "t2": t2, "t1s": t1s1, "t2s": t2s1, "t1s2": t1s2, "t2s2": t2s2})

        for team, opp, s1, s2, s1b, s2b in [
            (t1, t2, t1s1, t2s1, t1s2, t2s2),
            (t2, t1, t2s1, t1s1, t2s2, t1s2),
        ]:
            if team not in teams:
                teams[team] = {
                    "team": team,
                    "sets_won": 0,
                    "points_scored": 0,
                    "points_allowed": 0,
                }

            # Set 1
            teams[team]["points_scored"] += s1
            teams[team]["points_allowed"] += s2
            if s1 > s2:
                teams[team]["sets_won"] += 1

            # Set 2
            teams[team]["points_scored"] += s1b
            teams[team]["points_allowed"] += s2b
            if s1b > s2b:
                teams[team]["sets_won"] += 1

    # Compute point diff and ratio
    for t in teams.values():
        scored = t["points_scored"]
        allowed = t["points_allowed"]
        t["point_diff"] = scored - allowed
        t["point_ratio"] = scored / allowed if allowed > 0 else scored

    return list(teams.values()), matches


def build_sort_key(team, matches, all_teams):
    """Build tuple sort key for ranking with aggregated head-to-head results."""
    sets_won = team["sets_won"]
    point_diff = team["point_diff"]
    point_ratio = team["point_ratio"]

    head_to_head = 0
    h2h_results = []

    for opponent in all_teams:
        if opponent["team"] == team["team"]:
            continue
        if team["sets_won"] == opponent["sets_won"] and team["point_diff"] == opponent["point_diff"]:
            wins, losses, ties = 0, 0, 0
            for match in matches:
                if {match["t1"], match["t2"]} == {team["team"], opponent["team"]}:
                    if match["t1"] == team["team"]:
                        t_points = match["t1s"] + match["t1s2"]
                        o_points = match["t2s"] + match["t2s2"]
                    else:
                        t_points = match["t2s"] + match["t2s2"]
                        o_points = match["t1s"] + match["t1s2"]

                    if t_points > o_points:
                        wins += 1
                    elif t_points < o_points:
                        losses += 1
                    else:
                        ties += 1

            if wins or losses or ties:
                h2h_results.append(f"vs {opponent['team']} ({wins}-{losses})")
                if wins > losses:
                    head_to_head = max(head_to_head, 1)
                elif wins < losses:
                    head_to_head = min(head_to_head, -1)

    if not h2h_results:
        h2h_results = ["None"]

    team["head_to_head_result"] = ", ".join(h2h_results)

    return (sets_won, point_diff, head_to_head, point_ratio)


def rank_teams(teams, matches):
    """Rank all teams globally using tuple-based sort key."""
    # Compute sort key for each team
    for team in teams:
        team["sort_key"] = build_sort_key(team, matches, teams)

    # Sort all teams descending (best first)
    ranked = sorted(teams, key=lambda t: t["sort_key"], reverse=True)
    return ranked


def write_results(ws_name, teams):
    """Write ranked results to output sheet with Tied Teams column."""
    output = []

    # Compare each team to all others to find ties
    n = len(teams)
    for i, team in enumerate(teams):
        tied_with = []
        for j, other in enumerate(teams):
            if i == j:
                continue
            # Teams are tied if all metrics are equal
            if team["sort_key"] == other["sort_key"]:
                tied_with.append(other["team"])
        tied_str = ", ".join(tied_with) if tied_with else "None"

        output.append({
            "Overall Ranking": i + 1,
            "Team Name": team["team"],
            "Sets Won": team["sets_won"],
            "Point Differential": team["point_diff"],
            "Head to Head Result": team["head_to_head_result"],
            "Point Ratio": round(team["point_ratio"], 3),
            "Tied With": tied_str
        })

    df = pd.DataFrame(output)

    # Write to Google Sheet
    try:
        ws = output_sh.worksheet(ws_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = output_sh.add_worksheet(title=ws_name, rows="100", cols="25")

    ws.update([df.columns.values.tolist()] + df.values.tolist())


# --- MAIN ---
def main():
    for division, ws_name, out_ws in [("Mens", "Mens", "Mens_Day2"), ("Womens", "Womens", "Womens_Day2")]:
        df = get_scores(ws_name)
        teams, matches = calculate_team_stats(df)
        ranked = rank_teams(teams, matches)
        write_results(out_ws, ranked)


if __name__ == "__main__":
    main()
