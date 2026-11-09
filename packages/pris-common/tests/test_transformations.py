import pytest
from pris_msgs.camera_pb2 import (
    FrameTransformation,
    GetTransformationReply,
    GetTransformationRequest,
)
from pris_wire.core import Status, StatusCode

from pris_common.transformations import fetch_transformations

KNOWN = {
    (0, 1000): FrameTransformation(source=0, target=1000),
    (1000, 1): FrameTransformation(source=1000, target=1),
}


def get_transformation(request, context):
    reply = GetTransformationReply()
    for pair in request.ids:
        if (pair.source, pair.target) not in KNOWN:
            return Status(StatusCode.NOT_FOUND,
                          "no transformation from {} to {}".format(pair.source, pair.target))
        reply.transformations.append(KNOWN[(pair.source, pair.target)])
    return reply


@pytest.fixture
def server(serve, topic):
    serve(topic, get_transformation, GetTransformationRequest, GetTransformationReply)


def test_every_pair_known(channel, topic, server):
    assert fetch_transformations(channel, [(1000, 1), (0, 1000)], topic=topic) == KNOWN


def test_a_pair_without_route_is_an_error(channel, topic, server):
    with pytest.raises(RuntimeError, match="no transformation from 5 to 1000"):
        fetch_transformations(channel, [(0, 1000), (5, 1000)], topic=topic)
