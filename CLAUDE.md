# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project processes Global Agro-Ecological Zones (GAEZ) v4 data from FAO to analyze crop yield projections under different climate scenarios. The pipeline downloads geospatial raster data (GeoTIFF files) and consolidates them into xarray DataArrays for analysis of three crops (Maize, Wheat, Wetland rice) in China.

## Key Data Processing Pipeline

The workflow follows three main stages:

1. **Data Acquisition** (`tools/step_01_download_GAEZ.py`):
   - Filters FAO catalog CSVs for target crops: Maize, Wheat, Wetland rice
   - Normalizes water supply terminology across datasets (Irrigation/Rainfed/etc. → Irrigated/Dryland)
   - Downloads GeoTIFF files in parallel with 32 workers
   - Outputs `data/GAEZ_v4/GAEZ_df.csv` with metadata and local file paths

2. **Spatial Clipping** (`tools/step_02_clip_GAEZ.py`):
   - Clips global GeoTIFF rasters to China boundary using geopandas shapefile
   - Processes files in parallel with 8 workers
   - Saves clipped rasters with `_clipped.tif` suffix
   - Reads boundary from `data/Vector_boundary/China_boundary.shp`

3. **Data Consolidation** (`step_01_merge_GAEZ_to_NC.py`):
   - Loads clipped GeoTIFF files into xarray DataArrays using rioxarray
   - Separates historical (1981-2010) and future projections (2011-2100)
   - Calculates ensemble mean and standard deviation across climate models
   - Processes each crop separately (Wheat, Maize, Wetland rice)
   - Exports to NetCDF: `GAEZ_4_historical_yield.nc` and `GAEZ_4_future_yield.nc`

## Running Common Tasks

### Complete Pipeline Execution

1. **Download GAEZ Data**
```bash
python tools/step_01_download_GAEZ.py
```
This reads catalog files from `data/GAEZ_v4/GAEZ_raw_urls/`, filters for target crops/years/variables, and downloads GeoTIFF files to `data/GAEZ_v4/GAEZ_tifs/` with UUID-based filenames.

2. **Clip to China Boundary**
```bash
python tools/step_02_clip_GAEZ.py
```
Clips all downloaded GeoTIFF files to the China boundary shapefile using 8 parallel workers. Creates files with `_clipped.tif` suffix.

3. **Merge to NetCDF**
```bash
python step_01_merge_GAEZ_to_NC.py
```
Loads metadata from `GAEZ_df.csv`, converts clipped GeoTIFF rasters to xarray DataArrays, calculates ensemble statistics, and exports to NetCDF files.

## Architecture and Data Structure

### Data Dimensions

**GAEZ_4 (Future projections):**
- `year`: 1995, 2025, 2055, 2085 (mapped from period ranges)
- `model`: Climate models (e.g., NorESM1-M)
- `rcp`: RCP2.6, RCP4.5, RCP6.0, RCP8.5
- `crop`: Maize, Wetland rice, Wheat
- `water_supply`: Dryland, Irrigated
- `c02_fertilization`: With/Without CO2 Fertilization

**GAEZ_5 (Historical baseline):**
- `year`: 2010
- `crop`: Maize, Wetland rice, Wheat
- `water_supply`: Dryland, Irrigated
- `variable`: Yield or Harvested area

### Water Supply Normalization

The code standardizes inconsistent terminology from FAO catalogs:
```python
# GAEZ_4 mapping
'Irrigation' → 'Irrigated'
'Rainfed' → 'Dryland'
'Gravity Irrigation' → 'Irrigated'
'Sprinkler Irrigation' → 'Irrigated'
'Rainfed All Phases ' → 'Dryland'  # Note trailing space in source data
'Drip Irrigation' → 'Irrigated'
```

### Historical vs Future Data Handling

Historical data (1981-2010) uses codes `ycHa` or `ycHg` in the name field and has `rcp == "Historical"`. It collapses the model/rcp/c02_fertilization dimensions since there's only one baseline scenario.

Future data processes each crop separately to handle missing data issues (e.g., Wetland rice missing certain model/scenario combinations for 2071-2100).

### Key Functions

**`download_GAEZ_data(GAEZ_df, n_workers=32)`** (`tools/helpers.py`) - Parallel download orchestrator:
- Uses joblib with threading backend
- Default 32 concurrent workers
- Generates UUID filenames to avoid conflicts
- Returns dataframe with `fpath` column added

**`download_url(url, fpath)`** (`tools/helpers.py`) - Single file downloader:
- Downloads single file with retry logic
- Uses browser user-agent headers to avoid blocks

**`get_with_retry(get_url, headers, max_retries=5)`** (`tools/helpers.py`) - HTTP retry wrapper:
- Implements exponential backoff with 2-second delays
- Maximum 5 retry attempts
- Catches all HTTP exceptions

**`clip_raster(input_path, output_path, geometry)`** (`tools/step_02_clip_GAEZ.py`) - Raster clipping:
- Clips single raster to China boundary geometry
- Uses rioxarray for geospatial operations
- Saves clipped raster to output path

**`get_xr_darray_from_df(in_df)`** (`step_01_merge_GAEZ_to_NC.py`) - Converts indexed dataframe to xarray DataArray:
- Reads clipped GeoTIFF files using rioxarray
- Drops band dimension and squeezes to 2D spatial
- Expands dimensions based on dataframe multi-index
- Combines all rasters using `xr.combine_by_coords()`

**`calc_mean_std(in_xr)`** (`step_01_merge_GAEZ_to_NC.py`) - Computes ensemble statistics:
- Calculates mean across climate models
- Calculates standard deviation across models
- Returns concatenated DataArray with new `band` dimension: ['mean', 'std']

## Important Conventions

### Input Level Filtering
All processing assumes `input_level == "High"` which represents high-input agriculture (e.g., improved seeds, fertilizers, mechanization).

### Variable Filtering
- GAEZ_4: Only processes "Average attainable yield of current cropland"
- GAEZ_5: Only processes "Yield" or "Harvested area"

### Known Data Gaps
The code includes a comment noting missing data for Wetland rice in GAEZ_4:
- Year: 2071-2100
- Model: MIROC-ESM-CHEM
- RCP: RCP4.5
- Both With/Without CO2 Fertilization scenarios

This is why rice is processed separately from wheat and maize.

## Dependencies

Core scientific Python stack:
- **pandas**: Metadata manipulation and CSV I/O
- **xarray**: Multidimensional labeled arrays
- **rioxarray**: Geospatial raster I/O for xarray
- **geopandas**: Spatial vector operations and shapefile I/O
- **requests**: HTTP downloads with retry logic
- **joblib**: Parallel processing
- **tqdm**: Progress bars
- **uuid**: Unique filename generation

## Output Files

The pipeline produces the following output files:

- `data/GAEZ_v4/GAEZ_df.csv`: Metadata catalog with file paths for all downloaded GeoTIFFs
- `data/GAEZ_v4/GAEZ_tifs/{uuid}.tif`: Downloaded GeoTIFF files (UUID-named)
- `data/GAEZ_v4/GAEZ_tifs/{uuid}.tif_clipped.tif`: Clipped GeoTIFF files for China boundary
- `data/GAEZ_v4/GAEZ_4_historical_yield.nc`: Historical (1981-2010) yield data as NetCDF
- `data/GAEZ_v4/GAEZ_4_future_yield.nc`: Future projection (2011-2100) yield data with ensemble statistics as NetCDF

## File Naming Conventions

Downloaded GeoTIFF files use UUID-based naming to avoid conflicts:
```python
unique_id = uuid.uuid4()
fname = f"data/GAEZ_v4/GAEZ_tifs/{unique_id}.tif"
```

Mapping back to metadata is maintained through the `fpath` column in `GAEZ_df.csv`.

## Retry and Error Handling

HTTP downloads use exponential backoff with 5 retries and 2-second delays (`get_with_retry` function). Failed downloads print error messages but don't halt the pipeline.

Browser user-agent headers are required to avoid FAO server blocks:
```python
headers = {
    'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
}
```
