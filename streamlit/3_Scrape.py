# ruff: noqa: F401
import time

import streamlit as st

import job_search.scrape as sc
from job_search.scrape import DS_SF, HEALTH, P_interim_date

'Starting a long computation...'

# Add a placeholder
latest_iteration = st.empty()
bar = st.progress(0)

if st.button("Click to start"):
    for i in range(100):
        # Update the progress bar with each iteration.
        latest_iteration.text(f'Iteration {i+1}')
        bar.progress(i + 1)
        time.sleep(0.1)

    '...and now we\'re done!'

(board:=HEALTH, overwrite:=False, verbose:=True)
## health_boards_list = sc.load_boards(sc.HEALTH, verbose=True)
page = 0
## jobs_dict_list = [jobs_dict := sc.load_board(board, overwrite, verbose, page)]
################################################################################
## sc.load_board(board=HEALTH, overwrite=False, verbose=True, page=0)
assert isinstance(page, int) and page >= 0
P_jobs_json = P_interim_date / f'{board}/page{page}.json.gz'
board_url = f'{sc.HIRING_CAFE}/{sc._NEXT_PREFIX}/b/{board}.json'
url = f'{board_url}?page={page}'
url
# job_title_json = sc.requests_get(url)
# job_tritle_json
# st.code(job_title_json, language="json")