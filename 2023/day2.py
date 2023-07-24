########################## setup ###############################

from __future__ import print_function
import os.path
from pprint import pprint

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

import pandas as pd

### change based on which ones we're processing ###
TO_PROCESS = ['Mens', 'Womens']

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and ranges of relevant sheets.
# Second round sheet name
SHEET_NAME = '1oy9lEDhGdhYyx8OR5cXDxqEX0zLfq7HOTFrkyj4i6Lw'
RESP_RANGE = 'B:I'

OUT_SHEET = SHEET_NAME
MENS_OUT_RANGE = 'ScoreDisp!D5:E59'
WOMENS_OUT_RANGE = 'ScoreDisp!K5:L49'
MENS_TEAMS = 'ScoreDisp!B4:C59'
WOMENS_TEAMS = 'ScoreDisp!I4:J49'

# to do: make playoffs sheet
# verify court numbers
PLAYOFFS_SHEET_NAME = '1-FTWZxiApb8c2wAeFRFW7Jjmj3SEV56Px8gBbt5Mt88'
MENS_PLAYOFFS_OUT_RANGE = [ 'Mens GOLD!B4:E23',
                   'Mens SILVER!B4:E23',
                   'Mens BRONZE!B4:E18']
WOMENS_PLAYOFFS_OUT_RANGE = ['Womens GOLD!B4:E18',
                    'Womens SILVER!B4:E18',
                    'Womens BRONZE!B4:E18']

def creds():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    return sheet


def get_team_names(division):

    if division == 'Mens':
        TEAMS = MENS_TEAMS
    else:
        TEAMS = WOMENS_TEAMS

    sheet = creds()
    result = sheet.values().get(spreadsheetId=OUT_SHEET,
                                range=TEAMS).execute()
    values = result.get('values', [])

    score_disp = pd.DataFrame(values[1:], columns=values[0])

    # convert results
    score_disp['Wins'] = 0
    score_disp['Overall Pts'] = 0

    return score_disp


# def get_brackets(standings, div, num_gold, num_silver, num_bronze):
#     # sort by court, wins, overall points
#
#     if (div == 'Mens'):
#         data = standings[0].copy(deep=True)
#     else:
#         data = standings[1].copy(deep=True)
#
#     data.sort_values(['Court', 'Wins', 'Overall Pts'],
#                           ascending=[False, False, False],
#                           inplace=True,
#                           ignore_index=True)
#
#     data_ranked = pd.DataFrame(columns=data.columns)
#
#     for i in range(5):
#         to_add = data.groupby('Court').nth(i).sort_values(by=['Wins', 'Overall Pts'],
#                                                                     ascending=False)
#         data_ranked = data_ranked.append(to_add.reset_index())
#
#     data_ranked = data_ranked.reset_index()
#     data_ranked.drop('index', axis=1)
#
#     gold = data_ranked.iloc[:num_gold, 1:]
#     silver = data_ranked.iloc[num_gold:num_gold+num_silver, 1:]
#     bronze = data_ranked.iloc[num_gold+num_silver:, 1:]
#
#     return gold, silver, bronze

########################## end of setup ###############################

def day2():

    standings = []

    for div in TO_PROCESS:

        if div == 'Mens':
            RESP_RANGE = 'Mens!' + 'A:I'
            OUT_RANGE = MENS_OUT_RANGE
        else:
            OUT_RANGE = WOMENS_OUT_RANGE
            RESP_RANGE = 'Womens!' + 'A:I'

        data = get_team_names(div)

        sheet = creds()
        result = sheet.values().get(spreadsheetId=SHEET_NAME,
                                    range=RESP_RANGE).execute()
        values = result.get('values', [])

    ################ start processing data #########################

        sheet_in = pd.DataFrame(values[1:], columns=values[0])
        sheet_in = sheet_in.iloc[:, 5:]
        sheet_in.iloc[:, 2:] = pd.DataFrame(sheet_in.iloc[:, 2:], dtype=int)
        sheet_in['Game 1 Win'] = sheet_in['Team 1 Score'] - sheet_in['Team 2 Score']
        # sheet_in['Game 2 Win'] = sheet_in['Team 1 Score 2'] - sheet_in['Team 2 Score 2']
        sheet_in['Total Pt Diff'] = sheet_in['Game 1 Win']

        for ind in sheet_in.index: # iterate through each row

            if (sheet_in['Game 1 Win'][ind]) > 0: # if pt diff is positive
                winning_team = sheet_in['Team 1 Name'][ind]
            else:
                winning_team = sheet_in['Team 2 Name'][ind]

            ind_win = data[data['Team Name'] == winning_team].index[0]
            data.at[ind_win, 'Wins'] = data.at[ind_win, 'Wins'] + 1

            # if (sheet_in['Game 2 Win'][ind]) > 0:
            #     winning_team = sheet_in['Team 1 Name'][ind]
            # else:
            #     winning_team = sheet_in['Team 2 Name'][ind]

            # ind_win = data[data['Team Name'] == winning_team].index[0]
            # data.at[ind_win, 'Wins'] = data['Wins'][ind_win] + 1

            ind_1 = data[data['Team Name'] == sheet_in['Team 1 Name'][ind]].index[0]
            ind_2 = data[data['Team Name'] == sheet_in['Team 2 Name'][ind]].index[0]
            data.at[ind_1, 'Overall Pts'] = data.at[ind_1, 'Overall Pts'] + sheet_in.at[ind, 'Total Pt Diff']
            data.at[ind_2, 'Overall Pts'] = data.at[ind_2, 'Overall Pts'] - sheet_in.at[ind, 'Total Pt Diff']

            # print data to google sheet

        batch_update_values_request_body = {
            # How the input data should be interpreted.
            'value_input_option': 'USER_ENTERED',

            # The new values to apply to the spreadsheet.
            'data': [
                {
                    'range': OUT_RANGE,
                    'majorDimension': 'ROWS',
                    'values': (data.loc[:, 'Wins':'Overall Pts']).values.tolist()
                }
            ]
        }

        request = sheet.values().batchUpdate(spreadsheetId=OUT_SHEET,
                                             body=batch_update_values_request_body)
        response = request.execute()

        pprint(response)

        standings.append(data)

    return standings # mens, womens

def get_playoffs(standings, div, bracket):

    #### needs to be rewritten for playoffs
    ### rank teams in second pool play
    #### print to each playoff bracket

    MENS_GOLD_IN_RANGE = 'ScoreDisp!B5:E24'
    MENS_SILVER_IN_RANGE = 'ScoreDisp!B25:E44'
    MENS_BRONZE_IN_RANGE = 'ScoreDisp!B45:E59'

    WOMENS_GOLD_IN_RANGE = 'ScoreDisp!I5:L19'
    WOMENS_SILVER_IN_RANGE = 'ScoreDisp!I20:L34'
    WOMENS_BRONZE_IN_RANGE = 'ScoreDisp!I35:L49'

    if div == "Mens" and bracket == "Gold":
        IN_RANGE = MENS_GOLD_IN_RANGE
        OUT_RANGE = MENS_PLAYOFFS_OUT_RANGE[0]
        NUM_POOLS = 4
    elif div == "Mens" and bracket == "Silver":
        IN_RANGE = MENS_SILVER_IN_RANGE
        OUT_RANGE = MENS_PLAYOFFS_OUT_RANGE[1]
        NUM_POOLS = 2
    elif div == "Mens" and bracket == "Bronze":
        IN_RANGE = MENS_BRONZE_IN_RANGE
        OUT_RANGE = MENS_PLAYOFFS_OUT_RANGE[2]
        NUM_POOLS = 2
    elif div == "Womens" and bracket == "Gold":
        IN_RANGE = WOMENS_GOLD_IN_RANGE
        OUT_RANGE = WOMENS_PLAYOFFS_OUT_RANGE[0]
        NUM_POOLS = 2
    elif div == "Womens" and bracket == "Silver":
        IN_RANGE = WOMENS_SILVER_IN_RANGE
        OUT_RANGE = WOMENS_PLAYOFFS_OUT_RANGE[1]
        NUM_POOLS = 2
    elif div == "Womens" and bracket == "Bronze":
        IN_RANGE = WOMENS_BRONZE_IN_RANGE
        OUT_RANGE = WOMENS_PLAYOFFS_OUT_RANGE[2]
        NUM_POOLS = 2
    else:
        return ''

    # read in current standings
    sheet = creds()
    result = sheet.values().get(spreadsheetId=SHEET_NAME,
                                range=IN_RANGE).execute()
    values = pd.DataFrame(result.get('values', []),
                          columns=['Court', 'Team Name', 'Wins', 'Overall Pts'])
    values = values.astype({'Wins': 'int', 'Overall Pts':'int'})

    # sort by pool ranking
    values.sort_values(['Court', 'Wins', 'Overall Pts'],
                     ascending=[False, False, False],
                     inplace=True,
                     ignore_index=True)

    data_ranked = pd.DataFrame(columns=values.columns)

    for i in range(5):
        to_add = values.groupby('Court').nth(i).sort_values(by=['Wins', 'Overall Pts'],
                                                                    ascending=[False, False])
        data_ranked = data_ranked.append(to_add.reset_index())

        print(type(values['Overall Pts'][1]))

    data_ranked = data_ranked.reset_index()
    data_ranked.drop('index', axis=1)
    data_ranked = data_ranked.loc[:, 'Court':]

    # write to playoffs sheet
    batch_update_values_request_body = {
        # How the input data should be interpreted.
        'value_input_option': 'USER_ENTERED',

        # The new values to apply to the spreadsheet.
        'data': [
            {
                'range': OUT_RANGE,
                'majorDimension': 'ROWS',
                'values': data_ranked.values.tolist()
            }
        ]
    }

    request = sheet.values().batchUpdate(spreadsheetId=PLAYOFFS_SHEET_NAME,
                                         body=batch_update_values_request_body)
    response = request.execute()

    pprint(response)

if __name__ == '__main__':
    standings = day2()
    #
    # get_playoffs(standings, "Womens", "Gold")
    # get_playoffs(standings, "Womens", "Bronze")
    # get_playoffs(standings, "Womens", "Silver")
    # get_playoffs(standings, "Mens", "Gold")
    # get_playoffs(standings, "Mens", "Bronze")
    get_playoffs(standings, "Mens", "Silver")    #

# need to do head to head calcs