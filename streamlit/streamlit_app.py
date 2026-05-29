import streamlit as st

from utils import DA_HEALTH, DA_SF, DS_SF, HEALTH

BOARDS_LIST = ['ALL', DA_HEALTH, DA_SF, DS_SF, HEALTH]


st.set_page_config(layout="wide")
st.sidebar.pills("Dataset", BOARDS_LIST, key="dataset")

pg = st.navigation([
    st.Page("1_Home.py"),
    st.Page("2_Dashboard.py"),
    st.Page("3_Scrape.py"),
    st.Page("4_Resume.py"),
], position="top")
pg.run()