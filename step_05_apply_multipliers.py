import xarray as xr
import numpy as np

years = range(2020, 2101, 5)
sample_size = 30

# Load multipliers
multipliers_GAEZ = xr.open_dataarray('data/GAEZ_v4/GAEZ_4_yield_multipliers.nc')\
    .interp(year=years, kwargs={'fill_value': 'extrapolate'}).astype(np.float32)
multipliers_yearbook = xr.open_dataarray('data/Yearbook/crop_yield_multipliers.nc')

yield_2020 = xr.open_dataarray('data/GAEZ_v4/GAEZ_5_yield_2020.nc')



yield_preds = []

# Loop through years
for yr in years:
    # Generate GAEZ multipliers
    GAEZ_mean = multipliers_GAEZ.sel(year=yr, band='mean', drop=True).astype(np.float32)
    GAEZ_std = multipliers_GAEZ.sel(year=yr, band='std', drop=True).astype(np.float32)
    GAEZ_std = GAEZ_std.where(GAEZ_std > 0, 1e-6)  # avoid zero std
    multipliers_sample_GAEZ_xr = xr.DataArray(
        data = np.random.normal(
            loc=GAEZ_mean.data[...,None],
            scale=GAEZ_std.data[...,None] + 1e-6,
            size=(*GAEZ_mean.shape, sample_size)
        ).astype(np.float32),
        dims = (*GAEZ_mean.dims, 'sample'),
        coords = {**GAEZ_mean.coords, 'sample': np.arange(sample_size)}
    )
    
    # Generate Yearbook multipliers
    yearbook_mean = multipliers_yearbook.sel(year=yr, band='mean', drop=True).astype(np.float32)
    yearbook_std = multipliers_yearbook.sel(year=yr, band='std', drop=True).astype(np.float32)
    yearbook_std = yearbook_std.where(yearbook_std > 0, 1e-6)  # avoid zero std
    multipliers_sample_yearbook_xr = xr.DataArray(
        data = np.random.normal(
            loc=yearbook_mean.data[...,None],
            scale=yearbook_std.data[...,None],
            size=(*yearbook_mean.shape, sample_size)
        ).astype(np.float32),
        dims = (*yearbook_mean.dims, 'sample'),
        coords = {**yearbook_mean.coords, 'sample': np.arange(sample_size)}
    )
    
    # Get the final multipliers
    final_multipliers = (multipliers_sample_GAEZ_xr * multipliers_sample_yearbook_xr).expand_dims(year=[yr])
    
    # Get the yield prediction
    yield_prediction = yield_2020 * final_multipliers
    yield_preds.append(
        xr.concat([
            yield_prediction.mean(dim='sample').expand_dims(band=['mean']),
            yield_prediction.std(dim='sample').expand_dims(band=['std'])
        ], dim='band')
    )
    
    print(f'Processed year: {yr}')
    
# Combine all years
yield_preds_xr = xr.concat(yield_preds, dim='year')
yield_preds_xr.to_netcdf('data/crop_yield_2020_2100_by_5yr.nc')
    

