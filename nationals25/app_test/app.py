import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---- CONFIG ----
SCHEDULE_SHEET_ID = "18qz3f2-tqRwUoc54_5DHdkNcju2gRIaDHDYSQGRhPUk"
# RESULTS_SHEET_ID = "1SnbMJVwzD9JHvhzHfjuTHEzIMpSLLalVhyNh7216nXg"
RESULTS_SHEET_ID = "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc" # test sheet
ROSTER_SHEET_ID = "1sLcO9XSJTVmO2lNzZUxLLEM4pMuVzfAvzH1NRU7VQRc"

MEN_SHEET_KEY = "M_Schedule"
WOMEN_SHEET_KEY = "W_Schedule"

MEN_RESULTS_KEY = "Mens"
WOMEN_RESULTS_KEY = "Womens"

ROSTER_WORKSHEET_NAME = "NYC"

# ---- STREAMLIT CACHING FUNCTIONS ----
@st.cache_data(ttl=6*60*60)  # 6 hours
def load_sheet(sheet_id, worksheet_name):
    service_account_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(sheet_id).worksheet(worksheet_name)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    
    # rename columns
    df.rename(columns={
        "Court Number": "Court #",
        "Game Number": "Game #"
    }, inplace=True)
    
    return df

@st.cache_data(ttl=15*60)  # 15 minutes
def load_results_sheet(sheet_id, worksheet_name):
    service_account_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(sheet_id).worksheet(worksheet_name)
    data = ws.get_all_records()
    df = pd.DataFrame(data)

    if df.empty:
        return df
    else:
        df.columns = df.columns.str.strip()
        
        # rename columns
        df.rename(columns={
            "Court Number": "Court #",
            "Game Number (1-10)": "Game #"
        }, inplace=True)
        
        # convert timestamp
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
    
    return df

# ---- HELPER FUNCTIONS ----
def compute_status(row, team_name):
    if row.get("Team 1") == team_name or row.get("Team 2") == team_name:
        return "Playing"
    elif row.get("Work Team") == team_name:
        return "Working"
    else:
        return "Off"

def highlight_status(row):
    theme = st.get_option("theme.base")
    if theme == "dark":
        colors = {"Playing": "#006400", "Working": "#FFA500", "Off": "#444444"}
    else:
        colors = {"Playing": "#90EE90", "Working": "#FFD700", "Off": "#D3D3D3"}
    return [f'background-color: {colors.get(row["Team Status"], "")}']*len(row)

def load_team_results(df, team, team1_col="Team 1 Name", team2_col="Team 2 Name"):
    team_df = df[(df.get(team1_col) == team) | (df.get(team2_col) == team)]
    if team_df.empty:
        return pd.DataFrame()
    results = []
    for _, row in team_df.iterrows():
        if row[team1_col] == team:
            score1 = f"{row.get('Team 1 Score', '')}-{row.get('Team 2 Score', '')}"
            score2 = f"{row.get('Team 1 Score 2', '')}-{row.get('Team 2 Score 2', '')}"
        else:
            score1 = f"{row.get('Team 2 Score', '')}-{row.get('Team 1 Score', '')}"
            score2 = f"{row.get('Team 2 Score 2', '')}-{row.get('Team 1 Score 2', '')}"
        team_points = row.get('Team 1 Score', 0) + row.get('Team 1 Score 2', 0) if row[team1_col] == team else row.get('Team 2 Score', 0) + row.get('Team 2 Score 2', 0)
        opp_points = row.get('Team 2 Score', 0) + row.get('Team 2 Score 2', 0) if row[team1_col] == team else row.get('Team 1 Score', 0) + row.get('Team 1 Score 2', 0)
        winner = team if team_points > opp_points else row[team1_col] if row[team1_col] != team else row[team2_col] if team_points < opp_points else "Tie"
        results.append({
            "Court #": row.get("Court #", ""),
            "Game #": row.get("Game #", ""),
            "Opponent": row[team1_col] if row[team1_col] != team else row[team2_col],
            "Score 1": score1,
            "Score 2": score2,
            "Winner": winner
        })
    return pd.DataFrame(results)

# ---- MAIN APP ----
st.title("🏐 The 80th NACIVT in NYC")  # fixed title

tabs = st.tabs(["Schedule", "Results", "Roster"])

# --- SCHEDULE TAB ---
with tabs[0]:
    st.header("Schedule (Round 2)")
    division_sched = st.selectbox("Select Division (Schedule)", ["Men's", "Women's"], key="sched_div")
    schedule_tab = MEN_SHEET_KEY if division_sched == "Men's" else WOMEN_SHEET_KEY
    schedule_df = load_sheet(SCHEDULE_SHEET_ID, schedule_tab)

    # Unique team names for selector
    all_teams_sched = pd.Series(
        schedule_df["Team 1"].tolist() +
        schedule_df["Team 2"].tolist() +
        schedule_df["Work Team"].tolist()
    ).dropna().astype(str).str.strip()
    all_teams_sched = sorted(all_teams_sched[all_teams_sched != ""].unique())
    team_sched = st.selectbox("Select Team (Schedule)", all_teams_sched, key="sched_team")

    if schedule_df is not None and not schedule_df.empty:
        # Normalize team names in dataframe
        schedule_df["Team 1"] = schedule_df["Team 1"].astype(str).str.strip()
        schedule_df["Team 2"] = schedule_df["Team 2"].astype(str).str.strip()
        schedule_df["Work Team"] = schedule_df["Work Team"].astype(str).str.strip()

        # Normalize the selected team
        team_sched_norm = str(team_sched).strip()

        # Find the team’s court
        team_rows = schedule_df[
            (schedule_df["Team 1"] == team_sched_norm) | 
            (schedule_df["Team 2"] == team_sched_norm) | 
            (schedule_df["Work Team"] == team_sched_norm)
        ]

        if not team_rows.empty:
            team_court = team_rows["Court #"].iloc[0]

            # Filter schedule to that court only
            team_schedule = schedule_df[schedule_df["Court #"] == team_court].copy()

            # Compute status using normalized names
            team_schedule["Team Status"] = team_schedule.apply(
                lambda r: compute_status(r, team_sched_norm), axis=1
            )

            team_schedule.sort_values(by="Game #", inplace=True, ignore_index=True)

            st.dataframe(team_schedule.style.apply(highlight_status, axis=1))
        else:
            st.warning(f"No schedule found for team {team_sched}")


# ---- RESULTS TAB ----
with tabs[1]:
    st.header("Results")
    division_res = st.selectbox("Select Division (Results)", ["Men's", "Women's"], key="res_div")
    sheet_key_res = MEN_RESULTS_KEY if division_res == "Men's" else WOMEN_RESULTS_KEY
    
    df_results = load_results_sheet(RESULTS_SHEET_ID, sheet_key_res)

    if df_results.empty:
        st.info("No results available yet for this division.")
    else:
        # Get unique team names for selector
        all_teams_res = pd.Series(
            df_results.get("Team 1 Name", []).tolist() +
            df_results.get("Team 2 Name", []).tolist()
        ).dropna().astype(str).str.strip()
        all_teams_res = sorted(all_teams_res[all_teams_res != ""].unique())

        if not all_teams_res:
            st.info("No teams found in results yet.")
        else:
            team_res = st.selectbox("Select Team (Results)", all_teams_res, key="res_team")
            
            # Define round dates
            ROUND_DATES = {
                "Round 1": pd.to_datetime("2025-08-30").date(),
                "Round 2": pd.to_datetime("2025-08-31").date(),
            }
            
            for round_name, round_date in ROUND_DATES.items():
                st.subheader(round_name)
                # Filter by date only
                round_df = df_results[df_results["Timestamp"].dt.date == round_date] if "Timestamp" in df_results.columns else pd.DataFrame()
                df_team_results = load_team_results(round_df, team_res) if not round_df.empty else pd.DataFrame()
                
                if not df_team_results.empty:
                    st.dataframe(df_team_results)
                else:
                    st.info(f"No results for {team_res} on {round_name}")

    st.warning("Results may take up to 20 minutes to update. For corrections, please contact lye@nystrangers.org")

# --- ROSTER TAB ---
with tabs[2]:
    st.header("Roster")
    division_roster = st.selectbox("Select Division (Roster)", ["Men's", "Women's"], key="roster_div")
    roster_df = load_sheet(ROSTER_SHEET_ID, ROSTER_WORKSHEET_NAME)

    # Rename columns consistently
    roster_df.rename(columns={
        'Name': 'Player Name',
        'Jersey Number': 'Jersey #',
        'Wristband': 'Wristband Color',
        'Registration Name': 'Team',
        'Gender': 'Gender'
    }, inplace=True)
    roster_df["Division"] = roster_df["Gender"].map({"Male": "Men's", "Female": "Women's"})
    roster_div = roster_df[roster_df["Division"] == division_roster]

    all_teams_roster = sorted(roster_div["Team"].unique())
    team_roster = st.selectbox("Select Team (Roster)", all_teams_roster, key="roster_team")

    team_roster_df = roster_div[roster_div["Team"] == team_roster][
        ["Player Name", "Jersey #", "Wristband Color"]
    ].reset_index(drop=True)
    st.dataframe(team_roster_df)
