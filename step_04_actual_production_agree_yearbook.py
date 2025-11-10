import xarray as xr
import rioxarray as rxr
import geopandas as gpd
import pandas as pd
import numpy as np

from rasterio.features import rasterize
from tools.constants import Province_names_cn_en


# --------------------------- Load GAEZ-5 data ---------------------------
GAEZ_df = pd.read_csv('data/GAEZ_v4/GAEZ_df.csv')\
    .query('gaez_cat == "GAEZ_5"')\
    .query('water_supply == "Total"')\
    .set_index(["year", "crop", 'variable'])[['fpath']]


GAEZ_5_arrs = []
for idx, row in GAEZ_df.iterrows():
    year, crop, variable = idx
    xr_data = rxr.open_rasterio(row['fpath'] + '_clipped.tif', masked=True).sel(band=1, drop=True)
    GAEZ_5_arrs.append(
        xr_data.expand_dims({'crop':[crop], 'variable':[variable]})
    )
    
GAEZ_5_xr = xr.combine_by_coords(GAEZ_5_arrs, combine_attrs='drop')
Province_name2idx = {v:k for k,v in enumerate(Province_names_cn_en.values())}


    
    
# ------------------- Match GEAZ to yearbook ---------------------

# Get the yield increase ratio between 2010 and 2020 from yearbook data
yearbook_yield = pd.read_csv('data/Yearbook/yearbook_crop_yield_hist.csv')

yearbook_yield_t_ha_xr = xr.DataArray(
    data=np.zeros(
        (len(yearbook_yield['Province'].unique()),
        len(yearbook_yield['crop'].unique()),
        len(yearbook_yield['year'].unique()))
    ) * np.nan,
    coords={
        'Province': yearbook_yield['Province'].unique(),
        'crop': yearbook_yield['crop'].unique(),
        'year': yearbook_yield['year'].unique()
    },
    dims=['Province', 'crop', 'year']
)

for idx, row in yearbook_yield.iterrows():
    yearbook_yield_t_ha_xr.loc[
        dict(
            Province=row['Province'],
            crop=row['crop'],
            year=row['year']
        )
    ] = row['Yield (tonnes)']
    
yield_increase_2010_2020 = (
    yearbook_yield_t_ha_xr.sel(year=2020, drop=True) 
    / yearbook_yield_t_ha_xr.sel(year=2010, drop=True)
)

yield_increase_2010_2020 = yield_increase_2010_2020.where(
    yield_increase_2010_2020.notnull(), 
    other=1.0
)

yield_increase_2010_2020_df = yield_increase_2010_2020.to_dataframe('val').reset_index()

# Convert ratio to raster by crop
GAEZ_sample_xr = rxr.open_rasterio('data/GAEZ_v4/GAEZ_tifs/0a1a4943-3ec5-490e-8670-cc3ee7953729.tif_clipped.tif', masked=True).drop_vars('band').squeeze()
China_shp = gpd.read_file('data/Vector_boundary/China_boundary.shp')

crops = yield_increase_2010_2020_df['crop'].unique()

# Initialize the output xarray DataArray with crop dimension
yield_increase_rasterized = xr.DataArray(
    data=np.empty(
        (
            len(crops),
            GAEZ_sample_xr.shape[0],
            GAEZ_sample_xr.shape[1]
        ),
        dtype=np.float32
    ) * np.nan,
    coords={
        'crop': crops,
        'y': GAEZ_sample_xr.y,
        'x': GAEZ_sample_xr.x
    },
    dims=['crop', 'y', 'x']
)

# Loop through each crop, rasterizing all provinces with their multiplier values
for crop in crops:
    subset = yield_increase_2010_2020_df[yield_increase_2010_2020_df['crop'] == crop]
    raster_shp = China_shp.merge(
        subset,
        left_on='EN_Name',
        right_on='Province',
        how='inner'
    )
    shapes = [(geom, value) for geom, value in zip(raster_shp.geometry, raster_shp['val'])]
    rasterized = rasterize(
        shapes,
        out_shape=GAEZ_sample_xr.shape,
        transform=GAEZ_sample_xr.rio.transform(),
        fill=np.nan,
        dtype='float32'
    )
    yield_increase_rasterized.loc[dict(crop=crop)] = rasterized



# ------------------- Apply yield increase to GAEZ_2010 yield ---------------------
GAEZ_yield_2010 = GAEZ_5_xr.sel(variable='Yield', drop=True)
GAEZ_yield_2020 = GAEZ_yield_2010 * yield_increase_rasterized

GAEZ_yield_2020.to_netcdf('data/GAEZ_v4/GAEZ_5_yield_2020.nc')
