ADDR ?= localhost:8001
IMAGE ?= $(DOCKER_USERNAME)/pris-docs:$(shell cat VERSION)

.PHONY: serve build image

serve:
	uv run zensical serve --dev-addr=$(ADDR)

build:
	uv run zensical build --strict --clean

image:
	docker build --network host -f etc/docker/Dockerfile -t $(IMAGE) .
