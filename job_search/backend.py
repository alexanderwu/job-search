from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import job_search.company as com
from job_search.config import P_ROOT

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": f"{P_ROOT}"}

@app.get("/{hash}")
async def read_job(hash):
    next_data_dict = com.viewhash(hash)
    next_data_job = next_data_dict['props']['pageProps']['job']
    return next_data_job

@app.get("/viewjob/{hash}", response_class=HTMLResponse)
async def read_hash(hash):
    next_data_dict = com.viewhash(hash)
    next_data_job = next_data_dict['props']['pageProps']['job']
    html_content = next_data_job['job_information']['description']
    return html_content
