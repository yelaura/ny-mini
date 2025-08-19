import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import argparse

# --- Google Sheets setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

# --- Sheet IDs (replace with your actual ones) ---
SHEET_CONFIG = {
    "1": {  # Day 1
        "mens": "1SnbMJVwzD9JHvhzHfjuTHEzIMpSLLalVhyNh7216nXg",
        "womens": "1SAKd-O416viDWLYNAx1I2IyZrOJbKVB3eMAy-p1c68c",
        "output": "18qz3f2-tqRwUoc54_5DHdkNcju2gRIaDHDYSQGRhPUk",
    },
    "2": {  # Day 2
        "mens": "1SnbMJVwzD9JHvhzHfjuTHEzIMpSLLalVhyNh7216nXg",
        "womens": "1SAKd-O416viDWLYNAx1I2IyZrOJbKVB3eMAy-p1c68c",
        "output": "1vxYF86Jh8VL6U96jHarDUqsACYr51aFzuf8fUI65AiU",
    },
}

# --- Calculate Rankings ---
def calculate_rankings(sheet):
    data = sheet.get_all_records()
    df = pd.DataFrame(data).fillna(0)

    teams = {}

    for _, row in df.iterrows():
        t1, t2 = row["Team 1 Name"], row["Team 2 Name"]
        s1, s2 = row["Team 1 Score"], row["Team 2 Score"]
        s1_2, s2_2 = row["Team 1 Score 2"], row["Team 2 Score 2"]

        # Init
        if t1 not in teams:
            teams[t1] = {"Wins": 0, "Points For": 0, "Points Against": 0}
        if t2 not in teams:
            teams[t2] = {"Wins": 0, "Points For": 0, "Points Against": 0}

        # Game 1
        teams[t1]["Points For"] += s1
        teams[t1]["Points Against"] += s2
        teams[t2]["Points For"] += s2
        teams[t2]["Points Against"] += s1
        if s1 > s2: teams[t1]["Wins"] += 1
        elif s2 > s1: teams[t2]["Wins"] += 1

        # Game 2
        teams[t1]["Points For"] += s1_2
        teams[t1]["Points Against"] += s2_2
        teams[t2]["Points For"] += s2_2
        teams[t2]["Points Against"] += s1_2
        if s1_2 > s2_2: teams[t1]["Wins"] += 1
        elif s2_2 > s1_2: teams[t2]["Wins"] += 1

    # DataFrame
    standings = []
    for team, stats in teams.items():
        diff = stats["Points For"] - stats["Points Against"]
        standings.append([team, stats["Wins"], diff, stats["Points For"]])

    standings_df = pd.DataFrame(standings, columns=["Team", "Wins", "Point Differential", "Points For"])
    standings_df = standings_df.sort_values(by=["Wins", "Point Differential", "Points For"], ascending=[False, False, False])
    standings_df.insert(0, "Rank", range(1, len(standings_df) + 1))

    return standings_df


def get_or_create_worksheet(workbook, title, rows=100, cols=20):
    """Return worksheet if it exists, otherwise create it."""
    try:
        return workbook.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        return workbook.add_worksheet(title=title, rows=rows, cols=cols)


def main():
    parser = argparse.ArgumentParser(description="Tournament Results Processor")
    parser.add_argument("--day", type=int, required=True, help="Tournament day (1 or 2)")
    parser.add_argument("--division", type=str, default="both", choices=["mens", "womens", "both"],
                        help="Which division to process (mens, womens, or both)")
    args = parser.parse_args()

    config = SHEET_CONFIG[str(args.day)]
    out_wb = client.open_by_key(config["output"])

    # --- Mens ---
    if args.division in ["mens", "both"]:
        mens_sheet = client.open_by_key(config["mens"]).sheet1
        mens_rankings = calculate_rankings(mens_sheet)

        tab_name = f"Mens_Day{args.day}"
        mens_out = get_or_create_worksheet(out_wb, tab_name)
        mens_out.clear()
        mens_out.update([mens_rankings.columns.values.tolist()] + mens_rankings.values.tolist())
        print(f"✅ Day {args.day} Men's standings updated in tab '{tab_name}'")

    # --- Womens ---
    if args.division in ["womens", "both"]:
        womens_sheet = client.open_by_key(config["womens"]).sheet1
        womens_rankings = calculate_rankings(womens_sheet)

        tab_name = f"Womens_Day{args.day}"
        womens_out = get_or_create_worksheet(out_wb, tab_name)
        womens_out.clear()
        womens_out.update([womens_rankings.columns.values.tolist()] + womens_rankings.values.tolist())
        print(f"✅ Day {args.day} Women's standings updated in tab '{tab_name}'")

    if args.day == 2:
        print("⚠️ Check for ties across playoff brackets")


if __name__ == "__main__":
    main()
