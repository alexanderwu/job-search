import streamlit as st

import job_search.jobs as jobs

@st.cache_data
def load_data():
    return jobs