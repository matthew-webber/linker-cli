# Makefile
VENV := venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PTW := $(VENV)/bin/ptw

.PHONY: venv deps ptw test clean

venv:
	python3 -m venv $(VENV)

deps: venv
	$(PIP) install -U pip
	@if [ -f requirements-dev.txt ]; then \
	  $(PIP) install -r requirements-dev.txt; \
	else \
	  $(PIP) install pytest pytest-watch; \
	fi

ptw: deps
	$(PTW)

test: deps
	$(PY) -m pytest

clean:
	rm -rf $(VENV)