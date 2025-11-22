# %%
import os
import json
import pickle
from pathlib import Path

from IPython.display import HTML, Markdown, display
import pandas as pd
from tqdm.notebook import tqdm

import job_search.config as conf
import job_search.dataset as dat
import job_search.company as com
import job_search.resume as res
import job_search.utils as utils
from job_search.config import P_CACHE, P_DICT, P_QUERIES, _date
import aw
_date
# %%
utils.jupyter_css_style()
# %%
P_query = P_QUERIES / 'DS.txt'
P_save = dat.main0(P_query)
jdf = dat.load_jdf(P_save)
# %%
identifiers = set(jdf['position'] + '.' + jdf['hash'] + '.html')
P_dict_list = [p for p in P_DICT.glob("*.pkl") if p.stem in identifiers]
# P_dict_list = [p for p in P_DICT.glob("*.pkl")]
len(P_dict_list)
# Out: 18520
# %%
job_data_list = []
for path in tqdm(P_dict_list):
    with open(path, 'rb') as f:
        job_data = pickle.load(f)
    job_data_list.append(job_data)

_ctime = [os.path.getctime(p) for p in P_dict_list]
_ctime = pd.Series(_ctime).pipe(pd.to_datetime, unit='s').dt.floor('s')

job_series = pd.Series([d['props']['pageProps'].get('job', None) for d in job_data_list])
V5_JOB = 'v5_processed_job_data'
V5_COMP = 'v5_processed_company_data'
JOB_INFO = 'job_information'
job_v5 = job_series.str[V5_JOB]
job_comp = job_series.str[V5_COMP]
job_info = job_series.str[JOB_INFO]
_est_pub_date = job_v5.str['estimated_publish_date'].str[:10].pipe(pd.to_datetime)
_location = job_v5.str['formatted_workplace_location'].str.replace(', California', '').str.replace(', United States', '')
_id = [p.name.removesuffix('.html.pkl') for p in P_dict_list]

job_df = pd.DataFrame({
    '_id': _id,
    '_ctime': _ctime,
    '_est_pub_date': _est_pub_date,
    'title': job_info.str['title'],
    '_loc': _location,
    'yearly_min_compensation': job_v5.str['yearly_min_compensation'],
    'yearly_max_compensation': job_v5.str['yearly_max_compensation'],
    'workplace_type': job_v5.str['workplace_type'],
    'commitment': job_v5.str['commitment'],
    'company_name': job_v5.str['company_name'],
    'company_tagline': job_v5.str['company_tagline'],
    '_yoe': job_v5.str['min_industry_and_role_yoe'],
    '_mgmt': job_v5.str['min_management_and_leadership_yoe'],
    'requirements_summary': job_v5.str['requirements_summary'],
    'technical_tools': job_v5.str['technical_tools'],
    '_hash': job_series.str['requisition_id'],
    'collapse_key': job_series.str['collapse_key'],
    '_geoloc': job_series.str['_geoloc']
})
# %%
comp_df = pd.DataFrame({
    '_id': _id,
    'company_name': job_v5.str['company_name'],
    # 'company_tagline': job_v5.str['company_tagline'],
    'image_url': job_comp.str['image_url'],
    'website': job_comp.str['website'],
    'tagline': job_comp.str['tagline'],
    'is_non_profit': job_comp.str['is_non_profit'],
    'stock_symbol': job_comp.str['stock_symbol'],
    'collapse_key': job_series.str['collapse_key'],
    'year_founded': job_comp.str['year_founded'],
    'num_employees': job_comp.str['num_employees'],
    'industries': job_comp.str['industries'].apply(lambda x: tuple(x) if x else tuple()),
    'activities': job_comp.str['activities'].apply(lambda x: tuple(x) if x else tuple()),
    'latest_investment_amount': job_comp.str['latest_investment_amount'],
    'latest_investment_year': job_comp.str['latest_investment_year'],
    'latest_investment_series': job_comp.str['latest_investment_series'],
    'investors': job_comp.str['investors'].apply(lambda x: tuple(x) if x else tuple()),
    'parent_company': job_comp.str['parent_company'],
    'headquarters_country': job_comp.str['headquarters_country'],
    'linkedin_url': job_comp.str['linkedin_url'],
})
comp_df.nunique()
# %%
from markdownify import markdownify as md
src_df = pd.DataFrame({
    '_id': _id,
    '_ctime': _ctime,
    '_est_pub_date': _est_pub_date,
    'title': job_info.str['title'],
    'job_title_raw': job_info.str['job_title_raw'],
    'description': job_info.str['description'],
    'stripped_description': job_info.str['stripped_description'],
    'viewedByUsers': job_info.str['viewedByUsers'],
    'appliedFromUsers': job_info.str['appliedFromUsers'],
    '_hash': job_series.str['requisition_id'],
})
# src_df['_md'] = src_df['description'].fillna('').map(md)
# %%
N = job_df.shape[0]  # 20776
# N = 18_520
_perc = lambda x: print(f"{x.sum():,} of {N:,} ({100*x.mean():.1f}%)")
# _perc_N = lambda x: print(f"{x:,} of {N:,} ({100*x/N:.1f}%)")
# _perc_N(df['company_name'].isna().sum())
_perc(job_df['_hash'].isna())
# %%
_position = job_df['_id'].str.rsplit('.', n=1).str[0]
job_df['hash'] = job_df['_id'].str.rsplit('.', n=1).str[1]
job_df['_days'] = (pd.to_datetime(conf._date) - job_df['_est_pub_date']).dt.days
bay_cities = dat._load_cities()
regex_bay_cities = f"({'|'.join(bay_cities)})"
job_df['_bay'] = job_df['_loc'].str.extractall(regex_bay_cities).groupby(level=0)[0].apply(tuple)

_health_industries = set([
    INDUSTRY_MEDICAL := 'Medical Organizations',
    INDUSTRY_HEALTH := 'Health Care',
    INDUSTRY_HEALTHCARE := 'Healthcare',
    INDUSTRY_HOME_HEALTHCARE := 'Home Health Care',
    INDUSTRY_PHARMA := 'Pharmaceutical Companies',
    INDUSTRY_HOSPITAL := 'Hospitals',
    INDUSTRY_BIOTECH := 'Biotechnology Companies',
    INDUSTRY_PUBLIC_HEALTH := 'Public Health Organizations',
    INDUSTRY_HEALTH_INS := 'Health Insurance Companies',
    INDUSTRY_MED_TECH := 'Medical Technology Companies',
    INDUSTRY_PHARMACIES := 'Pharmacies',
])
# comp_df['industries'].explode().value_counts().to_frame().head(100).tail(50).style# %%
# %%
__DS_regex = r"(?:data|\bml\b|machine learning|\bai\b|artificial intelligence|\bnlp\b|statistical|\bbi\b|business intelligence|devops|mlops).+(?:engineer|scientist|science|programmer)"
_sw_mask = job_df['title'].fillna('').str.contains(r'software.+engineer', case=False)
__DS_mask = job_df['title'].fillna('').str.contains(__DS_regex, case=False)
_DS_mask = __DS_mask & ~_sw_mask
_perc(_DS_mask)
# %%
ds_mask = job_df['title'].fillna('').str.contains(r'data.+scien', case=False)
ml_mask = job_df['title'].fillna('').str.contains(r'\bml\b|machine.+learning', case=False)
ai_mask = job_df['title'].fillna('').str.contains(r'\bai\b|artificial.+intelligence', case=False)
nlp_mask = job_df['title'].fillna('').str.contains(r'\bnlp\b|natural.+lang.+process', case=False)
_eng_mask = job_df['title'].fillna('').str.contains(r'engineer', case=False)

bay_mask = job_df['_bay'].notna()
health_mask = comp_df['industries'].apply(set) & pd.Series([_health_industries]*len(job_df))
yoe_mask = job_df['_yoe'].fillna(0) < 7
_45d_mask = job_df['_days'].fillna(0) <= 45
remote_mask = job_df['workplace_type'] == "Remote"
yoe_45d_mask = yoe_mask & _45d_mask
bay_remote_mask = bay_mask | remote_mask
DS_mask = _DS_mask & bay_remote_mask & yoe_45d_mask
DS_health_mask = _DS_mask & health_mask & bay_remote_mask & yoe_45d_mask
# %%
_DS_set = job_df[_DS_mask]['_hash'].pipe(set)
bay_set = job_df[bay_mask]['_hash'].pipe(set)
health_set = job_df[health_mask]['_hash'].pipe(set)
yoe_set = job_df[yoe_mask]['_hash'].pipe(set)
_45d_set = job_df[_45d_mask]['_hash'].pipe(set)
remote_set = job_df[remote_mask]['_hash'].pipe(set)
yoe_45d_set = yoe_set & _45d_set
bay_remote_set = bay_set | remote_set

DS_set = _DS_set & bay_remote_set & yoe_45d_set
DS_health_set = _DS_set & health_set & bay_remote_set & yoe_45d_set
# %%
aw.displays(
    aw.combo_sizes([bay_remote_set, yoe_45d_set, _DS_set, health_set], ['Bay_Remote', 'yoe_45d', 'DS', 'Health']),
    aw.combo_sizes2([bay_remote_set, yoe_45d_set, _DS_set, health_set], ['Bay_Remote', 'yoe_45d', 'DS', 'Health']),
)
# %%
_DS_df = job_df[_DS_mask].sort_values(['_est_pub_date', '_ctime'], ascending=False).drop_duplicates('_hash')
DS_df = job_df[DS_mask].sort_values(['_est_pub_date', '_ctime'], ascending=False).drop_duplicates('_hash')
DS_health_df = job_df[DS_health_mask].sort_values(['_est_pub_date', '_ctime'], ascending=False).drop_duplicates('_hash')
_DS_df.shape[0], DS_df.shape[0], DS_health_df.shape[0]
# Out: _DS_df = job_df[_DS_mask].sort_values(['_est_pub_date', '_ctime'], ascending=False).drop_duplicates('_hash')
DS_df = job_df[DS_mask].sort_values(['_est_pub_date', '_ctime'], ascending=False).drop_duplicates('_hash')
DS_health_df = job_df[DS_health_mask].sort_values(['_est_pub_date', '_ctime'], ascending=False).drop_duplicates('_hash')
_DS_df.shape[0], DS_df.shape[0], DS_health_df.shape[0]
# Out: (460, 159, 23)
# %%
# aw.displays(
#     DS_df['company_name'].pipe(aw.vcounts),
#     DS_health_df['company_name'].pipe(aw.vcounts),
# )
# %%
aw.displays(
    # _DS_df['technical_tools'].explode().pipe(aw.vcounts, cutoff=30),
    DS_df['technical_tools'].explode().pipe(aw.vcounts, cutoff=30),
    DS_health_df['technical_tools'].explode().pipe(aw.vcounts, cutoff=30),
)
# %%
DL_mask = job_df['technical_tools'].apply(lambda x: bool(set(x) & {'PyTorch', 'TensorFlow', 'LangChain', 'LLMs', 'JAX', 'Keras', 'Hugging Face'}) if x else False)
_perc(DL_mask)
# %%
_merged_df = pd.merge(job_df, src_df, on=['_id', '_hash', '_ctime', '_est_pub_date', 'title'])
merged_df = pd.merge(_merged_df, comp_df, on=['_id', 'company_name', 'collapse_key'])
# %%
COLS = ['_id', '_ctime', '_est_pub_date', 'title', '_loc', 'yearly_min_compensation', 'yearly_max_compensation',
    'workplace_type', 'commitment', 'company_name', 'company_tagline', '_yoe', '_mgmt', 'requirements_summary',
    'technical_tools',
    # '_hash',
    '_bay', '_days', 'website', 'tagline', 'is_non_profit', 'year_founded', 'num_employees',
    'industries', 'latest_investment_amount', 'latest_investment_year', 'latest_investment_series', 'investors',
    'parent_company', 'headquarters_country', 'linkedin_url'
]
def viewhash(hash):
    row_df = merged_df.query('_hash == @hash').sort_values(['_est_pub_date', '_ctime'], ascending=False)
    row = row_df.iloc[0]

    # display(row_df.drop(columns=['description', 'stripped_description']).T.style)
    display(row_df[COLS].T.dropna().style)
    print(com.viewjob(hash))
    # display(HTML(row['description']))
    print()
    # print(md(row['description']))
    display(Markdown(md(row['description'])))

# %%
# DS_health_df['technical_tools'].explode().pipe(aw.vcounts, cutoff=50)
# DS_df['technical_tools'].explode().pipe(aw.vcounts, cutoff=50)
DS_health_df[['company_name', 'title', 'hash', 'workplace_type']]
# %%
import ipywidgets
from ipywidgets import interact
# viewhash("2dsfdhd97vnu3syj")
# viewhash("29f61wxdp7an278i")
hash_text = ipywidgets.Text(
    # value='John',
    placeholder='29f61wxdp7an278i',
    options=DS_df['hash'].to_list(),
    description='Hash:',
    ensure_option=True,
    disabled=False
)
# interact(viewhash, hash='29f61wxdp7an278i');
interact(viewhash, hash='zn0govk2aljqwd1d');
