from typing import Iterable

import pandas as pd
from oda_data import CRSData, set_data_path
from oda_data.clean_data.common import convert_units

from oda_data.tools import sector_lists

from scripts.config import Paths


def _assign_sub_sector(df: pd.DataFrame, broad: bool = False) -> pd.DataFrame:
    """Assigns sub-sector names based on purpose codes."""
    sub_sectors = sector_lists.get_sector_groups()

    for name, codes in sub_sectors.items():
        df.loc[df.purpose_code.isin(codes), "sub_sector"] = name

    if broad:
        broad_sectors = sector_lists.get_broad_sector_groups()
        df["sub_sector"] = (
            df["sub_sector"].map(broad_sectors).fillna("Unallocated/unspecified")
        )
    return df


def get_bilateral_by_sector(
    years: Iterable[int],
    by_recipient: bool = False,
    broad_sectors: bool = True,
    currency: str = "USD",
    base_year: int | None = None,
) -> pd.DataFrame:
    """Fetches and aggregates bilateral ODA disbursements by sector."""
    raw_bilateral = CRSData(years=list(years)).read(
        using_bulk_download=True,
        additional_filters=[
            ("flow_code", "in", [11, 13, 19, 60]),  # ODA
        ],
        columns=[
            "year",
            "donor_code",
            "donor_name",
            "recipient_name",
            "recipient_code",
            "purpose_code",
            "usd_disbursement",
        ],
    )

    idx = ["year", "donor_code", "donor_name", "sub_sector"]

    if by_recipient:
        idx += ["recipient_code", "recipient_name"]

    # Assign (broad) subsectors
    df = _assign_sub_sector(raw_bilateral, broad=broad_sectors)

    sectors = (
        df.groupby(
            idx,
            dropna=False,
            observed=True,
        )["usd_disbursement"]
        .sum()
        .reset_index()
        .rename(columns={"usd_disbursement": "value"})
        .loc[lambda d: d.value != 0]
    )

    sectors = convert_units(data=sectors, currency=currency, base_year=base_year)

    return sectors


def filter_health(df: pd.DataFrame) -> pd.DataFrame:
    data = df.loc[lambda d: d.sub_sector == "Health"].reset_index(drop=True)

    # Add share column
    data["donor_share_of_total"] = data.groupby(["year"], dropna=False, observed=True)[
        "value"
    ].transform(lambda x: x / x.sum())

    return data


if __name__ == "__main__":
    set_data_path(Paths.raw_data)
    sectors_data = get_bilateral_by_sector(years=range(2013, 2024), broad_sectors=True)
    health_data = filter_health(sectors_data)
