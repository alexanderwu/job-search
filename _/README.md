# job_search

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

Job search tools

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
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── pyproject.toml     <- Project configuration file with package metadata for 
│                         job_search and configuration for tools like black
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
└── job_search   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes job_search a Python module
    │
    ├── companies.py            <- Companies
    └── resume.py               <- Resume
```

## Getting Started

```sh
make sync
```

OR

```sh
uv add --no-sync docx2pdf google ipykernel ipywidgets lxml markdown markdownify pandas plotly polars pyarrow python pyyaml rich scipy seaborn selenium streamlit tqdm webdriver git+https://github.com/alexanderwu/aw.git
uv pip compile pyproject.toml -o requirements.txt
uv pip sync requirements.txt
uv pip install -e .
```