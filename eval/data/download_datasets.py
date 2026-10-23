import os
import io
import logging
import requests
import certifi
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval.data")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

DATASETS = {
    "deepset_test.parquet": "https://huggingface.co/datasets/deepset/prompt-injections/resolve/main/data/test-00000-of-00001-701d16158af87368.parquet",
    "deepset_train.parquet": "https://huggingface.co/datasets/deepset/prompt-injections/resolve/main/data/train-00000-of-00001-9564e8b05b4757ab.parquet",
    "jbb_harmful.csv": "https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/resolve/main/data/harmful-behaviors.csv",
    "jbb_benign.csv": "https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/resolve/main/data/benign-behaviors.csv",
}

def download_file(url: str, dest_path: str) -> bool:
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        logger.info(f"File already exists: {os.path.basename(dest_path)} ({os.path.getsize(dest_path)} bytes)")
        return True

    logger.info(f"Downloading {url} -> {os.path.basename(dest_path)}...")
    try:
        resp = requests.get(url, verify=certifi.where(), timeout=30)
        if resp.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"Successfully saved {os.path.basename(dest_path)} ({len(resp.content)} bytes)")
            return True
        else:
            logger.error(f"HTTP {resp.status_code} downloading {url}")
            return False
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    all_ok = True
    for filename, url in DATASETS.items():
        dest = os.path.join(DATA_DIR, filename)
        ok = download_file(url, dest)
        if not ok:
            all_ok = False

    if all_ok:
        logger.info("All public evaluation datasets downloaded and verified.")
    else:
        logger.warning("Some external datasets could not be downloaded. Local cached/curated datasets will be used.")

if __name__ == "__main__":
    main()
