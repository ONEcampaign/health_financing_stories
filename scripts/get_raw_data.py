"""Fetch raw data from various sources and save it to the raw_data folder."""

import pandas as pd
from bblocks.data_importers import GHED

from scripts.config import Paths


def _convert_ghed_units(
    df: pd.DataFrame, value_col: str = "value", unit_col: str = "unit"
) -> pd.DataFrame:
    """
    Convert df[value_col] according to df[unit_col], using:
      Millions -> *1_000_000
      Thousands -> *1_000
      Ones/Percentage -> *1

    Raises ValueError if any non-null unit isn’t one of the four allowed.
    """

    _CONVERSION_FACTORS = {
        "Millions": 1_000_000,
        "Thousands": 1_000,
        "Ones": 1,
        "Percentage": 1,
    }

    # find any unexpected units
    bad = df[unit_col].notna() & ~df[unit_col].isin(_CONVERSION_FACTORS)
    if bad.any():
        unexpected = df.loc[bad, unit_col].unique().tolist()
        raise ValueError(
            f"Unexpected units {unexpected!r}; allowed: {list(_CONVERSION_FACTORS)}"
        )

    out = df.copy()  # only copy once
    out[value_col] = out[value_col] * out[unit_col].map(_CONVERSION_FACTORS)
    return out


def fetch_ghed_data():
    """Fetch Global Health Expenditure Database (GHED) data."""

    ghed = GHED()
    ghed_data = ghed.get_data()

    # Convert units
    ghed_data = _convert_ghed_units(ghed_data)
    ghed_data = ghed_data.loc[
        :, ["country_name", "iso3_code", "year", "indicator_code", "value"]
    ]

    # Save to csv
    ghed_data.to_csv(Paths.raw_data / "ghed_data.csv", index=False)


def fetch_all():
    """Pipeline to fetch all the raw data"""

    fetch_ghed_data()


if __name__ == "__main__":
    fetch_all()
