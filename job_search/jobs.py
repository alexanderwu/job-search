from functools import cache
import re

import duckdb
from IPython.display import Markdown, display
from markdownify import markdownify as md
import pandas as pd

from job_search.ai import llm_extract
from job_search.config import DS_HEALTH, DS_NORCAL, P_CACHE, P_PROCESSED, VIEW_JOB_HTTPS
from job_search.dataset import load_jdf

COLS = ['company_name', 'title', 'estimated_publish_date', 'requirements_summary',
        'job_category', 'workplace_type', 'formatted_workplace_location',
        'technical_tools', 'role_activities', 'description',
        'seniority_level', 'company_tagline',
        '_md', '_hash',
        'health', 'norcal']


@cache
def load_jobs(clean=True, overwrite=False) -> pd.DataFrame:
    P_parquet = P_CACHE / 'jobs_df.parquet'
    if overwrite or not P_parquet.exists():
        with duckdb.connect("../jobs.duckdb") as con:
            jobs_df = con.table("jobs").df()

        jobs_df['_md'] = jobs_df['description'].map(md)
        jobs_df['_url'] = VIEW_JOB_HTTPS + jobs_df['requisition_id']
        jobs_df['_hash'] = jobs_df['requisition_id']

        if clean:
            # jobs_df['estimated_publish_date'] = jobs_df['estimated_publish_date'].dt.tz_localize('UTC')
            jobs_df['health'] = jobs_df['_hash'].isin(load_jdf_parquet(DS_HEALTH, overwrite=overwrite)['hash'])
            jobs_df['norcal'] = jobs_df['_hash'].isin(load_jdf_parquet(DS_NORCAL, overwrite=overwrite)['hash'])

        jobs_df.to_parquet(P_parquet)
        print('Saving:', P_parquet)
        return jobs_df

    jobs_df = pd.read_parquet(P_parquet)
    return jobs_df

@cache
def load_jobs2026(clean=True, overwrite=False) -> pd.DataFrame:
    jobs = load_jobs(clean, overwrite)
    jobs2026 = (jobs.query('estimated_publish_date >= "2026-01-01"')
        .sort_values('estimated_publish_date', ascending=False)
        .reset_index(drop=True))[COLS]
    jobs2026['estimated_publish_date'] = jobs2026['estimated_publish_date'].dt.tz_localize('UTC')
    return jobs2026

@cache
def load_jobs_feb(clean=True, overwrite=False) -> pd.DataFrame:
    jobs = load_jobs(clean, overwrite)
    jobs_feb = (jobs.query('estimated_publish_date >= "2026-02-01"')
        .sort_values('estimated_publish_date', ascending=False)
        .reset_index(drop=True))[COLS]
    jobs_feb['estimated_publish_date'] = jobs_feb['estimated_publish_date'].dt.tz_localize('UTC')
    return jobs_feb

@cache
def load_jdf_dict(**kwargs) -> dict[str, pd.DataFrame]:
    jdf_dict = {}
    _query_list = ['ALL', DS_HEALTH, DS_NORCAL]
    qdict = _load_query_dict()
    for _query in _query_list:
        _dfs = [load_jdf(path) for path in qdict[_query]]
        jdf_dict[_query] = pd.concat(_dfs).drop_duplicates(**kwargs).reset_index(drop=True)
    return jdf_dict

@cache
def _load_query_dict() -> dict[str, pd.Series]:
    query_dict = {
        'ALL': pd.Series([path for path in P_PROCESSED.rglob("*.html")]),
        DS_HEALTH: pd.Series([path for path in P_PROCESSED.rglob(f"{DS_HEALTH}.html")]),
        DS_NORCAL: pd.Series([path for path in P_PROCESSED.rglob(f"{DS_NORCAL}.html")]),
    }
    return query_dict

def load_jdf_parquet(query='ALL', overwrite=False, **kwargs):
    P_parquet = P_CACHE / f"{query}.parquet"
    if overwrite or not P_parquet.exists():
        _query_pd_series = _load_query_dict()[query]
        _dfs = [load_jdf(path) for path in _query_pd_series]
        query_jdf = pd.concat(_dfs).drop_duplicates(**kwargs).reset_index(drop=True)
        query_jdf.to_parquet(P_parquet)
        print('Saving:', P_parquet)
        return query_jdf
    query_jdf = pd.read_parquet(P_parquet)
    return query_jdf


################################################################################

HASH = "lt3eeomecenp5t50"

def display_mask(phrase, job_ii=1, job_df=None, llm=False):
    if job_df is None:
        job_df = load_jobs2026()
    _mask = mask(phrase, job_df=job_df)
    ii = job_ii - 1
    display(perc(_mask))
    if any(_mask):
        _mask_df = job_df[_mask]
        _mask_hash = _mask_df['_hash'].iloc[ii]
        print(f'{job_ii} of {_mask.sum()}: ' + VIEW_JOB_HTTPS + _mask_hash)

        display_job(_mask_hash, job_df=job_df, llm=llm)
        # job_md = hash2md(_mask_hash)
        # llm_extract(job_md, verbose=True)
        # display(_mask_df.query('_hash == @_mask_hash').drop(columns=['_md', 'description']).T.style)
        # display_hash(_mask_hash)
    else:
        print(f'No match for: {phrase}')

def display_ai(_hash=HASH, job_df=None):
    return display_job(_hash=HASH, job_df=None, llm=True)

def display_job(_hash=HASH, job_df=None, llm=False):
    if job_df is None:
        job_df = load_jobs()
    job_md = hash2md(_hash)
    if llm:
        llm_extract(job_md, verbose=True)
    display(job_df.query('_hash == @_hash')[COLS].drop(columns=['_md', 'description']).T.style)
    display_hash(_hash)

def display_hash(_hash=HASH, verbose=True):
    jobs = load_jobs()
    _row = jobs.query(f'requisition_id == "{_hash}"')
    _md = _row['_md'].iloc[0]
    _technical_tools = _row['technical_tools'].iloc[0]
    _replace_list = [*_technical_tools, 'AI']
    for tool in _replace_list:
        _md = re.sub(rf"\b{tool}\b", f'<span style="color: rebeccapurple">{tool}</span>', _md)
    return _display_md(_md, verbose=verbose)

def _display_md(_md, verbose=True):
    if verbose:
        _markdown = f'<div style="font-size:16px;max-width:45rem;margin:0 auto;">{str(_md)}</div>'
        return display(Markdown(_markdown))
    print(_md)

def hash2md(hash, verbose=False):
    _jobs = load_jobs()
    _md = _jobs.query('requisition_id==@hash')['_md'].iloc[0]
    if verbose:
        return print(_md)
    return _md

# @cache
def _load_text(job_df=None) -> pd.Series:
    if job_df is None:
        job_df = load_jobs2026()
    pd_series = (job_df['company_name'].fillna('') + ' - ' + job_df['title'] + '.' + job_df['_hash'] + '\n\n'
        + job_df['requirements_summary'] + '\n\n'
        + job_df['technical_tools'].str.join('; ') + '\n'
        + job_df['role_activities'].str.join('; ') + '\n\n'
        # + job_df['job_category'] + '; '
        + job_df['seniority_level'] + '; '
        # + job_df['workplace_type'] + '; '
        # + job_df['formatted_workplace_location'] + '\n\n'
        + job_df['company_tagline'].fillna('...') + '\n\n---\n\n'
        + job_df['_md'])
    return pd_series

def mask(phrase, job_df=None, regex=False, verbose=False, **kwargs):
    pd_series = _load_text(job_df)
    return rmask(phrase, pd_series, regex, verbose, **kwargs)

def rmask(phrase, pd_series=None, regex=False, verbose=False, **kwargs):
    if pd_series is None:
        pd_series = load_jobs2026()['_md']
    lower = phrase == phrase.lower()
    if lower:
        phrase = phrase.lower()
        pd_series = pd_series.str.lower()
    _regex = phrase if regex else rf"\b{phrase}"
    _mask = pd_series.str.contains(_regex)
    if verbose:
        return _mask.pipe(perc, **kwargs)
    return _mask

def tmask(phrase, pd_series=None, regex=False, verbose=False, **kwargs):
    if pd_series is None:
        pd_series = load_jobs2026()['technical_tools']
    lower = phrase == phrase.lower()
    if lower:
        phrase = phrase.lower()
        pd_series = pd_series.apply(lambda x_list: [x.lower() for x in x_list])
    _mask = pd_series.apply(lambda x_list: any(bool(re.match(phrase, x)) for x in x_list))
    if verbose:
        return _mask.pipe(perc, **kwargs)
    return _mask

def hmask(phrase, pd_df=None, regex=False):
    if pd_df is None:
        pd_df = load_jobs2026()
    _mask = mask(phrase, job_df=pd_df, regex=False)
    hash_set = set(pd_df[_mask]['_hash'])
    return hash_set

def perc(pd_series: pd.Series, caption='', display_false=False):
    """Display percentage

    Args:
        pd_series (pd.Series): Input values
        caption (str, optional): Caption. Defaults to ''.
        display_false (bool, optional): Display percentage of False values. Defaults to False.

    Returns:
        pd.DataFrame: Displayed percentage
    """
    # df = pd.value_counts(pd_series).to_frame().T
    df = pd_series.value_counts().to_frame().T
    if True not in df:
        df[True] = 0
    if False not in df:
        df[False] = 0
    df['Total'] = len(pd_series)
    df['%'] = 100*df[True] / df['Total']
    if not display_false:
        df = df.rename(columns={True: 'N'})
        df = df.drop(columns=[False])
    styled_df = (df.style.hide()
            .bar(vmin=0, vmax=100, color='#543b66', subset=['%'])
            .format('{:,.1f}', subset=['%']))
    if caption:
        styled_df = styled_df.set_caption(caption)  # ty:ignore[unresolved-attribute]
    return styled_df