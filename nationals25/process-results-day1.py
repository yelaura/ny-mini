import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from collections import defaultdict
from functools import cmp_to_key

# =======================
# Google Sheets Setup
# =======================
INPUT_SHEET_ID = "1SnbMJVwzD9JHvhzHfjuTHEzIMpSLLalVhyNh7216nXg"
# INPUT_SHEET_ID = "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc" # test input
OUTPUT_SHEET_ID = "18qz3f2-tqRwUoc54_5DHdkNcju2gRIaDHDYSQGRhPUk"
SERVICE_ACCOUNT_FILE = "service_account.json"  # Path to your JSON key

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
client = gspread.authorize(creds)

# =======================
# Ranking Logic
# =======================
def process_division(sheet_name):
    """Process one division (Mens/Womens) into ranked results with Pool Ranking"""
    ws = client.open_by_key(INPUT_SHEET_ID).worksheet(sheet_name)
    data = ws.get_all_records()
    df = pd.DataFrame(data)

    # Normalize column names
    df.columns = [c.strip() for c in df.columns]

    # Compute stats per team
    stats = defaultdict(lambda: {
        "court": None,
        "sets_won": 0,
        "sets_lost": 0,
        "points_for": 0,
        "points_against": 0,
        "head_to_head": defaultdict(lambda: {"wins": 0, "points_for": 0, "points_against": 0})
    })

    for _, row in df.iterrows():
        court = row["Court Number"]
        t1, t2 = row["Team 1 Name"], row["Team 2 Name"]
        s1a, s2a = int(row["Team 1 Score"]), int(row["Team 2 Score"])
        s1b, s2b = int(row.get("Team 1 Score 2", 0)), int(row.get("Team 2 Score 2", 0))

        # Update per set stats
        sets = [(s1a, s2a, t1, t2), (s2a, s1a, t2, t1), (s1b, s2b, t1, t2), (s2b, s1b, t2, t1)]
        for sc, oc, t, opp in sets:
            stats[t]["court"] = court
            stats[t]["points_for"] += sc
            stats[t]["points_against"] += oc
            if sc > oc:
                stats[t]["sets_won"] += 1
            else:
                stats[t]["sets_lost"] += 1
            stats[t]["head_to_head"][opp]["points_for"] += sc
            stats[t]["head_to_head"][opp]["points_against"] += oc
            if sc > oc:
                stats[t]["head_to_head"][opp]["wins"] += 1

    # Convert stats into dataframe
    teams = []
    for team, st in stats.items():
        pf, pa = st["points_for"], st["points_against"]
        pdiff = pf - pa
        pratio = pf / pa if pa > 0 else pf
        teams.append({
            "team": team,
            "court": st["court"],
            "sets_won": st["sets_won"],
            "point_diff": pdiff,
            "point_ratio": round(pratio, 3),
            "head_to_head": st["head_to_head"]
        })

    df_stats = pd.DataFrame(teams)

    # Sort within each court with head-to-head + points logic
    courts_ranked = []
    for court, group in df_stats.groupby("court"):
        group = list(group.to_dict("records"))

        def compare_teams(a, b):
            # 1. Sets won (overall)
            if a["sets_won"] != b["sets_won"]:
                return b["sets_won"] - a["sets_won"]

            # 2. Head-to-head sets
            if b["team"] in a["head_to_head"]:
                a_vs_b = a["head_to_head"][b["team"]]
                b_vs_a = b["head_to_head"][a["team"]]

                if a_vs_b["wins"] != b_vs_a["wins"]:
                    return b_vs_a["wins"] - a_vs_b["wins"]

                # 3. Head-to-head points (if sets tied)
                a_points = a_vs_b["points_for"] - a_vs_b["points_against"]
                b_points = b_vs_a["points_for"] - b_vs_a["points_against"]
                if a_points != b_points:
                    return b_points - a_points

            # 4. Point differential (overall)
            if a["point_diff"] != b["point_diff"]:
                return b["point_diff"] - a["point_diff"]

            # 5. Point ratio (overall)
            if a["point_ratio"] != b["point_ratio"]:
                return -1 if a["point_ratio"] < b["point_ratio"] else 1

            return 0

        group.sort(key=cmp_to_key(compare_teams))

        # Assign Pool Ranking within each court
        for i, t in enumerate(group, 1):
            t["Pool Ranking"] = i
        courts_ranked.extend(group)

    df_ranked = pd.DataFrame(courts_ranked)

    # Global ranking (across courts) — sorted by Pool Ranking, sets won, point diff, point ratio
    df_ranked = df_ranked.sort_values(
        by=["Pool Ranking", "sets_won", "point_diff", "point_ratio"],
        ascending=[True, False, False, False]
    ).reset_index(drop=True)

    df_ranked["Overall Rank"] = df_ranked.index + 1

    # Return columns with Pool Ranking right after team name
    return df_ranked[["Overall Rank", "team", "Pool Ranking", "court", "sets_won", "point_diff", "point_ratio"]]


# =======================
# Write Results
# =======================

def write_results(sheet_name, df):
    sh = client.open_by_key(OUTPUT_SHEET_ID)
    try:
        ws = sh.worksheet(sheet_name)
        sh.del_worksheet(ws)
    except:
        pass
    ws = sh.add_worksheet(title=sheet_name, rows="100", cols="10")
    ws.update([df.columns.values.tolist()] + df.values.tolist())


# =======================
# Run
# =======================
mens_results = process_division("Mens")
womens_results = process_division("Womens")

write_results("Mens_Day1", mens_results)
# write_results("Womens_Day1", womens_results)

print("✅ Ranking completed and written to output sheet.")