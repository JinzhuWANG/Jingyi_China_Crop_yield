import pandas as pd
import xarray as xr
import rioxarray as rxr


# Read GAEZ dataframe, which contains mapping of path to tif files
#   by default, input_level = High
GAEZ_df = pd.read_csv('data/GAEZ_v4/GAEZ_df.csv').query('input_level == "High"')

GAEZ_4_vars = ["year", "model", "rcp", "crop", "water_supply", "c02_fertilization"]
GAEZ_5_vars = ["year", "crop", "water_supply", 'variable']

year_rename = {
    '1981-2010':1995,
    '2011-2040':2025,
    '2041-2070':2055,
    '2071-2100':2085
}



# helpfer function to convert dataframe to xarray DataArray
def get_xr_darray_from_df(in_df):
    arrs = [] 
    for idx,row in in_df.iterrows():
        dim_coord = {k:[v] for k,v in zip(in_df.index.names, idx)}
        arrs.append(
            rxr.open_rasterio(row['fpath'])
            .drop_vars('band')
            .squeeze()
            .expand_dims(dim_coord)
        )

    out_xr = xr.combine_by_coords(arrs, combine_attrs='drop')
    return out_xr

def calc_mean_std(in_xr):
    mean_xr = in_xr.mean(dim='model').expand_dims(band=['mean'])
    std_xr = in_xr.std(dim='model').expand_dims(band=['std'])
    return xr.concat([mean_xr, std_xr], dim='band')

# Get historical yield
GAEZ_4_hist = (
    GAEZ_df.query('gaez_cat == "GAEZ_4" and name.str.contains("ycHa|ycHg") and rcp == "Historical"')
    .reset_index(drop=True)[[*GAEZ_4_vars, 'fpath']]
    .replace({'year': year_rename})
    .set_index(GAEZ_4_vars)
    .reset_index(['model', 'rcp', 'c02_fertilization'], drop=True)
)

GAEZ_4_hist_xr = get_xr_darray_from_df(GAEZ_4_hist)


# Get future yield
#  Rice has missing rows:
#   year=2071-2100, model=MIROC-ESM-CHEM, rcp=RCP4.5, crop=Wetland rice, water_supply=Irrigated, co2_fertilization=With CO2 Fertilization
#   year=2071-2100, model=MIROC-ESM-CHEM, rcp=RCP4.5, crop=Wetland rice, water_supply=Irrigated, co2_fertilization=Without CO2 Fertilization

GAEZ_4_future = (
    GAEZ_df.query('gaez_cat == "GAEZ_4" and rcp != "Historical"')
    .replace({'year': year_rename})
    .reset_index(drop=True)[[*GAEZ_4_vars, 'fpath']]
)
GAEZ_4_future_wheat = GAEZ_4_future.query('crop == "Wheat"').set_index(GAEZ_4_vars)
GAEZ_4_future_maize = GAEZ_4_future.query('crop == "Maize"').set_index(GAEZ_4_vars)
GAEZ_4_future_rice = GAEZ_4_future.query('crop == "Wetland rice"').set_index(GAEZ_4_vars)

GAEZ_4_future_wheat_xr = calc_mean_std(get_xr_darray_from_df(GAEZ_4_future_wheat))
GAEZ_4_future_maize_xr = calc_mean_std(get_xr_darray_from_df(GAEZ_4_future_maize))
GAEZ_4_future_rice_xr = calc_mean_std(get_xr_darray_from_df(GAEZ_4_future_rice))


GAEZ_4_future_rice_xr[0,0,0,0,0,0, ...]

