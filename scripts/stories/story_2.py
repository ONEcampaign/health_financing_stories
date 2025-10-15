"""Story 2: Health priority and government spending on health"""

import pandas as pd
from bblocks import places
from pydeflate import imf_gdp_deflate, set_pydeflate_path
import random

from scripts.config import Paths
from scripts.logger import logger
from scripts.common import read_ghed_data

GHED_DATA = read_ghed_data()
set_pydeflate_path(Paths.raw_data)


def chart_1():
    """bubble chart showing government health spending vs gdp per capita, sized by population"""

    # Preprocess the data
    data = (
        GHED_DATA.loc[lambda d: (d.year == 2022)]
        .loc[
            lambda d: d.indicator_code.isin(
                ["gghed_gdp", "pop", "gghed_ncu_pc", "gghed_usd2022_pc"]
            )
        ]
        .pivot(
            index=["country_name", "iso3_code", "year"],
            columns="indicator_code",
            values="value",
        )
        .reset_index()
        .pipe(
            imf_gdp_deflate,
            base_year=2015,
            source_currency="LCU",
            target_currency="USA",
            id_column="iso3_code",
            value_column="gghed_ncu_pc",
            target_value_column="gghed_usd2015_pc",
        )
        .drop(columns=["gghed_ncu_pc"])
        .dropna(
            subset=["gghed_gdp", "pop", "gghed_usd2015_pc"]
        )  # remove any countries with missing data
        .assign(
            income_level=lambda d: places.resolve_places(
                d.iso3_code,
                to_type="income_level",
                from_type="iso3_code",
                not_found="Not classified",
            ),
            region=lambda d: places.resolve_places(
                d.iso3_code,
                to_type="region",
                from_type="iso3_code",
                not_found="Other region",
            ),
        )
    )

    # export downloadable data
    rename_cols = {
        "gghed_gdp": "Domestic general government health expenditure (percent of GDP)",
        "pop": "Population",
        "gghed_usd2015_pc": "Domestic general government health expenditure per capita (constant 2015 US$)",
        "gghed_usd2022_pc": "Domestic general government health expenditure per capita (constant 2022 US$)",
        "income_level": "Income level",
        "region": "Region",
        "country_name": "Country",
        "year": "Year",
        "iso3_code": "ISO3 code",
    }
    (
        data.rename(columns=rename_cols).to_csv(
            Paths.output / "story_2" / "chart_1_data.csv", index=False
        )
    )

    # export chart data
    (
        data.loc[
            :,
            [
                "country_name",
                "year",
                "gghed_gdp",
                "gghed_usd2015_pc",
                "gghed_usd2022_pc",
                "pop",
                "region",
                "income_level",
            ],
        ]
        # create annotation for pop with "millions" at the end of the string
        .assign(
            pop_annotation=lambda d: d["pop"].apply(
                lambda x: f"{round(x / 1e6, 2)} million"
            )
        )
        # for china and india, show in billions
        .assign(
            pop_annotation=lambda d: d.apply(
                lambda x: (
                    f"{round(x["pop"] / 1e9, 2)} billion"
                    if x["country_name"] in ["China", "India"]
                    else x["pop_annotation"]
                ),
                axis=1,
            )
        )
        .assign(gghed_usd2022_pc=lambda d: d.gghed_usd2022_pc.round(2))
        .assign(
            africa_annotation=lambda d: d.apply(
                lambda x: True if x["region"] == "Africa" else None, axis=1
            )
        )
        .assign(
            other_annotation=lambda d: d.apply(
                lambda x: True if x["region"] != "Africa" else None, axis=1
            )
        )
        .to_csv(Paths.output / "story_2" / "chart_1.csv", index=False)
    )

    logger.info("Chart 1 complete")


def chart_2():
    """Chart 2 showing government health spending as percent of government expenditure for African countries
    (2001-2022), and Africa median"""

    # preprocess the data
    data = (
        GHED_DATA.loc[lambda d: d.indicator_code.isin(["gghed_gge"])]
        .assign(
            region=lambda d: places.resolve_places(
                d.iso3_code, to_type="region", from_type="iso3_code", not_found="ignore"
            )
        )
        .loc[lambda d: (d.region == "Africa") & (d.year >= 2001)]
        .drop(columns=["region", "indicator_code"])
    )

    # Africa median
    afr_median = (
        data.groupby("year")
        .agg({"value": "median"})
        .assign(country_name="Africa (median)")
        .reset_index()
    )

    # export downloadable data
    df = pd.merge(data, afr_median, how="outer").assign(
        indicator_name="Domestic general government health expenditure (percent general government expenditure)"
    )
    df.to_csv(Paths.output / "story_2" / "chart_2_data.csv", index=False)

    # export chart data
    (
        pd.concat([data.assign(country_cat=True), afr_median.assign(afr_category=True)])
        # .loc[lambda d: d.country_name.isin(get_afr_countries_list(d) + ["Africa (median)"])]
        .pivot(
            index=["year", "country_cat", "afr_category"],
            columns="country_name",
            values="value",
        )
        .reset_index()
        .to_csv(Paths.output / "story_2" / "chart_2.csv", index=False)
    )

    logger.info("Chart 2 complete")


if __name__ == "__main__":

    logger.info("Creating charts for Story 2...")
    chart_1()
    chart_2()
    logger.info("Story 2 complete.")
