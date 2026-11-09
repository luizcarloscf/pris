DOCKER_USERNAME ?= luizcarloscf
SERVICE := $(notdir $(CURDIR))

unexport VIRTUAL_ENV

.PHONY: proto image

proto:
	find src \( -name '*_pb2.py' -o -name '*_pb2.pyi' \) -delete
	cd src && PROTOC="python -m grpc_tools.protoc" uv run --no-sync python -m pris_msgs.utils.build pris_calibration_server/conf/options.proto

image:
	docker build --network host -f etc/docker/Dockerfile -t $(DOCKER_USERNAME)/$(SERVICE):$$(uv version --short) .
