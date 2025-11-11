import itertools
import xarray as xr
import numpy as np

from scipy import stats


years = range(2020, 2101, 5)

# Load yield predictions
yield_preds_xr = xr.open_dataarray('data/crop_yield_2020_2100_by_5yr.nc')
GAEZ_4_future_t_ha = xr.open_dataarray('data/GAEZ_v4/GAEZ_4_future_t_ha.nc')\
    .interp(year=years, kwargs={'fill_value': 'extrapolate'}).astype(np.float32)


# Concat pred with attainable
yield_pred_attainable = xr.concat([
    yield_preds_xr.expand_dims(_type=['attainable']),
    GAEZ_4_future_t_ha.expand_dims(_type=['attainable'])
], dim='_type')


yield_practical_mean = yield_pred_attainable\
    .sel(band=['mean'])\
    .min(dim='_type')

yield_practical_se = (
    yield_preds_xr.sel(band='std', drop=True) 
    / np.sqrt(30)
).expand_dims(band=['se'])
    
yield_practical = xr.concat([
    yield_practical_mean,
    yield_practical_se
], dim='band')


# Save the prediction with percentiles (25/75)
z_25 = stats.norm.ppf(0.25)  # -0.6745
z_75 = stats.norm.ppf(0.75)  # +0.6745

yield_practical_25 = yield_practical.sel(band='mean', drop=True) + z_25 * yield_practical.sel(band='se', drop=True)
yield_practical_75 = yield_practical.sel(band='mean', drop=True) + z_75 * yield_practical.sel(band='se', drop=True)


# Save as GTIFF
crops = yield_practical['crop'].values
years = yield_practical['year'].values
rcps = yield_practical['rcp'].values
water_supplies = yield_practical['water_supply'].values
co2_fertilizations = yield_practical['c02_fertilization'].values

for crop, year, rcp, water_supply, co2_fertilization in itertools.product(crops, years, rcps, water_supplies, co2_fertilizations):
    
    out_path = f"data/pred_yield_t_ha/{co2_fertilization}_{rcp}_{crop}_{water_supply}_{year}.tif"
    
    yield_practical_25.sel(
        crop=crop,
        year=year,
        rcp=rcp,
        water_supply=water_supply,
        c02_fertilization=co2_fertilization
    ).rio.to_raster(out_path.replace('.tif', '_25th_percentile.tif'), compress='LZW')
    
    
    yield_practical.sel(    # band mean is the 50th percentile
        band='mean',
        crop=crop,
        year=year,
        rcp=rcp,
        water_supply=water_supply,
        c02_fertilization=co2_fertilization
    ).rio.to_raster(out_path.replace('.tif', '_50th_percentile.tif'), compress='LZW')
    
    yield_practical_75.sel(
        crop=crop,
        year=year,
        rcp=rcp,
        water_supply=water_supply,
        c02_fertilization=co2_fertilization
    ).rio.to_raster(out_path.replace('.tif', '_75th_percentile.tif'), compress='LZW')