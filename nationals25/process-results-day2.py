import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
# INPUT_SHEET_KEY = "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc" # test input
INPUT_SHEET_KEY = "1SnbMJVwzD9JHvhzHfjuTHEzIMpSLLalVhyNh7216nXg"
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

def add_opponent_sets_won(teams, matches):
    """Add total opponent sets won as a strength-of-schedule tiebreaker."""
    team_lookup = {t["team"]: t for t in teams}

    for team in teams:
        opponents = set()
        for match in matches:
            if match["t1"] == team["team"]:
                opponents.add(match["t2"])
            elif match["t2"] == team["team"]:
                opponents.add(match["t1"])

        # sum all sets_won by this team's opponents
        opp_sets_won = sum(team_lookup[opp]["sets_won"] for opp in opponents if opp in team_lookup)
        team["opponent_sets_won"] = opp_sets_won


def build_sort_key(team, matches, all_teams):
    """Build sort key: sets won, point diff, head-to-head, point ratio, opponent sets won."""
    sets_won = team["sets_won"]
    point_diff = team["point_diff"]
    point_ratio = team["point_ratio"]
    opponent_sets_won = team.get("opponent_sets_won", 0)

    head_to_head = 0
    h2h_played = False
    h2h_results = []

    for opponent in all_teams:
        if opponent["team"] == team["team"]:
            continue

        if sets_won == opponent["sets_won"] and point_diff == opponent["point_diff"]:
            t_sets, o_sets = 0, 0
            t_points, o_points = 0, 0

            for match in matches:
                if {match["t1"], match["t2"]} == {team["team"], opponent["team"]}:
                    h2h_played = True
                    if match["t1"] == team["team"]:
                        s1, s2 = match["t1s"], match["t2s"]
                        s1b, s2b = match.get("t1s2", 0), match.get("t2s2", 0)
                        # Set 1
                        if s1 > s2:
                            t_sets += 1
                        elif s1 < s2:
                            o_sets += 1
                        t_points += s1
                        o_points += s2
                        # Set 2
                        if s1b > s2b:
                            t_sets += 1
                        elif s1b < s2b:
                            o_sets += 1
                        t_points += s1b
                        o_points += s2b
                    else:
                        s1, s2 = match["t2s"], match["t1s"]
                        s1b, s2b = match.get("t2s2", 0), match.get("t1s2", 0)
                        if s1 > s2:
                            t_sets += 1
                        elif s1 < s2:
                            o_sets += 1
                        t_points += s1
                        o_points += s2
                        if s1b > s2b:
                            t_sets += 1
                        elif s1b < s2b:
                            o_sets += 1
                        t_points += s1b
                        o_points += s2b

            if t_sets > o_sets:
                head_to_head = 1
            elif o_sets > t_sets:
                head_to_head = -1
            else:
                if t_points > o_points:
                    head_to_head = 1
                elif o_points > t_points:
                    head_to_head = -1
                else:
                    head_to_head = 0

            if t_sets or o_sets:
                h2h_results.append(f"vs {opponent['team']} (sets {t_sets}-{o_sets}, pts {t_points}-{o_points})")

    if not h2h_results:
        h2h_results = ["None"]

    team["head_to_head_result"] = ", ".join(h2h_results)
    team["h2h_played"] = h2h_played

    # Keep opponent_sets_won positive; reverse=True will sort descending
    return (sets_won, point_diff, head_to_head, round(point_ratio, 5), opponent_sets_won)



def rank_teams(teams, matches):
    """Rank teams using all tiebreakers including opponent sets won."""
    for team in teams:
        team["sort_key"] = build_sort_key(team, matches, teams)

    # Sort descending by all metrics: sets, point diff, head-to-head, point ratio, opponent sets
    ranked = sorted(
        teams,
        key=lambda t: (
            t["sort_key"][0],  # sets_won
            t["sort_key"][1],  # point_diff
            t["sort_key"][2],  # head_to_head
            t["sort_key"][3],  # point_ratio
            t["sort_key"][4],  # opponent_sets_won
        ),
        reverse=True
    )

    return ranked


def write_results(ws_name, teams):
    """Write ranked results with accurate tie reasons."""
    output = []

    for i, team in enumerate(teams):
        tied_with = []
        tie_reasons = []

        for j, other in enumerate(teams):
            if i == j:
                continue

            sets1, pd1, h2h1, pr1, opp_sets1 = team["sort_key"]
            sets2, pd2, h2h2, pr2, opp_sets2 = other["sort_key"]

            # Track teams tied ignoring opponent sets
            if team["sort_key"][:-1] == other["sort_key"][:-1]:
                tied_with.append(other["team"])

            # Only check tie reasons if sets & point diff tied
            if sets1 == sets2 and pd1 == pd2:
                # H2H tie reason only if teams played each other
                if h2h1 == h2h2 == 0 and team.get("h2h_played", False):
                    tie_reasons.append("equal sets & point diff, equal H2H sets & points")
                elif h2h1 == h2h2 and team.get("h2h_played", False):
                    tie_reasons.append("equal sets & point diff, equal H2H sets, fallback to point ratio")

                if pr1 == pr2:
                    tie_reasons.append("identical point ratio")

                    # Opponent sets won only if all else tied
                    if opp_sets1 != opp_sets2:
                        if opp_sets1 > opp_sets2:
                            tie_reasons.append(
                                f"won tie vs {other['team']} by opponent sets won ({opp_sets1} > {opp_sets2})"
                            )
                        else:
                            tie_reasons.append(
                                f"lost tie vs {other['team']} by opponent sets won ({opp_sets1} < {opp_sets2})"
                            )

        tied_str = ", ".join(tied_with) if tied_with else "None"
        reason_str = "; ".join(set(tie_reasons)) if tie_reasons else "None"

        output.append({
            "Overall Ranking": i + 1,
            "Team Name": team["team"],
            "Sets Won": team["sets_won"],
            "Point Differential": team["point_diff"],
            "Head to Head Result": team["head_to_head_result"],
            "Point Ratio": round(team["point_ratio"], 5),
            "Tied With": tied_str,
            "Tie Reason": reason_str,
            "Opponent Sets Won": team.get("opponent_sets_won", 0)
        })

    df = pd.DataFrame(output)

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
        add_opponent_sets_won(teams, matches)
        ranked = rank_teams(teams, matches)
        write_results(out_ws, ranked)


if __name__ == "__main__":
    main()
