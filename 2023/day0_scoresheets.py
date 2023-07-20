# goals: 
# import csv for court, game, team 1, team 2, work team
# fill in pdf using pdfotter
# merge pdfs using PyPDF2
# print merged pdfs

import pandas as pd
import requests
import shutil
from PyPDF2 import PdfWriter

# mens scoresheet values
csv_file = "csvs/M_Scoresheets.csv"
template_id = "tem_EoMyXzWPnMKd8g" # pdf otter: men's scoresheet
output_filename = "mens_scoresheets_prefilled"

# womens scoresheet values
# csv_file = "csvs/W_Scoresheets.csv"
# template_id = "tem_9nJiLWjj4q5a13" # pdf otter: women's scoresheet
# output_filename = "womens_scoresheets_prefilled"

# import csv

values = pd.read_csv(csv_file)

# set up pdf otter

url  = 'https://www.pdfotter.com/api/v1/pdf_templates/' + template_id + '/fill'
auth = ('prod_SbBGMdRZVbGDs8kdhT6rzc1NwUD96AC8', '')

# set up pdf merger
merger = PdfWriter()

# set up writing pdfs

for index, row in values.iterrows():
    json = {
        'data': {
        'Team 2': row['Team 2'],
        'Team 1': row['Team 1'],
        'Game': row['Game'],
        'Court': row['Court'],
        'Work Team': row['Work Team'],
         }
    }

    response = requests.post(url, auth=auth, json=json, stream=True)

    if response.status_code == 200:
        with open('pdfs/result.pdf', 'w+b') as file:
            shutil.copyfileobj(response.raw, file)
            merger.append(file)

output = open("pdfs/" + output_filename + ".pdf", "w+b")
merger.write(output)

merger.close()
output.close()