#!/usr/bin/env python3
"""
Download job description
"""

from functools import cache
from itertools import chain
import json
import logging
from pathlib import Path
import pickle
import random
import re
from textwrap import dedent
import time
import urllib.parse
from warnings import filterwarnings

from botasaurus.user_agent import UserAgent
from botasaurus_requests import request
import lxml
import lxml.html
from markdownify import markdownify as md

# from markdown_it import MarkdownIt
# from mdit_py_plugins.front_matter import front_matter_plugin
# from mdit_py_plugins.wordcount import wordcount_plugin
import numpy as np
import pandas as pd
from selenium.webdriver.common.by import By
from tqdm import TqdmExperimentalWarning
from tqdm.rich import tqdm

from job_search.config import (
    # P_ALL_COMPANY_URLS,
    # P_CACHE,
    P_DATA,
    P_DATE,
    P_DICT,
    P_JOBS,
    P_QUERY,
    P_STEM,
    P_STEM_PREV,
    P_URLS,
    QUERY_LIST,
    VIEW_JOB_HTTPS,
)
from job_search.utils import is_running_wsl

filterwarnings("ignore", category=TqdmExperimentalWarning)

# Selenium options
SCROLL_PAUSE_TIME = 0.5
WAIT_TIME = 10


def init_driver(headless=True, proxy=False):
    from seleniumbase import Driver

    PROXY = None
    # Use proxy. Format: "SERVER:PORT" or "USER:PASS@SERVER:PORT".
    if proxy:
        ii = random.randint(1, 44745)
        PROXY = f"byfdawqz-US-{ii}:fhx888ooginw@p.webshare.io:80"

    if is_running_wsl():
        driver = Driver(uc=True, proxy=PROXY, headless=False)
    else:
        driver = Driver(uc=True, proxy=PROXY, headless=headless)
    return driver


################################################################################
# Main Functions
################################################################################


def main0(path_query: Path, overwrite=False, bare=False, proxy=False) -> Path:
    """
    Get data/ds.html to prepare job cards
    """
    # datetime_now = now(time=True)
    P_save = P_DATE / f"{path_query.stem}/{path_query.stem}.html"
    P_save.parent.mkdir(parents=True, exist_ok=True)
    query_url = load_query_url(path_query)
    if bare:
        print(path_query)

    if not overwrite and P_save.exists():
        log(P_save).info(f"{P_save} already exists...")
        return P_save

    query_dict: dict = parse_query_url(query_url)
    P_query = P_save.parent / f"{P_save.stem}.txt"
    P_json = P_save.parent / f"{P_save.stem}.json"
    log(P_save).info(f"Preparing {P_save} outerHTML from {P_query}...")
    with open(P_query, "w") as f:
        f.write(query_url)
    with open(P_json, "w") as f:
        json.dump(query_dict, f, indent=4)

    def _format_loc(loc):
        _address = loc["address_components"][0]["long_name"].replace("+", " ")
        _radius = (
            f" - {loc['options']['radius']} {loc['options']['radius_unit']}"
            if loc["options"].keys()
            else ""
        )
        _workplaces = " | ".join(loc["workplace_types"])
        loc_formatted = f"{_address}{_radius}. {_workplaces}"
        return loc_formatted

    _job_title_query = query_dict["jobTitleQuery"].replace("+", " ").replace("AND", "\n\tAND")
    _locations = "\n\t".join([_format_loc(loc) for loc in query_dict["locations"]])
    _commitment_types = ", ".join(query_dict["commitmentTypes"]).replace("+", " ")
    _query_str = dedent(f"""{_job_title_query}
        {_locations}
        {_commitment_types}
    """)
    log(P_save).info(_query_str)

    if bare:
        scroll_jobs_outer_html = ""
        _title = f"{P_save.stem} (N=)"
        _data = dict(body=scroll_jobs_outer_html, title=_title, description=query_url)
        scroll_jobs_html = render_template(**_data).replace("</source>", "")
        with open(P_save, "w", encoding="utf-8") as f:
            f.write(scroll_jobs_html)
        return P_save

    driver = init_driver(headless=False, proxy=proxy)
    driver.maximize_window()
    driver.get(query_url)
    time.sleep(2)
    scroll_bottom(driver)

    _SCROLL_XPATH = "//div[@class='infinite-scroll-component__outerdiv']"
    try:
        # scroll_jobs = wait.until(EC.visibility_of_element_located((By.XPATH, _SCROLL_XPATH)))
        scroll_jobs = driver.wait_for_element(_SCROLL_XPATH)
        scroll_jobs_outer_html = scroll_jobs.get_attribute("outerHTML")
    # except TimeoutException:
    except Exception:
        log(P_save).warning(f"Could not save {P_save}...")
        scroll_jobs_outer_html = ""
        input("Press ENTER to continue...")

    # _CLASS = "//div[@class='relative bg-white rounded-xl border border-gray-200 shadow hover:border-gray-500 md:hover:border-gray-200']"
    # N = len(lxml.html.fromstring(scroll_jobs_outer_html).xpath(_CLASS))
    _grid = driver.find_element(
        "div[class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-x-4 gap-y-12 md:gap-x-10 px-4 md:px-8 xl:px-16 pb-4']"
    )
    N = len(_grid.find_elements(By.XPATH, "./*"))
    log(P_save).info(f"Saving {P_save} (N={N})...")

    ## Expand job cards
    # N_clicks = len(driver.find_elements("button[class='rounded-full bg-gray-400 w-1.5 h-1.5 flex-none']"))
    # log(P_save).info(f"Expanding jobs (N_clicks={N_clicks})...")
    # SCRIPT_INSERT_CARDS = dedent('''
    #     const clicks = document.querySelectorAll("button[class='rounded-full bg-gray-400 w-1.5 h-1.5 flex-none']")
    #     const grid = document.querySelector("div[class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-x-4 gap-y-12 md:gap-x-10 px-4 md:px-8 xl:px-16 pb-4']")
    #     console.log(grid)
    #     function insertCardBefore(e) {
    #         const card = this.closest("div[class='relative xl:z-10']");
    #         grid.insertBefore(card.cloneNode(true), card);
    #     }
    #     clicks.forEach((btn, index) => {
    #         btn.addEventListener("click", insertCardBefore, true);
    #         setTimeout(() => {
    #             btn.click()
    #         }, index*700)
    #     });
    # ''')
    # driver.execute_script(SCRIPT_INSERT_CARDS)
    # time.sleep(1 + N_clicks*0.77)
    # _grid = driver.find_element("div[class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-x-4 gap-y-12 md:gap-x-10 px-4 md:px-8 xl:px-16 pb-4']")
    # N_expanded = len(_grid.find_elements(By.XPATH, "./*"))
    # scroll_jobs = driver.wait_for_element(_SCROLL_XPATH)

    # _title = f"{P_save.stem} (N={N}, N_expanded={N_expanded})"
    _title = f"{P_save.stem} (N={N})"
    _data = dict(body=scroll_jobs_outer_html, title=_title, description=query_url)
    scroll_jobs_html = render_template(**_data).replace("</source>", "")

    with open(P_save, "w", encoding="utf-8") as f:
        f.write(scroll_jobs_html)

    return P_save


def main1(P_save: Path | str, proxy=False):
    """
    Scrape job urls and descriptions
    """
    log(P_save).info(f"Scraping initial job descriptions and metadata from {P_save}...")

    df = load_jdf(P_save)
    _save_dicts(df, proxy=proxy)


def _save_dicts(df, P_save=None, proxy=False):
    P_URLS.mkdir(exist_ok=True)
    P_JOBS.mkdir(exist_ok=True)
    P_DICT.mkdir(exist_ok=True)

    df_identifier: pd.Series = df["position"] + "." + df["hash"]
    if P_save:
        P_jdf: Path = P_save.parent / f"{P_save.stem}_identifiers.txt"
        df_identifier.to_csv(P_jdf, index=False, header=None)
        log(P_save).info(f"Saved {P_jdf} (N={len(df)})...")
    hash2identifier_dict = dict(zip(df["hash"], df_identifier))

    for url in (pbar := tqdm(VIEW_JOB_HTTPS + df["hash"])):
        hash: str = url.split("/")[-1]
        identifier = hash2identifier_dict[hash]
        pbar.set_description(f"{identifier}")
        P_url = P_URLS / f"{identifier}.html"
        P_md = P_JOBS / f"{identifier}.md"
        P_dict = P_DICT / f"{identifier}.html.pkl"
        # if P_md.exists():
        if P_dict.exists():
            continue
        if not P_dict.exists():
            url_get_content = requests_get(url, proxy=proxy)#
            # url_get_content = selenium_get(url, proxy=False)#
            # time.sleep(random.randint(2,4))
            time.sleep(random.uniform(1, 3))
            with open(P_url, "w", encoding="utf-8") as f:
                f.write(url_get_content)

            root = lxml.html.fromstring(url_get_content)
            _next_data_list = root.xpath("//script[@id='__NEXT_DATA__']")
            if len(_next_data_list) == 0:
                next_data_dict = {}
            else:
                _next_data = root.xpath("//script[@id='__NEXT_DATA__']")[0]
                next_data_dict = json.loads(_next_data.text_content())
            with open(P_dict, "wb") as f:
                pickle.dump(next_data_dict, f)
        else:
            with open(P_url, encoding="utf-8") as f:
                url_get_content = f.read()
            if url_get_content == "":
                print(P_url)
                continue
        root = lxml.html.fromstring(url_get_content)
        job_description = extract_job_description(root)
        if len(job_description) == 0:
            # P_url.unlink()
            print(P_url)
            continue
        else:
            with open(P_md, "w", encoding="utf-8") as f:
                f.write(job_description)


def load_query_url(path: Path | str) -> str:
    path = Path(path)
    if path.suffix == ".json":
        with open(path) as f:
            query_str = f.read()
    else:
        with open(path) as f:
            return f.read()
    _query_stripped = re.sub(r"\s*", "", query_str)
    _query_parsed = urllib.parse.quote(_query_stripped)
    query_url = f"https://hiring.cafe/?searchState={_query_parsed}".replace("%2B", "+")
    return query_url


def parse_query_url(query_url: str) -> dict:
    import json

    _query_parsed = query_url.removeprefix("https://hiring.cafe/?searchState=")
    _query_stripped: str = urllib.parse.unquote(_query_parsed)
    query_dict: dict = json.loads(_query_stripped)
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
    _next_data = root.xpath("//script[@id='__NEXT_DATA__']")[0]
    next_data_dict = json.loads(_next_data.text_content())
    next_data_job = next_data_dict["props"]["pageProps"]["job"]
    data_job_description = next_data_job["job_information"]["description"]
    if to_markdown:
        data_job_description = md(data_job_description, heading_style="ATX")
    return (
        data_job_description.replace("\xa0", " ")
        .replace("\u200b", " ")
        .replace("\u202f", " ")
        .replace("’", "'")
    )


def extract_job_info(root) -> dict:
    _next_data = root.xpath("//script[@id='__NEXT_DATA__']")[0]
    next_data_dict = json.loads(_next_data.text_content())
    next_data_job = next_data_dict["props"]["pageProps"]["job"]
    # _next_data_job_description = next_data_job['job_information']['description']
    # data_job_description = md(_next_data_job_description, heading_style='ATX')
    return next_data_job


@cache
def requests_get(url, proxy=False):
    # _user_agent = UserAgent().get_random_cycled()
    _user_agent = UserAgent.user_agent_106
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
    html_string = response.content.decode()
    return html_string


@cache
def selenium_get(url, wait_time=2, proxy=False):
    driver = init_driver(proxy=proxy)
    # wait = WebDriverWait(driver, 2)
    driver.get(url)
    # scroll_bottom(driver, wait_time=1)
    scroll_bottom(driver, wait_time=wait_time)
    try:
        # wait.until(EC.visibility_of_element_located((By.XPATH, ".//article")))
        driver.wait_for_element(".//article")
    except Exception:
        pass
    # body = wait.until(EC.visibility_of_element_located((By.XPATH, "/body")))
    # outerHTML = body.get_attribute("outerHTML")
    html_source = driver.page_source
    driver.close()
    return html_source


def identifier_get(identifier, save=False, verbose=True):
    hash = identifier.rsplit(".", 1)[-1]
    url = VIEW_JOB_HTTPS + hash
    # html_source = selenium_get(url)
    html_source = requests_get(url)
    if save:
        P_url = P_URLS / f"{identifier}.html"
        if verbose:
            print(f"Writing to {P_url}")
        with open(P_url, "w", encoding="utf-8") as f:
            f.write(html_source)
    else:
        return html_source


@cache
def load_jdf(P_save: Path | str = P_STEM) -> pd.DataFrame:
    _CLASS = "//div[@class='relative bg-white rounded-xl border border-gray-200 shadow hover:border-gray-500 md:hover:border-gray-200']"
    html_string = P_save
    if isinstance(P_save, Path):
        try:
            if not P_save.exists():
                P_save = P_STEM_PREV
            with open(P_save, encoding="utf-8") as f:
                html_string = f.read()
        except UnicodeDecodeError:
            print(P_save)
            raise

    company_ = None
    if html_string:
        tree = lxml.html.fromstring(html_string)
        _title_elem = tree.xpath("head/title")
        if _title_elem:
            company_ = f"{_title_elem[0].text}_"
        all_cards = tree.xpath(_CLASS)
    else:
        path_list = [P_DATA / f"{query}.html" for query in QUERY_LIST]
        html_list = [open(path, encoding="utf-8").read() for path in path_list]
        tree_list = [lxml.html.fromstring(html) for html in html_list]
        cards_list = [tree.xpath(_CLASS) for tree in tree_list]
        all_cards = chain.from_iterable(cards_list)

    use_chash = (company_ is None) or ("(N=" in company_)
    raw_texts_list = []
    for card in all_cards:
        raw_texts = [x.strip() for x in card.xpath(".//span/text()")]
        if not use_chash:
            raw_texts = raw_texts[1:]
        if not re.match(r"\d\d?[y|mo|w|d|h]", raw_texts[0]):
            raw_texts.insert(0, "0h")
        if (
            not raw_texts[3].endswith("yr")
            and not raw_texts[3].endswith("mo")
            and not raw_texts[3].endswith("wk")
            and not raw_texts[3].endswith("hr")
        ):
            raw_texts.insert(3, "-")
        if not use_chash:
            raw_texts.insert(6, company_)
            raw_texts.insert(7, None)
        if raw_texts[7].startswith(":"):
            raw_texts.insert(7, "-")
        if not raw_texts[9].endswith("YOE"):
            raw_texts.insert(9, "-")
        if not raw_texts[10].endswith("Mgmt"):
            raw_texts.insert(10, "-")
        if "Posting" in raw_texts[12]:
            raw_texts.insert(12, "-")
        url = card.xpath("div[2]/div/a[1]/@href")[0]
        hash = url.split("/")[-1]

        if use_chash:
            url2 = card.xpath("div[2]/div/a[2]/@href")[0]
            chash = url2.removeprefix("/?company=").split("&", maxsplit=1)[0]
            raw_texts_list.append([*raw_texts[:15], hash, chash])
        else:
            raw_texts_list.append([*raw_texts[:15], hash])
    if use_chash:
        _HEADER_COLS: list[str] = [
            "days",
            "title",
            "location",
            "salary",
            "onsite",
            "full_time",
            "company",
            "company_stock",
            "company_summary",
            "yoe",
            "mgmt",
            "job_summary",
            "skills",
            "_job_posting",
            "_views",
            "hash",
            "chash",
        ]
    else:
        _HEADER_COLS: list[str] = [
            "days",
            "title",
            "location",
            "salary",
            "onsite",
            "full_time",
            "company",
            "company_stock",
            "company_summary",
            "yoe",
            "mgmt",
            "job_summary",
            "skills",
            "_job_posting",
            "_views",
            "hash",
        ]
    HEADER_COLS = np.array(_HEADER_COLS)

    jdf = pd.DataFrame(raw_texts_list, columns=HEADER_COLS).replace(r"\s+", " ", regex=True)
    assert all(jdf["_job_posting"] == "Job Posting")
    jdf["company"] = jdf["company"].str.removesuffix(':').str.replace('"', "'").str.replace("’", "'")
    jdf = jdf.drop(columns=["_job_posting", "_views"])
    _BUTTONS_CLASS = ".//div[@class='flex justify-center space-x-2']/div"
    jdf["_len"] = pd.Series([len(card.xpath(_BUTTONS_CLASS)) for card in all_cards])
    jdf = _feature_engineering(jdf)
    return jdf


def _feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    def load_cities() -> pd.DataFrame:
        SILICON_VALLEY = "Silicon Valley"
        cities = pd.read_csv(P_DATA / "raw/cities.csv")[SILICON_VALLEY]
        bay_cities = cities[~cities.str.startswith("#")].reset_index(drop=True)
        return bay_cities

    df["hours"] = df["days"].str.split(r"\D").str[0].astype(int) * df["days"].str.split(r"\d").str[
        -1
    ].map({"h": 1, "d": 24, "w": 24 * 7, "mo": 730, "y": 24 * 365})
    df["position"] = (
        (df["company"].fillna('') + " - " + df["title"])
        .str.replace(r"[/|:\\*?]", "_", regex=True)
        .str.replace('"', "'")
        .str.replace("’", "'")
        .str.replace(r" +", " ", regex=True)
        .str.strip()
    )
    df["_position"] = df["position"].str.lower()
    df = (
        df.sort_values(["position", "hours", "company_summary"])
        .drop_duplicates(subset="_position")
        .reset_index(drop=True)
    )
    # df = df.sort_values(['_hours', 'position', 'company_summary']).drop_duplicates(subset='hash').reset_index(drop=True)

    df["location"] = (
        df["location"].str.replace(", California", "").str.replace(", United States", "")
    )
    _salary_type = df["salary"].str.split("/").str[1]
    _multiplier = (
        (_salary_type == "yr") + 12 * (_salary_type == "mo") + 2.080 * (_salary_type == "hr")
    )
    _salary_range = df["salary"].str.split("/").str[0].str.split("-")
    df["lower"] = (
        _salary_range.str[0].str[1:-1].replace("", None).pipe(pd.to_numeric, errors="coerce")
        * _multiplier
    )
    df["upper"] = (
        _salary_range.str[-1].str[1:-1].replace("", None).pipe(pd.to_numeric, errors="coerce")
        * _multiplier
    )
    df["median"] = (df["lower"] + df["upper"]) / 2
    df["yoe"] = df["yoe"].str.split("+").str[0].pipe(pd.to_numeric, errors="coerce")
    df["mgmt"] = df["mgmt"].str.split("+").str[0].pipe(pd.to_numeric, errors="coerce")

    bay_cities = load_cities()
    regex_bay_cities = f"({'|'.join(bay_cities)})"
    df["bay"] = df["location"].str.extractall(regex_bay_cities).groupby(level=0)[0].apply(tuple)
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

    env = Environment(loader=FileSystemLoader(P_DATA / "external"))
    JINJA_TEMPLATE = "template.html"
    template = env.get_template(JINJA_TEMPLATE)
    return template


@cache
def log(P_query: Path) -> logging.Logger:
    _filename = P_query.parent / f"{P_query.stem}.log"
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    file_handler = logging.FileHandler(filename=_filename)
    file_handler.setFormatter(logging.Formatter(FORMAT))
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


if __name__ == "__main__":
    P_query_list = [
        P_QUERY / ("DS_NorCal.txt"),
        # P_QUERY / ('DS_Healthcare.txt'),
    ]
    for P_query in P_query_list:
        P_save = main0(P_query, overwrite=False, bare=True)  # Path('data/2025-10-11/DS.html')
        # P_save = P_DATA / 'processed/2026-02-16/DS_NorCal' / 'DS_NorCal.html'
        # P_save = P_DATA / 'processed/2026-02-19/DS_NorCal' / 'DS_NorCal.html'
        # P_save = P_DATA / 'processed/2026-02-20/DS_NorCal' / 'DS_NorCal.html'
        main1(P_save, proxy=True)
