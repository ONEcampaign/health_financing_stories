"""Story 3: Out-of-pocket health spending"""

import pandas as pd
from bblocks import places

from scripts.config import Paths
from scripts.logger import logger
from scripts.common import read_ghed_data, add_income_fy22

GHED_DATA = read_ghed_data()


def preprocess_data() -> pd.DataFrame:
    """Preprocess data for story 3 charts."""

    indicator = "hf3_che"

    return (
        GHED_DATA.loc[lambda d: (d.indicator_code == indicator) & (d.year <= 2022)]
        # .assign(income_level=lambda d: places.resolve_places(d.iso3_code, to_type="income_level", from_type="iso3_code",
        #                                                      not_found="ignore"))
        .pipe(add_income_fy22).dropna(subset=["income_level"])
        # .loc[lambda d: d.income_level != "Not classified"]
        .reset_index(drop=True)
    )


def agg_income_group_medians(preprocessed_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate data to get income group medians."""

    return (
        preprocessed_df
        # remove Not classified or null income levels
        .dropna(subset=["income_level"])
        .loc[lambda d: d.income_level != "Not classified"]
        # group by year and income level and get median value
        .groupby(["year", "income_level"])
        .agg({"value": "median"})
        .reset_index()
    )


def export_data_downloadable(preprocessed_df, medians_df) -> None:
    """Export data for download as csv"""

    (
        pd.concat(
            [
                medians_df.assign(entity_name=lambda d: d.income_level + " (median)"),
                preprocessed_df.rename(columns={"country_name": "entity_name"}),
            ],
            ignore_index=True,
        )
        .loc[:, ["entity_name", "iso3_code", "year", "value", "income_level"]]
        .assign(
            indicator_name="Out-of-pocket health expenditure (% of current health expenditure)"
        )
        .to_csv(Paths.output / "story_3" / "chart_1_data.csv", index=False)
    )


def export_chart(preprocessed_df, medians_df) -> None:
    """Export chart data as csv"""

    (
        pd.concat(
            [
                medians_df.assign(
                    entity_name=lambda d: d.income_level + " (median)"
                ).assign(annotate_color=True),
                preprocessed_df.rename(columns={"country_name": "entity_name"}).assign(
                    annotate_gray=True
                ),
            ],
            ignore_index=True,
        )
        .dropna(subset=["income_level"])
        .loc[lambda d: d.income_level != "Not classified"]
        .pivot(
            index=["year", "income_level", "annotate_color", "annotate_gray"],
            columns="entity_name",
            values="value",
        )
        .loc[
            :,
            lambda d: [
                "Low income (median)",
                "Lower middle income (median)",
                "Upper middle income (median)",
                "High income (median)",
            ]
            + [
                c
                for c in d.columns
                if c
                not in [
                    "Low income (median)",
                    "Lower middle income (median)",
                    "Upper middle income (median)",
                    "High income (median)",
                ]
            ],
        ]
        .reset_index()
        # sort income level starting with Low income and ending with High income
        .assign(
            income_level=lambda d: pd.Categorical(
                d["income_level"],
                categories=[
                    "Low income",
                    "Lower middle income",
                    "Upper middle income",
                    "High income",
                ],
                ordered=True,
            )
        )
        .sort_values(["income_level", "year"])
        .to_csv(Paths.output / "story_3" / "chart_1.csv", index=False)
    )


def calculations_hf3_reliance() -> dict:
    """Calculations of reliance on OOP used in story 3 text
    1. # of countries where OOP is the primary health financing mechanism (hf3_che highest among hf1, hf2, hf3, hf4, hfnec)
    2. # of countries where OOP > 50% of current health expenditure (hf3_che > 50)
    3. List of African countries where OOP > 67% of current health expenditure
    """

    hf_vars = ["hf1_che", "hf2_che", "hf3_che", "hf4_che", "hfnec_che"]
    calc_dict = {}

    df = (
        GHED_DATA.loc[lambda d: d.indicator_code.isin(hf_vars)]
        .loc[lambda d: d.year == 2022]
        .sort_values(["country_name", "value"], ascending=[True, False])
        .drop_duplicates(subset=["country_name"], keep="first")
        .loc[lambda d: d.indicator_code == "hf3_che"]
    )

    calc_dict["oop_primary_mechanism"] = len(df)
    calc_dict["oop_gt_50"] = len(df.loc[lambda d: d.value > 50])
    calc_dict["oop_afr_gt_67"] = list(
        places.filter_african_countries(df.loc[lambda d: d.value >= 67].country_name)
    )

    return calc_dict


def chart_1():
    """Chart 1 showing out-of-pocket health spending by income group (2000-2022), and income group medians"""

    preprocessed_df = preprocess_data()
    medians_df = agg_income_group_medians(preprocessed_df)

    export_data_downloadable(preprocessed_df, medians_df)
    export_chart(preprocessed_df, medians_df)

    logger.info("Chart 1 complete")


if __name__ == "__main__":

    logger.info("Creating charts for Story 3...")
    chart_1()
    logger.info("Story 3 complete.")
