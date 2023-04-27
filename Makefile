APPNAME=$(shell grep name pyproject.toml|cut -f2 -d'"')
TARGETS=build clean dependencies deploy install test uninstall
VERSION=$(shell grep version pyproject.toml|cut -f2 -d'"')

all:
	@echo "Try one of: ${TARGETS}"

build: clean dependencies
	poetry build

clean:
	find . -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf dist *.egg-info build

dependencies:
	poetry install --without dev --no-root

dependencies_dev:
	poetry install --only dev --no-root

deploy:
	poetry install

install: build
	pip install dist/*.whl

tag:
	git tag v${VERSION}

test:
	@echo "Testing"
	python -m unittest discover -s tests

uninstall:
	pip uninstall -y ${APPNAME}
