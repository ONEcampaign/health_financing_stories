"""Story 5 - Voronoi total health spending"""

import pandas as pd
from bblocks import places

from scripts.common import read_ghed_data, add_income_fy22
from scripts.logger import logger
from scripts.config import Paths

GHED_DATA = read_ghed_data()




def prepare_base_data():
    """Prepare data for Voronoi total health spending chart."""

    return (GHED_DATA
            .loc[lambda d: d.indicator_code == "che_usd2023", ["country_name", "iso3_code", "year", "value"]]
            .pipe(add_income_fy22)
            .loc[lambda d: d.year == 2023]
            .dropna(subset=["income_level"])
            .assign(country_name = lambda d: places.resolve_places(d.iso3_code, to_type="name_short", from_type="iso3_code"))
            )


def power_compress(value: float, threshold: int, exp: float =0.75) -> float:
    """Apply a power compression to values below the threshold.

    Values at or above the threshold are returned unchanged. Values below
    are scaled using a power function so that the mapping is continuous
    at the threshold, making smaller values more visible in the chart.

    Args:
        value: The numeric value to transform.
        threshold: Values at or above this level pass through unchanged.
        exp: Exponent for the power compression (0 < exp < 1 compresses).

    Returns:
        The original or compressed value.
    """
    if value >= threshold:
        return value
    else:
        # Scale the compressed value so it's continuous at the threshold
        return threshold * (value / threshold) ** exp


def format_values(value_series: pd.Series, decimals: int = 1) -> pd.Series:
    """Format values based on appropriate scale - e.g., billions, millions, etc."""

    def _fmt(num):
        return f"{num:.{decimals}f}".rstrip("0").rstrip(".")

    def format_value(value):
        if value >= 1e12:
            return f"${_fmt(value / 1e12)} trillion"
        if value >= 1e9:
            return f"${_fmt(value / 1e9)} billion"
        elif value >= 1e6:
            return f"${_fmt(value / 1e6)} million"
        else:
            return f"${_fmt(value)}"

    return value_series.apply(format_value)


def chart_1():
    """Build and export Story 5 Voronoi chart data.

    Saves the full base dataset and a filtered/transformed version
    (countries with spending >= $500M) used for the Voronoi layout.
    """

    df = prepare_base_data()
    df.to_csv(Paths.output / "story_5" / "chart_1_data.csv", index=False)

    (df
     .loc[lambda d: d.value >= 500_000_000]
     .assign(weight=lambda d: d['value'].apply(lambda x: power_compress(x, threshold=10_000_000_000, exp=0.75)))
     .assign(value_annotation=lambda d: format_values(d.value))
     .to_csv(Paths.output / "story_5" / "chart_1_voronoi_data.csv", index=False)
     )

    logger.info("Story 5 chart generated successfully.")

if __name__ == "__main__":
    chart_1()
