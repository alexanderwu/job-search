#!/usr/bin/env python3
import logging
import random
import re
import time
import urllib
from functools import cache
from functools import reduce
from itertools import chain
from pathlib import Path


import lxml.html
import pandas as pd
import polars as pl
import polars.selectors as cs
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.wordcount import wordcount_plugin
from job_search.utils import now, reload
from job_search.dataset import (_feature_engineering, load_jdf, load_cdf)
from job_search.config import (
    VIEW_JOB_HTTPS,
    P_JOBS,
    P_URLS,
    P_DATA,
    QUERY_LIST,
    P_STEM,
    P_STEM_COMPANY_URLS,
)
from job_search._pl import (reduce_list, pl_remove, pl_reduce_list, pl_enum_min, pl_enum_max, pl_cast_enum, convert_enums)


# Polars
ONSITE_ENUM = pl.Enum(["Remote", "Hybrid", "Onsite"])
FULL_TIME_ENUM = pl.Enum([
    "Contract, Part Time",
    "Contract",
    "Full Time",
    "Contract, Temporary",
    "Contract, Full Time",
    "Full Time, Temporary",
    "Multiple Commitments Available",
])

def load_keywords():
    P_keywords = P_DATA / 'external' / 'keywords.csv'
    keywords_df = pd.read_csv(P_keywords).iloc[1:]
    return keywords_df


@cache
def load_df(P_save: Path | str = P_STEM, polars=True) -> pd.DataFrame:
    P_companies = P_save.parents[3] / f"cache/{P_save.stem}_company_urls"
    jdf = load_jdf(P_save)
    cdf = load_cdf(P_companies)
    df = pd.concat([jdf, cdf]).drop_duplicates('hash')
    if polars:
        df = (pl.from_pandas(df)
            .select(~cs.starts_with("_"))
            .drop(["url2", "mgmt"])
            .with_columns(
                #   c('hours').min().alias('days') // 24,
                pl.col('location').str.split(" or ").pipe(pl_remove, "United States"),
                pl.col('skills').str.split(", "),
                pl.col('full_time').str.split(', ').list.sort().list.join(', ')
            )
        ).pipe(convert_enums, columns=['full_time', 'onsite'])
    return df


@cache
def load_dfc(P_save: Path | str = P_STEM) -> pd.DataFrame:
    df = load_df(P_save)
    dfc = df.group_by('company').agg([
        pl.len(),
        pl.col('title').implode(),
        pl.col('company_summary').first(),
        pl.col('hours').min().alias('days') // 24,
        pl.col('bay').pipe(pl_reduce_list),
        pl.col('location').pipe(pl_reduce_list),
        pl.col('skills').pipe(pl_reduce_list),
        pl.col('onsite').pipe(pl_enum_min, df['onsite'].dtype),
        pl.col('full_time').pipe(pl_enum_max, df['full_time'].dtype),
        pl.col('lower').min(),
        pl.col('median').mean().round(2),
        pl.col('upper').max(),
        # pl.col('url2').n_unique(),
    ])
    return dfc


def viewjob(hash: str) -> str:
    return f'{VIEW_JOB_HTTPS}{hash}'


@cache
def viewhash(hash: str):
    import json
    from os.path import getctime
    P_url = max([p for p in P_URLS.glob(f'*{hash}.html')], key=getctime)
    with open(P_url, encoding='utf-8') as f:
        html_source = f.read()
    root = lxml.html.fromstring(html_source)
    _next_data = root.xpath("//script[@id='__NEXT_DATA__']")[0]
    next_data_dict = json.loads(_next_data.text_content())
    # next_data_job = next_data_dict['props']['pageProps']['job']
    # return next_data_job
    return next_data_dict


def word_count(path_md: Path | str):
    md = MarkdownIt('commonmark', {'breaks': True, 'html': True}).use(wordcount_plugin)
    env = {}
    with open(path_md) as f:
        md_text = f.read()
    _ = md.render(md_text, env)
    return env


def analyze(path_md: Path | str, explode=True) -> pd.DataFrame:
    """
    Returns:
        mdf (pd.DataFrame): markdown dataframe representation
    """
    md_ = MarkdownIt('commonmark', {'breaks': True, 'html': True}).use(front_matter_plugin)
    with open(path_md) as f:
        md_text = f.read()

    tokens = md_.parse(md_text)

    tdf = pd.DataFrame(tokens)
    tdf = tdf.loc[:,tdf.astype(str).nunique() > 1]
    tdf['_begin'] = tdf['map'].ffill().str[0]

    mdf = tdf.groupby('_begin').agg(
        _len=('_begin', len),  # pl.len(),
        _tag=('tag', 'last'),  # pl.col('tag').last(),
        markup=('markup', 'first'),  # pl.col('markup').first(),
        content=('content', ''.join),  # pl.col('content').implode().list.join(''),
    ).reset_index()
    # mdf['_tag'] = mdf['_tag'] + (mdf['_tag'] == mdf['_tag'].shift(-1)).map({True: '_', False: ''})
    mdf['_ul_next'] = mdf['_tag'].shift(-1).isin(['ul', 'li'])

    _md_suffix_newline = mdf['_tag'].isin(['li']).map({False: '\n', True: ''})
    _markdown_line = (mdf['markup'] + ' ' + mdf['content']).str.lstrip() + _md_suffix_newline
    mdf['_markdown'] = _markdown_line.str.split('\n')
    _suffix_newline = (mdf['_tag'].isin(['li', 'h2']) | mdf['_ul_next']).map({False: '\n', True: ''})
    _condensed_line = mdf['content'] + _suffix_newline
    mdf['_condensed'] = _condensed_line.str.split('\n')

    if explode:
        md_df = mdf.explode('_markdown').drop(columns='content').reset_index(drop=True)
        md_df['_line'] = 1 + md_df['_begin'] + md_df.groupby('_begin').cumcount()
        md_df['_i'] = md_df.groupby('_begin').cumcount()
        md_df['_condensed'] = md_df.apply(lambda x: x['_condensed'][x['_i']] if x['_i'] < len(x['_condensed']) else None, axis=1)
        return md_df
    return mdf


################################################################################
# Utility Functions
################################################################################

def path_names(path: Path, glob='*', stem=True) -> pd.Series:
    if stem:
        return pd.Series([p.stem for p in path.glob(glob)])
    return pd.Series([p.name for p in path.glob(glob)])

@cache
def path_df(path: Path, glob='*') -> pd.Series:
    import os
    from datetime import datetime
    pdf = pd.DataFrame({
        'name': pd.Series([p.name for p in path.glob(glob)]),
        'hash': pd.Series([p.stem.rsplit('.', 1)[-1] for p in path.glob(glob)]),
        'ctime': pd.Series([datetime.fromtimestamp(os.stat(p).st_birthtime) for p in path.glob(glob)]),
        'stsize': pd.Series([os.stat(p).st_size for p in path.glob(glob)]),
        'path': [p for p in path.glob(glob)],
    })
    return pdf


def reduce_list(list_list) -> list:
    uniq_set = reduce(lambda x, y: x | y, [set(x) for x in list_list if x is not None], set())
    uniq_list = sorted(uniq_set)
    return uniq_list

def uniq(_list, squeeze=True, as_list=True):
    uniq_tuple = tuple(dict.fromkeys(_list).keys())
    if squeeze and len(uniq_tuple) == 1:
        return uniq_tuple[0]
    if as_list:
        return list(uniq_tuple)
    return uniq_tuple


if __name__ == "__main__":
    P_query_list = [
        # Path('data/queries/Healthcare.txt'),
        # Path('data/queries/DS_NorCal.txt'),
        # Path('data/queries/DS_Remote.txt'),
        # Path('data/queries/SF.txt'),
        # Path('data/queries/DS_Seattle.txt'),
        # Path('data/queries/DS_Socal.txt'),
        # Path('data/queries/DS_Midwest.txt'),
        # Path('data/queries/DS_NY.txt'),
        # Path('data/queries/DS_DC.txt'),
        # Path('data/queries/SW.txt'),
        # Path('data/queries/SW_Remote.txt'),
    ]
    print(P_query_list)
