.PHONY: sync clean lint format test docs docs-serve dataset serve create-database postgres
#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_NAME = job_search
PYTHON_VERSION = 3.12
PYTHON_INTERPRETER = python

#################################################################################
# COMMANDS                                                                      #
#################################################################################

## Install Python dependencies
sync:
	uv pip compile pyproject.toml -o requirements.txt
	uv pip sync requirements.txt
	uv pip install -e .

## Delete all compiled Python files
clean:
	rip downloaded_files/
# 	find . -type f -name "*.py[co]" -delete
# 	find . -type d -name "__pycache__" -delete

## Lint using ruff (use `make format` to do formatting)
lint:
	ruff format --check
	ruff check

## Format source code with ruff
format:
	ruff check --fix
	ruff format

test:
	python -m pytest tests

docs:  ## build the static version of the docs
	cd docs && mkdocs build

docs-serve: ## serve documentation to livereload while you work
	cd docs && mkdocs serve

dataset:
	python job_search/dataset.py

resume:
	python job_search/resume.py

serve:
	fastapi dev job_search/backend.py

## Database
database:
	docker run --name postgres-db -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD -e POSTGRES_USER=$POSTGRES_USER -v postgres-data:/var/lib/postgresql -p 5432:5432 -d postgres

postgres:
	docker exec -it postgres-db psql -U wua27 -d postgres

#################################################################################
# PROJECT RULES                                                                 #
#################################################################################



#################################################################################
# Self Documenting Commands                                                     #
#################################################################################

.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys; \
lines = '\n'.join([line for line in sys.stdin]); \
matches = re.findall(r'\n## (.*)\n[\s\S]+?\n([a-zA-Z_-]+):', lines); \
print('Available rules:\n'); \
print('\n'.join(['{:25}{}'.format(*reversed(match)) for match in matches]))
endef
export PRINT_HELP_PYSCRIPT

help:
	@$(PYTHON_INTERPRETER) -c "${PRINT_HELP_PYSCRIPT}" < $(MAKEFILE_LIST)
