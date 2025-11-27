# job_search

Job search tools

## Goals

* Discover and recommend suitable jobs based on resume
    * Highlight keywords from job and match. ATS matching score
        * Industry and domain knowledge
        * Soft skills and leadership
        * Technical skills
        * Activities and tasks
    * Resume crafting
        * Take notes on job postings
    * Annotating keywords
        * (Options: Doccano, DataSaur, Label Studio)
* Understand job market and what skills and experiences are emphasized. What are trending industries and technologies.
* Summarize basic company info to help prepare for interviews
    * Research and providing context for LLMs
* Web scraping for recent jobs

## Project Organization

```
├── LICENSE            <- Open-source license if one is chosen
├── Makefile           <- Makefile with convenience commands like `make data` or `make train`
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── docs               <- A default mkdocs project; see www.mkdocs.org for details
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── pyproject.toml     <- Project configuration file with package metadata for 
│                         job_search and configuration for tools like black
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── setup.cfg          <- Configuration file for flake8
│
└── job_search   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes job_search a Python module
    │
    ├── config.py               <- Store useful variables and configuration
    │
    ├── dataset.py              <- Scripts to download or generate data
    │
    ├── features.py             <- Code to create features for modeling
    │
    ├── modeling                
    │   ├── __init__.py 
    │   ├── predict.py          <- Code to run model inference with trained models          
    │   └── train.py            <- Code to train models
    │
    └── plots.py                <- Code to create visualizations
```

## Getting Started

```sh
make sync
```

OR

```sh
# uv add --no-sync docx2pdf google ipykernel ipywidgets lxml markdown markdownify pandas plotly polars pyarrow python pyyaml rich scipy seaborn selenium streamlit tqdm webdriver git+https://github.com/alexanderwu/aw.git
uv add --no-sync docx2pdf ipykernel ipywidgets lxml markdown markdownify pandas plotly polars pyarrow python pyyaml rich scipy seaborn selenium streamlit tqdm webdriver git+https://github.com/alexanderwu/aw.git
uv pip compile pyproject.toml -o requirements.txt
uv pip sync requirements.txt
uv pip install -e .
```

```sh
docker run --name postgres-db \
  -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
  -e POSTGRES_USER=wua27 \
#   -v ./my-postgres.conf:/etc/postgresql/postgresql.conf \
  -v ./my-postgres.conf:/var/lib/postgresql/18/docker/postgresql.conf \
  -v postgres-data:/var/lib/postgresql \
  -p 5431:5432 \
  -d postgres \
  -c 'config_file=/etc/postgresql/postgresql.conf'

docker run --name postgres-db \
  -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
  -e POSTGRES_USER=${POSTGRES_USER:-wua27} \
  -v postgres-data:/var/lib/postgresql \
  -p 5431:5432 \
  -d postgres

docker run --name pgadmin \
  -p 5050:80 \
  -e "PGADMIN_DEFAULT_EMAIL=alexander.wu7@gmail.com" \
  -e "PGADMIN_DEFAULT_PASSWORD=$POSTGRES_PASSWORD" \
  -d dpage/pgadmin4

docker logs -f postgres-db

docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgres-db
docker inspect postgres-db -f "{{json .NetworkSettings.Networks }}"

docker network create
docker run --network pgnetwork --name postgres-db -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD -p 5432:5432 postgres
docker run --network pgnetwork --name pgadmin -p 80:80 dpage/pgadmin4

docker exec -it postgres-db psql -U wua27 -d postgres

docker start postgres-db
docker restart postgres-db
docker stop postgres-db
docker rm -v postgres-db
```

## Make dataset

```py
def main0(path_query: Path | str, overwrite=False) -> Path:
    """
    Get data/ds.html to prepare job cards
    """
    query_url = load_query_url(path_query)
    query_dict = parse_query_url(query_url)
    scroll_bottom(driver)

def main1(P_save: Path | str):
    """
    Scrape job urls and descriptions
    """
    df = load_jdf(P_save)
    url_get_content = requests_get(url).content
    job_description = extract_job_description(root)
        _html_string = decode_element(_elem, verbose=False)
    
```

((data OR "machine learning" OR "ai" OR "artificial intelligence" OR "statistical") AND (engineer OR scientist OR science OR programmer)) AND NOT "software engineer"

((data OR ml OR "machine learning" OR ai OR "artificial intelligence" OR nlp OR statistical OR bi OR "business intelligence" OR software OR front-end OR frontend OR back-end OR backend OR full-stack OR web OR application OR database OR devops OR mlops OR cloud OR platform OR systems OR "site reliability") AND (developer OR engineer OR engineering OR analyst OR analytics OR scientist OR science))



## Research

https://ai.gopubby.com/comparing-open-source-data-annotation-tools-customised-model-and-llm-api-integration-for-e59a51efe056
* Using Label Studio’s community version for model-assisted annotation is a powerful but non-trivial solution that requires some customization and technical expertise, especially when integrating custom models or LLM APIs.
* Argilla is mainly just an interface and API that can be plugged into any other ML workflow.
* 11:51pm: Getting started

```sh
pup install label-studio
```

Trying out typesense for search

```sh
curl -O https://dl.typesense.org/releases/29.0/typesense-server-29.0-amd64.deb
sudo apt install ./typesense-server-29.0-amd64.deb

# Start Typesense
sudo /usr/bin/./typesense-server --config=/etc/typesense/typesense-server.ini

# Verify that server is ready to accept requests
curl http://localhost:8108/health

cat /etc/typesense/typesense-server.ini
# ; Typesense Configuration
#
# [server]
#
# api-address = 0.0.0.0
# api-port = 8108
# data-dir = /var/lib/typesense
# api-key = 3GEBSYKyImPHvBGfDKm1iGTFzKdvp1fsLobTv3IwBedfnB4L
# log-dir = /var/log/typesense

curl -H 'X-TYPESENSE-API-KEY: 3GEBSYKyImPHvBGfDKm1iGTFzKdvp1fsLobTv3IwBedfnB4L' http://localhost:8108/debug

# Stop server
sudo systemctl stop typesense-server
# Start server
sudo service typesense-server start
# /usr/bin/./typesense-server --config=/etc/typesense/typesense-server.ini
```

* __11/6/25 (Thursday)__

Delete empty files

```py
[PosixPath('/mnt/c/Users/alexa/Dev/Companies/data/cache/jobs/Advocate Aurora Health - Cloud Business Data Analyst.p01z1w7hzffuuo3o.md'),
 PosixPath('/mnt/c/Users/alexa/Dev/Companies/data/cache/jobs/Advocate Aurora Health - Optimization Application Analyst.2terfi2gn5mkiokf.md'),
 PosixPath('/mnt/c/Users/alexa/Dev/Companies/data/cache/jobs/AiDash - Principal Machine Learning Engineer.bGV2ZXJfX19haWRhc2hfX181ZjZmNzEyMy1lMDMyLTRhYjgtYjUzYi0zOGM0ZGQ2ZDJkNzI=.md'),
 PosixPath('/mnt/c/Users/alexa/Dev/Companies/data/cache/jobs/Ambry Genetics - AI Omics Scientist III.oiv8tb6xj2w9cbvf.md'),
 PosixPath('/mnt/c/Users/alexa/Dev/Companies/data/cache/jobs/Bayer - Business Intelligence Data Engineer (Residence Based, Residence Based, US).1g33d5cy3i0o4daw.md'),
 PosixPath('/mnt/c/Users/alexa/Dev/Companies/data/cache/jobs/Becton Dickinson - Staff DevOps Software Engineer for Edge Device Images.6dk31q6pbzhp45yw.md'),
 PosixPath('/mnt/c/Users/alexa/Dev/Companies/data/cache/jobs/Crowe - AI Security Engineer.w1nkf73gjixo4iv8.md'),
 PosixPath('/mnt/c/Users/alexa/Dev/Companies/data/cache/jobs/PricewaterhouseCoopers - Forward Deployed AI Engineer-Palantir Foundry-Senior Associate.x4qbcze47wpxesk0.md'),
 PosixPath('/mnt/c/Users/alexa/Dev/Companies/data/cache/jobs/ServiceNow - Machine Learning Engineer.i97q9xrdrj5z8fyv.md')]
```

LabelStudio

```sh
mkdir ~/mydata
# sudo chown :0 mydata
sudo chmod -R 777 ~/mydata/
docker run -it -p 8080:8080 -v $(pwd)/mydata:/label-studio/data heartexlabs/label-studio:latest
```

Medical Organizations
Biotechnology Companies
Health Care Companies

Pharmaceutical Companies
Bioinformatics Organizations
Medical Technology Companies
Hospitals
Health Insurance Companies
Public Health Organizations
Public Administration
Medical Laboratories
Home Health Care
Mental Health Organizations
Physiotherapy Organization
Dental Companies
Alternative Medicine Organizations
Medical Associations

Life Insurance Companies
Pharmacies


* __11/10/25 (Monday)__
* Made a change starting with Abbvie. 3:10am
* then Radicle Health

```py
def save_template(P_stem_html: Path | str = P_STEM, verbose=True):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(P_DATA / 'external'))
    template = env.get_template(JINJA_TEMPLATE)
    with open(P_stem_html) as f:
        infinite_scroll_html = f.read()
    _data = {'infinite_scroll': infinite_scroll_html}
    output = template.render(_data).replace('</source>', '')
    P_stem_jobs_html = P_stem_html.parent / f'{P_stem_html.stem}_jobs.html'
    if verbose:
        print(f'Writing to {P_stem_jobs_html}...')
    with open(P_stem_jobs_html, 'w') as f:
        f.write(output)
```

## Dev

```py
def create_staging_table(cursor):
    cursor.execute("""
        DROP TABLE IF EXISTS staging_beers;
        CREATE TABLE staging_beers (
            id                  INTEGER,
            name                TEXT,
            tagline             TEXT,
            first_brewed        DATE,
            description         TEXT,
            image               TEXT,
            abv                 DECIMAL,
            ibu                 DECIMAL,
            target_fg           DECIMAL,
            target_og           DECIMAL,
            ebc                 DECIMAL,
            srm                 DECIMAL,
            ph                  DECIMAL,
            attenuation_level   DECIMAL,
            brewers_tips        TEXT,
            contributed_by      TEXT,
            volume              INTEGER
        );
    """)


with open(P_dict_list[0], 'rb') as f:
    job_data = pickle.load(f)
job_data.keys()
# dict_keys(['props', 'page', 'query', 'buildId', 'isFallback', 'isExperimentalCompile', 'gsp', 'scriptLoader'])

print(json.dumps(job_data, indent=2))

job_data_list = []
for path in tqdm(P_dict_list):
    with open(P_dict_list[0], 'rb') as f:
        job_data = pickle.load(f)
    job_data_list.append(job_data)

# validThrough = pd.Series([d['props']['pageProps']['validThrough'] for d in job_data_list])
# pd.to_datetime("2025-12-08T19:41:06.790Z")


job_keys = [
    "v5_processed_job_data",
    "collapse_key",
    "apply_url",
    "requisition_id",
    "v5_processed_company_data",
    "source_and_board_token",
    "job_information",
    "_geoloc",
    "board_token",
    "id",
    "source",
    "objectID",
]
print(com.load_jdf().head(1).T.to_markdown())
```

|                 | 0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|:----------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| days            | 1mo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| title           | Staff Software Engineer, Instrument Software                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| location        | Pleasanton                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| salary          | $210k-$285k/yr                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| onsite          | Onsite                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| full_time       | Full Time                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| company         | 10x Genomics                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| company_summary | Instrument and software developer enabling biology research                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| yoe             | 6.0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| mgmt            | nan                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| job_summary     | Experienced software engineer with 8+ years in C/C++, Python; leadership in instrument software; embedded development; Linux; AI tooling.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| skills          | C, C++, Python, Rust, Linux, Embedded Systems, AI tooling                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| hash            | z7o5ppxaydbno8c6                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| url2            | /?company=Z3JuaHNlX19fMTB4Z2Vub21pY3NfX18xMHggR2Vub21pY3NfX18xMHhnZW5vbWljcy5jb20%3D&searchState=%7B%22locations%22%3A%5B%7B%22id%22%3A%226xk1yZQBoEtHp_8Uv-2X%22%2C%22types%22%3A%5B%22locality%22%5D%2C%22address_components%22%3A%5B%7B%22long_name%22%3A%22San+Francisco%22%2C%22short_name%22%3A%22San+Francisco%22%2C%22types%22%3A%5B%22locality%22%5D%7D%2C%7B%22long_name%22%3A%22California%22%2C%22short_name%22%3A%22CA%22%2C%22types%22%3A%5B%22administrative_area_level_1%22%5D%7D%2C%7B%22long_name%22%3A%22United+States%22%2C%22short_name%22%3A%22US%22%2C%22types%22%3A%5B%22country%22%5D%7D%5D%2C%22geometry%22%3A%7B%22location%22%3A%7B%22lat%22%3A37.77493%2C%22lon%22%3A-122.41942%7D%7D%2C%22formatted_address%22%3A%22San+Francisco%2C+CA%2C+US%22%2C%22population%22%3A864816%2C%22workplace_types%22%3A%5B%5D%2C%22options%22%3A%7B%22radius%22%3A100%2C%22radius_unit%22%3A%22miles%22%2C%22ignore_radius%22%3Afalse%7D%7D%2C%7B%22types%22%3A%5B%22country%22%5D%2C%22formatted_address%22%3A%22United+States%22%2C%22address_components%22%3A%5B%7B%22long_name%22%3A%22United+States%22%2C%22short_name%22%3A%22US%22%2C%22types%22%3A%5B%22country%22%5D%7D%5D%2C%22workplace_types%22%3A%5B%22Remote%22%2C%22Hybrid%22%2C%22Onsite%22%5D%2C%22options%22%3A%7B%7D%2C%22id%22%3A%22United+Statescountry%22%7D%5D%2C%22commitmentTypes%22%3A%5B%22Full+Time%22%2C%22Contract%22%5D%2C%22dateFetchedPastNDays%22%3A1440%2C%22restrictJobsToTransparentSalaries%22%3Atrue%2C%22industries%22%3A%5B%22medical+organizations%22%2C%22biotechnology+companies%22%2C%22health+care+companies%22%5D%2C%22roleTypes%22%3A%5B%22Individual+Contributor%22%5D%2C%22jobTitleQuery%22%3A%22%28%28data+OR+ml+OR+%5C%22machine+learning%5C%22+OR+ai+OR+%5C%22artificial+intelligence%5C%22+OR+nlp+OR+statistical+OR+bi+OR+%5C%22business+intelligence%5C%22+OR+software+OR+front-end+OR+frontend+OR+back-end+OR+backend+OR+full-stack+OR+web+OR+application+OR+database+OR+devops+OR+mlops+OR+cloud+OR+platform+OR+systems+OR+%5C%22site+reliability%5C%22%29+AND+%28developer+OR+engineer+OR+engineering+OR+analyst+OR+analytics+OR+scientist+OR+science%29%29%22%7D |
| _len            | 2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| hours           | 730                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| position        | 10x Genomics - Staff Software Engineer, Instrument Software                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| _position       | 10x genomics - staff software engineer, instrument software                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| lower           | 210.0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| upper           | 285.0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| median          | 247.5                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| bay             | ('Pleasanton',)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |