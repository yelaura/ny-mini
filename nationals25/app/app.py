import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# ---- RESULTS CONFIG ----
RESULTS_SHEET_NAME = ["1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc", 
                      "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc",
                      "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc"]    # <-- Change this
MEN_SHEET_KEY = "Mens"
WOMEN_SHEET_KEY = "Womens"

@st.cache_data(ttl=900)
def load_results(sheet_name, sheet_key):
    service_account_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)

    # worksheet = gc.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
    sheet = gc.open_by_key(sheet_name)
    worksheet = sheet.worksheet(sheet_key)

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def load_team_results(df, team):
    if team:
            # Filter for team
            team_df = df[(df["Team 1 Name"] == team) | (df["Team 2 Name"] == team)]

            if not team_df.empty:

                # Show results with adjusted scores
                results = []
                for _, row in team_df.iterrows():
                    # Determine score order
                    if row["Team 1 Name"] == team:
                        score1 = f"{row['Team 1 Score']}-{row['Team 2 Score']}"
                        score2 = f"{row['Team 1 Score 2']}-{row['Team 2 Score 2']}"
                    else:
                        score1 = f"{row['Team 2 Score']}-{row['Team 1 Score']}"
                        score2 = f"{row['Team 2 Score 2']}-{row['Team 1 Score 2']}"

                    # Determine winner
                    team_points = row['Team 1 Score'] + row['Team 1 Score 2'] if row["Team 1 Name"] == team else row['Team 2 Score'] + row['Team 2 Score 2']
                    opp_points = row['Team 2 Score'] + row['Team 2 Score 2'] if row["Team 1 Name"] == team else row['Team 1 Score'] + row['Team 1 Score 2']
                    if team_points > opp_points:
                        winner = team
                    elif team_points < opp_points:
                        winner = row["Team 1 Name"] if row["Team 1 Name"] != team else row["Team 2 Name"]
                    else:
                        winner = "Tie"

                    results.append({
                        "Court Number": row["Court Number"],
                        "Game Number": row["Game Number (1-10)"],
                        "Opponent": row["Team 1 Name"] if row["Team 1 Name"] != team else row["Team 2 Name"],
                        "Score 1": score1,
                        "Score 2": score2,
                        "Winner": winner
                    })

                results_df = pd.DataFrame(results)
                st.dataframe(results_df)
            
            else:
                st.info("No game results available yet.")


# ---- ROSTER CONFIG ----
SHEET_NAME = "1MFrHYek18M6W9h1NI7r_dZbMGO_Ki-EjNnvASflelvw"  # <-- Change this
WORKSHEET_NAME = "Sheet1"

def check_ethnicity(value):
    if pd.isna(value) or str(value).strip() == "":
        return "No"
    elif "50% chinese" in str(value).lower():
        return "Yes"
    else:
        return "No"

@st.cache_data(ttl=1440)
def load_roster():
    service_account_info = st.secrets["GCP_SERVICE_ACCOUNT"]
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)

    # worksheet = gc.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
    sheet = gc.open_by_key(SHEET_NAME)
    worksheet = sheet.worksheet(WORKSHEET_NAME)

    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # Standardize column names
    df.columns = df.columns.str.strip()

    ## TODO: differentiate between mens and womens

    # Rename for convenience
    df.rename(columns={
        'Name': 'Player Name',
        'Jersey Number': 'Jersey #',
        'Registration Name': 'Team',
        'Are You 100% Chinese?': '100% Chinese?',
        'If No, Please Provide Perce...': 'Percent Chinese',
        'Category Type Name': 'Division'
    }, inplace=True)

    df["Is 50% Chinese?"] = df["Percent Chinese"].apply(check_ethnicity)
    df["Division"] = df["Division"].apply(
        lambda x: "Women's" if pd.notna(x) and "women" in x.lower() else "Men's"
    )

    # Derive Ethnicity column
    def determine_ethnicity(row):
        full_chinese = str(row["100% Chinese?"]).strip().lower()
        half_chinese = str(row["Is 50% Chinese?"]).strip().lower()
        other_info = str(row["Percent Chinese"]).strip()

        if full_chinese == "yes":
            return "G"
        elif half_chinese == "yes":
            return "Y"
        elif other_info != "":
            return "P"
        else:
            return ""

    df['Wristband Color'] = df.apply(determine_ethnicity, axis=1)
    return df[['Division', 'Team', 'Player Name', 'Jersey #', 'Wristband Color']]

def main():

    st.title("🏐 The 80th NACIVT in New York City 2025")
    
    df = load_roster()
    # Select division first
    division = st.selectbox("Select Division", options=df["Division"].unique())

    # Filter df by division
    df_division = df[df["Division"] == division]

    # Then select team within that division
    team = st.selectbox("Select Team", options=sorted(df_division["Team"].unique()))

    with st.expander("📋 View Results"):

        st.subheader("Round 1")
        # Pick correct sheet
        if division == "Men's":
            sheet_key = MEN_SHEET_KEY
        else:
            sheet_key = WOMEN_SHEET_KEY

        # Load results
        df = load_results(RESULTS_SHEET_NAME[0], sheet_key)

        load_team_results(df, team)

        st.subheader("Round 2")

        # Load results
        df = load_results(RESULTS_SHEET_NAME[1], sheet_key)

        load_team_results(df, team)

        st.subheader("Round 3")

        # Load results
        df = load_results(RESULTS_SHEET_NAME[2], sheet_key)

        load_team_results(df, team)

        

    with st.expander("📋 View Roster"):
        # Filter roster for selected team
        team_roster = df_division[df_division["Team"] == team][
        ["Player Name", "Jersey #", "Wristband Color"]
        ].reset_index(drop=True)

        st.dataframe(team_roster)

if __name__ == "__main__":
    main()