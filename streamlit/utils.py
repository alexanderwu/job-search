# ruff: noqa: F401, E402
from functools import cache
from pathlib import Path
import re
from textwrap import dedent
from zoneinfo import ZoneInfo

from aw import str_round
import lmstudio as lms
import markdown
import pandas as pd
import streamlit as st

import job_search.jobs as jb
from job_search.jobs import cmask, load_jobs, load_jobs2026, perc
from job_search.scrape import DA_HEALTH, DA_SF, DS_SF, HEALTH

ALL_DB = 'ALL.duckdb'
TZ_LA = ZoneInfo("America/Los_Angeles")
COLS = [
    'company_name',
    'title',
    'estimated_publish_date',
    'formatted_workplace_location',
    'yearly_min_compensation',
    'yearly_max_compensation',
    'listed_compensation_frequency',
    'workplace_type',
    'commitment',
    'requirements_summary',
    'min_industry_role_yoe',
    'company_tagline',
    'technical_tools',
    'requisition_id',
]
PROMPT_7 = "Summarize top seven job requirements (domain area, expertise, soft skills) and top seven nice-to-haves. Ignore details of location, compensation, travel, benefits. Format as concise bullet points:"

@st.cache_data
def load_data(dataset=ALL_DB):
    df = load_jobs(dataset)
    # df = load_jobs2026(dataset).drop(columns='description')
    # df = load_jobs2026(dataset)
    return df

def disp(jobs_df=ALL_DB, mask=None, ii=0, llm=False, **kwargs):
    jobs_df = load_jobs(jobs_df)
    if mask is None:
        mask = pd.Series(True, index=jobs_df.index)
    if not isinstance(mask, pd.Series):
        mask = cmask(mask, jobs_df=jobs_df, **kwargs)

    if len(jobs_df) == 0 or mask.sum() == 0:
        return write('No match')

    ii = ii % jobs_df.shape[0]
    job_ii = ii + 1
    mask = mask.reindex(jobs_df.index)
    if any(mask):
        mask_df = jobs_df[mask].sort_values("estimated_publish_date", ascending=False).reset_index(drop=True)
        mask_hash = mask_df['_hash'].iloc[ii]
        # write(f'{job_ii} of {mask.sum()}: ' + jb.VIEW_JOB_HTTPS + mask_hash)
        write(f'{job_ii} of {mask.sum()}: ' + jb.JOB_HTTPS + mask_hash)

        display_job(mask_hash, job_df=jobs_df, llm=llm)
    else:
        write('No match')

def strftime(date):
    import platform
    P = '#' if platform.system() == "Windows" else '-'
    # date_str = date.strftime(rf"%{P}m-%{P}d-%y (%A)")
    date_str = date.strftime(rf"%b %{P}d, %Y (%A)")
    return date_str

def date_ago(date, prefix="Posted ", badge=True):
    from datetime import datetime
    import platform
    date_str = strftime(date)
    try:
        ago = datetime.now() - date
    except TypeError:
        ago = datetime.now(TZ_LA) - date
    ago_str = f"{prefix}{ago.days}d ago"
    if ago.days < 1:
        ago_str = f"{prefix}{ago.seconds // 3600}hr ago"
    # date_str = f"{ago_str} ({date_str})"
    date_str = f"{ago_str} -- {date_str}"
    if badge:
        date_str = f":violet[:small[{date_str}]]"
    return date_str

def yoe(min_industry_role_yoe):
    if not min_industry_role_yoe or pd.isnull(min_industry_role_yoe):
        return ""
    return f":violet-badge[{(int(min_industry_role_yoe))}+ YOE]"

def salary_range(yearly_min_compensation, yearly_max_compensation):
    yr_min = yearly_min_compensation or yearly_max_compensation
    yr_max = yearly_max_compensation if yearly_max_compensation != yr_min else None
    if yr_max and not pd.isnull(yr_max):
        salary_range_str = f":grey-badge[\\${int(yr_min // 1000):,}k-\\${int(yr_max // 1000):,}k/yr]"
    elif yr_min and not pd.isnull(yr_min):
        salary_range_str = f":grey-badge[\\${int(yr_min // 1000):,}k/yr]"
    else:
        salary_range_str = ""
    return salary_range_str

def display_job(_hash, job_df=ALL_DB, llm=False):
    job_df = load_jobs(job_df)
    job_md = jb.hash2md(_hash, job_df)
    with st.container(border=True):
        tab1, tab2, tab3 = st.tabs(['Job Info', 'Job Description', 'LLM Summary'])

        with tab1:
            row = job_df.query('_hash == @_hash')[COLS].iloc[0]
            st.markdown(dedent(f'''
                {date_ago(row.estimated_publish_date)}

                ### {row.title}

                @ {row.company_name}

                :material/location_on: {row.formatted_workplace_location}

                {salary_range(row.yearly_min_compensation, row.yearly_max_compensation)}
                :grey-badge[{row.workplace_type}]
                {" ".join([f":grey-badge[{c}]" for c in row.commitment])}
                {yoe(row.min_industry_role_yoe)}

                **Responsibilities:**

                {row.requirements_summary}

                **Technical Tools Mentioned:**

                {" ".join([f":grey-badge[{c}]" for c in row.technical_tools])}

                **Company Tagline:**

                {row.company_tagline}
            '''))
            # write(job_df.query('_hash == @_hash')[COLS].T)
        with tab2:
            display_hash(_hash, job_df)
        with tab3:
            llm_md = ""
            with horizontal():
                if st.button("LLM Summary"):
                    llm_md = llm_extract(job_md, verbose=False)
                if st.button("LLM Summary 2"):
                    PROMPT_SKILL = "What is the #1 problem this team is hiring this role to solve? What 3 skills or experiences would make a candidate stand out vs. just qualify?"
                    llm_md = llm_extract(job_md, PROMPT_SKILL, verbose=False)
            st.markdown(llm_md)


def display_hash(_hash, job_df=ALL_DB, verbose=True):
    jobs_df = load_jobs(job_df)
    _row = jobs_df.query(f'requisition_id == "{_hash}"')
    _md = _row['_md'].iloc[0]
    _technical_tools = _row['technical_tools'].iloc[0]
    _replace_list = [*_technical_tools, 'AI']
    for tool in _replace_list:
        _md = re.sub(rf"\b{tool}\b", f'<span style="color: mediumpurple">{tool}</span>', _md)
    return _display_md(_md, verbose=verbose)

################################################################################

def llm_extract(_md, prompt=PROMPT_7, model="qwen/qwen3-4b-2507", verbose=False):
    _md = load_md(_md)
    _message = f"{prompt}\n\n{_md}"
    return llm_respond(_message, model=model, verbose=verbose)

def load_md(_md, verbose=False):
    if isinstance(_md, Path):
        with open(_md, encoding='utf-8') as f:
            _md = f.read()
    if verbose:
        st.markdown(str(_md))
    else:
        return _md

def llm_respond(_md, model="qwen/qwen3-4b-2507", verbose=True):
    result = _llm_respond(_md)
    if verbose:
        load_md(result, verbose=True)
    else:
        return load_md(result, verbose=False)

@cache
def _llm_respond(message, model="qwen/qwen3-4b-2507"):
    message = load_md(message)
    _model = lms.llm(model)
    result = _model.respond(message)
    return result

################################################################################

def horizontal(*args, **kwargs):
    return st.container(*args, horizontal=True, **kwargs)

def md(text, wrap_lines=True):
    return st.code(text, language='markdown', wrap_lines=wrap_lines)

def N(obj, color="gray", small=True):
    len_obj = obj
    if not isinstance(obj, int):
        len_obj = len(obj)
    N_str = f"(N={len_obj})"
    if color:
        N_str = f":{color}[{N_str}]"
    if small:
        N_str = f":small[{N_str}]"
    return N_str

def _display_md(_md, verbose=True):
    if verbose:
        _html = markdown.markdown(_md)
        _html_centered = f'<div style="font-size:16px;max-width:45rem;margin:0 auto;">{_html}</div>'
        st.html(_html_centered)
        # return display(HTML(_html_centered))
    else:
        st.code(_md)

def write(arg):
    if isinstance(arg, pd.DataFrame):
        arg = arg.style.format(lambda x: str_round(x, 2), na_rep="")
        st.table(arg, width='content', hide_header=False, border='horizontal')
    if isinstance(arg, pd.io.formats.style.Styler):
        arg = arg.format(lambda x: str_round(x, 2), na_rep="")
        st.table(arg, width='content', hide_header=False, border='horizontal')
        # st.dataframe(arg, width='content')
    else:
        st.write(arg)

def display(arg):
    if isinstance(arg, (pd.DataFrame, pd.io.formats.style.Styler)):
        st.table(arg, width='content', hide_header=True, border=False)
    else:
        st.write(arg)
