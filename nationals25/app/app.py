import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---- CONFIG ----
# Schedule sheet
SCHEDULE_SHEET_ID = "1ZHacBdlQy3sLp-qmkOUShn7IeA1nr-zQEul1kdmU-W8"
MEN_SHEET_KEY = "M_Scoresheets"
WOMEN_SHEET_KEY = "W_Scoresheets"

# Results sheet
RESULTS_SHEET_NAME = [
    "RESULTS_SHEET_ID_ROUND1",
    "RESULTS_SHEET_ID_ROUND2",
    "RESULTS_SHEET_ID_ROUND3"
]
MEN_RESULTS_KEY = "Mens"
WOMEN_RESULTS_KEY = "Womens"

# Roster sheet
ROSTER_SHEET_ID = "YOUR_ROSTER_SHEET_ID_HERE"
ROSTER_WORKSHEET_NAME = "NYC"

# ---- STREAMLIT CACHING FUNCTIONS ----
@st.cache_data(ttl=900)
def load_sheet(sheet_id, worksheet_name):
    """Load any Google Sheet worksheet as a DataFrame"""
    service_account_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(sheet_id).worksheet(worksheet_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)

# ---- HELPER FUNCTIONS ----
def compute_status(row, team_name):
    if row["Team 1"] == team_name or row["Team 2"] == team_name:
        return "Playing"
    elif row["Work Team"] == team_name:
        return "Working"
    else:
        return "Off"

def highlight_status(row):
    if row["Team Status"] == "Playing":
        return ['background-color: lightgreen']*len(row)
    elif row["Team Status"] == "Working":
        return ['background-color: lightyellow']*len(row)
    else:
        return ['background-color: lightgray']*len(row)

def load_team_results(df, team, team1_col="Team 1 Name", team2_col="Team 2 Name"):
    """Filter and format results for a given team"""
    team_df = df[(df[team1_col] == team) | (df[team2_col] == team)]
    if team_df.empty:
        st.info("No game results available yet.")
        return pd.DataFrame()
    results = []
    for _, row in team_df.iterrows():
        if row[team1_col] == team:
            score1 = f"{row['Team 1 Score']}-{row['Team 2 Score']}"
            score2 = f"{row['Team 1 Score 2']}-{row['Team 2 Score 2']}"
        else:
            score1 = f"{row['Team 2 Score']}-{row['Team 1 Score']}"
            score2 = f"{row['Team 2 Score 2']}-{row['Team 1 Score 2']}"
        team_points = row['Team 1 Score'] + row['Team 1 Score 2'] if row[team1_col] == team else row['Team 2 Score'] + row['Team 2 Score 2']
        opp_points = row['Team 2 Score'] + row['Team 2 Score 2'] if row[team1_col] == team else row['Team 1 Score'] + row['Team 1 Score 2']
        winner = team if team_points > opp_points else row[team1_col] if row[team1_col] != team else row[team2_col] if team_points < opp_points else "Tie"
        results.append({
            "Court Number": row["Court Number"],
            "Game Number": row["Game Number (1-10)"],
            "Opponent": row[team1_col] if row[team1_col] != team else row[team2_col],
            "Score 1": score1,
            "Score 2": score2,
            "Winner": winner
        })
    return pd.DataFrame(results)

# ---- MAIN APP ----
st.title("🏐 The 80th NACIVT in NYC")

# Create tabs
tabs = st.tabs(["Schedule", "Results", "Roster"])

# --- SCHEDULE TAB ---
with tabs[0]:
    st.header("Schedule")
    division = st.selectbox("Select Division (Schedule)", ["Men's", "Women's"], key="sched_div")
    team = st.selectbox("Select Team (Schedule)", [], key="sched_team")

    # Load schedule data
    schedule_sheet = MEN_SHEET_KEY if division == "Men's" else WOMEN_SHEET_KEY
    schedule_df = load_sheet(SCHEDULE_SHEET_ID, schedule_sheet)

    # Populate team selectbox dynamically
    if schedule_df is not None and not schedule_df.empty:
        all_teams = sorted(set(schedule_df["Team 1"].tolist() + schedule_df["Team 2"].tolist() + schedule_df["Work Team"].tolist()))
        team = st.selectbox("Select Team (Schedule)", all_teams, key="sched_team")

        # Compute Team Status
        schedule_df["Team Status"] = schedule_df.apply(lambda r: compute_status(r, team), axis=1)
        team_schedule = schedule_df[schedule_df["Team Status"] != "Off"]
        team_schedule.sort_values(by=["Court Number", "Game Number"], inplace=True, ignore_index=True)
        st.dataframe(team_schedule.style.apply(highlight_status, axis=1))

# --- RESULTS TAB ---
with tabs[1]:
    st.header("Results")
    division_res = st.selectbox("Select Division (Results)", ["Men's", "Women's"], key="res_div")
    team_res = st.selectbox("Select Team (Results)", [], key="res_team")

    # Populate team selectbox dynamically based on first round
    sheet_key = MEN_RESULTS_KEY if division_res == "Men's" else WOMEN_RESULTS_KEY
    df_first_round = load_sheet(RESULTS_SHEET_NAME[0], sheet_key)
    all_teams_res = sorted(set(df_first_round["Team 1 Name"].tolist() + df_first_round["Team 2 Name"].tolist()))
    team_res = st.selectbox("Select Team (Results)", all_teams_res, key="res_team")

    for round_idx, round_name in enumerate(["Round 1", "Round 2", "Round 3"]):
        st.subheader(round_name)
        df_results = load_sheet(RESULTS_SHEET_NAME[round_idx], sheet_key)
        df_team_results = load_team_results(df_results, team_res)
        if not df_team_results.empty:
            st.dataframe(df_team_results)

# --- ROSTER TAB ---
with tabs[2]:
    st.header("Roster")
    division_roster = st.selectbox("Select Division (Roster)", ["Men's", "Women's"], key="roster_div")
    team_roster = st.selectbox("Select Team (Roster)", [], key="roster_team")

    roster_df = load_sheet(ROSTER_SHEET_ID, ROSTER_WORKSHEET_NAME)
    roster_df["Division"] = roster_df["Gender"].map({"Male": "Men's", "Female": "Women's"})
    roster_div = roster_df[roster_df["Division"] == division_roster]

    all_teams_roster = sorted(roster_div["Registration Name"].unique())
    team_roster = st.selectbox("Select Team (Roster)", all_teams_roster, key="roster_team")

    team_roster_df = roster_div[roster_div["Registration Name"] == team_roster][
        ["Name", "Jersey Number", "Wristband"]
    ].reset_index(drop=True)
    st.dataframe(team_roster_df)
