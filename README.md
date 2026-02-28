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

* Autocomplete text search feature (bonus points if semantic) with tagging
* Easily find submitted resumes and job descriptions. View alignments

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
├── docs               <- A default mkdocs project; see www.mkdocs.org for details
├── models             <- Trained and serialized models, model predictions, or model summaries
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
├── pyproject.toml     <- Project configuration file with package metadata for 
│                         job_search and configuration for tools like black
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
└── job_search   <- Source code for use in this project.
    ├── __init__.py             <- Makes job_search a Python module
    ├── config.py               <- Store useful variables and configuration
    ├── dataset.py              <- Scripts to download or generate data
    └── plots.py                <- Code to create visualizations
```

## Getting Started

```sh
# uv add --no-sync docx2pdf ipykernel ipywidgets lxml markdown markdownify pandas plotly polars pyarrow python pyyaml rich scipy seaborn selenium streamlit tqdm webdriver git+https://github.com/alexanderwu/aw.git
uv pip compile pyproject.toml -o requirements.txt
uv pip sync requirements.txt
uv pip install -e .
```

## HiringCafe - Job Title Terms

```
((data OR ml OR "machine learning" OR "ai" OR "artificial intelligence" OR nlp OR statistical OR bi OR "business intelligence" OR devops OR mlops) AND (engineer OR scientist OR science OR programmer)) AND NOT "software engineer" AND NOT "electrical engineer"
```