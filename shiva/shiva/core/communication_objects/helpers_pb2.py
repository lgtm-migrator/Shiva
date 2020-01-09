# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: shiva/core/communication_objects/helpers.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='shiva/core/communication_objects/helpers.proto',
  package='communication_objects',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n.shiva/core/communication_objects/helpers.proto\x12\x15\x63ommunication_objects\"\x15\n\x05\x45mpty\x12\x0c\n\x04\x64\x61ta\x18\x01 \x01(\x05\"\x1a\n\nListOfInts\x12\x0c\n\x04\x64\x61ta\x18\x01 \x03(\x05\"\x1c\n\x0cListOfFloats\x12\x0c\n\x04\x64\x61ta\x18\x01 \x03(\x02\"\x1d\n\rListOfStrings\x12\x0c\n\x04\x64\x61ta\x18\x01 \x03(\tb\x06proto3')
)




_EMPTY = _descriptor.Descriptor(
  name='Empty',
  full_name='communication_objects.Empty',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='data', full_name='communication_objects.Empty.data', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=73,
  serialized_end=94,
)


_LISTOFINTS = _descriptor.Descriptor(
  name='ListOfInts',
  full_name='communication_objects.ListOfInts',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='data', full_name='communication_objects.ListOfInts.data', index=0,
      number=1, type=5, cpp_type=1, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=96,
  serialized_end=122,
)


_LISTOFFLOATS = _descriptor.Descriptor(
  name='ListOfFloats',
  full_name='communication_objects.ListOfFloats',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='data', full_name='communication_objects.ListOfFloats.data', index=0,
      number=1, type=2, cpp_type=6, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=124,
  serialized_end=152,
)


_LISTOFSTRINGS = _descriptor.Descriptor(
  name='ListOfStrings',
  full_name='communication_objects.ListOfStrings',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='data', full_name='communication_objects.ListOfStrings.data', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=154,
  serialized_end=183,
)

DESCRIPTOR.message_types_by_name['Empty'] = _EMPTY
DESCRIPTOR.message_types_by_name['ListOfInts'] = _LISTOFINTS
DESCRIPTOR.message_types_by_name['ListOfFloats'] = _LISTOFFLOATS
DESCRIPTOR.message_types_by_name['ListOfStrings'] = _LISTOFSTRINGS
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Empty = _reflection.GeneratedProtocolMessageType('Empty', (_message.Message,), {
  'DESCRIPTOR' : _EMPTY,
  '__module__' : 'shiva.core.communication_objects.helpers_pb2'
  # @@protoc_insertion_point(class_scope:communication_objects.Empty)
  })
_sym_db.RegisterMessage(Empty)

ListOfInts = _reflection.GeneratedProtocolMessageType('ListOfInts', (_message.Message,), {
  'DESCRIPTOR' : _LISTOFINTS,
  '__module__' : 'shiva.core.communication_objects.helpers_pb2'
  # @@protoc_insertion_point(class_scope:communication_objects.ListOfInts)
  })
_sym_db.RegisterMessage(ListOfInts)

ListOfFloats = _reflection.GeneratedProtocolMessageType('ListOfFloats', (_message.Message,), {
  'DESCRIPTOR' : _LISTOFFLOATS,
  '__module__' : 'shiva.core.communication_objects.helpers_pb2'
  # @@protoc_insertion_point(class_scope:communication_objects.ListOfFloats)
  })
_sym_db.RegisterMessage(ListOfFloats)

ListOfStrings = _reflection.GeneratedProtocolMessageType('ListOfStrings', (_message.Message,), {
  'DESCRIPTOR' : _LISTOFSTRINGS,
  '__module__' : 'shiva.core.communication_objects.helpers_pb2'
  # @@protoc_insertion_point(class_scope:communication_objects.ListOfStrings)
  })
_sym_db.RegisterMessage(ListOfStrings)


# @@protoc_insertion_point(module_scope)
