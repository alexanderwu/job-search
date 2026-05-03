from functools import cache
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
import pandas as pd
import requests
from tqdm import tqdm

from job_search.config import P_INTERIM, P_RAW
from job_search.utils import now

USER_AGENT_106 = 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.37'
HIRING_CAFE = "https://hiring.cafe"
HIRING_CAFE_ = "https://hiring.cafe/"
# _NEXT_PREFIX = "_next/data/KHL6pwrRx0qXfmkGIviUb"
# _NEXT_PREFIX = "_next/data/oRfiWtg_9xPWJQJPky-_H/"
# _NEXT_PREFIX = "_next/data/HL5jWvetFxVKM-S9HY3Et"
# _NEXT_PREFIX = "_next/data/hfnlOHQswTqpgwl1YXesc"
_NEXT_PREFIX = "_next/data/Nen3D_K_gniIeb-kIa9UW"
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
DS_SF = 'ds-sf-remote-77r5vzr1'
HEALTH = 'healthcare-9ierbt6f'
BOARD_URL = f'{HIRING_CAFE}/{_NEXT_PREFIX}/b/{HEALTH}.json'
# BOARD_URL = f'{HIRING_CAFE}/{_NEXT_PREFIX}/b/{DS_CA}.json'


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
        # if verbose:
        #     print('Reading:', P_locs_json)
        # with gzip.open(P_locs_json, "rt", encoding='utf-8') as f:
        #     jobs_dict = json.load(f)
    else:
        # _suffix = f'?jobTitle={loc}&location=united-states'
        loc_json_url = f'{HIRING_CAFE_}{_NEXT_PREFIX}/jobs/locations/{loc}.json'
        loc_json = request_get(loc_json_url, proxy=proxy)

        write_data(P_locs_json, loc_json, verbose=verbose)
        # if verbose:
        #     print('Saving:', P_locs_json)
        # P_locs_json.parent.mkdir(parents=True, exist_ok=True)
        # with gzip.open(P_locs_json, "wt", encoding="utf-8") as f:
        #     jobs_dict = json.loads(loc_json)
        #     json.dump(jobs_dict, f)

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
        # if verbose:
        #     print('Saving:', P_locs_json)
        # P_locs_json.parent.mkdir(parents=True, exist_ok=True)
        # with gzip.open(P_locs_json, "wt", encoding="utf-8") as f:
        #     jobs_dict = json.loads(loc_json)
        #     json.dump(jobs_dict, f)

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


def load_boards(board=HEALTH, overwrite=False, verbose=True):
    page = 0
    jobs_dict_list = [jobs_dict := load_board(board, overwrite, verbose, page)]
    while not jobs_dict['pageProps']['isLastPage']:
        page += 1
        jobs_dict_list.append(jobs_dict := load_board(board, overwrite, verbose, page))
    return jobs_dict_list


def load_board(board=HEALTH, overwrite=False, verbose=True, page=0):
    assert isinstance(page, int) and page >= 0

    P_jobs_json = P_interim_date / f'{board}/page{page}.json.gz'
    if P_jobs_json.exists() and not overwrite:
        jobs_dict = read_data(P_jobs_json, verbose=True)
    else:
        board_url = f'{HIRING_CAFE}/{_NEXT_PREFIX}/b/{board}.json'
        url = f'{board_url}?page={page}'
        job_title_json = requests_get(url)
        try:
            jobs_dict = json.loads(job_title_json)
        except json.decoder.JSONDecodeError:
            print(f'{HIRING_CAFE}/b/{board}')
            return {}
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


if __name__ == "__main__":
    from itertools import chain

    from tqdm import tqdm

    LOAD_SITEMAPS = True
    LOAD_TITLES = False
    LOAD_LOCATIONS = False
    LOAD_COMPANIES = True

    if LOAD_SITEMAPS:
        load_sitemap(SITEMAP_COMPANIES)
        load_sitemap(SITEMAP_LOCATIONS)
        load_sitemap(SITEMAP_JOB_TITLES)
        load_sitemap(SITEMAP_INDEX)

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
            load_locs(f'{loc}', verbose=False, proxy=True)
            sleep(0.2, 0.5)
            pbar.set_description(loc)
    ################################################################################
    # companies_df = load_sitemap(SITEMAP_COMPANIES)
    # companies = companies_df['sitemap'].str.removeprefix('company/')

    health_boards_list = load_boards(HEALTH, verbose=True)
    ds_sf_boards_list = load_boards(DS_SF, verbose=True)
    boards_list = [*health_boards_list, *ds_sf_boards_list]

    if LOAD_COMPANIES:
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