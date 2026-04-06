from job_search.config import P_ROOT
import job_search.jobs as jb

P_astro = P_ROOT.parent / 'job-astro' / 'src/data'
P_astro.exists()

jobs_df = jb.load_jobs()#.rename(columns={'title': 'title_', 'position': 'position_'})
print(jobs_df.shape)
jobs_mar = jobs_df.query('mar')
COLS = [
    'requisition_id',
    'title',
    'estimated_publish_date',
    'formatted_workplace_location',
    'yearly_min_compensation',
    'yearly_max_compensation',
    'listed_compensation_frequency',
    'workplace_type',
    'commitment',
    'requirements_summary',
    'min_industry_role_yoe',
    'company_name',
    'company_tagline',
    'technical_tools',
]
jobs_mar[COLS].rename(columns={'requisition_id': 'id', 'company_tagline': 'tagline'}).to_json(P_astro / 'jobs_mar.json', orient='records')