"""Story 1: Global trends in health spending"""

import pandas as pd
from bblocks import places
from typing import Literal
import numpy as np

from scripts.config import Paths
from scripts.logger import logger
from scripts.common import read_ghed_data, add_income_fy22


GHED_DATA = read_ghed_data()


def calc_cagr(start: float, end: float , periods: int) -> float:
    """ Calculate Compound annual growth rate (CAGR)."""
    return (end / start) ** (1 / periods) - 1

def calc_aagr(start: float | int, end: float | int, periods: int) -> float:
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
    # fn = calc_cagr if rate_type == "cagr" else calc_aagr
    #
    # # Compute growth rate per group
    # rates = {grp: fn(start_vals[grp], end_vals[grp], periods) for grp in end_vals.index}

    if rate_type == "cagr":
        rates = {grp: calc_cagr(start_vals[grp], end_vals[grp], periods) for grp in list(end_vals.index)}
    else:  # linear AAGR
        rates = {grp: calc_aagr(start_vals[grp], end_vals[grp], periods) for grp in list(end_vals.index)}

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


def forward_fill(df, value_col = "value", country_col="iso3_code", year_col="year", limit=2):
    """Forward fill missing values in `value_col` for each `country_col` up to `limit` years
    making sure the dataframe has continuous years for each country between min and max year.

    """

    d = df[[country_col, year_col, value_col]].copy()
    d = d.sort_values([country_col, year_col])

    filled_parts = []
    for key, g in d.groupby(country_col, sort=False):
        years = range(int(g[year_col].min()), int(g[year_col].max()) + 1)
        gg = (g.set_index(year_col)
              .reindex(years))  # may introduce completely missing years
        gg[value_col] = gg[value_col].ffill(limit=limit)
        gg[country_col] = key
        gg = gg.reset_index().rename(columns={"index": year_col})
        filled_parts.append(gg)

    filled = pd.concat(filled_parts, ignore_index=True)

    # keep only original (country, year) rows, preserving other columns from df
    out = df.merge(
        filled[[country_col, year_col, value_col]],
        on=[country_col, year_col],
        how="left",
        suffixes=("", "_filled"),
    )
    out[value_col] = out[f"{value_col}"].where(out[f"{value_col}"].notna(),
                                               out[f"{value_col}_filled"])
    out = out.drop(columns=[f"{value_col}_filled"])
    return out


def chart_1():
    """Chart 1 showing global health spending (2000-2022), and expected spending using CAGR for years 2019-2022
    """

    # create base dataframe for the chart
    df = (GHED_DATA
     .loc[lambda d: (d.indicator_code.isin(["che_usd2022"])) & (d.year != 2023)]
    # forward fill missing values up to 2 years
    .pipe(forward_fill, value_col="value", country_col="iso3_code", year_col="year", limit=2)
     .groupby(["year"])
     .agg({"value": "sum"})
     .reset_index()
     .assign(entity="World")
     .pipe(apply_growth, group_col="entity")
          .loc[lambda d: d.year>=2010]
     )

    # export downloadable data
    (df
     .assign(units = "Constant 2022 US$")
     .rename(columns={"value": "actual_spending"})
     .to_csv(Paths.output / "story_1" / "chart_1_data.csv", index=False)
     )

    # export chart data
    (df
    .rename(columns={"value": "actual_spending"})
    .melt(id_vars = ["year"], value_vars = ["actual_spending", "expected_spending"])
    # assign an annotate column with values of True where "variable" is "actual spending"
    .assign(annotate = lambda d: np.where(d.variable == "actual_spending", True, None))
    .pivot(index=["year", "annotate"], columns="variable", values="value")
    .dropna(subset=["actual_spending", "expected_spending"], how="all")
    # create an annotation column with actual spending in trillions rounded to 2 decimal places and as a string with "T" at the end
    .assign(value_annotation = lambda d: round((d.actual_spending/1000000000000), 2).astype(str) + " trillion")
    .reset_index()


    .to_csv(Paths.output / "story_1" / "chart_1.csv", index=False)
     )

    logger.info("Chart 1 complete")


def chart_2():
    """Chart 2 showing health spending by income group (2000-2022), and expected spending using CAGR for years 2019-2022
    """

    df = (GHED_DATA
     .loc[lambda d: d.indicator_code.isin(["che_usd2022"])]

    .pipe(add_income_fy22, iso3_col="iso3_code", income_level_col="income_level")
    .dropna(subset=["income_level"])
    .loc[lambda d: (d.year != 2023)]
    # group by year and country and forward fill missing values up to 2 year
    .pipe(forward_fill, value_col="value", country_col="iso3_code", year_col="year", limit=2)

     .groupby(["year", "income_level"])
     .agg({"value": "sum"})
     .reset_index()
     .pipe(apply_growth, group_col="income_level")
    .loc[lambda d: d.year >= 2010]
     )

    # export downloadable data
    (df
     .assign(units = "Constant 2022 US$")
     .rename(columns={"value": "actual_spending"})
     .to_csv(Paths.output / "story_1" / "chart_2_data.csv", index=False)
     )

    # export chart data
    (df
     # .pipe(add_covid_column, entity_col="income_level")
     .rename(columns={"value": "actual_spending"})
     .melt(id_vars=["year", "income_level"], value_vars=["actual_spending", "expected_spending"])
     # assign an annotate column with values of True where "variable" is "actual spending"
     .assign(annotate=lambda d: np.where(d.variable == "actual_spending", True, None))
     .pivot(index=["year", "annotate", "income_level"], columns="variable", values="value")
    .reset_index()
     .assign(value_annotation=lambda d: round((d.actual_spending / 1000000000), 2).astype(str) + " billion")
        # sort by income level
    .assign(income_level=lambda d: pd.Categorical(d.income_level, categories=["Low income", "Lower middle income", "Upper middle income", "High income"], ordered=True))
    .sort_values(["income_level", "year"])


     .to_csv(Paths.output / "story_1" / "chart_2.csv", index=False)
     )

    logger.info("Chart 2 complete")



if __name__ == "__main__":

    logger.info("Creating charts for Story 1...")
    chart_1()
    chart_2()
    logger.info("Story 1 complete.")