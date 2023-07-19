########################## setup ###############################

from __future__ import print_function
import os.path
from pprint import pprint

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

import pandas as pd

### change based on which ones we're processing ###
TO_PROCESS = ['Mens', 'Womens']

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and ranges of relevant sheets.
SHEET_NAME = '1Mm_bfIiPzjXhQD77C73Jo_UrbY8fDtEaZvo7BgsZ-WE'
RESP_RANGE = 'B:K'

OUT_SHEET = SHEET_NAME
MENS_OUT_RANGE = 'ScoreDisp!D5:E59'
WOMENS_OUT_RANGE = 'ScoreDisp!K5:L49'
MENS_TEAMS = 'ScoreDisp!B4:C59'
WOMENS_TEAMS = 'ScoreDisp!I4:J49'

SAMPLE_SPREADSHEET_ID = SHEET_NAME
SAMPLE_RANGE_NAME = WOMENS_TEAMS

# to do: update sheet names and ranges

SECOND_SHEET_NAME = '10Z5wJMsMjJKOjKtRN_HEJsAPhLWRk7egtfI5BlsZc0Q'
SECOND_DAY_POOLS_OUT_RANGE_MENS = [ 'Second Day!B3:E22',
                                    'Second Day!H3:K12',
                                    'Second Day!N3:Q12']
SECOND_DAY_POOLS_OUT_RANGE_WOMENS = ['Second Day!B27:E41',
                                    'Second Day!H27:K36',
                                    'Second Day!N27:Q36']

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

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheets = service.spreadsheets()
        result = sheets.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        print(result)
        values = result.get('values', [])

        if not values:
            print('No data found.')
            return
        
        print(values)

        return sheets

        # print('Name, Major:')
        # for row in values:
        #     # Print columns A and E, which correspond to indices 0 and 4.
        #     print('%s, %s' % (row[0], row[4]))
    except HttpError as err:
        print(err)


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


def get_brackets(standings, div, num_gold, num_silver, num_bronze):
    # sort by court, wins, overall points

    if (div == 'Mens'):
        data = standings[0].copy(deep=True)
    else:
        data = standings[1].copy(deep=True)

    data.sort_values(['Court', 'Wins', 'Overall Pts'],
                          ascending=[False, False, False],
                          inplace=True,
                          ignore_index=True)

    data_ranked = pd.DataFrame(columns=data.columns)

    for i in range(5):
        to_add = data.groupby('Court').nth(i).sort_values(by=['Wins', 'Overall Pts'],
                                                                    ascending=False)
        data_ranked = data_ranked.append(to_add.reset_index())

    data_ranked = data_ranked.reset_index()
    data_ranked.drop('index', axis=1)

    gold = data_ranked.iloc[:num_gold, 1:]
    silver = data_ranked.iloc[num_gold:num_gold+num_silver, 1:]
    bronze = data_ranked.iloc[num_gold+num_silver:, 1:]

    return gold, silver, bronze

########################## end of setup ###############################

def day1():

    standings = []

    for div in TO_PROCESS:

        RESPONSES = SHEET_NAME

        if div == 'Mens':
            RESP_RANGE = 'Mens!' + 'A:K'
            OUT_RANGE = MENS_OUT_RANGE
        else:
            OUT_RANGE = WOMENS_OUT_RANGE
            RESP_RANGE = 'Womens!' + 'A:K'

        data = get_team_names(div)

        sheet = creds()
        result = sheet.values().get(spreadsheetId=RESPONSES,
                                    range=RESP_RANGE).execute()
        values = result.get('values', [])

    ################ start processing data #########################

        sheet_in = pd.DataFrame(values[1:], columns=values[0])
        sheet_in = sheet_in.iloc[:, 5:]
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

        standings.append(data)

    return standings # mens, womens

def get_day2_pools(standings, div):

    MENS_NUM_GOLD = 20
    WOMENS_NUM_GOLD = 15
    NUM_SILVER = 10
    NUM_BRONZE = 10

    if div == 'Mens': # mens
        NUM_GOLD = MENS_NUM_GOLD
        OUT_RANGE = SECOND_DAY_POOLS_OUT_RANGE_MENS
    else:
        NUM_GOLD = WOMENS_NUM_GOLD
        OUT_RANGE = SECOND_DAY_POOLS_OUT_RANGE_WOMENS

    print(OUT_RANGE)

    pools = get_brackets(standings, div, NUM_GOLD, NUM_SILVER, NUM_BRONZE)

    sheet = creds()
    # result = sheet.values().get(spreadsheetId=SECOND_SHEET_NAME,
    #                             range=OUT_RANGE[0]).execute()
    # values = result.get('values', [])

    for flight in range(3):
        print ("flight = " + str(flight))

        OUT = OUT_RANGE[flight]
        data = pools[flight].reset_index(inplace=False).drop('index', axis=1)
        print(data)

        # write to second day pools
        batch_update_values_request_body = {
            # How the input data should be interpreted.
            'value_input_option': 'USER_ENTERED',

            # The new values to apply to the spreadsheet.
            'data': [
                {
                    'range': OUT,
                    'majorDimension': 'ROWS',
                    'values': data.values.tolist()
                }
            ]
        }
        #
        request = sheet.values().batchUpdate(spreadsheetId=SECOND_SHEET_NAME,
                                             body=batch_update_values_request_body)
        response = request.execute()

        pprint(response)

    return pools


if __name__ == '__main__':
    standings = day1()
    # mens_gold, mens_silver, mens_bronze = get_day2_pools(standings, "Mens")
    # womens_gold, womens_silver, womens_bronze = get_day2_pools(standings, "Womens")