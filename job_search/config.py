from pathlib import Path

from job_search.utils import is_running_wsl, now

P_ROOT = Path(__file__).parents[1]
if is_running_wsl():
    P_DATA = Path.home() / 'Dev/job-search/data'
else:
    P_DATA = P_ROOT.parent / 'job-search/data'
P_RAW = P_DATA / 'raw'
P_EXTERNAL = P_DATA / 'external'
P_PROCESSED = P_DATA / 'processed'
P_RESUME = P_RAW / 'AW_Resume.md'

HIRING_CAFE_HTTPS = "https://hiring.cafe"
VIEW_JOB_HTTPS = "https://hiring.cafe/viewjob/"
QUERY_LIST: list[str] = [
    DS_NORCAL := 'DS_NorCal',
    DS_HEALTH := 'DS_Healthcare',
    DS_NORCAL_REMOTE := 'DS_NorCal_Remote',
    DS := 'DS',
    HEALTH := 'Healthcare',
    SW_REMOTE := 'SW_Remote',
    SW := 'SW',
    DS_DC := 'DS_DC',
    DS_MIDWEST := 'DS_Midwest',
    DS_SOCAL := 'DS_SoCal',
    DS_SEATTLE := 'DS_Seattle',
    DS_NY := 'DS_NY',
    DS_REMOTE := 'DS_Remote',
]
JINJA_TEMPLATE = 'template.html'
P_QUERY = P_DATA / 'query'
P_CACHE = P_DATA / 'cache'
P_JOBS = P_DATA / 'cache/jobs'
P_URLS = P_DATA / 'cache/urls'
P_DICT = P_DATA / 'cache/dicts'
# P_COMPANY_URLS = P_DATA / 'cache/company_urls'
# P_ALL_COMPANY_URLS = P_CACHE / 'ALL_company_urls'

_date = now(time=False)
# STEM = 'Healthcare'
STEM = QUERY_LIST[0] if (len(QUERY_LIST) > 0) else 'Healthcare'
P_DATE = P_PROCESSED / f'{_date}'
P_STEM = P_DATE / f'{STEM}/{STEM}.html'
P_STEM_JOBS_HTML = P_DATE / f'{STEM}/{STEM}_jobs.html'
# P_STEM_COMPANY_URLS = P_DATE / f'{STEM}/{STEM}_company_urls/'
P_STEM_QUERY_TXT = P_QUERY / f'{STEM}.txt'
