#!/usr/bin/env python3
"""
Download job description
"""
from functools import cache, partial
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

import lxml.html
from markdownify import markdownify as md
import pandas as pd
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from seleniumbase import Driver
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
    PROXY = None
    # Use proxy. Format: "SERVER:PORT" or "USER:PASS@SERVER:PORT".
    if proxy:
        ii = random.randint(1, 44745)
        PROXY = f"byfdawqz-US-{ii}:fhx888ooginw@p.webshare.io:80"

    headless = headless and not is_running_wsl()
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
        grid_jobs_outer_html = ""
        _title = f"{P_save.stem} (N=)"
        _data = dict(body=grid_jobs_outer_html, title=_title, description=query_url)
        grid_jobs_html = render_template(**_data).replace("</source>", "")
        with open(P_save, "w", encoding="utf-8") as f:
            f.write(grid_jobs_html)
        return P_save

    driver = init_driver(headless=False, proxy=proxy)
    driver.maximize_window()
    driver.get(query_url)

    def querySelector(selectors, elem=driver):
        return elem.find_element(By.CSS_SELECTOR, selectors)
    def querySelectorAll(selectors, elem=driver):
        return elem.find_elements(By.CSS_SELECTOR, selectors)
    def children(elem):
        return elem.find_elements(By.XPATH, "./*")
    q = querySelector
    Q = querySelectorAll
    def click_close():
        x_button = q('button:has([d*="M6 18"])')
        ActionChains(driver).move_to_element(x_button).click().perform()
    def click_job(job):
        ActionChains(driver).move_to_element(job).click().perform()
    def extract_job():
        driver.wait_for_element('.grid')
        next_data_dict = json.loads(q('#__NEXT_DATA__').get_attribute("textContent"))
        return next_data_dict

    time.sleep(2)
    # scroll_bottom(driver)

    try:
        grid = driver.wait_for_element(GRID := ".grid")
        grid.children = partial(children, grid)
        # grid_jobs_outer_html = grid.get_attribute("outerHTML")
    # except TimeoutException:
    except Exception:
        log(P_save).warning(f"Could not save {P_save}...")
        grid_jobs_outer_html = ""
        input("Press ENTER to continue...")

    N_initial = len(grid.children())
    log(P_save).info(f"(N_initial={N_initial})...")

    # ruff: noqa
    cards = querySelectorAll('.grid > div')
    card = cards[0]
    card_btns_list = Q(BTNS := "button[class*='rounded-full bg-gray']", card)
    job = q(JOB := "[class*='340px']", card)
    hover = q(HOVER := "[class*='340px'] + div", card)

    # ActionChains(driver).move_to_element(hover).perform()
    click_job(job)
    # next_data_job = extract_job()
    next_data_dict = extract_job()
    len(next_data_dict['props']['pageProps']['ssrHits'])
    len(extract_job()['props']['pageProps']['ssrHits'])
    next_data_dict['props']['pageProps']['ssrHits'][0]

    driver.refresh()
    extract_job()['props']['pageProps']['ssrHits'][0]

    pages = Q("[class~='gap-0.5'] > a")
    len(pages)
    pages[0].get_attribute('href') == pages[1].get_attribute('href')
    driver.refresh()
    extract_job()['props']['pageProps']['ssrHits'][0]

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
def selenium_get(url, wait_time=2, proxy=False, driver=None):
    close_driver = False
    if driver is None:
        close_driver = True
        driver = init_driver(proxy=proxy, headless=False)
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
    if close_driver:
        driver.close()
    return html_source


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
    P_query = P_QUERY / "DS_NorCal.txt"
    ## from job_search import *
    ## (path_query:=P_query, overwrite:=False, bare:=False, proxy:=False)
    P_save = main0(P_query, overwrite=False)
    # P_save = main0(P_query, overwrite=False, bare=True)  # Path('data/2025-10-11/DS.html')
    # P_save = P_DATA / 'processed/2026-04-13/DS_NorCal' / 'DS_NorCal.html'
    main1(P_save, proxy=True)
