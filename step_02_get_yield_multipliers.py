import numpy as np
import xarray as xr
import itertools

# Read GAEZ_4 yield data
#  Only need the mean band for getting multipliers
GAEZ_4_hist_t_ha = xr.open_dataarray('data/GAEZ_v4/GAEZ_4_historical_t_ha.nc').compute()
GAEZ_4_future_t_ha = xr.open_dataarray('data/GAEZ_v4/GAEZ_4_future_t_ha.nc').compute()

GAEZ_4_t_ha = xr.concat([GAEZ_4_hist_t_ha, GAEZ_4_future_t_ha], dim='year')

# Get GAEZ_4 for 2020
GAEZ_4_yr_2020_t_ha = GAEZ_4_t_ha.interp(year=[2020], method='linear')
GAEZ_4_yr_2020_t_ha = GAEZ_4_yr_2020_t_ha.drop_vars('year').squeeze().astype(np.float32)

# Get the yield multipliers
GAEZ_4_multiplier = (
    GAEZ_4_future_t_ha / GAEZ_4_yr_2020_t_ha
)


# --------- loop through each layer to exclude extreme multipliers ---------
dims_to_iterate = ['year', 'rcp', 'crop', 'water_supply', 'c02_fertilization']

dim_values = {
    dim: GAEZ_4_multiplier.coords[dim].values.tolist()
    for dim in dims_to_iterate
}

all_combinations = list(itertools.product(*[dim_values[dim] for dim in dims_to_iterate]))

# Iterate through all combinations
for combo in all_combinations:
    sel_dict = dict(zip(dims_to_iterate, combo))
    spatial_band = GAEZ_4_multiplier.sel(sel_dict)
    extreme_max = min(np.nanpercentile(spatial_band, 95), 2.0)
    print(f"Processing {sel_dict}, setting max to {extreme_max:.4f}")
    spatial_band = spatial_band.clip(max=extreme_max)
    
    GAEZ_4_multiplier.loc[sel_dict] = spatial_band


# Save the yield multipliers
GAEZ_4_multiplier.to_netcdf('data/GAEZ_v4/GAEZ_4_yield_multipliers.nc')
