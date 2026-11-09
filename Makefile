DOCKER_USERNAME ?= luizcarloscf
BROKER_NAME ?= rabbitmq
BROKER_IMAGE ?= rabbitmq:4.3.6
MYPY_PACKAGES := pris_msgs pris_wire opentelemetry.instrumentation.pris_wire pris_common
SERVICES := $(patsubst services/%/uv.lock,%,$(wildcard services/*/uv.lock))

unexport VIRTUAL_ENV

.PHONY: help sync proto test lint build clean broker-up broker-down docs-serve docs-build docs-image

help:
	@echo "sync         install every workspace package (editable) into .venv"
	@echo "proto        regenerate the Python code (*_pb2.py/.pyi) of every package and service"
	@echo "test         run the tests of the packages and of every service (needs make broker-up)"
	@echo "lint         flake8 + mypy, packages and services"
	@echo "build        build sdists and wheels into dist/"
	@echo "broker-up    start a local RabbitMQ (host network)"
	@echo "broker-down  stop the local RabbitMQ"
	@echo "docs-serve   serve the documentation with live reload"
	@echo "docs-build   build the documentation into docs/site (strict)"
	@echo "docs-image   build the documentation image $(DOCKER_USERNAME)/pris-docs locally"

sync:
	uv sync --all-packages

proto:
	$(MAKE) -C packages/pris-msgs proto
	$(MAKE) -C packages/pris-wire proto
	@set -e; for service in $(SERVICES); do $(MAKE) -C services/$$service proto; done

test:
	@docker inspect -f '{{.State.Running}}' $(BROKER_NAME) 2>/dev/null | grep -q true \
		|| { echo "no $(BROKER_NAME) container running: make broker-up"; exit 1; }
	uv run pytest
	@set -e; for service in $(SERVICES); do echo "== $$service"; uv --directory services/$$service run pytest; done

lint:
	uv run flake8
	uv run mypy $(addprefix -p ,$(MYPY_PACKAGES))
	@set -e; for service in $(SERVICES); do echo "== $$service"; uv --directory services/$$service run mypy src; done

build:
	uv build --all-packages --out-dir dist

broker-up:
	docker run -d --rm --network host --name $(BROKER_NAME) $(BROKER_IMAGE)

broker-down:
	docker stop $(BROKER_NAME)

docs-serve docs-build docs-image:
	$(MAKE) -C docs $(@:docs-%=%) DOCKER_USERNAME=$(DOCKER_USERNAME)

clean:
	rm -rf dist .pytest_cache .mypy_cache services/*/.pytest_cache services/*/.mypy_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
