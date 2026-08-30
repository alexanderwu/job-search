from functools import cache
import glob
import gzip
import json
from pathlib import Path
import pickle
import random
import time

from botasaurus.user_agent import UserAgent
from botasaurus_requests import request
from IPython.display import Code
from lxml import etree
from lxml.etree import _Element as Element
from lxml.etree import _ElementTree as ElementTree
import lxml.html
import pandas as pd
import polars as pl
import requests
from tqdm import tqdm

from job_search.config import JOB_HTTPS, P_CACHE, P_INTERIM, P_RAW
from job_search.dataset import init_driver
from job_search.utils import now

USER_AGENT_106 = 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.37'
# HIRING_CAFE = "https://hiring.cafe"
# HIRING_CAFE_ = "https://hiring.cafe/"
HIRING_CAFE = "https://hiringcafe.com"
HIRING_CAFE_ = "https://hiringcafe.com/"
_NEXT_PREFIX = "_next/data/UiNY3DniHUEpbt0-TVyEJ"
_now = now(time=False, days=0)
# _now = '2026-04-20'
P_raw_date = P_RAW / _now.replace('-', '/')
P_interim_date = P_INTERIM / _now.replace('-', '/')

SITEMAP = 'sitemap'
SITEMAP_INDEX = 'sitemap-index'
SITEMAP_COMPANIES = 'sitemap-companies-index'
SITEMAP_JOB_TITLES = 'sitemap-job-titles-index'
SITEMAP_LOCATIONS = 'sitemap-locations-index'

DS_CA = 'ds-ca-2tzfqdib'
DA_SF = 'da-sf-remote-tgl2fcys'
DS_SF = 'ds-sf-remote-77r5vzr1'
DA_HEALTH = 'da-healthcare-awiifu1z'
HEALTH = 'healthcare-9ierbt6f'
BOARD_URL = f'{HIRING_CAFE}/{_NEXT_PREFIX}/b/{HEALTH}.json'
# BOARD_URL = f'{HIRING_CAFE}/{_NEXT_PREFIX}/b/{DS_CA}.json'
GLOB_STR = "../data/interim/2026/05/**/*.json.gz"
# glob_str = "../data/interim/2026/05/*/da-healthcare-awiifu1z/*.json.gz"


def load_sitemap(sitemap=SITEMAP_LOCATIONS, overwrite=False, verbose=True):
    P_sitemap = P_interim_date / f'{sitemap}.parquet'
    if P_sitemap.exists() and not overwrite:
        print('Loading from:', P_sitemap)
        sitemap_df = pd.read_parquet(P_sitemap)
        return sitemap_df
    _sitemap_list = load_tree(sitemap)['sitemap']
    if verbose:
        _sitemap_list = tqdm(_sitemap_list)
    _location_list = [load_tree(x) for x in _sitemap_list]
    sitemap_df = pd.concat(_location_list)
    if verbose:
        print('Saving to:', P_sitemap)
    P_sitemap.parent.mkdir(parents=True, exist_ok=True)
    sitemap_df.to_parquet(P_sitemap)
    return sitemap_df


def xml(sitemap=SITEMAP, N=60, **kwargs):
    """Load and display xml"""
    tree = load_xml(sitemap, **kwargs)
    return _display_xml(tree, N=N)


def load_tree(sitemap=SITEMAP_INDEX, gz=True, overwrite=False, verbose=False):
    tree = load_xml(sitemap, gz, overwrite, verbose)
    NSMAP = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    loc = pd.Series([x.text for x in tree.xpath('//s:loc[text()]', namespaces=NSMAP)])
    tree_df = pd.DataFrame({
        # 'loc': loc,
        'sitemap': loc.str.removeprefix(HIRING_CAFE_),
        'lastmod': [x.text for x in tree.xpath('//s:lastmod[text()]', namespaces=NSMAP)],
    })
    return tree_df


def load_xml(sitemap=SITEMAP, gz=True, overwrite=False, verbose=True) -> ElementTree:
    """Load sitemap xml if it exists on local path, otherwise scrape and save to path"""
    if overwrite:
        return _load_xml.__wrapped__(sitemap, gz, overwrite, verbose)
    return _load_xml(sitemap, gz, overwrite, verbose)


@cache
def _load_xml(sitemap=SITEMAP, gz=True, overwrite=False, verbose=False) -> ElementTree:
    # P_sitemap = P_raw_date / sitemap
    P_sitemap = path_sitemap(sitemap, gz=gz)
    if P_sitemap.exists() and not overwrite:
        if verbose:
            print('Loading from:', P_sitemap)
        tree = etree.parse(P_sitemap)
        return tree

    tree = scrape_xml(sitemap, overwrite=True, verbose=verbose)
    _write_xml(tree, sitemap, gz=True, verbose=verbose)
    return tree


def scrape_xml(sitemap=SITEMAP, overwrite=True, verbose=True) -> ElementTree:
    """Scrape sitemap XML from hiring.cafe"""
    if not sitemap.startswith(HIRING_CAFE):
        sitemap = f'{HIRING_CAFE_}/{sitemap}'
    if not sitemap.endswith('.xml'):
        sitemap = f'{sitemap}.xml'

    if verbose:
        print(f"Scraping from: {sitemap}")

    if overwrite:
        sitemap_xml = _requests_xml.__wrapped__(sitemap)
    else:
        sitemap_xml = _requests_xml(sitemap)
    root = etree.fromstring(sitemap_xml)
    tree = etree.ElementTree(root)
    return tree


@cache
def _requests_xml(url: str) -> bytes:
    _headers = {
        "User-Agent": USER_AGENT_106,
        "Referer": "https://hiring.cafe/",
        "Origin": "https://hiring.cafe",
        "Sec-Fetch-Dest": "empty",
        "Accept": "application/xml",
    }
    response = requests.get(url, headers=_headers)
    response.raise_for_status()
    return response.content


def _write_xml(tree: Element | ElementTree, name=SITEMAP, overwrite=False, gz=True, verbose=True):
    """Save XML to path"""
    P_save = path_sitemap(name, gz=gz)
    if P_save.exists() and not overwrite:
        return

    if verbose:
        print(f'Saving to: {P_save}')
    P_save.parent.mkdir(parents=True, exist_ok=True)

    if gz:
        with gzip.open(P_save, 'wb') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True)
    else:
        tree.write(P_save)


def path_sitemap(name: Path | str = SITEMAP, gz=True) -> Path:
    """Get XML path from sitemap name or URL"""
    if isinstance(name, Path):
        return (P_save := name)

    # TODO: add query time option
    name = name.strip().removeprefix(HIRING_CAFE).removesuffix('.xml')
    P_raw_date = P_RAW / now(time=False).replace('-', '/')
    P_save = P_raw_date / f'{name}.xml'
    if gz:
        P_save = P_save.parent / f'{name}.xml.gz'
    return P_save


def _display_xml(xml: Element | ElementTree | str, N=60):
    """Display truncated XML"""
    if not isinstance(xml, str):
        xml = etree.tostring(xml, pretty_print=True).decode()
    if N is not None and xml.count('\n') > N:
        K = N // 2
        xml_ = '\n'.join(xml.split('\n', maxsplit=K)[:K])
        _xml = '\n'.join(xml.rsplit('\n', maxsplit=K)[-K:])
        xml = f"{xml_}\n...\n{_xml}"
    return Code(xml)


################################################################################


def load_ds_job_titles():
    job_titles_df = load_sitemap(SITEMAP_JOB_TITLES)
    job_titles = job_titles_df['sitemap'].str.removeprefix('jobs/').str.removesuffix('/locations/united-states')

    # ((data OR ml OR "machine learning" OR "ai" OR "artificial intelligence" OR nlp OR statistical OR bi OR "business intelligence" OR devops OR mlops)
    #         AND (engineer OR scientist OR science OR programmer))
    #         AND NOT "software engineer"
    #         AND NOT "electrical engineer"
    data_mask = job_titles.str.contains('data')
    ml_mask = job_titles.str.contains(r'\bml\b') | job_titles.str.contains('machine-learning')
    ai_mask = job_titles.str.contains(r'\bai\b') | job_titles.str.contains('artificial-intelligence')
    nlp_mask = job_titles.str.contains(r'\bnlp\b') | job_titles.str.contains('natural-language-processing')
    bi_mask = job_titles.str.contains(r'\bbi\b') | job_titles.str.contains('business-intelligence')
    ops_mask = job_titles.str.contains('devops') | job_titles.str.contains('mlops')
    part1_mask = data_mask | ml_mask | ai_mask | nlp_mask | bi_mask | ops_mask
    eng_mask = job_titles.str.contains('engineer')
    science_mask = job_titles.str.contains('scientist') | job_titles.str.contains('science')
    programmer_mask = job_titles.str.contains('programmer')
    part2_mask = eng_mask | science_mask | programmer_mask
    neg_mask = job_titles.str.contains(r'(?:software|electrical)-engineer')
    ds_mask = part1_mask & part2_mask & ~neg_mask
    ds_job_titles = job_titles[ds_mask]
    return ds_job_titles



def load_jobs(job_title='data-scientist', overwrite=False, verbose=True, proxy=False, page=0) -> dict:
    P_jobs_json = P_interim_date / f'jobs/{job_title}/page{page}.json.gz'
    if P_jobs_json.exists() and not overwrite:
        jobs_dict = read_data(P_jobs_json, verbose=verbose)
    else:
        # _suffix = f'?jobTitle={job_title}&location=united-states'
        job_title_json_url = f'{HIRING_CAFE_}{_NEXT_PREFIX}/jobs/{job_title}/locations/united-states.json?page={page}'
        job_title_json = request_get(job_title_json_url, proxy=proxy)
        jobs_dict = json.loads(job_title_json)
        write_data(P_jobs_json, jobs_dict, verbose=verbose)

    try:
        if not jobs_dict['pageProps']['ssrIsLastPage']:
            sleep(0.2, 0.5)
            load_jobs(job_title, verbose=verbose, page=page+1)
    except KeyError:
        print(P_jobs_json)
        raise

    return jobs_dict

def load_loc(loc='san-jose-california', overwrite=False, verbose=True, proxy=False, page=0) -> dict:
    P_locs_json = P_interim_date / f'locations/{loc}/page{page}.json.gz'
    if P_locs_json.exists() and not overwrite:
        jobs_dict = read_data(P_locs_json, verbose=verbose)
    else:
        # _suffix = f'?jobTitle={loc}&location=united-states'
        loc_json_url = f'{HIRING_CAFE_}{_NEXT_PREFIX}/jobs/locations/{loc}.json'
        loc_json = request_get(loc_json_url, proxy=proxy)

        write_data(P_locs_json, loc_json, verbose=verbose)
    return jobs_dict

def load_locs(loc='albany-california', overwrite=False, verbose=True, proxy=False, page=0) -> dict:
    P_locs_json = P_interim_date / f'locations/{loc}/page{page}.json.gz'
    if P_locs_json.exists() and not overwrite:
        if verbose:
            print('Reading:', P_locs_json)
        with gzip.open(P_locs_json, "rt", encoding='utf-8') as f:
            jobs_dict = json.load(f)
    else:
        # _suffix = f'?jobTitle={loc}&location=united-states'
        loc_json_url = f'{HIRING_CAFE_}{_NEXT_PREFIX}/jobs/locations/{loc}.json?page={page}'
        loc_json = request_get(loc_json_url, proxy=proxy)

        write_data(P_locs_json, loc_json, verbose=verbose)
    try:
        if not jobs_dict['pageProps']['ssrIsLastPage']:
            sleep(0.2, 0.5)
            load_locs(loc, verbose=verbose, page=page+1)
    except KeyError:
        print(P_locs_json)
        raise

    return jobs_dict

COMPANY_QUERY = "?loc=eyJmIjoiQ2FsaWZvcm5pYSwgVW5pdGVkIFN0YXRlcyIsInQiOlsiYWRtaW5pc3RyYXRpdmVfYXJlYV9sZXZlbF8xIl0sImFjIjpbeyJsIjoiQ2FsaWZvcm5pYSIsInMiOiJDQSIsInQiOlsiYWRtaW5pc3RyYXRpdmVfYXJlYV9sZXZlbF8xIl19LHsibCI6IlVuaXRlZCBTdGF0ZXMiLCJzIjoiVVMiLCJ0IjpbImNvdW50cnkiXX1dfQ&rt=Individual+Contributor"
def load_company(company='komodohealth.com', overwrite=False, verbose=False) -> dict:
    P_company_json = P_interim_date / f'company/{company}/page0.json.gz'
    if P_company_json.exists() and not overwrite:
        if verbose:
            print('Reading:', P_company_json)
        with gzip.open(P_company_json, "rt", encoding='utf-8') as f:
            jobs_dict = json.load(f)
    else:
        # _suffix = f'?jobTitle={company}&companyation=united-states'
        company_json_url = f'{HIRING_CAFE_}{_NEXT_PREFIX}/jobs/company/{company}.json{COMPANY_QUERY}'
        company_json = request_get(company_json_url)

        if verbose:
            print('Saving:', P_company_json)
        P_company_json.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(P_company_json, "wt", encoding="utf-8") as f:
            jobs_dict = json.loads(company_json)
            json.dump(jobs_dict, f)

    return jobs_dict


def load_boards(board=HEALTH, overwrite=False, verbose=True, pages=100, driver=None):
    page = 0
    if pages is None:
        pages = 1000

    jobs_dict_list = [jobs_dict := load_board(board, overwrite, verbose, page, driver)]
    while not jobs_dict.get('props', jobs_dict)['pageProps']['isLastPage'] and page < pages:
        page += 1
        jobs_dict_list.append(jobs_dict := load_board(board, overwrite, verbose, page, driver))
    return jobs_dict_list


def load_board(board=HEALTH, overwrite=False, verbose=True, page=0, driver=None):
    assert isinstance(page, int) and page >= 0

    P_jobs_json = P_interim_date / f'{board}/page{page}.json.gz'
    # P_jobs_html = P_interim_date / f'{board}/page{page}.html'
    if P_jobs_json.exists() and not overwrite:
        jobs_dict = read_data(P_jobs_json, verbose=True)
    else:
        board_json_url = f'{HIRING_CAFE}/{_NEXT_PREFIX}/b/{board}.json'
        url = f'{board_json_url}?page={page}'
        job_title_json = requests_get(url)
        try:
            jobs_dict = json.loads(job_title_json)
        except json.decoder.JSONDecodeError:
            board_url = f'{HIRING_CAFE}/b/{board}?page={page}'
            url_get_content = selenium_get(board_url, proxy=False, driver=driver)#
            # with open(P_jobs_html, "w", encoding="utf-8") as f:
            #     f.write(url_get_content)
            root = lxml.html.fromstring(url_get_content)
            _next_data_list = root.xpath("//script[@id='__NEXT_DATA__']")
            if len(_next_data_list) == 0:
                jobs_dict = {}
            else:
                _next_data = root.xpath("//script[@id='__NEXT_DATA__']")[0]
                jobs_dict = json.loads(_next_data.text_content())
                jobs_dict = jobs_dict.get('props', jobs_dict)
        except Exception:
            print(f'{HIRING_CAFE}/b/{board}')
            return None

        if not jobs_dict:
            print("ERROR")
            return None
        write_data(P_jobs_json, jobs_dict, verbose=verbose)

    # if not jobs_dict['pageProps']['isLastPage']:
    #     load_ds_ca(board, verbose=verbose, page=page+1)

    return jobs_dict

@cache
def requests_get(url, start=0.2, end=0.5):
    _user_agent = USER_AGENT_106
    _headers = {
        "User-Agent": _user_agent,
        "Referer": "https://hiring.cafe/",
        "Origin": "https://hiring.cafe",
        "Sec-Fetch-Dest": "empty",
    }
    response = requests.get(url, headers=_headers)
    html_string = response.content.decode()
    sleep(start, end)
    return html_string

@cache
def selenium_get(url, wait_time=2, proxy=False, driver=None):
    close_driver = False
    if driver is None:
        close_driver = True
        driver = init_driver(proxy=proxy, headless=False)
    # wait = WebDriverWait(driver, 2)
    driver.get(url)
    # scroll_bottom(driver, wait_time=1)
    try:
        # wait.until(EC.visibility_of_element_located((By.XPATH, ".//article")))
        driver.wait_for_element("#__NEXT_DATA__")
    except Exception:
        pass
    scroll_bottom(driver, wait_time=wait_time)
    time.sleep(random.uniform(0, 0.3))
    # body = wait.until(EC.visibility_of_element_located((By.XPATH, "/body")))
    # outerHTML = body.get_attribute("outerHTML")
    html_source = driver.page_source
    if close_driver:
        driver.close()
    return html_source


def scroll_bottom(driver, scroll_pause_time=0.5, wait_time=3):
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
def request_get(url, proxy=False):
    _user_agent = UserAgent().get_random_cycled()
    _headers = {
        "User-Agent": _user_agent,
        "Referer": "https://hiring.cafe/",
        "Origin": "https://hiring.cafe",
        "Sec-Fetch-Dest": "empty",
    }
    if proxy:
        ii = random.randint(1, 44745)
        PROXY = f"byfdawqz-US-{ii}:fhx888ooginw@p.webshare.io:80"
        _headers["proxy"] = {
            "http": PROXY,
            "https": PROXY,
        }
    response = request.get(url, headers=_headers)
    response.raise_for_status()
    html_string = response.content.decode()
    return html_string

def sleep(start=1, end=3):
    time.sleep(random.uniform(start, end))


def read_data(P_dict: Path, verbose=False):
    if verbose:
        print("Reading:", P_dict)
    if P_dict.name.endswith('.json.gz'):
        with gzip.open(P_dict, "rt", encoding='utf-8') as f:
            data = json.load(f)
    elif P_dict.name.endswith('.json'):
        with open(P_dict, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        with open(P_dict, 'rb') as f:
            data = pickle.load(f)
    return data


def write_data(P_dict: Path, data: dict | str, verbose=True):
    jobs_dict = data
    if isinstance(data, str):
        jobs_dict = json.loads(data)

    if verbose:
        print("Writing:", P_dict)
    P_dict.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(P_dict, "wt", encoding="utf-8") as f:
        json.dump(jobs_dict, f)


@cache
def load_json_gz(glob_str=GLOB_STR, metadata=False):
    json_gz_paths = sorted([Path(path) for path in glob.glob(glob_str, recursive=True)])
    try:
        pl_df = pl.read_ndjson(json_gz_paths)
        _pageProps = pl_df['pageProps'].to_pandas()
    # except pl.ComputeError:
    except Exception:
        json_gz_list = []
        for P_json_gz in tqdm(json_gz_paths):
            _json_gz_df = pd.read_json(P_json_gz, lines=True, compression='gzip')
            json_gz_list.append(_json_gz_df)
        pl_df = pd.concat(json_gz_list)
        _pageProps = pl_df['pageProps']

    json_gz_df = pd.DataFrame({
        'hits': _pageProps.str['hits'],
    })
    if metadata:
        json_gz_df['st_mtime'] = pd.to_datetime([p.stat().st_mtime for p in json_gz_paths], unit='s')
        json_gz_df['st_size'] = [p.stat().st_size for p in json_gz_paths]

    df = json_gz_df.explode('hits')
    job = df['hits']
    job_info = job.str['job_information']
    v5_processed = job.str['v5_processed_job_data']
    v5_company_data = job.str['v5_processed_company_data'].apply(lambda x: x if isinstance(x, dict) else {})
    company_data = job.str['enriched_company_data']

    df['requisition_id'] = job.str['requisition_id']
    df['job_id'] = job.str['id']
    df['board_token'] = job.str['board_token'].astype(str)
    df['source'] = job.str['source']
    df['apply_url'] = job.str['apply_url']
    df['collapse_key'] = job.str['collapse_key']
    df['is_expired'] = job.str['is_expired']

    # Job information
    df['title'] = job_info.str['title']
    df['job_title_raw'] = job_info.str['job_title_raw']
    df['description'] = job_info.str['description']
    df['core_job_title'] = v5_processed.str['core_job_title']
    df['requirements_summary'] = v5_processed.str['requirements_summary']

    # Structured data
    df['technical_tools'] = v5_processed.str['technical_tools']
    df['licenses_certifications'] = v5_processed.str['licenses_or_certifications']
    df['role_activities'] = v5_processed.str['role_activities']
    df['language_requirements'] = v5_processed.str['language_requirements']

    # Degree requirements
    df['associates_degree_requirement'] = v5_processed.str['associates_degree_requirement']
    df['associates_degree_fields'] = v5_processed.str['associates_degree_fields_of_study']
    df['bachelors_degree_requirement'] = v5_processed.str['bachelors_degree_requirement']
    df['bachelors_degree_fields'] = v5_processed.str['bachelors_degree_fields_of_study']
    df['masters_degree_requirement'] = v5_processed.str['masters_degree_requirement']
    df['masters_degree_fields'] = v5_processed.str['masters_degree_fields_of_study']
    df['doctorate_degree_requirement'] = v5_processed.str['doctorate_degree_requirement']
    df['doctorate_degree_fields'] = v5_processed.str['doctorate_degree_fields_of_study']
    df['is_high_school_required'] = v5_processed.str['is_high_school_required']

    # Experience requirements
    df['min_industry_role_yoe'] = v5_processed.str['min_industry_and_role_yoe']
    df['is_min_industry_role_yoe_not_mentioned'] = v5_processed.str['is_min_industry_and_role_yoe_not_mentioned']
    df['min_management_leadership_yoe'] = v5_processed.str['min_management_and_leadership_yoe']
    df['is_min_management_leadership_yoe_not_mentioned'] = v5_processed.str['is_min_management_and_leadership_yoe_not_mentioned']

    # Role details
    df['job_category'] = v5_processed.str['job_category']
    df['commitment'] = v5_processed.str['commitment']
    df['role_type'] = v5_processed.str['role_type']
    df['seniority_level'] = v5_processed.str['seniority_level']

    # Workplace
    df['workplace_type'] = v5_processed.str['workplace_type']
    df['workplace_physical_environment'] = v5_processed.str['workplace_physical_environment']
    df['formatted_workplace_location'] = v5_processed.str['formatted_workplace_location']
    df['is_workplace_worldwide_ok'] = v5_processed.str['is_workplace_worldwide_ok']
    df['workplace_cities'] = v5_processed.str['workplace_cities']
    df['workplace_counties'] = v5_processed.str['workplace_counties']
    df['workplace_states'] = v5_processed.str['workplace_states']
    df['workplace_countries'] = v5_processed.str['workplace_countries']
    df['workplace_continents'] = v5_processed.str['workplace_continents']
    df['boundless_workplace_states'] = v5_processed.str['boundless_workplace_states']
    df['boundless_workplace_countries'] = v5_processed.str['boundless_workplace_countries']
    df['boundless_workplace_continents'] = v5_processed.str['boundless_workplace_continents']
    df['number_of_workplace_cities'] = v5_processed.str['number_of_workplace_cities']
    df['number_of_workplace_counties'] = v5_processed.str['number_of_workplace_counties']
    df['number_of_workplace_states'] = v5_processed.str['number_of_workplace_states']
    df['number_of_workplace_countries'] = v5_processed.str['number_of_workplace_countries']
    df['number_of_workplace_continents'] = v5_processed.str['number_of_workplace_continents']

    # Work conditions
    df['oral_communication_level'] = v5_processed.str['oral_communication_level']
    df['physical_labor_intensity'] = v5_processed.str['physical_labor_intensity']
    df['physical_position'] = v5_processed.str['physical_position']
    df['computer_usage'] = v5_processed.str['computer_usage']
    df['cognitive_demand'] = v5_processed.str['cognitive_demand']
    df['air_travel_requirement'] = v5_processed.str['air_travel_requirement']
    df['land_travel_requirement'] = v5_processed.str['land_travel_requirement']
    df['morning_shift_work'] = v5_processed.str['morning_shift_work']
    df['evening_shift_work'] = v5_processed.str['evening_shift_work']
    df['overnight_work'] = v5_processed.str['overnight_work']
    df['on_call_requirement'] = v5_processed.str['on_call_requirement']
    df['weekend_availability_required'] = v5_processed.str['weekend_availability_required']
    df['holiday_availability_required'] = v5_processed.str['holiday_availability_required']
    df['overtime_required'] = v5_processed.str['overtime_required']

    # Compensation
    df['yearly_min_compensation'] = v5_processed.str['yearly_min_compensation']
    df['yearly_max_compensation'] = v5_processed.str['yearly_max_compensation']
    df['monthly_min_compensation'] = v5_processed.str['monthly_min_compensation']
    df['monthly_max_compensation'] = v5_processed.str['monthly_max_compensation']
    df['weekly_min_compensation'] = v5_processed.str['weekly_min_compensation']
    df['weekly_max_compensation'] = v5_processed.str['weekly_max_compensation']
    df['hourly_min_compensation'] = v5_processed.str['hourly_min_compensation']
    df['hourly_max_compensation'] = v5_processed.str['hourly_max_compensation']
    df['biweekly_min_compensation'] = v5_processed.str['bi-weekly_min_compensation']
    df['biweekly_max_compensation'] = v5_processed.str['bi-weekly_max_compensation']
    df['daily_min_compensation'] = v5_processed.str['daily_min_compensation']
    df['daily_max_compensation'] = v5_processed.str['daily_max_compensation']
    df['is_compensation_transparent'] = v5_processed.str['is_compensation_transparent']
    df['listed_compensation_currency'] = v5_processed.str['listed_compensation_currency']
    df['listed_compensation_frequency'] = v5_processed.str['listed_compensation_frequency']

    # Benefits
    df['four_oh_one_k_matching'] = v5_processed.str['401k_matching']
    df['generous_paid_time_off'] = v5_processed.str['generous_paid_time_off']
    df['four_day_work_week'] = v5_processed.str['four_day_work_week']
    df['tuition_reimbursement'] = v5_processed.str['tuition_reimbursement']
    df['retirement_plan'] = v5_processed.str['retirement_plan']
    df['generous_parental_leave'] = v5_processed.str['generous_parental_leave']
    df['fair_chance'] = v5_processed.str['fair_chance']
    df['visa_sponsorship'] = v5_processed.str['visa_sponsorship']
    df['relocation_assistance'] = v5_processed.str['relocation_assistance']
    df['military_veterans'] = v5_processed.str['military_veterans']

    # Other
    df['security_clearance'] = v5_processed.str['security_clearance']
    df['is_driver_license_required'] = v5_processed.str['is_driver_license_required']
    df['position_employer_type'] = v5_processed.str['position_employer_type']
    df['company_sector_and_industry'] = v5_processed.str['company_sector_and_industry']

    # Dates
    _estimated_publish_date = v5_processed.str['estimated_publish_date']
    # if isinstance(_estimated_publish_date, int):
    #     _estimated_publish_date = datetime.fromtimestamp(_estimated_publish_date / 1000)
    df['estimated_publish_date'] = _estimated_publish_date
    df['estimated_publish_date_millis'] = v5_processed.str['estimated_publish_date_millis']

    _v5_is_public = v5_company_data.str['is_public']
    # _v5_org_type = {True: 'Public', False: 'Private'}.get(_v5_is_public)
    # if v5_company_data.get('is_non_profit'):
    #     _v5_org_type = 'Non-Profit'
    _v5_org_type = _v5_is_public.map({True: 'Public', False: 'Private'})
    _v5_org_type.loc[v5_company_data.str['is_non_profit'].astype(bool)] = 'Non-Profit'

    df = pd.concat([df,
        # User interactions
        job_info.str['hiddenFromUsers'].rename('hiddenFromUsers'),
        job_info.str['viewedByUsers'].rename('viewedByUsers'),
        job_info.str['applied_from_users'].rename('applied_from_users'),

        # Enriched Company data (embedded)
        company_data.str['enriched_at'].rename('company_enriched_at'),
        company_data.str['status'].rename('company_status'),
        company_data.str['name'].fillna(v5_processed.str['company_name']).fillna(v5_company_data.str['name']).rename('company_name'),
        company_data.str['homepage_uri'].fillna(v5_processed.str['company_website']).fillna(v5_company_data.str['website']).rename('company_homepage_uri'),
        company_data.str['hq_country'].fillna(v5_company_data.str['headquarters_country']).rename('company_hq_country'),
        company_data.str['parent_company'].fillna(v5_company_data.str['parent_company']).rename('company_parent_company'),
        company_data.str['subsidiaries'].fillna(v5_company_data.str['subsidiaries']).rename('company_subsidiaries'),
        company_data.str['industries'].fillna(v5_company_data.str['industries']).rename('company_industries'),
        company_data.str['activities'].fillna(v5_processed.str['company_activities']).fillna(v5_company_data.str['activities']).apply(lambda x: x if isinstance(x, list) else []).rename('company_activities'),
        company_data.str['nb_employees'].fillna(v5_company_data.str['number_employees'].astype(float)).rename('company_nb_employees'),
        company_data.str['year_founded'].fillna(v5_company_data.str['year_founded'].astype(float)).rename('company_year_founded'),
        company_data.str['tagline'].fillna(v5_processed.str['tagline']).fillna(v5_company_data.str['tagline']).rename('company_tagline'),
        company_data.str['organization_type'].fillna(_v5_org_type).rename('company_organization_type'),
        company_data.str['latest_funding_investors'].fillna(v5_company_data.str['investors']).rename('company_latest_funding_investors)'),
        company_data.str['latest_funding_type'].fillna(v5_company_data.str['latest_funding_series']).rename('company_latest_funding_type'),
        company_data.str['latest_funding_year'].fillna(v5_company_data.str['latest_funding_year'].astype(float)).rename('company_latest_funding_year'),
        company_data.str['latest_funding_amount'].fillna(v5_company_data.str['latest_funding_amount'].astype(float)).rename('company_latest_funding_amount'),
        company_data.str['stock_exchange'].fillna(v5_company_data.str['stock_exchange']).rename('company_stock_exchange'),
        company_data.str['stock_symbol'].fillna(v5_company_data.str['stock_exchange']).rename('company_stock_symbol'),

        # Extract location arrays
        job.str['_geoloc'].apply(lambda x: x if isinstance(x, list) else []).apply(lambda x_list: [x.get('lon') for x in x_list] if not isinstance(x_list, float) else []).rename('location_longitudes'),
        job.str['_geoloc'].apply(lambda x: x if isinstance(x, list) else []).apply(lambda x_list: [x.get('lat') for x in x_list] if not isinstance(x_list, float) else []).rename('location_latitudes'),
    ], axis=1).drop(columns='hits').reset_index(drop=True)
    return df

def save_hash(_hash, driver=None):
    P_url = P_CACHE / 'url' / f'{_hash}.html'
    P_json = P_CACHE / 'json' / f'{_hash}.json.gz'
    if P_url.exists():
        return

    url = JOB_HTTPS + _hash
    # print(url)

    # url_get_content = selenium_get(url, driver=driver)
    try:
        url_get_content = requests_get(url)
    except Exception:
        if driver is None:
            driver = init_driver()
        url_get_content = selenium_get(url, driver=driver)

    root = lxml.html.fromstring(url_get_content)
    _next_data_list = root.xpath("//script[@id='__NEXT_DATA__']")
    if len(_next_data_list) == 0:
        jobs_dict = {}
        print(url)
        return
    else:
        _next_data = root.xpath("//script[@id='__NEXT_DATA__']")[0]
        jobs_dict = json.loads(_next_data.text_content())
        jobs_dict = jobs_dict.get('props', jobs_dict)

    write_data(P_json, jobs_dict)
    with open(P_url, "w", encoding="utf-8") as f:
        f.write(url_get_content)
    sleep(0.2, 0.5)



if __name__ == "__main__":
    from itertools import chain

    from tqdm import tqdm

    LOAD_SITEMAPS = False
    LOAD_TITLES = False
    LOAD_LOCATIONS = False
    LOAD_COMPANIES = False
    PAGES = 5
    # PAGES = 100

    if LOAD_SITEMAPS:
        load_sitemap('jobs-sitemap')
        # load_sitemap(SITEMAP_COMPANIES)
        # load_sitemap(SITEMAP_LOCATIONS)
        # load_sitemap(SITEMAP_JOB_TITLES)
        # load_sitemap(SITEMAP_INDEX)

    if LOAD_TITLES:
        ds_job_titles = load_ds_job_titles()

        jobs_json_list = [P_interim_date / f'jobs/{job_title}/page0.json.gz'
                            for job_title in ds_job_titles]
        _list = [path for path in jobs_json_list if not path.exists()]
        for job_title in (pbar := tqdm(ds_job_titles)):
            P_jobs_json = P_interim_date / f'jobs/{job_title}/page0.json.gz'
            if P_jobs_json.exists():
                continue

            load_jobs(job_title, verbose=False, proxy=False)
            sleep(0.2, 0.5)
            pbar.set_description(job_title)


    ################################################################################
    if LOAD_LOCATIONS:
        locations_df = load_sitemap(SITEMAP_LOCATIONS)
        locations = locations_df['sitemap'].str.removeprefix('jobs/locations/')
        california_mask = locations.str.contains(r'\bcalifornia')
        # ca_locations = locations[california_mask].str.removesuffix('-california')
        ca_locations = locations[california_mask]

        jobs_json_list = [P_interim_date / f'locations/{loc}/page0.json.gz'
                          for loc in ca_locations]
        _list = [path for path in jobs_json_list if not path.exists()]
        # for loc in (pbar := tqdm(ca_locations)):
        for ii, loc in enumerate(ca_locations):
            P_jobs_json = P_interim_date / f'locations/{loc}/page0.json.gz'
            if P_jobs_json.exists():
                continue

            print(ii, loc)
            load_locs(f'{loc}', verbose=False, proxy=False)
            sleep(0.2, 0.5)
            pbar.set_description(loc)
    ################################################################################
    # companies_df = load_sitemap(SITEMAP_COMPANIES)
    # companies = companies_df['sitemap'].str.removeprefix('company/')

    driver = init_driver(headless=False)
    health_boards_list = load_boards(HEALTH, verbose=True, pages=PAGES, driver=driver)
    da_health_boards_list = load_boards(DA_HEALTH, verbose=True, pages=PAGES, driver=driver)
    ds_sf_boards_list = load_boards(DS_SF, verbose=True, pages=PAGES, driver=driver)
    da_sf_boards_list = load_boards(DA_SF, verbose=True, pages=PAGES, driver=driver)
    driver.quit()#

    if LOAD_COMPANIES:
        boards_list = [*health_boards_list, *da_health_boards_list, *ds_sf_boards_list, *da_sf_boards_list]
        hits_list = chain.from_iterable([board['pageProps']['hits'] for board in boards_list])
        homepage_uri_list = [hit.get('enriched_company_data', {}).get('homepage_uri', None) for hit in hits_list]
        companies = pd.Series(homepage_uri_list).drop_duplicates().dropna().sort_values()

        jobs_json_list = [P_interim_date / f'company/{company}/page0.json.gz'
                        for company in companies]
        _list = [path for path in jobs_json_list if not path.exists()]
        N_companies = len(companies)
        for ii, company in enumerate(companies):
            P_jobs_json = P_interim_date / f'company/{company}/page0.json.gz'
            if P_jobs_json.exists():
                continue

            print(f'{ii}/{N_companies}, {company}')
            load_company(f'{company}', verbose=False)
            sleep(0.2, 0.5)
            # pbar.set_description(company)

    ii = 1
    _boards = [*health_boards_list, *da_health_boards_list, *ds_sf_boards_list, *da_sf_boards_list]
    N = sum([len(b['pageProps']['hits']) for b in _boards])
    for board in _boards:
        for hit in board['pageProps']['hits']:
            print(ii, 'of', N, _hash := hit['requisition_id'])
            save_hash(_hash)
            ii += 1

    # all_df = pd.read_parquet(P_CACHE / 'ALL.parquet')
    # for i, _hash in enumerate(all_df['requisition_id']):
    #     print(i, ii, _hash)
    #     save_hash(_hash)
    #     ii += 1
