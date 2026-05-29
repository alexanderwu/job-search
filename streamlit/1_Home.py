# ruff: noqa: F401
import streamlit as st

import job_search.jobs as jb
import utils as ut
from utils import COLS, N, load_data, write

RWD_MASK = "rwd|real.?world data"
QUERY_MASK = "mar"

if "dataset" not in st.session_state:
    st.session_state.dataset = ut.HEALTH
if "mask" not in st.session_state:
    st.session_state.mask = RWD_MASK
if "query" not in st.session_state:
    st.session_state.query = QUERY_MASK
if "cols" not in st.session_state:
    st.session_state.cols = COLS
if "show" not in st.session_state:
    st.session_state.show = False

with ut.horizontal():
    if st.button("Reset"):
        st.session_state.mask = RWD_MASK
        st.session_state.query = QUERY_MASK
    if st.button("Clear"):
        st.session_state.mask = ""
        st.session_state.query = ""
        st.session_state.hash = ""

data = load_data(st.session_state.dataset)
with ut.horizontal():
    search = st.text_input("Search", key="mask")
    query = st.text_input("Query", key="query")
    try:
        data = data.query(query)
    except ValueError:
        pass
    mask = jb.cmask(search, jobs_df=data)
    data_masked = data[mask].sort_values('estimated_publish_date', ascending=False)
    # _hash = st.selectbox("Hash", ["", *data['_hash']], key="hash")
    _hash = st.selectbox(f"Hash {N(data_masked)}", ["", *data_masked['_hash']], key="hash")
    data_hashed = data.query('_hash==@_hash')

with ut.horizontal():
    if any(mask):
        ii = st.number_input("Job #", min_value=1, max_value=mask.sum(), key='job_num', width=121) - 1
    write(ut.perc(mask))

if _hash:
    ut.disp(data_hashed)
else:
    ut.disp(data, mask, ii)


st.checkbox(f'Show dataframe {N(int(bool(_hash)) or len(data_masked))}', key='show')
if st.session_state.show:
    with ut.horizontal():
        if st.button("Reset Columns"):
            st.session_state.cols = COLS
        if st.button("Scenario 1"):
            SCENARIO_COLS = [
                "position",
                "estimated_publish_date"
            ]
            st.session_state.cols = SCENARIO_COLS
        if st.button("ALL"):
            st.session_state.cols = list(data.drop(columns=['_md', 'description']).columns)
            # st.session_state.cols = list(data.columns)
    with st.expander(f"Columns {N(st.session_state.cols)}"):
        cols = st.multiselect("", options=data.columns, key="cols")
    if _hash:
        row = data_hashed[cols].T#.style.format(lambda x: x, na_rep="")
        st.table(row, border=False, hide_header=True)
        # st.dataframe(row)
    else:
        st.dataframe(data_masked[cols].reset_index(drop=True))
