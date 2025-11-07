from pathlib import Path
from job_search.utils import now, is_wsl


P_ROOT = Path(__file__).parents[1]
if is_wsl():
    P_DATA = Path('/mnt/c/Users/alexa/Dev/Companies/data')
else:
    P_DATA = P_ROOT.parent / 'Companies/data'
P_RAW = P_DATA / 'raw'
P_EXTERNAL = P_DATA / 'external'
P_PROCESSED = P_DATA / 'processed'

HIRING_CAFE_HTTPS = "https://hiring.cafe"
VIEW_JOB_HTTPS = "https://hiring.cafe/viewjob/"
QUERY_LIST = [
    # SW_REMOTE := 'SW_Remote',
    # SW := 'SW',
    # DS_DC := 'DS_DC',
    # DS_MIDWEST := 'DS_Midwest',
    # DS_NORCAL := 'DS_NorCal',
    # DS_SOCAL := 'DS_SoCal',
    # DS_SEATTLE := 'DS_Seattle',
    # DS_NY := 'DS_NY',
    # DS_REMOTE := 'DS_Remote',
    # DS_HEALTH := 'DS_healthcare',
    HEALTH := 'Healthcare',
]
JINJA_TEMPLATE = 'template.html'
P_QUERIES = P_DATA / 'queries'
P_CACHE = P_DATA / 'cache'
P_JOBS = P_DATA / 'cache/jobs'
P_URLS = P_DATA / 'cache/urls'
P_COMPANY_URLS = P_DATA / 'cache/company_urls'

_date = now(time=False)
# STEM = 'Healthcare'
STEM = QUERY_LIST[0] if (len(QUERY_LIST) > 0) else 'Healthcare'
P_DATE = P_DATA / f'processed/{_date}'
P_STEM = P_DATE / f'{STEM}/{STEM}.html'
P_STEM_JOBS_HTML = P_DATE / f'{STEM}/{STEM}_jobs.html'
P_STEM_COMPANY_URLS = P_DATE / f'{STEM}/{STEM}_company_urls/'
P_STEM_QUERY_TXT = P_QUERIES / f'{STEM}.txt'