# China Crop Yield Analysis - GAEZ v4 Data Processing Pipeline

This project processes Global Agro-Ecological Zones (GAEZ) v4 data from the Food and Agriculture Organization (FAO) to analyze crop yield projections under different climate scenarios for China. The pipeline downloads geospatial raster data (GeoTIFF files), clips them to China's boundary, and consolidates them into xarray DataArrays for analysis.

## Overview

The pipeline processes data for three major crops in China:
- **Maize**
- **Wheat**
- **Wetland rice**

It analyzes both historical baseline data (1981-2010) and future climate projections (2011-2100) under multiple Representative Concentration Pathway (RCP) scenarios.

## Features

- Parallel downloading of GAEZ v4 geospatial data (32 workers)
- Automatic normalization of water supply terminology across datasets
- Spatial clipping to China boundary (8 parallel workers)
- Ensemble statistics calculation across climate models (mean and standard deviation)
- NetCDF export for efficient storage and analysis
- Handles missing data scenarios for specific crop/model/RCP combinations

## Installation

### Prerequisites

- Python 3.7+
- Required Python packages:

```bash
pip install pandas xarray rioxarray geopandas requests joblib tqdm
```

### Data Requirements

1. GAEZ catalog CSV files in `data/GAEZ_v4/GAEZ_raw_urls/`:
   - `GAEZ_4.csv` (future projections)
   - `GAEZ_5.csv` (historical baseline)

2. China boundary shapefile in `data/Vector_boundary/`:
   - `China_boundary.shp` (and associated .shx, .dbf, .prj files)

## Usage

### Complete Pipeline Execution

Run the following scripts in sequence:

#### 1. Download GAEZ Data

```bash
python tools/step_01_download_GAEZ.py
```

This script:
- Filters FAO catalog CSVs for target crops (Maize, Wheat, Wetland rice)
- Normalizes water supply terminology (Irrigation/Rainfed → Irrigated/Dryland)
- Downloads GeoTIFF files in parallel (32 workers)
- Saves metadata catalog to `data/GAEZ_v4/GAEZ_df.csv`

#### 2. Clip to China Boundary

```bash
python tools/step_02_clip_GAEZ.py
```

This script:
- Clips global GeoTIFF rasters to China boundary
- Processes files in parallel (8 workers)
- Saves clipped rasters with `_clipped.tif` suffix

#### 3. Merge to NetCDF

```bash
python step_01_merge_GAEZ_to_NC.py
```

This script:
- Loads clipped GeoTIFF files into xarray DataArrays
- Separates historical and future data
- Calculates ensemble mean and standard deviation across climate models
- Exports to NetCDF files:
  - `data/GAEZ_v4/GAEZ_4_historical_yield.nc`
  - `data/GAEZ_v4/GAEZ_4_future_yield.nc`

## Data Structure

### Dimensions

**Future Projections (GAEZ_4):**
- `year`: 1995, 2025, 2055, 2085 (mapped from period ranges)
- `model`: Climate models (e.g., NorESM1-M, MIROC-ESM-CHEM, etc.)
- `rcp`: RCP2.6, RCP4.5, RCP6.0, RCP8.5
- `crop`: Maize, Wetland rice, Wheat
- `water_supply`: Dryland, Irrigated
- `c02_fertilization`: With CO2 Fertilization, Without CO2 Fertilization
- `band`: mean, std (ensemble statistics)

**Historical Baseline (GAEZ_5):**
- `year`: 2010
- `crop`: Maize, Wetland rice, Wheat
- `water_supply`: Dryland, Irrigated
- `variable`: Yield, Harvested area

### Water Supply Normalization

The pipeline standardizes inconsistent terminology from FAO catalogs:

| Original Term | Normalized Term |
|--------------|-----------------|
| Irrigation | Irrigated |
| Rainfed | Dryland |
| Gravity Irrigation | Irrigated |
| Sprinkler Irrigation | Irrigated |
| Drip Irrigation | Irrigated |
| Rainfed All Phases | Dryland |

### Year Mapping

Period ranges are mapped to representative years:

| Period Range | Representative Year |
|-------------|---------------------|
| 1981-2010 | 1995 |
| 2011-2040 | 2025 |
| 2041-2070 | 2055 |
| 2071-2100 | 2085 |

## Output Files

The pipeline produces the following files:

| File | Description |
|------|-------------|
| `data/GAEZ_v4/GAEZ_df.csv` | Metadata catalog with file paths |
| `data/GAEZ_v4/GAEZ_tifs/{uuid}.tif` | Downloaded GeoTIFF files |
| `data/GAEZ_v4/GAEZ_tifs/{uuid}.tif_clipped.tif` | Clipped GeoTIFF files |
| `data/GAEZ_v4/GAEZ_4_historical_yield.nc` | Historical yield data (NetCDF) |
| `data/GAEZ_v4/GAEZ_4_future_yield.nc` | Future projection yield data (NetCDF) |

## Key Features

### Parallel Processing

- **Download**: 32 concurrent workers using joblib threading backend
- **Clipping**: 8 concurrent workers for spatial operations
- **Progress tracking**: tqdm progress bars for all operations

### Error Handling

- HTTP downloads use exponential backoff with 5 retries and 2-second delays
- Browser user-agent headers prevent FAO server blocks
- Failed downloads print error messages but don't halt the pipeline

### Data Quality

- Only processes "High" input level data (improved seeds, fertilizers, mechanization)
- Handles missing data scenarios (e.g., Wetland rice missing MIROC-ESM-CHEM/RCP4.5 data for 2071-2100)
- Calculates ensemble statistics (mean and standard deviation) across climate models

## Known Limitations

### Missing Data

The following data combinations are missing from the GAEZ_4 dataset for Wetland rice:
- Year: 2071-2100
- Model: MIROC-ESM-CHEM
- RCP: RCP4.5
- Both With/Without CO2 Fertilization scenarios

This is handled by processing each crop separately to avoid data alignment issues.

## Project Structure

```
.
├── data/
│   ├── GAEZ_v4/
│   │   ├── GAEZ_raw_urls/        # Input catalog CSVs
│   │   ├── GAEZ_tifs/            # Downloaded and clipped GeoTIFFs
│   │   ├── GAEZ_df.csv           # Metadata catalog
│   │   ├── GAEZ_4_historical_yield.nc
│   │   └── GAEZ_4_future_yield.nc
│   └── Vector_boundary/
│       └── China_boundary.shp     # China boundary shapefile
├── tools/
│   ├── helpers.py                 # Download and retry utilities
│   ├── step_01_download_GAEZ.py  # Download script
│   └── step_02_clip_GAEZ.py      # Clipping script
├── step_01_merge_GAEZ_to_NC.py   # NetCDF consolidation script
└── README.md
```

## Data Source

Global Agro-Ecological Zones (GAEZ) v4 data is provided by the Food and Agriculture Organization (FAO):
- [GAEZ v4 Data Portal](https://gaez.fao.org/)

## License

Please refer to the FAO GAEZ v4 data usage terms and conditions for the underlying data.

## Contributing

For questions or contributions, please contact the project maintainer.

## Citation

If you use this pipeline in your research, please cite the GAEZ v4 data source:

> IIASA/FAO. 2023. Global Agro-Ecological Zones v4 (GAEZ v4): Model documentation. IIASA, Laxenburg, Austria and FAO, Rome, Italy.
