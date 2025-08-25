import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# ---- SHEET IDS ----
SCHEDULE_SHEET_ID = "1ZHacBdlQy3sLp-qmkOUShn7IeA1nr-zQEul1kdmU-W8"
RESULTS_SHEET_ID  = "1SnbMJVwzD9JHvhzHfjuTHEzIMpSLLalVhyNh7216nXg"
ROSTER_SHEET_ID   = "1sLcO9XSJTVmO2lNzZUxLLEM4pMuVzfAvzH1NRU7VQRc"

MEN_SHEET_KEY     = "Mens"
WOMEN_SHEET_KEY   = "Womens"

# ---- SCHEDULE CONFIG ----
START_TIME = datetime.strptime("07:30", "%H:%M")
GAME_DURATION = timedelta(hours=1)

# ---- AUTH ----
def get_client():
    service_account_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return gspread.authorize(creds)

# ---- LOAD DATA ----
@st.cache_data(ttl=21600)  # 6 hours
def load_roster():
    gc = get_client()
    sheet = gc.open_by_key(ROSTER_SHEET_ID)
    ws = sheet.worksheet("NYC")
    data = ws.get("A:H")
    df = pd.DataFrame(data[1:], columns=data[0]).fillna("").astype(str)
    df.columns = df.columns.str.strip()
    df.rename(columns={
        'Name': 'Player Name',
        'Jersey Number': 'Jersey #',
        'Registration Name': 'Team',
        'Wristband': 'Wristband Color'
    }, inplace=True)

    # Make sure 'Gender' column exists in the sheet!
    if "Gender" in df.columns:
        df["Division"] = df["Gender"].map({"Male": "Men's", "Female": "Women's"})
    else:
        # fallback: assign based on external knowledge or keep empty
        df["Division"] = ""

    return df

@st.cache_data(ttl=21600)  # 6 hours
def load_schedule(sheet_id, ws_name, court_row, team_start_row, team_end_row):
    """Return full court schedule"""
    gc = get_client()
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(ws_name)

    courts = ws.row_values(court_row)[2:]
    from gspread.utils import rowcol_to_a1
    start_cell = rowcol_to_a1(team_start_row, 3)
    end_cell = rowcol_to_a1(team_end_row, 2 + len(courts))
    team_grid = ws.get(f"{start_cell}:{end_cell}")

    court_team_maps = {}
    for col_idx, court in enumerate(courts):
        mapping = {}
        for row_idx, row in enumerate(team_grid):
            team_name = row[col_idx] if col_idx < len(row) else ""
            if team_name.strip():
                mapping[str(row_idx + 1)] = team_name
        court_team_maps[court] = mapping

    # Get pool schedule
    pool_ws = sh.worksheet("Pool Schedules")
    pool_data = pool_ws.get("F5:I14")
    pool_df = pd.DataFrame(pool_data, columns=["Game", "Team 1", "Team 2", "Work Team"])

    # Expand schedule
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

@st.cache_data(ttl=900)  # 15 minutes
def load_results(sheet_id, ws_name):
    gc = get_client()
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(ws_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)

# ---- HELPER ----
def team_status(row, team):
    if row["Team 1"] == team or row["Team 2"] == team:
        return "Playing"
    elif row["Work Team"] == team:
        return "Working"
    else:
        return "Off"

# ---- APP ----
def main():
    st.title("🏐 The 80th NACIVT in NYC")

    roster_df = load_roster()

    tabs = st.tabs(["Schedule", "Results", "Roster"])

    # -------- SCHEDULE TAB --------
    with tabs[0]:
        st.header("Schedule")
        division = st.selectbox("Select Division", options=["Men's", "Women's"])
        team = st.selectbox(
            "Select Team", 
            options=sorted(roster_df[roster_df["Division"]==division]["Team"].unique())
        )

        # Pick schedule worksheet and ranges
        if division == "Men's":
            schedule_df = load_schedule(SCHEDULE_SHEET_ID, "Mens Master", court_row=4, team_start_row=5, team_end_row=9)
        else:
            schedule_df = load_schedule(SCHEDULE_SHEET_ID, "Womens Master", court_row=4, team_start_row=5, team_end_row=9)

        # Filter for the court the team is on
        team_court = None
        for court, group in schedule_df.groupby("Court Number"):
            if team in group["Team 1"].values or team in group["Team 2"].values:
                team_court = court
                break
        st.subheader(f"Schedule for Court {team_court}")
        schedule_df_court = schedule_df[schedule_df["Court Number"]==team_court].copy()
        schedule_df_court["Status"] = schedule_df_court.apply(lambda r: team_status(r, team), axis=1)
        st.dataframe(schedule_df_court)

    # -------- RESULTS TAB --------
    with tabs[1]:
        st.header("Results")
        division = st.selectbox("Select Division (Results)", options=["Men's", "Women's"], key="results_div")
        team = st.selectbox(
            "Select Team (Results)", 
            options=sorted(roster_df[roster_df["Division"]==division]["Team"].unique()),
            key="results_team"
        )

        sheet_key = MEN_SHEET_KEY if division=="Men's" else WOMEN_SHEET_KEY
        results_df = load_results(RESULTS_SHEET_ID, sheet_key)

        # Round 1
        st.subheader("Round 1")
        r1_df = results_df[results_df["Timestamp"].str.startswith("8/30/2025")]
        st.dataframe(r1_df[(r1_df["Team 1 Name"]==team)|(r1_df["Team 2 Name"]==team)])

        # Round 2
        st.subheader("Round 2")
        r2_df = results_df[results_df["Timestamp"].str.startswith("8/31/2025")]
        st.dataframe(r2_df[(r2_df["Team 1 Name"]==team)|(r2_df["Team 2 Name"]==team)])

        # Round 3
        st.subheader("Round 3")
        st.dataframe(results_df[(results_df["Team 1 Name"]==team)|(results_df["Team 2 Name"]==team)])

    # -------- ROSTER TAB --------
    with tabs[2]:
        st.header("Roster")
        division = st.selectbox("Select Division (Roster)", options=["Men's", "Women's"], key="roster_div")
        team = st.selectbox(
            "Select Team (Roster)", 
            options=sorted(roster_df[roster_df["Division"]==division]["Team"].unique()),
            key="roster_team"
        )
        roster_team_df = roster_df[(roster_df["Division"]==division) & (roster_df["Team"]==team)][
            ["Player Name","Jersey #","Wristband Color"]
        ].reset_index(drop=True)
        st.dataframe(roster_team_df)

if __name__ == "__main__":
    main()
