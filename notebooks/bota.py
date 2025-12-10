# %% Setup
from pathlib import Path

from botasaurus.browser import browser, Driver, Wait
# from botasaurus.request import request, Request
from botasaurus.user_agent import UserAgent
# from botasaurus import user_agent, window_size

from botasaurus_requests import request, Session

from job_search.config import P_DATE, P_QUERIES
from job_search.dataset import load_query_url#, parse_query_url

PROXY = "http://byfdawqz-rotate:fhx888ooginw@p.webshare.io:80/"
path_query = P_query = P_QUERIES / ('DS_NorCal_Remote.txt')
P_save = P_DATE / f"{path_query.stem}/{path_query.stem}.html"

query_url = load_query_url(path_query)
print(query_url)

###############################################################################
# %%
query_url = "https://hiring.cafe/?searchState=%7B%22locations%22%3A%5B%7B%22id%22%3A%226xk1yZQBoEtHp_8Uv-2X%22%2C%22types%22%3A%5B%22locality%22%5D%2C%22address_components%22%3A%5B%7B%22long_name%22%3A%22San+Francisco%22%2C%22short_name%22%3A%22San+Francisco%22%2C%22types%22%3A%5B%22locality%22%5D%7D%2C%7B%22long_name%22%3A%22California%22%2C%22short_name%22%3A%22CA%22%2C%22types%22%3A%5B%22administrative_area_level_1%22%5D%7D%2C%7B%22long_name%22%3A%22United+States%22%2C%22short_name%22%3A%22US%22%2C%22types%22%3A%5B%22country%22%5D%7D%5D%2C%22geometry%22%3A%7B%22location%22%3A%7B%22lat%22%3A37.77493%2C%22lon%22%3A-122.41942%7D%7D%2C%22formatted_address%22%3A%22San+Francisco%2C+CA%2C+US%22%2C%22population%22%3A864816%2C%22workplace_types%22%3A%5B%5D%2C%22options%22%3A%7B%22radius%22%3A100%2C%22radius_unit%22%3A%22miles%22%2C%22ignore_radius%22%3Afalse%7D%7D%2C%7B%22id%22%3A%222hk1yZQBoEtHp_8Uv-2X%22%2C%22types%22%3A%5B%22locality%22%5D%2C%22address_components%22%3A%5B%7B%22long_name%22%3A%22Sacramento%22%2C%22short_name%22%3A%22Sacramento%22%2C%22types%22%3A%5B%22locality%22%5D%7D%2C%7B%22long_name%22%3A%22California%22%2C%22short_name%22%3A%22CA%22%2C%22types%22%3A%5B%22administrative_area_level_1%22%5D%7D%2C%7B%22long_name%22%3A%22United+States%22%2C%22short_name%22%3A%22US%22%2C%22types%22%3A%5B%22country%22%5D%7D%5D%2C%22geometry%22%3A%7B%22location%22%3A%7B%22lat%22%3A38.58157%2C%22lon%22%3A-121.4944%7D%7D%2C%22formatted_address%22%3A%22Sacramento%2C+CA%2C+US%22%2C%22population%22%3A490712%2C%22workplace_types%22%3A%5B%5D%2C%22options%22%3A%7B%22radius%22%3A100%2C%22radius_unit%22%3A%22miles%22%2C%22ignore_radius%22%3Afalse%7D%7D%2C%7B%22id%22%3A%228Bk1yZQBoEtHp_8Uv-2X%22%2C%22types%22%3A%5B%22locality%22%5D%2C%22address_components%22%3A%5B%7B%22long_name%22%3A%22San+Jose%22%2C%22short_name%22%3A%22San+Jose%22%2C%22types%22%3A%5B%22locality%22%5D%7D%2C%7B%22long_name%22%3A%22California%22%2C%22short_name%22%3A%22CA%22%2C%22types%22%3A%5B%22administrative_area_level_1%22%5D%7D%2C%7B%22long_name%22%3A%22United+States%22%2C%22short_name%22%3A%22US%22%2C%22types%22%3A%5B%22country%22%5D%7D%5D%2C%22geometry%22%3A%7B%22location%22%3A%7B%22lat%22%3A37.33939%2C%22lon%22%3A-121.89496%7D%7D%2C%22formatted_address%22%3A%22San+Jose%2C+CA%2C+US%22%2C%22population%22%3A1026908%2C%22workplace_types%22%3A%5B%5D%2C%22options%22%3A%7B%22radius%22%3A100%2C%22radius_unit%22%3A%22miles%22%2C%22ignore_radius%22%3Afalse%7D%7D%5D%2C%22commitmentTypes%22%3A%5B%22Full+Time%22%2C%22Contract%22%5D%2C%22dateFetchedPastNDays%22%3A4%2C%22restrictJobsToTransparentSalaries%22%3Atrue%2C%22roleTypes%22%3A%5B%22Individual+Contributor%22%5D%2C%22jobTitleQuery%22%3A%22%28%28data+OR+ml+OR+%5C%22machine+learning%5C%22+OR+%5C%22ai%5C%22+OR+%5C%22artificial+intelligence%5C%22+OR+nlp+OR+statistical+OR+bi+OR+%5C%22business+intelligence%5C%22+OR+devops+OR+mlops%29+AND+%28engineer+OR+scientist+OR+science+OR+programmer%29%29+AND+NOT+%5C%22software+engineer%5C%22+AND+NOT+%5C%22electrical+engineer%5C%22%5Cn%22%7D"
query_url


################################################################################
# %% requests_get
def requests_get(url):
    # _user_agent = UserAgent().get_random_cycled()
    _user_agent = UserAgent.user_agent_106
    _headers = {
        'User-Agent': _user_agent,
        'Referer': 'https://hiring.cafe/',
        'Origin': 'https://hiring.cafe',
        'Sec-Fetch-Dest': 'empty',
        # 'proxy': {
        #     'http': PROXY,
        #     'https': PROXY,
        # }
    }
    url_get = request.get(url, headers=_headers)
    return url_get

response = requests_get(query_url)
response


################################################################################
# %%
from seleniumbase import Driver#, SB, sb_cdp
driver = Driver(uc=True)
driver.get(query_url)

################################################################################
# %%
from job_search.dataset import scroll_bottom
scroll_bottom(driver)
driver.maximize_window()
_SCROLL_XPATH = "//div[@class='infinite-scroll-component__outerdiv']"
scroll_jobs = driver.wait_for_element(_SCROLL_XPATH)
scroll_jobs_outer_html = scroll_jobs.get_attribute("outerHTML")
scroll_jobs_outer_html

################################################################################
# %%
import lxml.html
root = lxml.html.fromstring(scroll_jobs_outer_html)
_CLICKS_XPATH = "//button[@class='rounded-full bg-gray-400 w-1.5 h-1.5 flex-none']"
clicks = root.xpath(_CLICKS_XPATH)
clicks

################################################################################
# %%
from textwrap import dedent
# script_insert_cards = dedent('''
#     const clicks = document.querySelectorAll("button[class='rounded-full bg-gray-400 w-1.5 h-1.5 flex-none']")
#     const grid = document.querySelector("div[class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-x-4 gap-y-12 md:gap-x-10 px-4 md:px-8 xl:px-16 pb-4']")[0]
#     function insertCardBefore(e) {
#         const card = this.closest("div[class='relative xl:z-10']");
#         grid.insertBefore(card.cloneNode(true), card);
#     }
#     for (const btn of clicks) {
#         btn.addEventListener("click", insertCardBefore, true);
#         btn.click()
#     }
# ''')
script_insert_cards = dedent('''
    const clicks = document.querySelectorAll("button[class='rounded-full bg-gray-400 w-1.5 h-1.5 flex-none']")
    const grid = document.querySelectorAll("div[class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-x-4 gap-y-12 md:gap-x-10 px-4 md:px-8 xl:px-16 pb-4']")
    console.log(clicks.length);
''')
driver.execute_script(script_insert_cards)

################################################################################
# %%
script_insert_cards = dedent('''
    const clicks = document.querySelectorAll("button[class='rounded-full bg-gray-400 w-1.5 h-1.5 flex-none']")
    const grid = document.querySelector("div[class='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-x-4 gap-y-12 md:gap-x-10 px-4 md:px-8 xl:px-16 pb-4']")
    console.log(grid)
    function insertCardBefore(e) {
        const card = this.closest("div[class='relative xl:z-10']");
        grid.insertBefore(card.cloneNode(true), card);
    }
    clicks.forEach((btn, index) => {
        btn.addEventListener("click", insertCardBefore, true);
        setTimeout(() => {
            btn.click()
        }, index*500)
    });
''')

script_remove_cards = dedent('''
    const clicked = document.querySelectorAll("button[class='rounded-full bg-gray-800 w-2 h-2 flex-none']")
    function removeCardBefore(e) {
        const card = this.closest("div[class='relative xl:z-10']");
        card.previousElementSibling.remove()
    }
    for (const btn of clicked) {
        btn.addEventListener("click", removeCardBefore, true);
    }
''')
# driver.execute_script(script_remove_cards)
# driver.execute_script(script_insert_cards)
################################################################################
# %%
