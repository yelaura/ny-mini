import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---- CONFIG ----
RESULTS_SHEET_NAME = [
    "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc",
    "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc",
    "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc"
]
MEN_SHEET_KEY = "Mens"
WOMEN_SHEET_KEY = "Womens"

ROSTER_SHEET_NAME = "1sLcO9XSJTVmO2lNzZUxLLEM4pMuVzfAvzH1NRU7VQRc"
ROSTER_WORKSHEET_NAME = "NYC"

# ---- STREAMLIT CACHING FUNCTIONS ----
@st.cache_data(ttl=900)
def load_results(sheet_name, sheet_key):
    service_account_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(sheet_name)
    worksheet = sheet.worksheet(sheet_key)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

@st.cache_data(ttl=600)
def load_roster():
    service_account_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(ROSTER_SHEET_NAME)
    worksheet = sheet.worksheet(ROSTER_WORKSHEET_NAME)
    data = worksheet.get("A:H")
    df = pd.DataFrame(data[1:], columns=data[0]).fillna("").astype(str)
    df.columns = df.columns.str.strip()
    df.rename(columns={
        'Name': 'Player Name',
        'Jersey Number': 'Jersey #',
        'Registration Name': 'Team',
        'Wristband': 'Wristband Color'
    }, inplace=True)
    df["Division"] = df["Gender"].map({"Male": "Men's", "Female": "Women's"})
    return df

# ---- HELPER FUNCTION ----
def compute_status(row, team_name):
    if row["Team 1"] == team_name or row["Team 2"] == team_name:
        return "Playing"
    elif row["Work Team"] == team_name:
        return "Working"
    else:
        return "Off"

def load_team_results(df, team):
    if team:
        # Filter for team
        team_df = df[(df["Team 1 Name"] == team) | (df["Team 2 Name"] == team)]
        if not team_df.empty:
            results = []
            for _, row in team_df.iterrows():
                if row["Team 1 Name"] == team:
                    score1 = f"{row['Team 1 Score']}-{row['Team 2 Score']}"
                    score2 = f"{row['Team 1 Score 2']}-{row['Team 2 Score 2']}"
                else:
                    score1 = f"{row['Team 2 Score']}-{row['Team 1 Score']}"
                    score2 = f"{row['Team 2 Score 2']}-{row['Team 1 Score 2']}"
                team_points = row['Team 1 Score'] + row['Team 1 Score 2'] if row["Team 1 Name"] == team else row['Team 2 Score'] + row['Team 2 Score 2']
                opp_points = row['Team 2 Score'] + row['Team 2 Score 2'] if row["Team 1 Name"] == team else row['Team 1 Score'] + row['Team 1 Score 2']
                winner = team if team_points > opp_points else row["Team 1 Name"] if row["Team 1 Name"] != team else row["Team 2 Name"] if team_points < opp_points else "Tie"
                results.append({
                    "Court Number": row["Court Number"],
                    "Game Number": row["Game Number (1-10)"],
                    "Opponent": row["Team 1 Name"] if row["Team 1 Name"] != team else row["Team 2 Name"],
                    "Score 1": score1,
                    "Score 2": score2,
                    "Winner": winner
                })
            st.dataframe(pd.DataFrame(results))
        else:
            st.info("No game results available yet.")

# ---- MAIN APP ----
def main():
    st.title("🏐 The 80th NACIVT in New York City")

    df_roster = load_roster()

    # Select division first
    division = st.selectbox("Select Division", options=df_roster["Division"].unique())
    df_division = df_roster[df_roster["Division"] == division]

    # Then select team within that division
    team = st.selectbox("Select Team", options=sorted(df_division["Team"].unique()))

   # --- SCHEDULE SECTION ---
    with st.expander("📋 View Schedule"):
        st.subheader(f"Schedule for {team}")

        # Pick correct worksheet tab
        schedule_tab = MEN_SHEET_KEY if division == "Men's" else WOMEN_SHEET_KEY

        # Load schedule from its own sheet
        schedule_df = load_results("1ZHacBdlQy3sLp-qmkOUShn7IeA1nr-zQEul1kdmU-W8", schedule_tab)

        # Compute Team Status
        schedule_df["Team Status"] = schedule_df.apply(lambda r: compute_status(r, team), axis=1)

        # Filter rows where team is Playing or Working
        team_schedule = schedule_df[schedule_df["Team Status"] != "Off"]

        # Sort by Court and Game
        team_schedule.sort_values(by=["Court Number", "Game Number"], inplace=True, ignore_index=True)

        # Color-coded display
        def highlight_status(row):
            if row["Team Status"] == "Playing":
                return ['background-color: lightgreen']*len(row)
            elif row["Team Status"] == "Working":
                return ['background-color: lightyellow']*len(row)
            else:
                return ['background-color: lightgray']*len(row)

        st.dataframe(team_schedule.style.apply(highlight_status, axis=1))

    # --- RESULTS SECTION ---
    with st.expander("📋 View Results"):
        for round_idx, round_name in enumerate(["Round 1", "Round 2", "Round 3"]):
            st.subheader(round_name)
            sheet_key = MEN_SHEET_KEY if division == "Men's" else WOMEN_SHEET_KEY
            df_results = load_results(RESULTS_SHEET_NAME[round_idx], sheet_key)
            load_team_results(df_results, team)

    # --- ROSTER SECTION ---
    with st.expander("📋 View Roster"):
        team_roster = df_division[df_division["Team"] == team][
            ["Player Name", "Jersey #", "Wristband Color"]
        ].reset_index(drop=True)
        st.dataframe(team_roster)


if __name__ == "__main__":
    main()
