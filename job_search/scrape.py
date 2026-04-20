from functools import cache
import gzip
import json
from pathlib import Path
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
_NEXT_PREFIX = "_next/data/KHL6pwrRx0qXfmkGIviUb"
P_raw_date = P_RAW / now(time=False).replace('-', '/')
P_interim_date = P_INTERIM / now(time=False).replace('-', '/')

SITEMAP = 'sitemap'
SITEMAP_INDEX = 'sitemap-index'
SITEMAP_COMPANIES = 'sitemap-companies-index'
SITEMAP_JOB_TITLES = 'sitemap-job-titles-index'
SITEMAP_LOCATIONS = 'sitemap-locations-index'


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


@cache
def load_jobs(job_title='data-scientist', overwrite=False, verbose=True) -> dict:
    if overwrite:
        return _load_jobs.__wrapped__(job_title, overwrite, verbose)
    return _load_jobs(job_title, overwrite, verbose)


def _load_jobs(job_title='data-scientist', overwrite=False, verbose=True) -> dict:
    P_jobs_json = P_interim_date / f'jobs/{job_title}/page.json.gz'
    if P_jobs_json.exists() and not overwrite:
        if verbose:
            print('Reading:', P_jobs_json)
        with gzip.open(P_jobs_json, "rt", encoding='utf-8') as f:
            jobs_dict = json.load(f)
            return jobs_dict

    # _suffix = f'?jobTitle={job_title}&location=united-states'
    job_title_json_url = f'{HIRING_CAFE_}{_NEXT_PREFIX}/jobs/{job_title}/locations/united-states.json'
    job_title_json = requests_get(job_title_json_url)

    if verbose:
        print('Saving:', P_jobs_json)
    P_jobs_json.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(P_jobs_json, "wt", encoding="utf-8") as f:
        jobs_dict = json.loads(job_title_json)
        json.dump(jobs_dict, f)

    return jobs_dict


DS_CA = 'ds-ca-2tzfqdib'
BOARD_URL = f'{HIRING_CAFE}/{_NEXT_PREFIX}/b/{DS_CA}.json'
def load_ds_ca(board=DS_CA, overwrite=False, verbose=True, page=0):
    assert isinstance(page, int) and page >= 0

    P_jobs_json = P_interim_date / f'{board}/page{page}.json.gz'
    if P_jobs_json.exists() and not overwrite:
        if verbose:
            print('Reading:', P_jobs_json)
        with gzip.open(P_jobs_json, "rt", encoding='utf-8') as f:
            jobs_dict = json.load(f)
    else:
        board_url = f'{HIRING_CAFE}/{_NEXT_PREFIX}/b/{DS_CA}.json'
        url = f'{board_url}?page={page}'
        job_title_json = requests_get(url)
        if verbose:
            print('Saving:', P_jobs_json)
        P_jobs_json.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(P_jobs_json, "wt", encoding="utf-8") as f:
            jobs_dict = json.loads(job_title_json)
            json.dump(jobs_dict, f)

    if not jobs_dict['pageProps']['isLastPage']:
        sleep()
        load_ds_ca(board, verbose=verbose, page=page+1)

    return jobs_dict

@cache
def requests_get(url, proxy=False):
    _user_agent = USER_AGENT_106
    _headers = {
        "User-Agent": _user_agent,
        "Referer": "https://hiring.cafe/",
        "Origin": "https://hiring.cafe",
        "Sec-Fetch-Dest": "empty",
        # 'proxy': {
        #     'http': PROXY,
        #     'https': PROXY,
        # }
    }
    if proxy:
        ii = random.randint(1, 44745)
        PROXY = f"byfdawqz-US-{ii}:fhx888ooginw@p.webshare.io:80"
        _headers["proxy"] = {
            "http": PROXY,
            "https": PROXY,
        }
    response = requests.get(url, headers=_headers)
    html_string = response.content.decode()
    return html_string


@cache
def request_get(url, proxy=False):
    _user_agent = UserAgent().get_random_cycled()
    # _user_agent = USER_AGENT_106
    _headers = {
        "User-Agent": _user_agent,
        "Referer": "https://hiring.cafe/",
        "Origin": "https://hiring.cafe",
        "Sec-Fetch-Dest": "empty",
        # 'proxy': {
        #     'http': PROXY,
        #     'https': PROXY,
        # }
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
    time.sleep(random.uniform(1,3))




if __name__ == "__main__":
    from tqdm import tqdm

    ds_job_titles = load_ds_job_titles()

    jobs_json_list = [P_interim_date / f'jobs/{job_title}/page.json.gz'
                        for job_title in ds_job_titles]
    _list = [path for path in jobs_json_list if not path.exists()]
    for job_title in tqdm(ds_job_titles):
        P_jobs_json = P_interim_date / f'jobs/{job_title}/page.json.gz'
        if P_jobs_json.exists():
            continue

        jobs_dict = load_jobs(job_title, verbose=False)
        sleep(0.5, 1.5)
