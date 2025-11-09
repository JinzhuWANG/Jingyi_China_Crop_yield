import numpy as np
import xarray as xr
import rioxarray as rxr
import plotnine as p9
import pandas as pd
import geopandas as gpd
import statsmodels.api as sm

from rasterio.features import rasterize

PRED_BASE_YR = 2020
PRED_TARGET_YR = 2100
PRED_STEP = 5


Province_names_cn_en = {
    '北京市':'Beijing',
    '天津市':'Tianjin',
    '河北省':'Hebei',
    '山西省':'Shanxi',
    '内蒙古':'Inner Mongolia',
    '辽宁省':'Liaoning',
    '吉林省':'Jilin',
    '黑龙江省':'Heilongjiang',
    '上海市':'Shanghai',
    '江苏省':'Jiangsu',
    '浙江省':'Zhejiang',
    '安徽省':'Anhui',
    '福建省':'Fujian',
    '江西省':'Jiangxi',
    '山东省':'Shandong',
    '河南省':'Henan',
    '湖北省':'Hubei',
    '湖南省':'Hunan',
    '广东省':'Guangdong',
    '广西':'Guangxi',
    '海南省':'Hainan',
    '重庆市':'Chongqing',
    '四川省':'Sichuan',
    '贵州省':'Guizhou',
    '云南省':'Yunnan',
    '西藏':'Tibet',
    '陕西省':'Shaanxi',
    '甘肃省':'Gansu',
    '青海省':'Qinghai',
    '宁夏':'Ningxia',
    '新疆':'Xinjiang',
}


# helper functions
def read_yearbook(path:str, crop_name:str=None, city_cn_en:dict=Province_names_cn_en):

    # read and reshape data to long format
    df = pd.read_csv(path)
    df = df.set_index('地区')
    df = df.stack().reset_index()
    df.columns = ['Province','year','Value']
    df['year'] = df['year'].apply(lambda x: int(x[:4]))
    df['crop'] = crop_name

    # fitler df and replace CN to EN
    df = df[df['Province'].isin(city_cn_en.keys())]
    df = df.replace(city_cn_en)

    # remove 0s
    df = df[df['Value']!=0]
    return df.sort_values(['Province','year']).reset_index(drop=True)

def fit_linear_model(df):
    
    # Fit a linear model to the data
    X = df['year']
    y = df['Yield (tonnes)']
    X = sm.add_constant(X)
    model = sm.OLS(y, X).fit()
    
    # Extrapolate the model to from <BASE_YR> to <TARGET_YR>
    pred_years = pd.DataFrame({'year': range(PRED_BASE_YR, PRED_TARGET_YR + 1, PRED_STEP)})
    pred_years = sm.add_constant(pred_years)
    
    extrapolate_df = model.get_prediction(pred_years)
    extrapolate_df = extrapolate_df.summary_frame(alpha=0.32)   # 0.68 CI indicates the mean+/-std
    extrapolate_df['std'] = (extrapolate_df['obs_ci_upper'] - extrapolate_df['mean'])
    extrapolate_df['year'] = pred_years['year']

    return extrapolate_df[['year','mean', 'std']]


# Read the yearbook data for wheat, wetland rice, and maize
wheat_yield_history = read_yearbook('data/Yearbook/Provincial_wheat_yield.csv','Wheat')
rice_yield_history = read_yearbook('data/Yearbook/Provincial_rice_yield.csv','Wetland rice')
maize_yield_history = read_yearbook('data/Yearbook/Provincial_maize_yield.csv','Maize')

# Concatenate the data, and convert kg to tonnes
#  only keep data from 1990 onwards
yearbook_yield = pd.concat([
    wheat_yield_history, 
    rice_yield_history, 
    maize_yield_history], axis=0
).query('year >= 1990').reset_index(drop=True)

yearbook_yield['Yield (tonnes)'] = yearbook_yield['Value'] / 1000


# Function to fit a linear model to the data
yearbook_yield_fitted = pd.DataFrame()
for (province,crop), df in yearbook_yield.groupby(['Province', 'crop']):
    fitted_df = fit_linear_model(df)
    fitted_df.insert(0, 'Province', province)
    fitted_df.insert(1, 'crop', crop)
    yearbook_yield_fitted = pd.concat([yearbook_yield_fitted, fitted_df])

yearbook_yield_fitted = yearbook_yield_fitted.sort_values(['Province','crop','year']).reset_index(drop=True)


# Get the multipliers given the 2020 yield as baseline
yearbook_yield_fitted_xr = xr.DataArray(
    data = np.empty(
        (   
            yearbook_yield_fitted['Province'].nunique(),
            yearbook_yield_fitted['crop'].nunique(),
            yearbook_yield_fitted['year'].nunique(),
            2, # mean and std
        ),
        dtype = np.float32
    ) * np.nan,
    coords = {
        'Province': yearbook_yield_fitted['Province'].unique(),
        'crop': yearbook_yield_fitted['crop'].unique(),
        'year': yearbook_yield_fitted['year'].unique(),
        'band': ['mean', 'std'],
    },
    dims = ['Province', 'crop', 'year', 'band']
)

for _, row in yearbook_yield_fitted.iterrows():
    yearbook_yield_fitted_xr.loc[
        dict(
            Province = row['Province'],
            crop = row['crop'],
            year = row['year']
        )] = row[['mean', 'std']]
    

# Calculate multipliers
yearbook_multipliers = (
    yearbook_yield_fitted_xr 
    / yearbook_yield_fitted_xr.sel(year=PRED_BASE_YR, band='mean', drop=True)
)

yearbook_multipliers_df = yearbook_multipliers.to_dataframe('val').reset_index()
yearbook_multipliers_df = yearbook_multipliers_df.pivot(
    index=['Province','crop','year'], 
    columns='band', 
    values='val'
).reset_index()


# Rasterise multipliers to Province-level in China (mosaiced raster for all provinces)
GAEZ_sample_xr = rxr.open_rasterio('data/GAEZ_v4/GAEZ_tifs/0a1a4943-3ec5-490e-8670-cc3ee7953729.tif_clipped.tif', masked=True).drop_vars('band').squeeze()
China_shp = gpd.read_file('data/Vector_boundary/China_boundary.shp')

# Get unique values for each dimension (excluding Province)
crops = yearbook_multipliers_df['crop'].unique()
years = yearbook_multipliers_df['year'].unique()
bands = ['mean', 'std']

# Initialize the output xarray DataArray (no Province dimension)
rasterized_multipliers = xr.DataArray(
    data=np.empty(
        (
            len(crops),
            len(years),
            len(bands),
            GAEZ_sample_xr.shape[0],
            GAEZ_sample_xr.shape[1]
        ),
        dtype=np.float32
    ) * np.nan,
    coords={
        'crop': crops,
        'year': years,
        'band': bands,
        'y': GAEZ_sample_xr.y,
        'x': GAEZ_sample_xr.x
    },
    dims=['crop', 'year', 'band', 'y', 'x']
)


# Loop through each crop and year combination, rasterizing all provinces together
for crop in crops:
    for year in years:
        # Filter data for this crop and year (all provinces)
        subset = yearbook_multipliers_df[
            (yearbook_multipliers_df['crop'] == crop) &
            (yearbook_multipliers_df['year'] == year)
        ]

        # Merge with shapefile to get geometries for all provinces
        raster_shp = China_shp.merge(
            subset,
            left_on='EN_Name',
            right_on='Province',
            how='inner'
        )

        # Rasterize mean - burn all province geometries with their respective values
        shapes_mean = [(geom, value) for geom, value in zip(raster_shp.geometry, raster_shp['mean'])]
        rasterized_mean = rasterize(
            shapes_mean,
            out_shape=GAEZ_sample_xr.shape,
            transform=GAEZ_sample_xr.rio.transform(),
            fill=np.nan,
            dtype='float32'
        )

        # Rasterize std - burn all province geometries with their respective values
        shapes_std = [(geom, value) for geom, value in zip(raster_shp.geometry, raster_shp['std'])]
        rasterized_std = rasterize(
            shapes_std,
            out_shape=GAEZ_sample_xr.shape,
            transform=GAEZ_sample_xr.rio.transform(),
            fill=np.nan,
            dtype='float32'
        )

        # Assign to the DataArray
        rasterized_multipliers.loc[
            dict(
                crop=crop,
                year=year,
                band='mean'
            )
        ] = rasterized_mean

        rasterized_multipliers.loc[
            dict(
                crop=crop,
                year=year,
                band='std'
            )
        ] = rasterized_std

# Save the rasterized multipliers to a NetCDF file
rasterized_multipliers.to_netcdf('data/Yearbook/crop_yield_multipliers.nc')


# Plot for sanity check
if __name__ == '__main__':


    fig = (
        p9.ggplot() +
        p9.geom_point(
            yearbook_yield, 
            p9.aes(x='year', y='Yield (tonnes)', color='crop'),
            alpha=0.6, 
            size=0.05
        ) +
        p9.geom_ribbon(
            yearbook_yield_fitted, 
            p9.aes(x='year', ymin='mean - std', ymax='mean + std', fill='crop'), 
            alpha=0.3
        ) +
        p9.facet_wrap('~Province', ncol=3) +
        p9.theme_bw() +
        p9.theme(
            legend_position='right',
            figure_size=(8,12)
        ) +
        p9.labs(
            title='Historical crop yields in Chinese provinces (from Yearbook data)',
            y='Yield (tonnes per hectare)',
            x='Year'
        )
    )

    # The multipliers plot
    fig = (
        p9.ggplot() +
        p9.geom_ribbon(
            yearbook_multipliers_df,
            p9.aes(x='year', ymin='mean - std', ymax='mean + std', fill='crop'),
            alpha=0.3) +
        p9.geom_line(
            yearbook_multipliers_df,
            p9.aes(x='year', y='mean', color='crop'),
            size=0.5) +
        p9.facet_wrap('~Province', ncol=3) +
        p9.theme_bw() +
        p9.theme(
            legend_position='right',
            figure_size=(8,12)
        ) +
        p9.labs(
            title='Projected crop yield multipliers in Chinese provinces (Yearbook data)',
            y='Yield multiplier (relative to 2020)',
            x='Year'
        )
    )