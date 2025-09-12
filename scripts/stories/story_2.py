"""Story 2: Health priority and government spending on health"""

import pandas as pd
from bblocks import places
from pydeflate import imf_gdp_deflate, set_pydeflate_path

from scripts.config import Paths
from scripts.logger import logger
from scripts.common import read_ghed_data

GHED_DATA = read_ghed_data()
set_pydeflate_path(Paths.raw_data)


def chart_1():
    """bubble chart"""

    return (GHED_DATA
     .loc[lambda d: (d.year == 2022)]
     .loc[lambda d: d.indicator_code.isin(["gghed_gdp", "pop", "gghed_ncu_pc"])]
     .pivot(index=["country_name", "iso3_code", "year"],
            columns="indicator_code", values="value")
     .reset_index()
     .pipe(imf_gdp_deflate,
           base_year=2015,
           source_currency="LCU",
           target_currency="USA",
           id_column="iso3_code",
           value_column="gghed_ncu_pc",
           target_value_column="gghed_usd2015"

           )
     .drop(columns=["gghed_ncu_pc"])
     .dropna(subset=["gghed_gdp", "pop", "gghed_usd2015"])
     .assign(income_level=lambda d: places.resolve_places(d.iso3_code, to_type="income_level", from_type="iso3_code",
                                                          not_found="ignore"),
             region=lambda d: places.resolve_places(d.iso3_code, to_type="region", from_type="iso3_code",
                                                    not_found="ignore")
             )
     .dropna(subset=["income_level", "region"])


     )



countries = ['Benin',
 'Cabo Verde',
 'Cameroon',
 'Congo',
 'Equatorial Guinea',
 'Eritrea',
 'Liberia',
 'Madagascar',
 'Namibia',
 'Sao Tome and Principe',
 'South Africa',
 'South Sudan',
 'Zimbabwe',
 'Sudan']


afr_ghed = (df
 .loc[lambda d: d.indicator_code.isin(["gghed_gge"])]
    # .assign(region = lambda d: places.resolve_places(d.iso3_code, to_type="region", from_type="iso3_code", not_found="ignore"))
 .loc[lambda d: d.country_name.isin(countries)]
    .pivot(index=["year"], columns="country_name", values="value")
.reset_index()
 # .to_clipboard(index=False)



)


(df
 .loc[lambda d: d.indicator_code.isin(["gghed_gge"])]
.assign(region = lambda d: places.resolve_places(d.iso3_code, to_type="region", from_type="iso3_code", not_found="ignore"))
 .loc[lambda d: d.region =="Africa"]

    .groupby("year")
    .agg({"value": "median"})
 .rename(columns={"value": "Africa (median)"})
 .reset_index()

 .merge(afr_ghed, how="right")


 .to_clipboard(index=False)
 )


