"""Curative vs preventative care"""


import pandas as pd
import numpy as np
from bblocks import places
import statsmodels.api as sm

from scripts.common import read_ghed_data

GHED_DATA = read_ghed_data()


indicators = {"hc1": "hc1_che",
              "hc6": "hc6_che",
              "gdp": "gdp_usd2022_pc"
              }


def loess_smooth(df, x_col, y_col, frac=0.5):
    """Apply LOESS smoothing and return smoothed values."""
    smoothed = sm.nonparametric.lowess(df[y_col], df[x_col], frac=frac)
    return pd.DataFrame(smoothed, columns=[x_col, f"{y_col}_smoothed"])


df = (GHED_DATA

 .loc[lambda d: d.indicator_code.isin(indicators.values())]
 .dropna(subset=["value"])
 .loc[lambda d: (d.year >= 2018) & (d.year < 2023)]
 .pivot(index=['country_name', "iso3_code", "year"], columns="indicator_code", values="value")
 .reset_index()
 .dropna(subset=list(indicators.values()))
 .sort_values(["country_name", "year"])
 .groupby(["country_name", "iso3_code"]).tail(1)
 .drop(columns = ["year"])
 .sort_values(by="gdp_usd2022_pc")

 .assign(
        hc1_che_loess=lambda d: pd.Series(
            sm.nonparametric.lowess(
                endog=d[indicators["hc1"]],
                exog=d["gdp_usd2022_pc"],
                frac=0.5,
                return_sorted=False
            ),
            index=d.index
        ),
    hc6_che_loess=lambda d: pd.Series(
            sm.nonparametric.lowess(
                endog=d[indicators["hc6"]],
                exog=d["gdp_usd2022_pc"],
                frac=0.5,
                return_sorted=False
            ),
            index=d.index
        )
)


 )


(df.melt(id_vars=["country_name", "iso3_code", "gdp_usd2022_pc"], value_vars=["hc1_che_loess", "hc6_che_loess", indicators["hc6"], indicators["hc1"]])
 .assign(connect = lambda d: np.where(d.indicator_code=="hc1_che_loess", "hc1_loess", np.where(d.indicator_code=="hc6_che_loess", "hc6_loess", None)))
 .assign(size = lambda d: np.where(d.indicator_code=="hc1_che_loess", 0, np.where(d.indicator_code=="hc6_che_loess", 0, 1)))
.assign(color = lambda d: np.where(d.indicator_code.str.contains("hc1"), "hc1", "hc6"))



 # .sort_values("indicator_code", ascending=False)

 # .head().to_clipboard(index=False)
.to_clipboard(index=False)
 )