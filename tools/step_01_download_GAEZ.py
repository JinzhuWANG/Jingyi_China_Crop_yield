import pandas as pd
from tools.helpers import download_GAEZ_data


UNIQUE_VALUES = { 
    'crop':['Maize', 'Wetland rice', 'Wheat'],
    'water_supply':['Dryland', 'Irrigated'],
    'c02_fertilization':['With CO2 Fertilization', 'Without CO2 Fertilization'],
    'rcp':['RCP2.6', 'RCP4.5', 'RCP6.0', 'RCP8.5'],
}

# Define the columns used in the analysis
GAEZ_columns = {
    "GAEZ_1": ["name", "sub_theme_name", "variable", "year", "model", "rcp", "units", "download_url"],
    "GAEZ_2": ["name", "sub_theme_name", "variable", "year", "model", "rcp", "units", "download_url"],
    "GAEZ_3": ["name", "sub_theme_name", "variable", "year", "model", "rcp", "crop", "water_supply", "units", "input_level", "download_url"],
    "GAEZ_4": ["name", "sub_theme_name", "variable", "year", "model", "rcp", "crop", "water_supply", "units", "input_level", "c02_fertilization", "download_url"],
    "GAEZ_5": ["name", "sub_theme_name", "variable", "year", "crop", "water_supply", "units", "download_url"],
    "GAEZ_6": ["name", "sub_theme_name", "variable", "year", "crop", "water_supply", "units"]
}

GAEZ_years = {
    "GAEZ_4": ['1981-2010', '2011-2040', '2041-2070','2071-2100'],
    "GAEZ_5": [2010],
}

GAEZ_water_supply = {
    'GAEZ_4':{
        'Irrigation': 'Irrigated', 
        'Rainfed': "Dryland", 
        'Gravity Irrigation': 'Irrigated',
        'Sprinkler Irrigation': 'Irrigated', 
        'Rainfed All Phases ': 'Dryland',  # Note the space at the end
        'Drip Irrigation': 'Irrigated'
    },
    'GAEZ_5':{
        'Irrigated': 'Irrigated',
        'Rainfed': 'Dryland',
        'Rainfed All Phases': 'Dryland',
    }
}


GAEZ_filter_con = {
    "GAEZ_4": 'variable == "Average attainable yield of current cropland"',
    "GAEZ_5": '(variable == "Yield" or variable == "Harvested area")' 
}


# Read the GAEZ_url file
GAEZ_df = []
for gaez_cat in ['GAEZ_4', 'GAEZ_5']:
    
    df = pd.read_csv(f'data/GAEZ_v4/GAEZ_raw_urls/{gaez_cat}.csv').rename(columns = {'Name':'name'})
    df = df[GAEZ_columns[gaez_cat]]
    
    filter_con = f"crop in {UNIQUE_VALUES['crop']} and year in {GAEZ_years[gaez_cat]} and {GAEZ_filter_con[gaez_cat]}"
    df = df.query(filter_con)
    df['water_supply'] = df['water_supply'].replace(GAEZ_water_supply[gaez_cat])
    df.insert(0, 'gaez_cat', gaez_cat)

    GAEZ_df.append(df)

# Concatenate the GAEZ_df    
GAEZ_df = pd.concat(GAEZ_df).reset_index(drop = True)

# Download the gaez_cat data
GAEZ_df = download_GAEZ_data(GAEZ_df)
GAEZ_df.to_csv('data/GAEZ_v4/GAEZ_df.csv', index = False)