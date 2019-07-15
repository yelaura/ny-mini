
# coding: utf-8

# In[2]:


import gspread
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials

def open_workbook(ws_name):
# use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)

# Find a workbook by name and open the first sheet
# Make sure you use the right name here.
    return client.open(ws_name)

def open_worksheet(ws_name, shtname):
    wkbook = open_workbook(ws_name)
    return wkbook.worksheet(shtname)

def write_gdoc(data, ws_name, sht_name, row, col):
    wksht = open_worksheet(ws_name, sht_name)
    
    for i in range(len(data)):
        for j in range(len(data)):
            wksht.update_cell(row+i, col+j, data[i][j])
            
def read_gdoc_range(ws_name,sht_name="Sheet1",startrow=1,startcol=1, endrow=1, endcol=1):
    wksht = open_worksheet(ws_name, sht_name)
    r = wksht.range(startrow, startcol, endrow, endcol)
    values = []
    
    for i in r:
        values.append(i.value)
        
    values = np.array(values)
    values.resize(endrow-startrow+1, endcol-startcol+1)
    
    return values

def newest_time(ws_name, sheet):
    wksht = open_worksheet(ws_name, sheet)
    return wksht.updated

def write_gdoc_cell(data, ws_name, sht_name, row, col):
    wksht = open_worksheet(ws_name, sht_name)
    
    wksht.update_cell(row,col,data)


# In[3]:


def main():
    ws_name = "Laura"
    sht_name = ["Goals", "Test"]

    data = read_gdoc_range(ws_name,sht_name[0], 1,1,7,3)
    #write_gdoc(data,ws_name, sht_name[1], 1,1)
    print(new("NY Mini 2017 - 1st Round", "Court M3") < new("NY Mini 2017 - 1st Round", "Court M1"))

