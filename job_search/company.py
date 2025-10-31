"""
Download job description
"""
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
from textwrap import dedent
from warnings import filterwarnings

import lxml.html
import pandas as pd
import polars as pl
import requests
import polars.selectors as cs
from markdownify import markdownify as md
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.wordcount import wordcount_plugin
from tqdm import TqdmExperimentalWarning
from tqdm.rich import tqdm
filterwarnings("ignore", category=TqdmExperimentalWarning)


HIRING_CAFE_HTTPS = "https://hiring.cafe"
VIEW_JOB_HTTPS = "https://hiring.cafe/viewjob/"
QUERY_LIST = ['ds',]
P_DS_QUERY_TXT = Path('data/DS.txt')
P_SW_QUERY_TXT = Path('data/SW.txt')
# P_DS = Path('data/2025-10-08/DS.html')
P_DS = Path('data/2025-10-09/DS.html')
P_COMPANY_URLS = Path(f'data/cache/company_urls')
P_JOBS = Path(f'data/cache/jobs')
P_URLS = Path(f'data/cache/urls')

# Selenium options
SCROLL_PAUSE_TIME = 0.5
WAIT_TIME = 5

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


@cache
def load_df(P_save: Path | str = P_DS, polars=True) -> pd.DataFrame:
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
def load_dfc(P_save: Path | str = P_DS) -> pd.DataFrame:
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


@cache
def load_jdf(P_save: Path | str | None = P_DS) -> pd.DataFrame:
    _CLASS = "//div[@class='relative bg-white rounded-xl border border-gray-200 shadow hover:border-gray-500 md:hover:border-gray-200']"
    html_string = P_save
    if isinstance(P_save, Path):
        with open(P_save, encoding='utf-8') as f:
            html_string = f.read()
    if html_string:
        tree = lxml.html.fromstring(html_string)
        all_cards = tree.xpath(_CLASS)
    else:
        path_list = [Path(f'data/{query}.html') for query in QUERY_LIST]
        html_list = [open(path, encoding='utf-8').read() for path in path_list]
        tree_list = [lxml.html.fromstring(html) for html in html_list]
        cards_list = [tree.xpath(_CLASS) for tree in tree_list]
        all_cards = chain.from_iterable(cards_list)

    raw_texts_list = []
    for card in all_cards:
        raw_texts = [x.strip() for x in card.xpath('.//span/text()')]
        if not re.match(r"\d\d?[y|mo|w|d|h]", raw_texts[0]):
            raw_texts.insert(0, '0h')
        if not raw_texts[3].endswith('yr') and not raw_texts[3].endswith('mo') and not raw_texts[3].endswith('wk') and not raw_texts[3].endswith('hr'):
            raw_texts.insert(3, '-')
        if not raw_texts[8].endswith('YOE'):
            raw_texts.insert(8, '-')
        if not raw_texts[9].endswith('Mgmt'):
            raw_texts.insert(9, '-')
        if "Posting" in raw_texts[11]:
            raw_texts.insert(11, '-')
        url = card.xpath('div[2]/div/a[1]/@href')[0]
        hash = url.split('/')[-1]
        url2 = card.xpath('div[2]/div/a[2]/@href')[0]
        raw_texts_list.append([*raw_texts[:14], hash, url2])
        # raw_texts_list.append([*raw_texts, hash, url2])
    # HEADER_COLS = ['days', 'title', 'location', 'salary', 'onsite', 'full_time', 'company', 'company_summary', 'yoe', 'mgmt', 'job_summary', 'skills',
    #             '_job_posting', 'views', '_views', 'saves', '_saves', 'applications', '_applications', 'hash', 'url2']
    HEADER_COLS = ['days', 'title', 'location', 'salary', 'onsite', 'full_time', 'company', 'company_summary', 'yoe', 'mgmt', 'job_summary', 'skills',
                '_job_posting', '_views', 'hash', 'url2']
    jdf = pd.DataFrame(raw_texts_list, columns=HEADER_COLS).replace(r'\s+', ' ', regex=True)
    assert all(jdf['_job_posting'] == "Job Posting")
    jdf['company'] = jdf['company'].str[:-1].str.replace('"', "'").str.replace('’', "'")
    jdf = jdf.drop(columns=['_job_posting', '_views'])
    _BUTTONS_CLASS = ".//div[@class='flex justify-center space-x-2']/div"
    jdf['_len'] = pd.Series([len(card.xpath(_BUTTONS_CLASS)) for card in all_cards])
    jdf = _feature_engineering(jdf)
    return jdf


@cache
def load_cdf(P_companies: Path | str = P_COMPANY_URLS, verbose=False) -> pd.DataFrame:
    HEADER_COLS = ['days', 'title', 'location', 'salary', 'onsite', 'full_time',
                'company', 'company_summary', 'yoe', 'mgmt', 'job_summary', 'skills',
                '_job_posting']
    company2cdf = {}

    for path in P_companies.glob('*.html'):
        with open(path, encoding='utf-8') as f:
            html_string = f.read()

        if len(html_string) == 0:
            if verbose:
                print(f'{path.stem} is empty...')
            continue

        all_cards = lxml.html.fromstring(html_string)

        raw_texts_list = []
        url_list = []
        for card in all_cards:
            # header, info = card.xpath("div")
            raw_texts = [x.strip() for x in card.xpath('.//span/text()')]
            if not re.match(r"\d\d?[y|mo|w|d|h]", raw_texts[0]):
                raw_texts.insert(0, '0h')
            if not raw_texts[3].endswith('yr') and not raw_texts[3].endswith('mo') and not raw_texts[3].endswith('wk') and not raw_texts[3].endswith('hr'):
                raw_texts.insert(3, '-')
            raw_texts.insert(6, path.stem)
            raw_texts.insert(7, '')
            if not raw_texts[8].endswith('YOE'):
                raw_texts.insert(8, '-')
            if not raw_texts[9].endswith('Mgmt'):
                raw_texts.insert(9, '-')
            if "Posting" in raw_texts[11]:
                raw_texts.insert(11, '-')
            raw_texts_list.append([*raw_texts[:13]])
            url_list.append(card.xpath('.//@href'))

        _cdf = pd.DataFrame(raw_texts_list, columns=HEADER_COLS).replace(r'\s+', ' ', regex=True)
        _urls = pd.Series(chain.from_iterable(url_list))
        _cdf['hash'] = _urls.str.split('/').str[-1]
        company2cdf[path.name] = _cdf

    cdf = pd.concat(company2cdf, ignore_index=True)
    cdf = _feature_engineering(cdf)
    return cdf


def _feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    df['hours'] = (df['days'].str.split(r'\D').str[0].astype(int)
                   * df['days'].str.split(r'\d').str[-1].map({'h': 1, 'd': 24, 'w': 24*7, 'mo': 730, 'y': 24*365}))
    df['position'] = (df['company'] + ' - ' + df['title']).str.replace(r'[/|:\\*]', '_', regex=True).str.replace('"', "'").str.replace('’', "'")
    df['_position'] = df['position'].str.lower()
    df = df.sort_values(['position', 'hours', 'company_summary']).drop_duplicates(subset='_position').reset_index(drop=True)
    # df = df.sort_values(['_hours', 'position', 'company_summary']).drop_duplicates(subset='hash').reset_index(drop=True)

    df['location'] = df['location'].str.replace(', California', '').str.replace(', United States', '')
    _salary_type = df['salary'].str.split('/').str[1]
    _multipler = (_salary_type == 'yr') + 12*(_salary_type == 'mo') + 2.080*(_salary_type == 'hr')
    _salary_range = df['salary'].str.split('/').str[0].str.split('-')
    df['lower'] = _salary_range.str[0].str[1:-1].replace('', None).pipe(pd.to_numeric, errors='coerce') * _multipler
    df['upper'] = _salary_range.str[1].str[1:-1].replace('', None).pipe(pd.to_numeric, errors='coerce') * _multipler
    df['median'] = (df['lower'] + df['upper']) / 2
    df['yoe'] = df['yoe'].str.split('+').str[0].pipe(pd.to_numeric, errors='coerce')
    df['mgmt'] = df['mgmt'].str.split('+').str[0].pipe(pd.to_numeric, errors='coerce')

    bay_cities = load_cities()
    regex_bay_cities = f"({'|'.join(bay_cities)})"
    df['bay'] = df['location'].str.extractall(regex_bay_cities).groupby(level=0)[0].apply(tuple)
    # _series = df['location'].str.extractall(regex_bay_cities)
    # for i in range(4):
    #     df[f'bay{i}'] = _series[0].loc[:,i].reindex_like(df)#.fillna('')

    return df


def load_query_url(path: Path | str = P_DS_QUERY_TXT) -> str:
    path = Path(path)
    if path.suffix == '.json':
        with open(path) as f:
            query_str = f.read()
    else:
        with open(path) as f:
            return f.read()
    _query_stripped = re.sub(r"\s*", "", query_str)
    _query_parsed = urllib.parse.quote(_query_stripped)
    query_url = f"https://hiring.cafe/?searchState={_query_parsed}".replace("%2B", "+")
    return query_url


def parse_query_url(query_url: str) -> str:
    import json
    _query_parsed = query_url.removeprefix("https://hiring.cafe/?searchState=")
    _query_stripped = urllib.parse.unquote(_query_parsed)
    query_dict = json.loads(_query_stripped)
    return query_dict


def load_cities() -> pd.DataFrame:
    SILICON_VALLEY = 'Silicon Valley'
    cities = pd.read_csv('data/raw/cities.csv')[SILICON_VALLEY]
    bay_cities = cities[~cities.str.startswith('#')].reset_index(drop=True)
    return bay_cities


def decode_element(element, base_level=0, verbose=False) -> None | str:
    if isinstance(element, str):
        if verbose:
            display_code(element, language='html')
        else:
            return element
    if isinstance(element, list):
        html_string_list = [decode_element(elem, base_level, verbose=False) for elem in element]
        html_string = '\n'.join(html_string_list)
    else:
        _str = lxml.html.tostring(element).decode(errors='ignore')
        html_string = dedent('    '*base_level + _str)
    if verbose:
        display_code(html_string, language='html')
    else:
        return html_string


def viewjob(hash: str) -> str:
    return f'{VIEW_JOB_HTTPS}{hash}'


def extract_job_description(root, to_markdown=True) -> str:
    def _sanitize(string: str) -> str:
        return string.replace(u'\xa0', ' ').replace(u'\u200b', ' ').replace(u'\u202f', ' ').replace('’', "'")
    _elem = root.xpath('//article')
    _html_string = decode_element(_elem, verbose=False)
    job_description = _sanitize(_html_string)
    if to_markdown:
        job_description = md(job_description, heading_style='ATX')
    return job_description


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
## Polars functions
################################################################################

def pl_remove(input_column, *items) -> pl.Expr:
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    return pl_col.list.eval(pl.element().filter(~pl.element().is_in(items)))

def pl_reduce_list(input_column: str | pl.Expr) -> pl.Expr:
    """Usage: pl_col.pipe(pl_reduce_list)"""
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    return pl_col.drop_nulls().map_batches(reduce_list, returns_scalar=True)

def pl_enum_min(input_column: str | pl.Expr, pl_enum=None) -> pl.Expr:
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    return pl_col.cast(pl.Int8).min().cast(pl_enum)

def pl_enum_max(input_column: str | pl.Expr, pl_enum=None) -> pl.Expr:
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    return pl_col.cast(pl.Int8).max().cast(pl_enum)

def pl_cast_enum(input_column: str | pl.Expr, pl_enum: pl.Enum):
    pl_col = input_column
    if isinstance(input_column, str):
        pl_col = pl.col(input_column)
    enum2index = {k: v for v, k in enumerate(pl_enum.categories)}
    return pl_col.replace(enum2index).cast(pl.Int8).cast(pl_enum)

def convert_enums(pl_df: pl.DataFrame, columns: str | list | None = None, cutoff=32, sort=True, return_enums=False) -> dict | pl.DataFrame:
    if columns is None:
        columns = pl_df.select(cs.string() | cs.enum()).columns
    elif isinstance(columns, str):
        columns = [columns,]
    if sort:
        col2enum = {col: pl.Enum(list(pl_df[col].unique().sort()))
                    for col in columns if pl_df[col].n_unique() < cutoff}
    else:
        col2enum = {col: pl.Enum(list(pl_df[col].unique(maintain_order=True)))
                    for col in columns if pl_df[col].n_unique() < cutoff}
    if return_enums:
        return col2enum
    return pl_df.with_columns(pl.col(col).pipe(pl_cast_enum, col2enum[col]) for col in col2enum)


################################################################################
# Utility Functions
################################################################################

def path_names(path: Path, glob='*', stem=True) -> pd.Series:
    if stem:
        return pd.Series([p.stem for p in path.glob(glob)])
    return pd.Series([p.name for p in path.glob(glob)])

@cache
def requests_get(url):
    url_get = requests.get(url)
    return url_get

def now(time=True, file=True) -> str:
    from datetime import datetime
    datetime_now = datetime.now()
    if time:
        if file:
            return datetime_now.strftime(r"%Y-%m-%d_%H%M%S")
        return datetime_now.strftime(r"%#I:%M%p").lower()
    else:
        if file:
            return datetime_now.strftime(r"%Y-%m-%d")
        return datetime_now.strftime(r"%#m/%#d/%y (%A)")

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

def display_code(code: str, language: str = 'python'):
    from IPython.display import display, Markdown
    markdown_code = f'```{language}\n{code}\n```'
    display(Markdown(markdown_code))

def jupyter_css_style():
    from IPython.display import HTML
    css_style = HTML("""
        <!-- https://stackoverflow.com/questions/71534901/make-tqdm-bar-dark-in-vscode-jupyter-notebook -->
        <style>
        .cell-output-ipywidget-background {
            background-color: transparent !important;
        }
        :root {
            --jp-widgets-color: var(--vscode-editor-foreground);
            --jp-widgets-font-size: var(--vscode-editor-font-size);
        }
        </style>
    """)
    return css_style

def reload(module=None):
    """Reload module (for use in Jupyter Notebook)

    Args:
        module (types.ModuleType, optional): module to reload
    """
    import sys
    import importlib
    importlib.reload(module or sys.modules[__name__])

################################################################################
# Main Functions
################################################################################

def main0(path_query: Path | str = P_DS_QUERY_TXT, overwrite=False) -> Path:
    """
    Get data/ds.html to prepare job cards
    """
    import json
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException


    # datetime_now = now(time=True)
    datetime_now = now(time=False)
    P_save = Path(f"data/processed/{datetime_now}/{path_query.stem}/{path_query.stem}.html")
    P_save.parent.mkdir(parents=True, exist_ok=True)

    if not overwrite and P_save.exists():
        log(P_save).info(f"{P_save} already exists...")
        return P_save

    query_url = load_query_url(path_query)
    query_dict = parse_query_url(query_url)
    P_query = P_save.parent / f"{P_save.stem}.txt"
    P_json = P_save.parent / f"{P_save.stem}.json"
    log(P_save).info(f"Preparing {P_save} outerHTML from {P_query}...")
    with open(P_query, 'w') as f:
        f.write(query_url)
    with open(P_json, 'w') as f:
        json.dump(query_dict, f, indent=4)
    def _format_loc(loc):
        _address = loc['address_components'][0]['long_name'].replace('+', ' ')
        _radius = f" - {loc['options']['radius']} {loc['options']['radius_unit']}" if loc['options'].keys() else ''
        _workplaces = " | ".join(loc['workplace_types'])
        loc_formatted = f"{_address}{_radius}. {_workplaces}"
        return loc_formatted
    _job_title_query = query_dict['jobTitleQuery'].replace('+', ' ').replace('AND', '\n\tAND')
    _locations = '\n\t'.join([_format_loc(loc) for loc in query_dict['locations']])
    _commitment_types = ", ".join(query_dict['commitmentTypes']).replace('+', ' ')
    _query_str = dedent(f"""{_job_title_query}
        {_locations}
        {_commitment_types}
    """)
    log(P_save).info(_query_str)
    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get(query_url)
    wait = WebDriverWait(driver, 10)
    scroll_bottom(driver)

    _SCROLL_XPATH = "//div[@class='infinite-scroll-component__outerdiv']"
    try:
        scroll_jobs = wait.until(EC.visibility_of_element_located((By.XPATH, _SCROLL_XPATH)))
        scroll_jobs_outer_html = scroll_jobs.get_attribute("outerHTML")
    except TimeoutException:
        log(P_save).warning(f"Could not save {P_save}...")
        scroll_jobs_outer_html = ''
        input("Press ENTER to continue...")

    _CLASS = "//div[@class='relative bg-white rounded-xl border border-gray-200 shadow hover:border-gray-500 md:hover:border-gray-200']"
    N = len(lxml.html.fromstring(scroll_jobs_outer_html).xpath(_CLASS))
    log(P_save).info(f"Saving {P_save} (N={N})...")
    with open(P_save, 'w', encoding='utf-8') as f:
        f.write(scroll_jobs_outer_html)

    return P_save

def main1(P_save: Path | str = P_DS):
    """
    Scrape job urls and descriptions
    """
    log(P_save).info(f"Scraping initial job descriptions and metadata from {P_save}...")

    df = load_jdf(P_save)
    df_identifier = (df['position'] + '.' + df['hash'])
    P_jdf = P_save.parent / f"{P_save.stem}_identifiers.txt"
    df_identifier.to_csv(P_jdf, index=False, header=None)
    log(P_save).info(f"Saved {P_jdf} (N={len(df_identifier)})...")

    hash2identifier_dict = dict(zip(df['hash'], df_identifier))

    P_URLS.mkdir(exist_ok=True)
    P_JOBS.mkdir(exist_ok=True)
    for url in (pbar := tqdm(VIEW_JOB_HTTPS + df['hash'], 1)):
        hash = url.split('/')[-1]
        identifier = hash2identifier_dict[hash]
        pbar.set_description(f"{identifier}")
        P_URL = Path(f'data/cache/urls/{identifier}.html')
        P_MD = Path(f'data/cache/jobs/{identifier}.md')
        if P_MD.exists():
            continue
        if not P_URL.exists():
            url_get_content = requests_get(url).content
            time.sleep(random.randint(1,3))
            with open(P_URL, 'wb') as f:
                f.write(url_get_content)
        else:
            with open(P_URL, encoding='utf-8') as f:
                url_get_content = f.read()
        if len(url_get_content) == 0:
            continue
        with open(P_MD, 'w', encoding='utf-8') as f:
            root = lxml.html.fromstring(url_get_content)
            job_description = extract_job_description(root)
            f.write(job_description)

def main2(P_save: Path | str = P_DS):
    """
    Get outerHTML of job cards for companies with multiple job listings
    """
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException

    log(P_save).info(f"Scraping job urls from companies with multiple listings from {P_save}...")

    HIRING_CAFE_HTTPS = 'https://hiring.cafe'

    df = load_jdf(P_save)
    df2 = df.query('_len > 1').reset_index(drop=True)
    # df2_company = df2['company'].str.replace(r'[/|\\*]', '_', regex=True)
    df2_company = df2['company'].str.replace(r'[/|:\\*]', '_', regex=True).str.replace('"', "'").str.replace('’', "'")
    company_url2_list = list(zip(df2_company, df2['url2']))

    if len(company_url2_list) == 0:
        log(P_save).warning('No companies with multiple listings... ')
        return

    # P_companies = Path(f'data/company_urls')
    P_companies = P_save.parents[3] / f"cache/{P_save.stem}_company_urls"
    P_companies.mkdir(parents=True, exist_ok=True)
    # if all([Path(f'data/cache/company_urls/{_comp}.html').exists() for _comp in df2_company]):
    if all([(P_companies / f"{_comp}.html").exists() for _comp in df2_company]):
        log(P_save).info('All downloaded...')
        return

    log(P_save).info(f'Downloading {len(company_url2_list)} companies...')

    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 10)

    for company, url2 in (pbar := tqdm(company_url2_list)):
        pbar.set_description(f"{(company)}")
        # P_URL = Path(f'company_urls/{company}.html')
        P_URL = P_companies / f"{company}.html"
        if P_URL.exists():
            continue

        company_url = HIRING_CAFE_HTTPS + url2
        _GRID_XPATH = "//div[@class='my-masonry-grid']"
        driver.get(company_url)

        scroll_bottom(driver, wait_time=1)

        try:
            job_cards = wait.until(EC.visibility_of_element_located((By.XPATH, _GRID_XPATH)))
            job_cards_outer_html = job_cards.get_attribute("outerHTML")
        except TimeoutException:
            job_cards_outer_html = ''

        with open(P_URL, 'w', encoding='utf-8') as f:
            f.write(job_cards_outer_html)
        time.sleep(random.randint(1,3))

def main3(P_save: Path | str = P_DS) -> pd.DataFrame:
    """Scrape other job urls and descriptions from companies with multiple job postings"""
    log(P_save).info(f"Scraping the rest of job descriptions and metadata from {P_save}...")
    P_companies = P_save.parents[3] / f"cache/{P_save.stem}_company_urls"

    cdf = load_cdf(P_companies, verbose=True)
    hash2identifier_dict = dict(zip(cdf['hash'], cdf['position'] + '.' + cdf['hash']))

    for url in (pbar := tqdm(VIEW_JOB_HTTPS + cdf['hash'], 1)):
        hash = url.split('/')[-1]
        identifier = hash2identifier_dict[hash]
        pbar.set_description(f"{identifier}")
        P_URL = Path(f'data/cache/urls/{identifier}.html')
        P_MD = Path(f'data/cache/jobs/{identifier}.md')
        if P_MD.exists():
            continue
        if not P_URL.exists():
            url_get_content = requests_get(url).content
            time.sleep(random.randint(1,3))
            with open(P_URL, 'wb') as f:
                f.write(url_get_content)
        else:
            with open(P_URL, encoding='utf-8') as f:
                url_get_content = f.read()
        if len(url_get_content) == 0:
            continue
        with open(P_MD, 'w', encoding='utf-8') as f:
            root = lxml.html.fromstring(url_get_content)
            job_description = extract_job_description(root)
            f.write(job_description)

    log(P_save).info("Done.")

def main4(P_save: Path | str = P_DS, obsidian=False):
    """Sync with Obsidian"""
    import yaml
    YAML_COLS = ['company', 'title', 'hours', 'onsite', 'full_time',
                'lower', 'median', 'upper', 'bay', 'skills',]
    P_save_jobs = P_save.parent / f'{P_save.stem}_jobs'
    P_save_jobs.mkdir(exist_ok=True)
    df = load_df(P_save)
    log(P_save).info(f"Syncing job descriptions into {P_save_jobs} (N={len(df)})...")

    job_descriptions = []
    frontmatters = []
    if obsidian:
        P_OBSIDIAN_JOBS = Path(fr"C:\Users\alexa\Dropbox\DropSyncFiles\Obsidian Vault\Companies\jobs")
        log(P_save).info(f"Syncing {P_OBSIDIAN_JOBS}...")
        for path in P_OBSIDIAN_JOBS.glob('*.md'):
            path.unlink()

    _list = list(zip(df['position'], df['hash'], df[YAML_COLS].to_dicts()))
    for position, hash, row_dict in (pbar := tqdm(_list)):
        _filename = f"{position}.{hash}.md"
        P_src = P_JOBS / _filename
        P_dst = P_save_jobs / _filename
        if not P_src.exists():#
            print(P_src)#
        assert P_src.exists()
        _row_yaml = yaml.dump(row_dict, sort_keys=False)
        _url = viewjob(hash)
        frontmatter = f"---\n{_row_yaml}---\n[[Jobs List.base]] | {_url}\n\n"
        with open(P_src, encoding='utf-8') as f:
            job_description = f.read().replace(u'\xa0', ' ').replace(u'\u200b', ' ').replace(u'\u202f', ' ').replace('’', "'")
        with open(P_dst, 'w', encoding='utf-8') as f:
            f.write(f"{frontmatter}{job_description}")

        if obsidian:
            with open(P_OBSIDIAN_JOBS / _filename, 'w', encoding='utf-8') as f:
                f.write(f"{frontmatter}{job_description}")
        frontmatters.append(frontmatter)
        job_descriptions.append(job_description)

    P_job_descriptions = P_save.parent / f'{P_save.stem}_job_descriptions.txt'
    log(P_save).info(f"Writing {P_job_descriptions}...")
    job_descriptions_txt = '\n\n---\n\n'.join(job_descriptions)
    with open(P_job_descriptions, 'w', encoding='utf-8') as f:
        f.write(job_descriptions_txt)


def scroll_bottom(driver, scroll_pause_time=SCROLL_PAUSE_TIME, wait_time=WAIT_TIME):
    """Selenium driver scroll to bottom"""
    NUM_RETRIES = int(wait_time / scroll_pause_time)

    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause_time)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            continue_scroll = False
            for _ in range(NUM_RETRIES):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height != last_height:
                    continue_scroll = True
                    break
            if not continue_scroll:
                # print('Reached bottom of page...')
                break
        last_height = new_height


@cache
def log(P_query: Path) -> logging.Logger:
    _filename = P_query.parent / f'{P_query.stem}.log'
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    file_handler = logging.FileHandler(filename=_filename)
    file_handler.setFormatter(logging.Formatter(FORMAT))
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


if __name__ == "__main__":
    P_query_list = [
        # Path('data/queries/DS_Remote.txt'),
        # Path('data/queries/DS_NorCal.txt'),
        # Path('data/queries/DS_Seattle.txt'),
        # Path('data/queries/DS_Socal.txt'),
        # Path('data/queries/DS_Midwest.txt'),
        # Path('data/queries/DS_NY.txt'),
        # Path('data/queries/DS_DC.txt'),
        # Path('data/queries/SW.txt'),
        # Path('data/queries/SW_Remote.txt'),
    ]

    for P_query in P_query_list:
        P_save = main0(P_query, overwrite=True)  # Path('data/2025-10-11/DS.html')
        main1(P_save)
        main2(P_save)
        main3(P_save)
        main4(P_save, obsidian=False)
