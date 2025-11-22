"""
Download job description
"""
#!/usr/bin/env python3
import json
import logging
import os
import pickle
import random
import re
import time
import urllib
from functools import cache
from itertools import chain
from pathlib import Path
from textwrap import dedent
from warnings import filterwarnings

import lxml.html
import requests
from markdownify import markdownify as md
# from markdown_it import MarkdownIt
# from mdit_py_plugins.front_matter import front_matter_plugin
# from mdit_py_plugins.wordcount import wordcount_plugin
import pandas as pd
from tqdm import TqdmExperimentalWarning
from tqdm.rich import tqdm
filterwarnings("ignore", category=TqdmExperimentalWarning)
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from job_search.utils import is_running_wsl
from job_search.config import (
    HIRING_CAFE_HTTPS,
    VIEW_JOB_HTTPS,
    QUERY_LIST,
    JINJA_TEMPLATE,
    P_DATA,
    P_QUERIES,
    P_CACHE,
    P_JOBS,
    P_URLS,
    P_DICT,
    P_ALL_COMPANY_URLS,
    STEM,
    P_DATE,
    P_STEM,
    P_STEM_JOBS_HTML,
    P_STEM_COMPANY_URLS,
    P_STEM_QUERY_TXT,
)


# Selenium options
SCROLL_PAUSE_TIME = 0.5
WAIT_TIME = 10


def init_driver(headless=True):
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    if headless:
        chrome_options.add_argument("--headless")  # Ensure GUI is off
    if is_running_wsl():
        webdriver_service = Service(f"/usr/lib/chromium-browser/chromedriver")
        driver = webdriver.Chrome(service=webdriver_service, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    return driver


################################################################################
# Main Functions
################################################################################

def main0(path_query: Path | str, overwrite=False) -> Path:
    """
    Get data/ds.html to prepare job cards
    """
    # datetime_now = now(time=True)
    P_save = P_DATE / f"{path_query.stem}/{path_query.stem}.html"
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

    driver = init_driver(headless=False)
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

    _title = f"{P_save.stem} (N={N})"
    _data = dict(body=scroll_jobs_outer_html, title=_title, description=query_url)
    scroll_jobs_html = render_template(**_data).replace('</source>', '')

    with open(P_save, 'w', encoding='utf-8') as f:
        f.write(scroll_jobs_html)

    return P_save

def main1(P_save: Path | str):
    """
    Scrape job urls and descriptions
    """
    log(P_save).info(f"Scraping initial job descriptions and metadata from {P_save}...")

    df = load_jdf(P_save)
    _save_dicts(df)


def _save_dicts(df, P_save=None):
    P_URLS.mkdir(exist_ok=True)
    P_JOBS.mkdir(exist_ok=True)
    P_DICT.mkdir(exist_ok=True)

    df_identifier = (df['position'] + '.' + df['hash'])
    if P_save:
        P_jdf = P_save.parent / f"{P_save.stem}_identifiers.txt"
        df_identifier.to_csv(P_jdf, index=False, header=None)
        log(P_save).info(f"Saved {P_jdf} (N={len(df)})...")
    hash2identifier_dict = dict(zip(df['hash'], df_identifier))

    for url in (pbar := tqdm(VIEW_JOB_HTTPS + df['hash'])):
        hash = url.split('/')[-1]
        identifier = hash2identifier_dict[hash]
        pbar.set_description(f"{identifier}")
        P_url = P_URLS / f"{identifier}.html"
        P_md = P_JOBS / f"{identifier}.md"
        P_dict = P_DICT / f"{identifier}.html.pkl"
        # if P_md.exists():
        if P_dict.exists():
            continue
        if not P_dict.exists():
            # url_get_content = requests_get(url).content
            url_get_content = selenium_get(url)
            time.sleep(random.randint(0,2))
            with open(P_url, 'w', encoding='utf-8') as f:
                f.write(url_get_content)

            root = lxml.html.fromstring(url_get_content)
            _next_data_list = root.xpath("//script[@id='__NEXT_DATA__']")
            if len(_next_data_list) == 0:
                next_data_dict = {}
            else:
                _next_data = root.xpath("//script[@id='__NEXT_DATA__']")[0]
                next_data_dict = json.loads(_next_data.text_content())
            with open(P_dict, 'wb') as f:
                pickle.dump(next_data_dict, f)
        else:
            with open(P_url, encoding='utf-8') as f:
                url_get_content = f.read()
            if url_get_content == '':
                print(P_url)
                continue
        root = lxml.html.fromstring(url_get_content)
        job_description = extract_job_description(root)
        if len(job_description) == 0:
            # P_url.unlink()
            print(P_url)
            continue
        else:
            with open(P_md, 'w', encoding='utf-8') as f:
                f.write(job_description)


def main2(P_save: Path | str):
    """
    Get outerHTML of job cards for companies with multiple job listings
    """
    from datetime import datetime
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException

    log(P_save).info(f"Scraping job urls from companies with multiple listings from {P_save}...")

    HIRING_CAFE_HTTPS = 'https://hiring.cafe'

    df = load_jdf(P_save)
    df2 = df.query('_len > 1').reset_index(drop=True)
    df2_company = df2['company'].str.replace(r'[/|:\\*]', '_', regex=True).str.replace('"', "'").str.replace('’', "'")
    company_chash_list = list(zip(df2_company, df2['chash']))

    if len(company_chash_list) == 0:
        log(P_save).warning('No companies with multiple listings... ')
        return

    P_companies = P_save.parents[3] / f"cache/{P_save.stem}_company_urls"
    P_companies.mkdir(parents=True, exist_ok=True)
    P_ALL_COMPANY_URLS = P_companies.parent / "ALL_company_urls"
    P_ALL_COMPANY_URLS.mkdir(parents=True, exist_ok=True)
    # if all([(P_ALL_COMPANY_URLS / f"{_comp}.html").exists() for _comp in df2_company]):
    #     log(P_save).info('All downloaded...')
    #     return

    log(P_save).info(f'Downloading {len(company_chash_list)} companies...')

    driver = init_driver()
    wait = WebDriverWait(driver, 10)

    P_ALL = load_query_url(P_QUERIES / 'ALL.txt')
    ALL_SEARCH_STATE = P_ALL.split('?', maxsplit=1)[1]
    for company, chash in (pbar := tqdm(company_chash_list)):
        pbar.set_description(f"{(company)}")
        P_company_url = P_ALL_COMPANY_URLS / f"{company}.html"
        # Skip if file exists and recently downloaded
        if P_company_url.exists():
            # _rand_refresh = random.randint(2,7)
            # _rand_refresh = random.randint(1,2)
            _rand_refresh = 1
            if (datetime.now() - datetime.fromtimestamp(P_company_url.stat().st_mtime)).days < _rand_refresh:
                continue

        company_url = f"{HIRING_CAFE_HTTPS}/?company={chash}&{ALL_SEARCH_STATE}"
        _GRID_XPATH = "//div[@class='my-masonry-grid']"
        driver.get(company_url)

        _rand_wait_time = random.randint(2,3)
        # _rand_wait_time = random.randint(4,6)
        scroll_bottom(driver, wait_time=_rand_wait_time)

        try:
            job_cards = wait.until(EC.visibility_of_element_located((By.XPATH, _GRID_XPATH)))
            job_cards_outer_html = job_cards.get_attribute("outerHTML")
        except TimeoutException:
            job_cards_outer_html = ''

        _data = dict(body=job_cards_outer_html, title=company, description=company_url)
        output_html = render_template(**_data)

        with open(P_company_url, 'w', encoding='utf-8') as f:
            f.write(output_html)


def main3(P_save: Path | str) -> pd.DataFrame:
    """Scrape other job urls and descriptions from companies with multiple job postings"""
    log(P_save).info(f"Scraping the rest of job descriptions and metadata from {P_save}...")
    # P_companies = P_save.parents[3] / f"cache/{P_save.stem}_company_urls"
    P_companies = P_save.parents[3] / f"cache/ALL_company_urls"

    df = load_jdf(P_save)
    df2 = df.query('_len > 1').reset_index(drop=True)
    _df2_companies = df2['company'].str.replace(r'[/|:\\*]', '_', regex=True).str.replace('"', "'").str.replace('’', "'")
    cdf2_dict = {}
    for company in _df2_companies:
        P_company = P_ALL_COMPANY_URLS / f"{company}.html"
        with open(P_company, 'r', encoding='utf-8') as f:
            html_string = f.read()

        company_df = load_jdf(html_string)
        # _save_dicts(company_df, P_companies)
        cdf2_dict[company] = company_df
    cdf2 = pd.concat(cdf2_dict)
    # cdf2 = load_cdf(P_companies, verbose=True)[lambda x: x['company'].isin(_df2_companies)]
    log(P_save).info(f"Scraping company jobs (N={len(cdf2)}).")
    _save_dicts(cdf2, P_companies)

    log(P_save).info("Done.")

def main4(P_save: Path | str, obsidian=False):
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
            continue
        assert P_src.exists()
        _row_yaml = yaml.dump(row_dict, sort_keys=False)
        _url = f'{VIEW_JOB_HTTPS}{hash}'
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


def load_query_url(path: Path | str) -> str:
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


def extract_job_description(root, to_markdown=True) -> str:
    def _sanitize(string: str) -> str:
        return string.replace(u'\xa0', ' ').replace(u'\u200b', ' ').replace(u'\u202f', ' ').replace('’', "'")
    _elem = root.xpath('//article')
    _html_string = decode_element(_elem)
    job_description = _sanitize(_html_string)
    if to_markdown:
        job_description = md(job_description, heading_style='ATX')
    return job_description


def extract_job_info(root) -> dict:
    _next_data = root.xpath("//script[@id='__NEXT_DATA__']")[0]
    next_data_dict = json.loads(_next_data.text_content())
    next_data_job = next_data_dict['props']['pageProps']['job']
    # _next_data_job_description = next_data_job['job_information']['description']
    # data_job_description = md(_next_data_job_description, heading_style='ATX')
    return next_data_job

def decode_element(element, base_level=0) -> None | str:
    if isinstance(element, str):
        return element
    if isinstance(element, list):
        html_string_list = [decode_element(elem, base_level) for elem in element]
        html_string = '\n'.join(html_string_list)
    else:
        _str = lxml.html.tostring(element).decode(errors='ignore')
        html_string = dedent('    '*base_level + _str)
    return html_string


@cache
def requests_get(url):
    url_get = requests.get(url)
    return url_get


@cache
def selenium_get(url, wait_time=2):
    driver = init_driver()
    wait = WebDriverWait(driver, 2)
    driver.get(url)
    # scroll_bottom(driver, wait_time=1)
    scroll_bottom(driver, wait_time=wait_time)
    try:
        wait.until(EC.visibility_of_element_located((By.XPATH, ".//article")))
    except:
        pass
    # body = wait.until(EC.visibility_of_element_located((By.XPATH, "/body")))
    # outerHTML = body.get_attribute("outerHTML")
    html_source = driver.page_source
    driver.close()
    return html_source


def identifier_get(identifier, save=False, verbose=True):
    hash = identifier.rsplit('.', 1)[-1]
    url = VIEW_JOB_HTTPS + hash
    html_source = selenium_get(url)
    if save:
        P_url = P_URLS / f"{identifier}.html"
        if verbose:
            print(f'Writing to {P_url}')
        with open(P_url, 'w', encoding='utf-8') as f:
            f.write(html_source)
    else:
        return html_source


@cache
def load_jdf(P_save: Path | str | None = P_STEM) -> pd.DataFrame:
    _CLASS = "//div[@class='relative bg-white rounded-xl border border-gray-200 shadow hover:border-gray-500 md:hover:border-gray-200']"
    html_string = P_save
    if isinstance(P_save, Path):
        with open(P_save, encoding='utf-8') as f:
            html_string = f.read()

    company_ = None
    if html_string:
        tree = lxml.html.fromstring(html_string)
        _title_elem = tree.xpath('head/title')
        if _title_elem:
            company_ = f"{_title_elem[0].text}_"
        all_cards = tree.xpath(_CLASS)
    else:
        path_list = [P_DATA / f"{query}.html" for query in QUERY_LIST]
        html_list = [open(path, encoding='utf-8').read() for path in path_list]
        tree_list = [lxml.html.fromstring(html) for html in html_list]
        cards_list = [tree.xpath(_CLASS) for tree in tree_list]
        all_cards = chain.from_iterable(cards_list)

    use_chash = (company_ is None) or ('(N=' in company_)
    raw_texts_list = []
    for card in all_cards:
        raw_texts = [x.strip() for x in card.xpath('.//span/text()')]
        if not use_chash:
            raw_texts = raw_texts[1:]
        if not re.match(r"\d\d?[y|mo|w|d|h]", raw_texts[0]):
            raw_texts.insert(0, '0h')
        if not raw_texts[3].endswith('yr') and not raw_texts[3].endswith('mo') and not raw_texts[3].endswith('wk') and not raw_texts[3].endswith('hr'):
            raw_texts.insert(3, '-')
        if not use_chash:
            raw_texts.insert(6, company_)
            raw_texts.insert(7, None)
        if not raw_texts[8].endswith('YOE'):
            raw_texts.insert(8, '-')
        if not raw_texts[9].endswith('Mgmt'):
            raw_texts.insert(9, '-')
        if "Posting" in raw_texts[11]:
            raw_texts.insert(11, '-')
        url = card.xpath('div[2]/div/a[1]/@href')[0]
        hash = url.split('/')[-1]

        if use_chash:
            url2 = card.xpath('div[2]/div/a[2]/@href')[0]
            chash = url2.removeprefix('/?company=').split('&', maxsplit=1)[0]
            raw_texts_list.append([*raw_texts[:14], hash, chash])
        else:
            raw_texts_list.append([*raw_texts[:14], hash])
    if use_chash:
        HEADER_COLS = ['days', 'title', 'location', 'salary', 'onsite', 'full_time', 'company', 'company_summary', 'yoe', 'mgmt', 'job_summary', 'skills',
                    '_job_posting', '_views', 'hash', 'chash']
    else:
        HEADER_COLS = ['days', 'title', 'location', 'salary', 'onsite', 'full_time', 'company', 'company_summary', 'yoe', 'mgmt', 'job_summary', 'skills',
                    '_job_posting', '_views', 'hash']

    jdf = pd.DataFrame(raw_texts_list, columns=HEADER_COLS).replace(r'\s+', ' ', regex=True)
    assert all(jdf['_job_posting'] == "Job Posting")
    jdf['company'] = jdf['company'].str[:-1].str.replace('"', "'").str.replace('’', "'")
    jdf = jdf.drop(columns=['_job_posting', '_views'])
    _BUTTONS_CLASS = ".//div[@class='flex justify-center space-x-2']/div"
    jdf['_len'] = pd.Series([len(card.xpath(_BUTTONS_CLASS)) for card in all_cards])
    jdf = _feature_engineering(jdf)
    return jdf


@cache
def load_cdf(P_companies: Path | str = P_ALL_COMPANY_URLS, verbose=False) -> pd.DataFrame:
    if P_companies == P_ALL_COMPANY_URLS:
        _P_cdf_parquet = P_CACHE / 'cdf_2025-11-10.parquet'
        cdf = pd.read_parquet(_P_cdf_parquet)
        return cdf

    HEADER_COLS = ['days', 'title', 'location', 'salary', 'onsite', 'full_time',
                'company', 'company_summary', 'yoe', 'mgmt', 'job_summary', 'skills',
                '_job_posting']

    company2cdf = {}

    companies_path_list = [p for p in P_companies.glob('*.html')]
    if verbose:
        companies_path_list = tqdm(companies_path_list)
    for path in companies_path_list:
        if os.stat(path).st_size < 3000:
            if verbose:
                print(f'{path.stem} is empty...')
            continue

        _cdf = load_jdf(path)
        company2cdf[path.name] = _cdf

    cdf = pd.concat(company2cdf, ignore_index=True)
    # cdf = _feature_engineering(cdf)
    return cdf


@cache
def load_df(P_save: Path | str = P_STEM) -> pd.DataFrame:
    import polars as pl
    P_companies = P_save.parents[3] / f"cache/{P_save.stem}_company_urls"
    jdf = load_jdf(P_save)
    cdf = load_cdf(P_companies)
    df = pd.concat([jdf, cdf]).drop_duplicates('hash')
    df = pl.from_pandas(df)
    return df



def _feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    def load_cities() -> pd.DataFrame:
        SILICON_VALLEY = 'Silicon Valley'
        cities = pd.read_csv(P_DATA / 'raw/cities.csv')[SILICON_VALLEY]
        bay_cities = cities[~cities.str.startswith('#')].reset_index(drop=True)
        return bay_cities

    df['hours'] = (df['days'].str.split(r'\D').str[0].astype(int)
                   * df['days'].str.split(r'\d').str[-1].map({'h': 1, 'd': 24, 'w': 24*7, 'mo': 730, 'y': 24*365}))
    df['position'] = (df['company'] + ' - ' + df['title']).str.replace(r'[/|:\\*?]', '_', regex=True).str.replace('"', "'").str.replace('’', "'")
    df['_position'] = df['position'].str.lower()
    df = df.sort_values(['position', 'hours', 'company_summary']).drop_duplicates(subset='_position').reset_index(drop=True)
    # df = df.sort_values(['_hours', 'position', 'company_summary']).drop_duplicates(subset='hash').reset_index(drop=True)

    df['location'] = df['location'].str.replace(', California', '').str.replace(', United States', '')
    _salary_type = df['salary'].str.split('/').str[1]
    _multiplier = (_salary_type == 'yr') + 12*(_salary_type == 'mo') + 2.080*(_salary_type == 'hr')
    _salary_range = df['salary'].str.split('/').str[0].str.split('-')
    df['lower'] = _salary_range.str[0].str[1:-1].replace('', None).pipe(pd.to_numeric, errors='coerce') * _multiplier
    df['upper'] = _salary_range.str[-1].str[1:-1].replace('', None).pipe(pd.to_numeric, errors='coerce') * _multiplier
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


def render_template(**kwargs):
    output_html = _template().render(**kwargs)
    return output_html


@cache
def _template():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(P_DATA / 'external'))
    JINJA_TEMPLATE = 'template.html'
    template = env.get_template(JINJA_TEMPLATE)
    return template


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
        # P_QUERIES / ('ALL.txt'),
        # P_QUERIES / ('DS.txt'),
        # P_QUERIES / ('DS_NorCal_Remote.txt'),
        P_QUERIES / ('DS_NorCal.txt'),
        # P_QUERIES / ('Healthcare.txt'),
        # P_QUERIES / ('SF.txt'),
        # P_QUERIES / ('SW.txt'),
        # P_QUERIES / ('DS_Remote.txt'),
        # P_QUERIES / ('DS_Socal.txt'),
        # P_QUERIES / ('DS_Seattle.txt'),
        # P_QUERIES / ('DS_NY.txt'),
        # P_QUERIES / ('DS_Midwest.txt'),
        # P_QUERIES / ('DS_DC.txt'),
        # P_QUERIES / ('SW_Remote.txt'),
    ]
    for P_query in P_query_list:
        P_save = main0(P_query, overwrite=False)  # Path('data/2025-10-11/DS.html')
        main1(P_save)
        # main2(P_save)
        # main3(P_save)
        # main4(P_save, obsidian=False)
