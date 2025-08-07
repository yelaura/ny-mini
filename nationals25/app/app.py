import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# ---- CONFIG ----
SHEET_NAME = "1MFrHYek18M6W9h1NI7r_dZbMGO_Ki-EjNnvASflelvw"  # <-- Change this
WORKSHEET_NAME = "Sheet1"

def check_ethnicity(value):
    if pd.isna(value) or str(value).strip() == "":
        return "No"
    elif "50% chinese" in str(value).lower():
        return "Yes"
    else:
        return "No"

@st.cache_data(ttl=600)
def load_data():
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
        'If No, Please Provide Perce...': 'Percent Chinese'
    }, inplace=True)

    df["Is 50% Chinese?"] = df["Percent Chinese"].apply(check_ethnicity)

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

    df['Ethnicity'] = df.apply(determine_ethnicity, axis=1)
    return df[['Team', 'Player Name', 'Jersey #', 'Ethnicity']]

def main():
    st.title("🏐 NY Nationals: View Rosters by Team")

    df = load_data()
    # Select division first
    division = st.selectbox("Select Division", options=df["Category Type Name"].unique())

    # Filter df by division
    df_division = df[df["Category Type Name"] == division]

    # Then select team within that division
    team = st.selectbox("Select Team", options=sorted(df_division["Registration Name"].unique()))

    # Filter roster for selected team
    team_roster = df_division[df_division["Registration Name"] == team][
        ["Name", "Jersey Number", "Ethnicity"]
    ]

    st.write(f"Roster for {team} ({division}):")
    st.dataframe(team_roster)

if __name__ == "__main__":
    main()