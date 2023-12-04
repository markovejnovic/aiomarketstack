PYTHON = poetry run python

# Directories or files which can be linted
LINTABLE_NODES = aiomarketstack tests

.PHONY: lint autolint test build

lint:
	$(PYTHON) -m mypy aiomarketstack tests
	$(PYTHON) -m ruff check .

autolint:
	$(PYTHON) -m ruff check --fix .

test:
	$(PYTHON) -m pytest \
		--cov=aiomarketstack \
		--cov-report=html \
		--cov-report=term

build:
	mkdir -p build-artifacts
	poetry build
	rm -rf build-artifacts/dist
	mv dist build-artifacts/dist

ci-build-lint-test: build lint test
	tar -czf build-artifacts.tar.gz build-artifacts
