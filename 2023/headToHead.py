# library to determine head to head

import numpy as np
import pandas as pd

def head_to_head_winner(team_1_name, team_2_name, values):
    # values = sheet_in

    # assuming they played 2 sets

    # find team_1_name vs team_2_name

    values.loc[((values['Team 1 Name'] == team_1_name) and (values['Team 2 Name'] == team_2_name)) or 
        ((values['Team 2 Name'] == team_1_name) and (values['Team 1 Name'] == team_2_name))]