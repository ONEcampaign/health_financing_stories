"""Curative vs preventative care"""


import pandas as pd
import numpy as np
from bblocks import places
import statsmodels.api as sm

from scripts.common import read_ghed_data
from scripts.config import Paths
from scripts.logger import logger

GHED_DATA = read_ghed_data()


chart_1_indicators = {"hc1": "hc1_che","hc6": "hc6_che"}

gdp_var = "gdp_usd2022_pc"


def loess_smooth(df, endog, exog , frac=0.5) -> pd.Series:
    """Applies LOESS smoothing to a DataFrame column."""

    s = pd.Series(
            sm.nonparametric.lowess(
                endog=endog,
                exog=exog,
                frac=frac,
                return_sorted=False
            ),
            index=df.index
        )

    return s


def prepare_chart1_data():
    """Prepare data for curative vs preventative care chart."""

    return (GHED_DATA

 .loc[lambda d: d.indicator_code.isin(list(chart_1_indicators.values()) + [gdp_var])]
 .dropna(subset=["value"])
 .loc[lambda d: (d.year >= 2018) & (d.year < 2023)]
 .pivot(index=['country_name', "iso3_code", "year"], columns="indicator_code", values="value")
 .reset_index()
 .dropna(subset=list(chart_1_indicators.values()))
 .sort_values(["country_name", "year"])
 .groupby(["country_name", "iso3_code"]).tail(1)
.sort_values(by=gdp_var) # sort by gdp per capita to have a meaningful loess smoothing
 .reset_index(drop=True)
#       apply loess smoothing
      .assign(
    hc1_che_loess=lambda d: loess_smooth(d, endog=d[chart_1_indicators["hc1"]], exog=d[gdp_var]),
    hc6_che_loess=lambda d: loess_smooth(d, endog=d[chart_1_indicators["hc6"]], exog=d[gdp_var])
    )

    .melt(id_vars=["country_name", "iso3_code", gdp_var, "year"])


)

def chart1():
    """Generate download and chart data for chart 1"""

    df = prepare_chart1_data()



    # download data
    (df.pivot(index=["country_name", "iso3_code", gdp_var, "year"],
              columns="indicator_code",
              values="value"
              ).reset_index()

    .loc[:, ["country_name", "iso3_code", gdp_var, "hc1_che", "hc6_che", "year"]]
    .rename(columns={
        "hc1_che": "Curative care (% of current health expenditure)",
        "hc6_che": "Preventive care (% of current health expenditure)",
        gdp_var: "GDP per capita (USD, 2022)",
        "country_name": "Country",
        "iso3_code": "ISO3 Code"
    })
        .to_csv(Paths.output / "story_4" / "chart_1_data.csv", index=False)

    )

    # chart data
    (df
     .assign(connet=lambda d: d.indicator_code.map({
        "hc1_che_loess": "hc1_loess",
        "hc6_che_loess": "hc6_loess"
    }))
     # color column where indicator code starts with hc1 or hc6
     .assign(color=lambda d: np.where(d.indicator_code.str.startswith("hc1"), "hc1", "hc6"))

     # size 0 where indicator code ends with loess and 1 otherwise
     .assign(size=lambda d: np.where(d.indicator_code.str.endswith("loess"), 0, 1))

     # popup True where connect is false
     .assign(popup=lambda d: np.where(d.connet.isnull(), True, None))

     .assign(indicator_name=lambda d: d.indicator_code.map({
        "hc1_che": "Curative care",
        "hc6_che": "Preventive care",
        "hc1_che_loess": "Curative care (loess smoothed)",
        "hc6_che_loess": "Preventive care (loess smoothed)"
    }))

     .to_csv(Paths.output / "story_4" / "chart_1.csv", index=False)

     )

    logger.info("Chart 1 data generated")



chart_2_indicators = {"gghed": "hc6_gghed_che",
              "ext": "hc6_ext_che",
              }


def prepare_chart2_data():
    """ """

    return (GHED_DATA

          .loc[lambda d: d.indicator_code.isin(list(chart_2_indicators.values()) + [gdp_var])]
          .dropna(subset=["value"])
          .loc[lambda d: (d.year >= 2018) & (d.year < 2023)]
          .pivot(index=['country_name', "iso3_code", "year"], columns="indicator_code", values="value")

          .dropna(subset=list(chart_2_indicators.values()))
          .reset_index()
          .sort_values(["country_name", "year"])
          .groupby(["country_name", "iso3_code"]).tail(1)

          .sort_values(by=gdp_var)
          .reset_index(drop=True)
          #       apply loess smoothing
          .assign(
        hc6_gghed_loess=lambda d: loess_smooth(d, endog=d[chart_2_indicators["gghed"]], exog=d[gdp_var]),
        hc6_ext_loess=lambda d: loess_smooth(d, endog=d[chart_2_indicators["ext"]], exog=d[gdp_var])
    )
          # .loc[:, ["country_name", "iso3_code", gdp_var, "year", "gghed_loess", "ext_loess", "gghed_share", "ext_share"]]
          .melt(id_vars=["country_name", "iso3_code", gdp_var, "year"])

          )


def chart2():
    """ """

    df = prepare_chart2_data()

    # download data
    (df.pivot(index=["country_name", "iso3_code", gdp_var, "year"],
              columns="indicator_code",
              values="value"
              ).reset_index()
     .loc[:, ["country_name", "iso3_code", gdp_var, "hc6_ext_che", "hc6_gghed_che", "year"]]
     .rename(columns={
        "hc6_ext_che": "External expenditure on preventive care (% of current health expenditure)",
        "hc6_gghed_che": "Domestic government expenditure on preventive care (% of current health expenditure)",
        gdp_var: "GDP per capita (USD, 2022)",
        "country_name": "Country",
        "iso3_code": "ISO3 Code"
    })
     .to_csv(Paths.output / "story_4" / "chart_2_data.csv", index=False)
     )




    (df
     .assign(connet=lambda d: d.indicator_code.map({
        "hc6_gghed_loess": "hc6_gghed_loess",
        "hc6_ext_loess": "hc6_ext_loess"
    }))
     .assign(color=lambda d: np.where(d.indicator_code.str.startswith("hc6_ext"), "ext", "gghed"))
     .assign(size=lambda d: np.where(d.indicator_code.str.endswith("loess"), 0, 1))
     .assign(popup=lambda d: np.where(d.connet.isnull(), True, None))

    .assign(indicator_name = lambda d: d.indicator_code.map({
        "hc6_gghed_che": "Domestic government expenditure on preventive care",
        "hc6_ext_che": "External expenditure on preventive care",
        "hc6_gghed_loess": "Domestic government expenditure on preventive care (loess smoothed)",
        "hc6_ext_loess": "External expenditure on preventive care (loess smoothed)"
    }))

     .to_csv(Paths.output / "story_4" / "chart_2.csv", index=False)
     )

    logger.info("Chart 2 data generated")


if __name__ == "__main__":
    chart1()
    chart2()