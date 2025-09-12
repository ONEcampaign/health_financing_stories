"""Common utilities"""

import pandas as pd

from scripts.config import Paths
from scripts.logger import logger
from scripts.get_raw_data import fetch_ghed_data


def read_ghed_data() -> pd.DataFrame:

    path = Paths.raw_data / "ghed_data.csv"

    if not path.exists():
        logger.info("GHED data not found, fetching...")
        fetch_ghed_data()

    logger.info("Reading GHED data...")
    return pd.read_csv(path)