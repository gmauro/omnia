APPNAME=`cat omnia/APPNAME`
TARGETS=build clean dependencies deploy install test uninstall
VERSION=`cat omnia/VERSION`

all:
	@echo "Try one of: ${TARGETS}"

build: clean dependencies
	python setup.py sdist
	python setup.py bdist_wheel --universal

clean:
	python setup.py clean --all
	find . -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf dist *.egg-info build

dependencies: environment.yml
	conda env update --file environment.yml

dependencies_dev: dependencies environment_dev.yml
	conda env update --file environment_dev.yml

deploy: build
	twine upload dist/*

install: build
	pip install dist/*.whl

tag:
	git tag v${VERSION}

test:
	@echo "test"

uninstall:
	pip uninstall -y ${APPNAME}
