# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: shiva/core/communication_objects/specs.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from shiva.core.communication_objects import enums_pb2 as shiva_dot_core_dot_communication__objects_dot_enums__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='shiva/core/communication_objects/specs.proto',
  package='communication_objects',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n,shiva/core/communication_objects/specs.proto\x12\x15\x63ommunication_objects\x1a,shiva/core/communication_objects/enums.proto\"F\n\x10\x41\x63tionSpaceProto\x12\x10\n\x08\x64iscrete\x18\x01 \x01(\x05\x12\r\n\x05param\x18\x02 \x01(\x05\x12\x11\n\tacs_space\x18\x03 \x01(\x05\"}\n\rEnvSpecsProto\x12\x19\n\x11observation_space\x18\x01 \x01(\x05\x12=\n\x0c\x61\x63tion_space\x18\x02 \x01(\x0b\x32\'.communication_objects.ActionSpaceProto\x12\x12\n\nnum_agents\x18\x03 \x01(\x05\"_\n\x12MultiEnvSpecsProto\x12\x37\n\tenv_specs\x18\x01 \x01(\x0b\x32$.communication_objects.EnvSpecsProto\x12\x10\n\x08num_envs\x18\x02 \x01(\x05\"!\n\x11LearnerSpecsProto\x12\x0c\n\x04\x64\x61ta\x18\x01 \x01(\t\"\xd4\x02\n\nSpecsProto\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x32\n\x04type\x18\x02 \x01(\x0e\x32$.communication_objects.ComponentType\x12\x31\n\x06status\x18\x03 \x01(\x0e\x32!.communication_objects.StatusType\x12\x0f\n\x07\x61\x64\x64ress\x18\x04 \x01(\t\x12\x33\n\x03\x65nv\x18\x05 \x01(\x0b\x32$.communication_objects.EnvSpecsProtoH\x00\x12\x39\n\x04menv\x18\x06 \x01(\x0b\x32).communication_objects.MultiEnvSpecsProtoH\x00\x12;\n\x07learner\x18\x07 \x01(\x0b\x32(.communication_objects.LearnerSpecsProtoH\x00\x12\r\n\x05\x65xtra\x18\x08 \x01(\tB\x06\n\x04\x64\x61tab\x06proto3')
  ,
  dependencies=[shiva_dot_core_dot_communication__objects_dot_enums__pb2.DESCRIPTOR,])




_ACTIONSPACEPROTO = _descriptor.Descriptor(
  name='ActionSpaceProto',
  full_name='communication_objects.ActionSpaceProto',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='discrete', full_name='communication_objects.ActionSpaceProto.discrete', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='param', full_name='communication_objects.ActionSpaceProto.param', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='acs_space', full_name='communication_objects.ActionSpaceProto.acs_space', index=2,
      number=3, type=5, cpp_type=1, label=1,
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
  serialized_start=117,
  serialized_end=187,
)


_ENVSPECSPROTO = _descriptor.Descriptor(
  name='EnvSpecsProto',
  full_name='communication_objects.EnvSpecsProto',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='observation_space', full_name='communication_objects.EnvSpecsProto.observation_space', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='action_space', full_name='communication_objects.EnvSpecsProto.action_space', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='num_agents', full_name='communication_objects.EnvSpecsProto.num_agents', index=2,
      number=3, type=5, cpp_type=1, label=1,
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
  serialized_start=189,
  serialized_end=314,
)


_MULTIENVSPECSPROTO = _descriptor.Descriptor(
  name='MultiEnvSpecsProto',
  full_name='communication_objects.MultiEnvSpecsProto',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='env_specs', full_name='communication_objects.MultiEnvSpecsProto.env_specs', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='num_envs', full_name='communication_objects.MultiEnvSpecsProto.num_envs', index=1,
      number=2, type=5, cpp_type=1, label=1,
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
  serialized_start=316,
  serialized_end=411,
)


_LEARNERSPECSPROTO = _descriptor.Descriptor(
  name='LearnerSpecsProto',
  full_name='communication_objects.LearnerSpecsProto',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='data', full_name='communication_objects.LearnerSpecsProto.data', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
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
  serialized_start=413,
  serialized_end=446,
)


_SPECSPROTO = _descriptor.Descriptor(
  name='SpecsProto',
  full_name='communication_objects.SpecsProto',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='communication_objects.SpecsProto.id', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='type', full_name='communication_objects.SpecsProto.type', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='status', full_name='communication_objects.SpecsProto.status', index=2,
      number=3, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='address', full_name='communication_objects.SpecsProto.address', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='env', full_name='communication_objects.SpecsProto.env', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='menv', full_name='communication_objects.SpecsProto.menv', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='learner', full_name='communication_objects.SpecsProto.learner', index=6,
      number=7, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='extra', full_name='communication_objects.SpecsProto.extra', index=7,
      number=8, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
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
    _descriptor.OneofDescriptor(
      name='data', full_name='communication_objects.SpecsProto.data',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=449,
  serialized_end=789,
)

_ENVSPECSPROTO.fields_by_name['action_space'].message_type = _ACTIONSPACEPROTO
_MULTIENVSPECSPROTO.fields_by_name['env_specs'].message_type = _ENVSPECSPROTO
_SPECSPROTO.fields_by_name['type'].enum_type = shiva_dot_core_dot_communication__objects_dot_enums__pb2._COMPONENTTYPE
_SPECSPROTO.fields_by_name['status'].enum_type = shiva_dot_core_dot_communication__objects_dot_enums__pb2._STATUSTYPE
_SPECSPROTO.fields_by_name['env'].message_type = _ENVSPECSPROTO
_SPECSPROTO.fields_by_name['menv'].message_type = _MULTIENVSPECSPROTO
_SPECSPROTO.fields_by_name['learner'].message_type = _LEARNERSPECSPROTO
_SPECSPROTO.oneofs_by_name['data'].fields.append(
  _SPECSPROTO.fields_by_name['env'])
_SPECSPROTO.fields_by_name['env'].containing_oneof = _SPECSPROTO.oneofs_by_name['data']
_SPECSPROTO.oneofs_by_name['data'].fields.append(
  _SPECSPROTO.fields_by_name['menv'])
_SPECSPROTO.fields_by_name['menv'].containing_oneof = _SPECSPROTO.oneofs_by_name['data']
_SPECSPROTO.oneofs_by_name['data'].fields.append(
  _SPECSPROTO.fields_by_name['learner'])
_SPECSPROTO.fields_by_name['learner'].containing_oneof = _SPECSPROTO.oneofs_by_name['data']
DESCRIPTOR.message_types_by_name['ActionSpaceProto'] = _ACTIONSPACEPROTO
DESCRIPTOR.message_types_by_name['EnvSpecsProto'] = _ENVSPECSPROTO
DESCRIPTOR.message_types_by_name['MultiEnvSpecsProto'] = _MULTIENVSPECSPROTO
DESCRIPTOR.message_types_by_name['LearnerSpecsProto'] = _LEARNERSPECSPROTO
DESCRIPTOR.message_types_by_name['SpecsProto'] = _SPECSPROTO
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

ActionSpaceProto = _reflection.GeneratedProtocolMessageType('ActionSpaceProto', (_message.Message,), {
  'DESCRIPTOR' : _ACTIONSPACEPROTO,
  '__module__' : 'shiva.core.communication_objects.specs_pb2'
  # @@protoc_insertion_point(class_scope:communication_objects.ActionSpaceProto)
  })
_sym_db.RegisterMessage(ActionSpaceProto)

EnvSpecsProto = _reflection.GeneratedProtocolMessageType('EnvSpecsProto', (_message.Message,), {
  'DESCRIPTOR' : _ENVSPECSPROTO,
  '__module__' : 'shiva.core.communication_objects.specs_pb2'
  # @@protoc_insertion_point(class_scope:communication_objects.EnvSpecsProto)
  })
_sym_db.RegisterMessage(EnvSpecsProto)

MultiEnvSpecsProto = _reflection.GeneratedProtocolMessageType('MultiEnvSpecsProto', (_message.Message,), {
  'DESCRIPTOR' : _MULTIENVSPECSPROTO,
  '__module__' : 'shiva.core.communication_objects.specs_pb2'
  # @@protoc_insertion_point(class_scope:communication_objects.MultiEnvSpecsProto)
  })
_sym_db.RegisterMessage(MultiEnvSpecsProto)

LearnerSpecsProto = _reflection.GeneratedProtocolMessageType('LearnerSpecsProto', (_message.Message,), {
  'DESCRIPTOR' : _LEARNERSPECSPROTO,
  '__module__' : 'shiva.core.communication_objects.specs_pb2'
  # @@protoc_insertion_point(class_scope:communication_objects.LearnerSpecsProto)
  })
_sym_db.RegisterMessage(LearnerSpecsProto)

SpecsProto = _reflection.GeneratedProtocolMessageType('SpecsProto', (_message.Message,), {
  'DESCRIPTOR' : _SPECSPROTO,
  '__module__' : 'shiva.core.communication_objects.specs_pb2'
  # @@protoc_insertion_point(class_scope:communication_objects.SpecsProto)
  })
_sym_db.RegisterMessage(SpecsProto)


# @@protoc_insertion_point(module_scope)
