unexport VIRTUAL_ENV

.PHONY: proto

proto:
	find src \( -name '*_pb2.py' -o -name '*_pb2.pyi' \) -delete
	cd src && PROTOC="python -m grpc_tools.protoc" uv run --no-sync python -m pris_msgs.utils.build pris_frame_transformation/conf/options.proto

