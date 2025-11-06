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

## Research

https://ai.gopubby.com/comparing-open-source-data-annotation-tools-customised-model-and-llm-api-integration-for-e59a51efe056
* Using Label Studio’s community version for model-assisted annotation is a powerful but non-trivial solution that requires some customization and technical expertise, especially when integrating custom models or LLM APIs.
* Argilla is mainly just an interface and API that can be plugged into any other ML workflow.
* 11:51pm: Getting started

```sh
pup install label-studio
```