import geopandas as gpd
import pandas as pd
import rioxarray as rxr

from joblib import Parallel, delayed
from tqdm.auto import tqdm

# Read tif paths
GAEZ_df = pd.read_csv('data/GAEZ_v4/GAEZ_df.csv')
China_shp = gpd.read_file('data/Vector_boundary/China_boundary.shp')


def clip_raster(input_path, output_path, geometry):
    """Clip a single raster file to the given geometry and save."""
    img = rxr.open_rasterio(input_path, masked=True).drop_vars('band').squeeze()
    clipped = img.rio.clip(geometry)
    clipped.rio.to_raster(output_path)
    return output_path


# Create output tasks
tasks = []
for idx, row in GAEZ_df.iterrows():
    input_path = row['fpath']
    output_path = input_path + '_clipped.tif'
    tasks.append(
        delayed(clip_raster)(input_path, output_path, China_shp.geometry)
    )


# Run parallel clipping
for _ in tqdm(Parallel(n_jobs=8, return_as='generator')(tasks), total=len(tasks)):
    pass