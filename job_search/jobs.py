from functools import cache, reduce
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
        # 'company_activities',
        'health', 'norcal'
        ]
MASK_COLS = ['company_name', 'title', '_hash', 'requirements_summary', 'technical_tools',
             'role_activities', 'job_category', 'seniority_level', 'workplace_type',
             'formatted_workplace_location', 'company_tagline', '_md']


@cache
def load_jobs(clean=True, overwrite=False) -> pd.DataFrame:
    P_parquet = P_CACHE / 'jobs_df.parquet'
    if overwrite or not P_parquet.exists():
        with duckdb.connect("../jobs.duckdb") as con:
            jobs_df = con.table("jobs").df()

        jobs_df['_md'] = jobs_df['description'].map(md)
        jobs_df['_url'] = VIEW_JOB_HTTPS + jobs_df['requisition_id']
        jobs_df['_hash'] = jobs_df['requisition_id']

        P_parquet.parent.mkdir(exist_ok=True)
        jobs_df.to_parquet(P_parquet)
        print('Saving:', P_parquet)
    else:
        jobs_df = pd.read_parquet(P_parquet)

    if clean:
        jobs_df = jobs_df.dropna(how='all')
        # jobs_df['estimated_publish_date'] = jobs_df['estimated_publish_date'].dt.tz_localize('UTC')
        sf_remote_mask = jobs_df['formatted_workplace_location'].str.contains('San Francisco|San Jose', case=False)
        jobs_df['norcal'] = _norcal_mask(jobs_df) | sf_remote_mask
        jobs_df['health'] = cmask(['health', 'medical', 'biotech'], col='company_activities')
        jobs_df['jan'] = jobs_df['estimated_publish_date'] >= "2026-01-01"
        jobs_df['feb'] = jobs_df['estimated_publish_date'] >= "2026-02-01"
        jobs_df['position'] = (
            (jobs_df["company_name"].fillna('') + " - " + jobs_df["title"])
            .str.replace(r"[/|:\\*?]", "_", regex=True)
            .str.replace('"', "'")
            .str.replace("’", "'")
            .str.replace(r" +", " ", regex=True)
            .str.strip()
        )

    return jobs_df

def _norcal_mask(df_lon_lats):
    assert 'location_latitudes' in df_lon_lats and 'location_longitudes' in df_lon_lats
    df_lon_lats = df_lon_lats.reset_index(drop=True)
    lon_lats = df_lon_lats.explode(['location_latitudes', 'location_longitudes'])[['location_latitudes', 'location_longitudes']].reset_index()
    ## https://en.wikipedia.org/wiki/Module:Location_map/data/San_Francisco_Bay_Area
    # BOTTOM_LAT, TOP_LAT = 37.1897, 38.2033
    # LEFT_LON, RIGHT_LON = -122.6445, -121.5871
    BOTTOM_LAT, TOP_LAT = 37, 39
    LEFT_LON, RIGHT_LON = -123, -121
    lat_mask = (BOTTOM_LAT <= lon_lats['location_latitudes']) & (lon_lats['location_latitudes'] <= TOP_LAT)
    lon_mask = (LEFT_LON <= lon_lats['location_longitudes']) & (lon_lats['location_longitudes'] <= RIGHT_LON)
    job_df_bay_area_indices = lon_lats[lat_mask & lon_mask]['index'].drop_duplicates()
    norcal_mask = pd.Series(True, index=job_df_bay_area_indices).reindex(index=df_lon_lats.index, fill_value=False)
    return norcal_mask

@cache
def load_jobs2026(clean=True, overwrite=False) -> pd.DataFrame:
    jobs_df = load_jobs(clean, overwrite)
    jobs2026 = (jobs_df.query('estimated_publish_date >= "2026-01-01"')
        .sort_values('estimated_publish_date', ascending=False)
        .reset_index(drop=True))[COLS]
    jobs2026['estimated_publish_date'] = jobs2026['estimated_publish_date'].dt.tz_localize('UTC')
    return jobs2026

@cache
def load_jobs_feb(clean=True, overwrite=False) -> pd.DataFrame:
    jobs_df = load_jobs(clean, overwrite)
    jobs_feb = (jobs_df.query('estimated_publish_date >= "2026-02-01"')
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
        query_jdf = pd.concat(_dfs, ignore_index=True)
        query_jdf.to_parquet(P_parquet)
        print('Saving:', P_parquet)
        return query_jdf
    query_jdf = pd.read_parquet(P_parquet).drop_duplicates(**kwargs)
    return query_jdf


################################################################################

HASH = "lt3eeomecenp5t50"

def display_text_mask(keywords, job_ii=1, job_df=None, llm=False):
    if job_df is None:
        job_df = load_jobs()
    _mask = text_mask(keywords, job_df=job_df)
    ii = job_ii - 1
    display(perc(_mask))
    if any(_mask):
        _mask_df = job_df[_mask]
        _mask_hash = _mask_df['_hash'].iloc[ii]
        print(f'{job_ii} of {_mask.sum()}: ' + VIEW_JOB_HTTPS + _mask_hash)

        display_job(_mask_hash, job_df=job_df, llm=llm)
    else:
        print(f'No match for: {keywords}')

def disp(jobs_df=None, mask=None, ii=0, llm=False, **kwargs):
    if jobs_df is None:
        jobs_df = load_jobs()
    if mask is None:
        mask = pd.Series(True, index=jobs_df.index)
    if not isinstance(mask, pd.Series):
        mask = cmask(mask, **kwargs)

    if len(jobs_df) == 0 or mask.sum() == 0:
        return print('No match')

    ii = ii % jobs_df.shape[0]
    job_ii = ii + 1
    mask = mask.reindex(jobs_df.index)
    display(perc(mask))
    if any(mask):
        mask_df = jobs_df[mask]
        mask_hash = mask_df['_hash'].iloc[ii]
        print(f'{job_ii} of {mask.sum()}: ' + VIEW_JOB_HTTPS + mask_hash)

        display_job(mask_hash, job_df=jobs_df, llm=llm)
    else:
        print('No match')

def display_cmask(keywords, job_ii=1, llm=False):
    job_df = load_jobs()
    _mask = cmask(keywords)
    if len(job_df) == 0:
        return print('No match')
    ii = (job_ii - 1) % job_df
    display(perc(_mask))
    if any(_mask):
        _mask_df = job_df[_mask]
        _mask_hash = _mask_df['_hash'].iloc[ii]
        print(f'{job_ii} of {_mask.sum()}: ' + VIEW_JOB_HTTPS + _mask_hash)

        display_job(_mask_hash, job_df=job_df, llm=llm)
    else:
        print(f'No match for: {keywords}')

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
    jobs_df = load_jobs()
    _row = jobs_df.query(f'requisition_id == "{_hash}"')
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
    _jobs_df = load_jobs()
    _md = _jobs_df.query('requisition_id==@hash')['_md'].iloc[0]
    if verbose:
        return print(_md)
    return _md

# @cache
def _load_text(job_df=None) -> pd.Series:
    if job_df is None:
        job_df = load_jobs()
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

def text_mask(phrase, job_df=None, regex=False, verbose=False, **kwargs):
    """General search with regex"""
    pd_series = _load_text(job_df)
    return rmask(phrase, pd_series, regex, verbose, **kwargs)

def rmask(phrase, pd_series=None, regex=False, verbose=False, **kwargs):
    """Regex search"""
    if pd_series is None:
        pd_series = load_jobs()['_md']
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
    """Mask on technical tools"""
    if pd_series is None:
        pd_series = load_jobs()['technical_tools']
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
        pd_df = load_jobs()
    _mask = text_mask(phrase, job_df=pd_df, regex=False)
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

################################################################################
# Company Activities
################################################################################

# COL = 'company_activities'
COL = '_md'

@cache
def _cmask(keywords, contains=True, case=None, col=COL):
    if not isinstance(keywords, (list, tuple)):
        keywords = [keywords]
    jobs_df = load_jobs(clean=False)

    regex = r'\b' + r"|\b".join(keywords)
    if case is None:
        case = (regex != regex.lower())
    if not case:
        keywords = tuple(k.lower() for k in keywords)

    def _set_match(x_list, case):
        x_set = set([x.lower() for x in x_list]) if case else set(x_list)
        return bool(set(keywords) & x_set)

    jobs_df_col = jobs_df[col].apply(lambda x: [x] if isinstance(x, str) else x)
    if contains:
        mask = jobs_df_col.str.join('; ').str.contains(regex, case=case, na=False)
    else:
        mask = jobs_df_col.apply(_set_match, case=case)
    return mask

def _chashes(keywords, contains=True, case=False, col=COL):
    mask = _cmask(keywords, contains, case, col)
    jobs_df = load_jobs(clean=False)
    hashes = jobs_df[mask]['_hash'].pipe(set)
    return hashes

def cmask(keywords, contains=True, case=False, col=MASK_COLS):
    if isinstance(col, (list, tuple)):
        masks_list = [cmask(keywords, contains, case, c) for c in col]
        mask = reduce(lambda x, y: x|y, masks_list)
        return mask
    if not isinstance(keywords, (list, tuple)):
        keywords = [keywords]
    keywords = tuple(keywords)
    mask = _cmask(keywords, contains, case, col)
    return mask

def chashes(keywords, contains=True, case=False, jobs_df=None, col=MASK_COLS):
    if not isinstance(keywords, (list, tuple)):
        keywords = [keywords]
    keywords = tuple(keywords)
    hashes = _chashes(keywords, contains, case, col)

    if jobs_df is not None:
        jobs_df = load_jobs()
        hashes = hashes & set(jobs_df['_hash'])
    return hashes
