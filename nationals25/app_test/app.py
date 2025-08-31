import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---- CONFIG ----
SCHEDULE_SHEET_ID = "18qz3f2-tqRwUoc54_5DHdkNcju2gRIaDHDYSQGRhPUk"
RESULTS_SHEET_ID = "1SnbMJVwzD9JHvhzHfjuTHEzIMpSLLalVhyNh7216nXg"
# RESULTS_SHEET_ID = "1ljlOAzr8o-3T5L97vjl6pdI7m_qvfa2-Oo_xaTXGEfc" # test sheet
ROSTER_SHEET_ID = "1sLcO9XSJTVmO2lNzZUxLLEM4pMuVzfAvzH1NRU7VQRc"

MEN_SHEET_KEY = "M_Scoresheets"
WOMEN_SHEET_KEY = "W_Scoresheets"

MEN_RESULTS_KEY = "Mens"
WOMEN_RESULTS_KEY = "Womens"

ROSTER_WORKSHEET_NAME = "NYC"

WOMENS_PLAYOFFS = [
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPTmXZ_OJJBbRUdtbiU3qamF0-r9dA9eJnznhuRyNq7Cgwk3uk878Ss2UXd7nnw433sRIYf-3hkOPP/pubhtml?gid=1969705780&single=true",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPTmXZ_OJJBbRUdtbiU3qamF0-r9dA9eJnznhuRyNq7Cgwk3uk878Ss2UXd7nnw433sRIYf-3hkOPP/pubhtml?gid=294712363&single=true",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPTmXZ_OJJBbRUdtbiU3qamF0-r9dA9eJnznhuRyNq7Cgwk3uk878Ss2UXd7nnw433sRIYf-3hkOPP/pubhtml?gid=1289632369&single=true",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPTmXZ_OJJBbRUdtbiU3qamF0-r9dA9eJnznhuRyNq7Cgwk3uk878Ss2UXd7nnw433sRIYf-3hkOPP/pubhtml?gid=408416220&single=true"
]

MENS_PLAYOFFS = [
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPTmXZ_OJJBbRUdtbiU3qamF0-r9dA9eJnznhuRyNq7Cgwk3uk878Ss2UXd7nnw433sRIYf-3hkOPP/pubhtml?gid=1353991113&single=true",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPTmXZ_OJJBbRUdtbiU3qamF0-r9dA9eJnznhuRyNq7Cgwk3uk878Ss2UXd7nnw433sRIYf-3hkOPP/pubhtml?gid=992689214&single=true",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPTmXZ_OJJBbRUdtbiU3qamF0-r9dA9eJnznhuRyNq7Cgwk3uk878Ss2UXd7nnw433sRIYf-3hkOPP/pubhtml?gid=1459094529&single=true",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPTmXZ_OJJBbRUdtbiU3qamF0-r9dA9eJnznhuRyNq7Cgwk3uk878Ss2UXd7nnw433sRIYf-3hkOPP/pubhtml?gid=902053005&single=true",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRPTmXZ_OJJBbRUdtbiU3qamF0-r9dA9eJnznhuRyNq7Cgwk3uk878Ss2UXd7nnw433sRIYf-3hkOPP/pubhtml?gid=280122778&single=true"
]

WOMENS_BRACKETS = ["Gold", "Silver", "Bronze", "Copper"]
MENS_BRACKETS = ["Gold", "Silver", "Bronze", "Copper", "Contention"]

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

# ---- HELPER: COURT STANDINGS ----
def compute_court_standings(results_df, court_num):
    """Compute standings for all teams on a given court (wins/losses per set)."""
    court_df = results_df[results_df["Court #"] == court_num]
    teams = pd.unique(court_df[["Team 1 Name", "Team 2 Name"]].values.ravel())
    standings = []

    for team in teams:
        if pd.isna(team) or team.strip() == "":
            continue

        team_games = court_df[
            (court_df["Team 1 Name"] == team) | (court_df["Team 2 Name"] == team)
        ]
        
        wins, losses, points_for, points_against = 0, 0, 0, 0

        for _, row in team_games.iterrows():
            # skip games without scores
            if pd.isna(row.get("Team 1 Score")) or pd.isna(row.get("Team 2 Score")):
                continue  

            t1, t2 = row.get("Team 1 Name"), row.get("Team 2 Name")

            # --- First set ---
            s1, s2 = row.get("Team 1 Score", 0), row.get("Team 2 Score", 0)
            if team == t1:
                points_for += s1
                points_against += s2
                if s1 > s2:
                    wins += 1
                elif s1 < s2:
                    losses += 1
            elif team == t2:
                points_for += s2
                points_against += s1
                if s2 > s1:
                    wins += 1
                elif s2 < s1:
                    losses += 1

            # --- Second set ---
            s1b, s2b = row.get("Team 1 Score 2", 0), row.get("Team 2 Score 2", 0)
            if team == t1:
                points_for += s1b
                points_against += s2b
                if s1b > s2b:
                    wins += 1
                elif s1b < s2b:
                    losses += 1
            elif team == t2:
                points_for += s2b
                points_against += s1b
                if s2b > s1b:
                    wins += 1
                elif s2b < s1b:
                    losses += 1

        # compute metrics
        point_diff = points_for - points_against
        point_ratio = round(points_for / points_against, 3) if points_against > 0 else "N/A"

        standings.append({
            "Team": team,
            "Wins (Sets)": wins,   # per set now
            "Losses": losses,
            "Point Differential": point_diff,
            "Point Ratio": point_ratio
        })

    standings_df = pd.DataFrame(standings)
    standings_df.sort_values(
        by=["Wins (Sets)", "Point Differential", "Point Ratio"], 
        ascending=[False, False, False], 
        inplace=True
    )
    return standings_df.reset_index(drop=True)

# ---- HELPER: OVERALL RANKINGS with Head-to-Head ----
def compute_overall_rankings(results_df):
    """Compute overall standings across all courts with tie-breaking rules."""
    teams = pd.unique(results_df[["Team 1 Name", "Team 2 Name"]].values.ravel())
    standings = []

    # Aggregate stats for each team
    for team in teams:
        if pd.isna(team) or team.strip() == "":
            continue

        team_games = results_df[
            (results_df["Team 1 Name"] == team) | (results_df["Team 2 Name"] == team)
        ]
        
        wins, losses, points_for, points_against = 0, 0, 0, 0

        for _, row in team_games.iterrows():
            if pd.isna(row.get("Team 1 Score")) or pd.isna(row.get("Team 2 Score")):
                continue  

            t1, t2 = row["Team 1 Name"], row["Team 2 Name"]

            # --- First set ---
            s1, s2 = row.get("Team 1 Score", 0), row.get("Team 2 Score", 0)
            if team == t1:
                points_for += s1; points_against += s2
                wins += 1 if s1 > s2 else 0
                losses += 1 if s1 < s2 else 0
            elif team == t2:
                points_for += s2; points_against += s1
                wins += 1 if s2 > s1 else 0
                losses += 1 if s2 < s1 else 0

            # --- Second set ---
            s1b, s2b = row.get("Team 1 Score 2", 0), row.get("Team 2 Score 2", 0)
            if team == t1:
                points_for += s1b; points_against += s2b
                wins += 1 if s1b > s2b else 0
                losses += 1 if s1b < s2b else 0
            elif team == t2:
                points_for += s2b; points_against += s1b
                wins += 1 if s2b > s1b else 0
                losses += 1 if s2b < s1b else 0

        point_diff = points_for - points_against
        point_ratio = round(points_for / points_against, 3) if points_against > 0 else float("inf")

        standings.append({
            "Team": team,
            "Sets Won": wins,
            "Losses": losses,
            "Point Differential": point_diff,
            "Point Ratio": point_ratio
        })

    standings_df = pd.DataFrame(standings)

    # ---- Sort Step 1: by sets won, point diff, point ratio ----
    standings_df.sort_values(
        by=["Sets Won", "Point Differential", "Point Ratio"],
        ascending=[False, False, False],
        inplace=True
    )
    standings_df.reset_index(drop=True, inplace=True)

    # ---- Step 2: Apply head-to-head tiebreakers ----
    def resolve_ties(df, results_df):
        ranked = []
        i = 0
        while i < len(df):
            # find group with same Sets Won + Point Differential
            group = df[
                (df["Sets Won"] == df.iloc[i]["Sets Won"]) &
                (df["Point Differential"] == df.iloc[i]["Point Differential"])
            ]
            if len(group) == 1:
                ranked.append(group)
                i += 1
            else:
                # compute head-to-head within group
                teams_in_group = group["Team"].tolist()
                h2h_stats = []
                for team in teams_in_group:
                    h2h_wins, h2h_points_for, h2h_points_against = 0, 0, 0
                    # filter only matches among tied teams
                    h2h_games = results_df[
                        (results_df["Team 1 Name"].isin(teams_in_group)) &
                        (results_df["Team 2 Name"].isin(teams_in_group)) &
                        ((results_df["Team 1 Name"] == team) | (results_df["Team 2 Name"] == team))
                    ]
                    for _, row in h2h_games.iterrows():
                        t1, t2 = row["Team 1 Name"], row["Team 2 Name"]
                        s1, s2 = row.get("Team 1 Score", 0), row.get("Team 2 Score", 0)
                        s1b, s2b = row.get("Team 1 Score 2", 0), row.get("Team 2 Score 2", 0)

                        if team == t1:
                            # set 1
                            h2h_points_for += s1; h2h_points_against += s2
                            h2h_wins += 1 if s1 > s2 else 0
                            # set 2
                            h2h_points_for += s1b; h2h_points_against += s2b
                            h2h_wins += 1 if s1b > s2b else 0
                        elif team == t2:
                            # set 1
                            h2h_points_for += s2; h2h_points_against += s1
                            h2h_wins += 1 if s2 > s1 else 0
                            # set 2
                            h2h_points_for += s2b; h2h_points_against += s1b
                            h2h_wins += 1 if s2b > s1b else 0

                    h2h_point_diff = h2h_points_for - h2h_points_against
                    h2h_stats.append({
                        "Team": team,
                        "h2h Sets Won": h2h_wins,
                        "h2h Point Diff": h2h_point_diff,
                        "h2h Point Ratio": round(h2h_points_for / h2h_points_against, 3) if h2h_points_against > 0 else float("inf")
                    })

                h2h_df = pd.DataFrame(h2h_stats)
                # sort by head-to-head criteria
                h2h_df.sort_values(
                    by=["h2h Sets Won", "h2h Point Diff", "h2h Point Ratio"],
                    ascending=[False, False, False],
                    inplace=True
                )
                # merge back with original group’s global stats
                merged = group.set_index("Team").loc[h2h_df["Team"]].reset_index()
                ranked.append(merged)
                i += len(group)
        return pd.concat(ranked, ignore_index=True)

    standings_df = resolve_ties(standings_df, results_df)
    standings_df.index = standings_df.index + 1
    standings_df.index.name = "Rank"

    return standings_df[["Team", "Sets Won", "Point Differential", "Point Ratio"]]

# ---- MAIN APP ----
st.title("[Test App] 🏐 The 80th NACIVT in NYC")  # fixed title

tabs = st.tabs(["Schedule", "Results", "Roster", "Overall Rankings", "Playoffs"])

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

                # --- Add Court Standings after each round ---
                if not round_df.empty:
                    team_rows = round_df[
                        (round_df["Team 1 Name"] == team_res) | 
                        (round_df["Team 2 Name"] == team_res)
                    ]
                    if not team_rows.empty:
                        team_court = team_rows["Court #"].iloc[0]
                        st.subheader(f"Court {team_court} Standings ({round_name})")
                        standings_df = compute_court_standings(round_df, team_court)

                        # Highlight selected team
                        def highlight_team(row, team_name=team_res):
                            return [
                                'background-color: yellow; font-weight: bold;' 
                                if row["Team"] == team_name else ''
                                for _ in row
                            ]

                        st.dataframe(
                            standings_df.style.apply(highlight_team, team_name=team_res, axis=1)
                        )

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

# --- OVERALL RANKINGS TAB ---
with tabs[3]:
    st.header("Overall Rankings")
    division_rank = st.selectbox("Select Division (Rankings)", ["Men's", "Women's"], key="rank_div")
    sheet_key_rank = MEN_RESULTS_KEY if division_rank == "Men's" else WOMEN_RESULTS_KEY

    df_rankings = load_results_sheet(RESULTS_SHEET_ID, sheet_key_rank)

    if df_rankings.empty:
        st.info("No results available yet for this division.")
    else:
        st.header("Overall Rankings (Round 1 + Round 2)")
        overall_df = compute_overall_rankings(df_rankings)
        st.dataframe(overall_df)

        st.warning("Results may take up to 20 minutes to update. For corrections, please contact lye@nystrangers.org")

# --- PLAYOFFS TAB ---
with tabs[4]:
    st.header("Playoff Brackets")

    col1, col2 = st.columns(2)

    with col2:
        st.subheader("Womens Brackets")
        for name, url in zip(WOMENS_BRACKETS, WOMENS_PLAYOFFS):
            if st.button(f"{name} Bracket", key=f"women_{name}"):
                st.write(f"Opening {name} Bracket...")
                st.markdown(f'<a href="{url}" target="_blank">Click here to open</a>', unsafe_allow_html=True)


    with col1:
        st.subheader("Mens Brackets")
        for name, url in zip(MENS_BRACKETS, MENS_PLAYOFFS):
            st.markdown(f"[{name} Bracket]({url})", unsafe_allow_html=True)
