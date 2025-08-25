import gspread
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SHEET_KEY = "1ZHacBdlQy3sLp-qmkOUShn7IeA1nr-zQEul1kdmU-W8"

START_TIME = datetime.strptime("08:30", "%H:%M")
GAME_DURATION = timedelta(hours=1)

# --- AUTH ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)
# creds = Credentials.from_service_account_info(
#     SERVICE_ACCOUNT_INFO,
#     scopes=["https://www.googleapis.com/auth/spreadsheets"]
# )
gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_KEY)


def get_court_team_maps(ws_name, court_row=4, team_start_row=5, team_end_row=9):
    """Return {court_number: {team_number: team_name}}"""
    ws = sh.worksheet(ws_name)
    courts = ws.row_values(court_row)[2:]  # C4:Y4
    team_grid = ws.get(f"C{team_start_row}:{chr(66+len(courts))}{team_end_row}")  

    court_team_maps = {}
    for col_idx, court in enumerate(courts):
        mapping = {}
        for row_idx, team_name in enumerate([r[col_idx] for r in team_grid]):
            team_number = str(row_idx + 1)  # Teams 1..N per court
            if team_name.strip():
                mapping[team_number] = team_name
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
    # sort by court (ascending) then by game (ascending)
    df.sort_values(by=["Court Number", "Game Number"], inplace=True, ignore_index=True)
    return df

def write_schedule(df, ws_name):
    ws = sh.worksheet(ws_name)
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())


def main():
    pool_df = get_pool_schedule()

    # Mens
    men_maps, men_courts = get_court_team_maps("Mens Master")
    men_sched = expand_schedule(men_maps, men_courts, pool_df)
    write_schedule(men_sched, "M_Scoresheets")

    # Womens
    women_maps, women_courts = get_court_team_maps("Womens Master")
    women_sched = expand_schedule(women_maps, women_courts, pool_df)
    write_schedule(women_sched, "W_Scoresheets")

if __name__ == "__main__":
    main()