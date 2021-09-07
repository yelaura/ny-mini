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
PROCESSING = 'MENS'
PROCESSING = 'WOMENS'

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and ranges of relevant sheets.
MENS_RESPONSES = '1Avj3tnoHoRHVejeQNRlSNoixdvvQH9U_oK61J9ps7qE'
WOMENS_RESPONSES = '1pJmvOxRwG_AoKwtFwjyzODug_dHC4XjPkdSvZiaqGyQ'
RESP_RANGE = 'Form Responses 1!B:L'

OUT_SHEET = '1kNVCoKTia-XIK6qx62xcR3946zzb54QADSE01gFUHEE'
MENS_OUT_RANGE = 'ScoreDisp!D5:E36'
WOMENS_OUT_RANGE = 'ScoreDisp!K5:L24'
MENS_TEAMS = 'ScoreDisp!B4:C36'
WOMENS_TEAMS = 'ScoreDisp!I4:J24'

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

def get_team_names():

    if PROCESSING == 'MENS':
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


########################## end of setup ###############################

def main():

    if PROCESSING == 'MENS':
        RESPONSES = MENS_RESPONSES
        OUT_RANGE = MENS_OUT_RANGE
    else:
        RESPONSES = WOMENS_RESPONSES
        OUT_RANGE = WOMENS_OUT_RANGE

    data = get_team_names()

    sheet = creds()
    result = sheet.values().get(spreadsheetId=RESPONSES,
                                range=RESP_RANGE).execute()
    values = result.get('values', [])

    ################ start processing data #########################

    sheet_in = pd.DataFrame(values[1:], columns=values[0])
    sheet_in = sheet_in.iloc[:, 5:12]
    sheet_in.iloc[:, 2:] = pd.DataFrame(sheet_in.iloc[:, 2:], dtype=int)
    sheet_in['Game 1 Win'] = sheet_in['Team 1 Score'] - sheet_in['Team 2 Score']
    sheet_in['Game 2 Win'] = sheet_in['Team 1 Score 2'] - sheet_in['Team 2 Score 2']
    sheet_in['Total Pt Diff'] = sheet_in['Game 1 Win'] + sheet_in['Game 2 Win']

    for ind in sheet_in.index: # iterate through each row

        if (sheet_in['Game 1 Win'][ind]) > 0: # if pt diff is positive
            winning_team = sheet_in['Team 1 Name'][ind]
        else:
            winning_team = sheet_in['Team 2 Name'][ind]

        ind_win = data[data['Team Name'] == winning_team].index[0]
        data.at[ind_win, 'Wins'] = data.at[ind_win, 'Wins'] + 1

        if (sheet_in['Game 2 Win'][ind]) > 0:
            winning_team = sheet_in['Team 1 Name'][ind]
        else:
            winning_team = sheet_in['Team 2 Name'][ind]

        ind_win = data[data['Team Name'] == winning_team].index[0]
        data.at[ind_win, 'Wins'] = data['Wins'][ind_win] + 1

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

if __name__ == '__main__':
    main()
