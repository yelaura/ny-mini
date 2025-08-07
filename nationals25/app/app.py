import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# ---- CONFIG ----
SHEET_NAME = "1MFrHYek18M6W9h1NI7r_dZbMGO_Ki-EjNnvASflelvw"  # <-- Change this
WORKSHEET_NAME = "Sheet1"

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

    # Rename for convenience
    df.rename(columns={
        'Name': 'Player Name',
        'Jersey Number': 'Jersey #',
        'Registration Name': 'Team',
        'Are you 100% Chinese?': '100% Chinese?',
        'If No, Please Provide Perce...': 'Percent Chinese'
    }, inplace=True)

    st.write(df.head())

    # Derive Ethnicity column
    def determine_ethnicity(row):
        if str(row['100% Chinese?']).strip().lower() == 'yes':
            return 'C'
        try:
            percent = float(str(row['Percent Chinese']).strip().replace('%', ''))
            return 'Y' if percent >= 50 else 'P'
        except:
            return 'P'

    df['Ethnicity'] = df.apply(determine_ethnicity, axis=1)
    return df[['Team', 'Player Name', 'Jersey #', 'Ethnicity']]

def main():
    st.title("🏐 Volleyball Roster Viewer by Team")

    df = load_data()
    teams = sorted(df['Team'].dropna().unique())
    selected_team = st.selectbox("Select a team:", teams)

    if selected_team:
        team_df = df[df['Team'] == selected_team][['Player Name', 'Jersey #', 'Ethnicity']]
        st.subheader(f"Roster for {selected_team}")
        st.table(team_df)

if __name__ == "__main__":
    main()