import time
import uuid
import requests
from joblib import Parallel, delayed
from tqdm import tqdm


def get_with_retry(get_url, headers, max_retries=5):
    for i in range(max_retries):
        try:
            response = requests.get(get_url, headers=headers)
            response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xx
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed with {e}. Retrying...")
            time.sleep(2)  # Wait for 2 seconds before retrying
    print(f"Failed to fetch the URL after {max_retries} attempts.")
    return None


def download_url(url, fpath):
    # Send a GET request to the URL
    headers = {
        'user-agent': (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " 
            "AppleWebKit/537.36 (KHTML, like Gecko) " 
            "Chrome/101.0.4951.67 Safari/537.36")
    }
    response = get_with_retry(url, headers=headers)

    if response is None:
        print(f"Failed to download data from {url}")

    else:
        # Open the file in write mode
        with open(fpath, 'wb') as f:
            f.write(response.content)
            
def download_GAEZ_data(GAEZ_df, n_workers=32):
    # Prepare tasks
    tasks = []
    fpaths = []
    for _, row in GAEZ_df.iterrows():
        unique_id = uuid.uuid4()
        fname = f"data/GAEZ_v4/GAEZ_tifs/{unique_id}.tif"
        url = row['download_url']

        tasks.append((url, fname))
        fpaths.append(fname)

    # Execute downloads in parallel with joblib
    Parallel(n_jobs=n_workers, backend='threading')(
        delayed(download_url)(url, fname)
        for url, fname in tqdm(tasks, desc="Downloading GAEZ data")
    )

    # Append the fpaths to the GAEZ_df
    GAEZ_df['fpath'] = fpaths

    return GAEZ_df
    
