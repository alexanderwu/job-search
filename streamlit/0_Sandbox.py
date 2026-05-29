# ruff: noqa: F401
import numpy as np
import pandas as pd
import streamlit as st

from utils import load_data

data = load_data(st.session_state.dataset)
search = st.text_input("Search", key="mask")
_hash = st.selectbox("Hash", ["", *data['_hash']], key="hash")

map_data = pd.DataFrame(
    np.random.randn(1000, 2) / [50, 50] + [37.76, -122.4],
    columns=['lat', 'lon'])

st.map(map_data)
