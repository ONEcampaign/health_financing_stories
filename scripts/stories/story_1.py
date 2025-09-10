"""Story 1: Global trends in health spending"""

import pandas as pd
from bblocks import places
from typing import Literal

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


GHED_DATA = read_ghed_data()


def calc_cagr(start: float, end: float, periods: int) -> float:
    """ Calculate Compound annual growth rate (CAGR)."""
    return (end / start) ** (1 / periods) - 1

def calc_aagr(start: float, end: float, periods: int) -> float:
    """Calculate Average annual growth rate (AAGR, linear)."""
    return ((end - start) / periods) / start


def apply_growth(
    df: pd.DataFrame,
    group_col: str,
    year_col: str = "year",
    value_col: str = "value",
    start_year: int = 2000,
    end_year: int = 2019,
    proj_to: int = 2022,
    rate_type: Literal["cagr", "aagr"] = "cagr",
    out_col: str = "expected_spending"
) -> pd.DataFrame:
    """Add `out_col` with expected values from end_year..proj_to using CAGR or AAGR."""

    # Number of years between start and end (e.g. 2000→2019 = 19)
    periods = end_year - start_year

    # Get values at start and end years for each group
    start_vals = df.loc[df[year_col] == start_year].set_index(group_col)[value_col]
    end_vals = df.loc[df[year_col] == end_year].set_index(group_col)[value_col]

    # Choose the correct growth function
    fn = calc_cagr if rate_type == "cagr" else calc_aagr

    # Compute growth rate per group
    rates = {grp: fn(start_vals[grp], end_vals[grp], periods) for grp in end_vals.index}

    # Build projection years (end_year..proj_to)
    years = list(range(end_year, proj_to + 1))
    exp = pd.MultiIndex.from_product([end_vals.index, years], names=[group_col, year_col]).to_frame(index=False)

    # Attach base value (end_year actual) and growth rate
    exp["base"] = exp[group_col].map(end_vals)
    exp["rate"] = exp[group_col].map(rates)

    # Distance from end_year (so end_year itself has t=0 → stays unchanged)
    t = exp[year_col] - end_year

    # Compute projected values
    if rate_type == "cagr":
        exp[out_col] = exp["base"] * (1 + exp["rate"]) ** t
    else:  # linear AAGR
        exp[out_col] = exp["base"] * (1 + exp["rate"] * t)

    # Keep only projection results
    exp = exp[[group_col, year_col, out_col]]

    # Merge back into the original dataframe
    return df.merge(exp, on=[group_col, year_col], how="left")


def chart_1():
    """Chart 1 showing global health spending (2000-2022), and expected spending using CAGR for years 2019-2022
    """

    # create base dataframe for the chart
    df = (GHED_DATA
     .loc[lambda d: (d.indicator_code.isin(["che_usd2022"])) & (d.year != 2023)]
     .groupby(["year"])
     .agg({"value": "sum"})
     .reset_index()
     .assign(entity="World")
     .pipe(apply_growth, group_col="entity", rate_type="cagr")
     )

    # export downloadable data
    (df
     .assign(units = "Constant 2022 US$")
     .rename(columns={"value": "actual_spending"})
     .to_csv(Paths.output / "story_1" / "chart_1_data.csv", index=False)
     )

    # export chart data
    (df
     # TODO: Fix and customise annotations and popups as needed
    .to_csv(Paths.output / "story_1" / "chart_1.csv", index=False)
     )

    logger.info("Chart 1 complete")


def add_covid_column(df: pd.DataFrame, entity_col: str) -> pd.DataFrame:
    """Create a column with 2019 values for each entity"""

    covid = df[df.year == 2019][[entity_col, "value"]].rename(columns={"value": "covid"})
    return df.merge(covid, on=entity_col, how="left")

def chart_2():
    """Chart 2 showing health spending by income group (2000-2022), and expected spending using CAGR for years 2019-2022
    """

    df = (GHED_DATA
     .loc[lambda d: d.indicator_code.isin(["che_usd2022"])]
     .assign(income_level=lambda d: places.resolve_places(d.iso3_code,
                                                          not_found="ignore",
                                                          from_type="iso3_code",
                                                          to_type="income_level"))
     .loc[lambda d: (d.year != 2023) & (d.income_level != "Not classified")]
     .groupby(["year", "income_level"])
     .agg({"value": "sum"})
     .reset_index()
     .pipe(apply_growth, group_col="income_level")
     )

    # export downloadable data
    (df
     .assign(units = "Constant 2022 US$")
     .rename(columns={"value": "actual_spending"})
     .to_csv(Paths.output / "story_1" / "chart_2_data.csv", index=False)
     )

    # export chart data
    (df
     .pipe(add_covid_column, entity_col="income_level")
     #TODO: Fix and customise annotations and popups as needed
     .to_csv(Paths.output / "story_1" / "chart_2.csv", index=False)
     )

    logger.info("Chart 2 complete")



if __name__ == "__main__":

    logger.info("Creating charts for Story 1...")
    chart_1()
    chart_2()
    logger.info("Story 1 complete.")