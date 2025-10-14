.PHONY: sync clean lint format test
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
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

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
