import xarray as xr
import rioxarray as rxr
import pandas as pd
import numpy as np
import itertools



# Read multipliers
multiplier_GAEZ_4 = xr.open_dataarray('data/GAEZ_v4/GAEZ_4_yield_multipliers.nc').compute()
multiplier_yearbook = xr.open_dataarray('data/Yearbook/crop_yield_multipliers.nc').compute().sel(year = multiplier_GAEZ_4['year'])



for crop, year, band in itertools.product(
    multiplier_yearbook['crop'].values,
    multiplier_yearbook['year'].values,
    multiplier_yearbook['band'].values
):

    img = multiplier_yearbook.sel(crop=crop, year=year, band=band)
    img.rio.to_raster(
        f'data/out_GTIFFs/Yearbook_multiplier_{crop}_{year}_{band}.tif',
        compress='LZW',
        dtype='float32',
        nodata=np.nan
    )
    
for band, year, rcp, crop, water_supply, c02_fertilization in itertools.product(
    multiplier_GAEZ_4['band'].values,
    multiplier_GAEZ_4['year'].values,
    multiplier_GAEZ_4['rcp'].values,
    multiplier_GAEZ_4['crop'].values,
    multiplier_GAEZ_4['water_supply'].values,
    multiplier_GAEZ_4['c02_fertilization'].values,
):
    img = multiplier_GAEZ_4.sel(
        band=band,
        year=year,
        rcp=rcp,
        crop=crop,
        water_supply=water_supply,
        c02_fertilization=c02_fertilization,
    )
    img.rio.to_raster(
        f'data/out_GTIFFs/GAEZ4_multiplier_{crop}_{year}_rcp{rcp}_ws{water_supply}_co2{c02_fertilization}_{band}.tif',
        compress='LZW',
        dtype='float32',
        nodata=np.nan
    )



