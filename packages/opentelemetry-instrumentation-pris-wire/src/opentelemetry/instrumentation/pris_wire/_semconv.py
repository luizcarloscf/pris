"""The semantic convention names this instrumentation uses, from the pinned
opentelemetry-semantic-conventions release."""

from opentelemetry.semconv._incubating.attributes import messaging_attributes as _messaging
from opentelemetry.semconv._incubating.attributes import rpc_attributes as _rpc
from opentelemetry.semconv.attributes import error_attributes as _error
from opentelemetry.semconv.attributes import server_attributes as _server

MESSAGING_SYSTEM = _messaging.MESSAGING_SYSTEM
MESSAGING_OPERATION_TYPE = _messaging.MESSAGING_OPERATION_TYPE
MESSAGING_OPERATION_NAME = _messaging.MESSAGING_OPERATION_NAME
MESSAGING_DESTINATION_NAME = _messaging.MESSAGING_DESTINATION_NAME
MESSAGING_DESTINATION_TEMPORARY = _messaging.MESSAGING_DESTINATION_TEMPORARY
MESSAGING_RABBITMQ_ROUTING_KEY = _messaging.MESSAGING_RABBITMQ_DESTINATION_ROUTING_KEY
MESSAGING_MESSAGE_CONVERSATION_ID = _messaging.MESSAGING_MESSAGE_CONVERSATION_ID
MESSAGING_MESSAGE_BODY_SIZE = _messaging.MESSAGING_MESSAGE_BODY_SIZE
ERROR_TYPE = _error.ERROR_TYPE
SERVER_ADDRESS = _server.SERVER_ADDRESS
SERVER_PORT = _server.SERVER_PORT
RPC_SYSTEM_NAME = _rpc.RPC_SYSTEM_NAME
RPC_METHOD = _rpc.RPC_METHOD
RPC_RESPONSE_STATUS_CODE = _rpc.RPC_RESPONSE_STATUS_CODE

RABBITMQ = "rabbitmq"
SEND = "send"
PUBLISH = "publish"
RECEIVE = "receive"

REPLY_DESTINATION = "(reply)"

PRIS_WIRE = "pris_wire"
OTHER_METHOD = "_OTHER"

MESSAGING_CLIENT_OPERATION_DURATION = "messaging.client.operation.duration"
MESSAGING_CLIENT_SENT_MESSAGES = "messaging.client.sent.messages"
MESSAGING_CLIENT_CONSUMED_MESSAGES = "messaging.client.consumed.messages"
RPC_SERVER_CALL_DURATION = "rpc.server.call.duration"

DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10)
