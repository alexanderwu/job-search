# ruff: noqa: F401
import aw
import streamlit as st

import job_search.jobs as jb
import utils as ut
from utils import DS_SF, HEALTH, load_data

jobs_mar = load_data().query('mar')
ds_mar = load_data(DS_SF).query('mar')
health_mar = load_data(HEALTH).query('mar')

aw_df = aw.combo_sizes([set(ds_mar['_hash']), set(jobs_mar['_hash'])],
    ['DS_DF (March)', 'Jobs (March)'])
# st.dataframe(aw_df)
st.table(aw_df, width='content')

_hash = "pgy4ysq31yrbcuzp"
job_df = load_data()
job_md = jb.hash2md(_hash, job_df)
