import gspread
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials
from gspread.utils import rowcol_to_a1

# --- CONFIG ---
SHEET_KEY = "18qz3f2-tqRwUoc54_5DHdkNcju2gRIaDHDYSQGRhPUk"
START_TIME = datetime.strptime("07:30", "%H:%M")
GAME_DURATION = timedelta(hours=1)

# --- AUTH ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_KEY)

# --- FUNCTIONS ---
def get_court_team_maps(ws_name, court_row, team_start_row, team_end_row):
    """
    Returns a mapping of courts to team numbers and team names.
    Ensures all columns including the last court are fetched correctly.
    """
    ws = sh.worksheet(ws_name)

    # Get court numbers from the header row
    courts = ws.row_values(court_row)[2:]  # e.g., C3:Y3

    # Build exact range for the team names
    start_cell = rowcol_to_a1(team_start_row, 3)  # column C
    end_cell = rowcol_to_a1(team_end_row, 2 + len(courts))  # last court column
    team_grid = ws.get(f"{start_cell}:{end_cell}")

    court_team_maps = {}
    for col_idx, court in enumerate(courts):
        mapping = {}
        for row_idx, row in enumerate(team_grid):
            # Safe access in case some rows are shorter
            team_name = row[col_idx] if col_idx < len(row) else ""
            if team_name.strip():
                mapping[str(row_idx + 1)] = team_name
        court_team_maps[court] = mapping

    return court_team_maps, courts

def get_pool_schedule():
    """Reads pool schedules (game, t1, t2, work)"""
    ws = sh.worksheet("Pool Schedules")
    data = ws.get("F5:I14")
    df = pd.DataFrame(data, columns=["Game", "Team 1", "Team 2", "Work Team"])
    return df

def expand_schedule(court_team_maps, courts, pool_df):
    """Expand pool schedule across all courts with correct team names per court"""
    schedule = []
    for _, row in pool_df.iterrows():
        game_num = int(row["Game"])
        start_time = (START_TIME + (game_num - 1) * GAME_DURATION).strftime("%I:%M %p")
        for court in courts:
            team_map = court_team_maps[court]
            schedule.append({
                "Start Time": start_time,
                "Court Number": court,
                "Game Number": game_num,
                "Team 1": team_map.get(str(row["Team 1"]), f"Team {row['Team 1']}"),
                "Team 2": team_map.get(str(row["Team 2"]), f"Team {row['Team 2']}"),
                "Work Team": team_map.get(str(row["Work Team"]), f"Team {row['Work Team']}")
            })
    df = pd.DataFrame(schedule)
    df.sort_values(by=["Court Number", "Game Number"], inplace=True, ignore_index=True)
    return df

def write_schedule(df, ws_name):
    try:
        ws = sh.worksheet(ws_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=ws_name, rows="100", cols="20")
    ws.update([df.columns.values.tolist()] + df.values.tolist())

# --- MAIN ---
def main():
    pool_df = get_pool_schedule()

    # Mens Round 2: courts C3:Y3, teams C4:Y8
    men_maps, men_courts = get_court_team_maps("Round 2 Pools", court_row=3, team_start_row=4, team_end_row=8)
    men_sched = expand_schedule(men_maps, men_courts, pool_df)
    write_schedule(men_sched, "M_Scoresheets")

    # Womens Round 2: courts C13:T13, teams C14:T18
    # women_maps, women_courts = get_court_team_maps("Round 2 Pools", court_row=13, team_start_row=14, team_end_row=18)
    # women_sched = expand_schedule(women_maps, women_courts, pool_df)
    # write_schedule(women_sched, "W_Scoresheets")

if __name__ == "__main__":
    main()
