# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from shiva.core.communication_objects import helpers_pb2 as shiva_dot_core_dot_communication__objects_dot_helpers__pb2


class IOHandlerStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.AskIORequest = channel.unary_unary(
        '/communication_objects.IOHandler/AskIORequest',
        request_serializer=shiva_dot_core_dot_communication__objects_dot_helpers__pb2.SimpleMessage.SerializeToString,
        response_deserializer=shiva_dot_core_dot_communication__objects_dot_helpers__pb2.SimpleMessage.FromString,
        )
    self.DoneIO = channel.unary_unary(
        '/communication_objects.IOHandler/DoneIO',
        request_serializer=shiva_dot_core_dot_communication__objects_dot_helpers__pb2.SimpleMessage.SerializeToString,
        response_deserializer=shiva_dot_core_dot_communication__objects_dot_helpers__pb2.Empty.FromString,
        )


class IOHandlerServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def AskIORequest(self, request, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def DoneIO(self, request, context):
    """rpc SendSpecs(SimpleMessage) returns (Empty); // used for the single environments to check-in
    rpc GetSpecs(SimpleMessage) returns (SimpleMessage);
    rpc GetActions(SimpleMessage) returns (SimpleMessage);
    rpc SendConfig(ConfigProto) returns (Empty);
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_IOHandlerServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'AskIORequest': grpc.unary_unary_rpc_method_handler(
          servicer.AskIORequest,
          request_deserializer=shiva_dot_core_dot_communication__objects_dot_helpers__pb2.SimpleMessage.FromString,
          response_serializer=shiva_dot_core_dot_communication__objects_dot_helpers__pb2.SimpleMessage.SerializeToString,
      ),
      'DoneIO': grpc.unary_unary_rpc_method_handler(
          servicer.DoneIO,
          request_deserializer=shiva_dot_core_dot_communication__objects_dot_helpers__pb2.SimpleMessage.FromString,
          response_serializer=shiva_dot_core_dot_communication__objects_dot_helpers__pb2.Empty.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'communication_objects.IOHandler', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
