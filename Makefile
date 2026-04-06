.PHONY: upload download sync clean lint format test docs docs-serve dataset serve create-database postgres
#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_NAME = job_search
PYTHON_VERSION = 3.12
PYTHON_INTERPRETER = python
# PY_312 = ~/miniconda3/envs/py312/python
PY_312 = C:\Users\Alex\miniconda3\envs\py312\python.exe
PY_SCRIPTS = C:\Users\Alex\miniconda3\envs\py312\Scripts
JOB_MIGRATE = C:\Users\Alex\miniconda3\envs\py312\Scripts\job-migrate.exe


#################################################################################
# COMMANDS                                                                      #
#################################################################################

make: ## Edit makefile
	code Makefile

upload: ## Upload data to gDrive
	rclone copy data gdrive:Dev/data --progress

download: ## Download data from gDrive
	rclone copy gdrive:Dev/data data --progress

## Install Python dependencies
sync:
	uv pip compile pyproject.toml -o requirements.txt
	uv pip sync requirements.txt
	uv pip install -e .

## Delete all compiled Python files
clean:
ifneq ($(wildcard ./downloaded_files/),)
	rip downloaded_files/
# 	find . -type f -name "*.py[co]" -delete
# 	find . -type d -name "__pycache__" -delete
endif

lint: ## Lint using ruff (use `make format` to do formatting)
	ruff format --check
	ruff check

format: ## Format source code with ruff
	ruff check --fix
	ruff format

test:
	@$(PY_312) -m pytest tests

## build the static version of the docs
docs:
	cd docs && mkdocs build

## serve documentation to livereload while you work
docs-serve:
	cd docs && mkdocs serve

migrate: ## migrate
	@$(JOB_MIGRATE)

dataset: ## dataset
	@$(PY_312) job_search/dataset.py

resume: ## resume
	@$(PY_312) job_search/resume.py

db2json: ## db2json
	@$(PY_312) scripts/db2json.py

## serve backend
serve:
	fastapi dev job_search/backend.py

## Database
database:
	docker run --name postgres-db -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD -e POSTGRES_USER=$POSTGRES_USER -v postgres-data:/var/lib/postgresql -p 5432:5432 -d postgres

postgres:
	docker exec -it postgres-db psql -U wua27 -d postgres

#################################################################################
# Self Documenting Commands                                                     #
#################################################################################

.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys; \
lines = '\n'.join([line for line in sys.stdin]); \
matches = re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', lines, re.M); \
_MAGENTA, _RESET = '\033[35m', '\033[0m'; \
print('\n'.join([f'{_MAGENTA}{m[0]:20}{_RESET}{m[1]}' for m in matches]))
endef
export PRINT_HELP_PYSCRIPT

help:
	@$(PYTHON_INTERPRETER) -c "${PRINT_HELP_PYSCRIPT}" < $(MAKEFILE_LIST)
