# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: index_tree.proto
# Protobuf Python Version: 4.25.3
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10index_tree.proto\x12\nindex_tree\"L\n\x05Value\x12\x11\n\x07str_val\x18\x01 \x01(\tH\x00\x12\x11\n\x07int_val\x18\x02 \x01(\x03H\x00\x12\x14\n\ndouble_val\x18\x03 \x01(\x01H\x00\x42\x07\n\x05value\"j\n\x04Node\x12\x0c\n\x04\x61xis\x18\x01 \x01(\t\x12 \n\x05value\x18\x02 \x03(\x0b\x32\x11.index_tree.Value\x12\x0e\n\x06result\x18\x03 \x03(\x01\x12\"\n\x08\x63hildren\x18\x04 \x03(\x0b\x32\x10.index_tree.Node')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'index_tree_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_VALUE']._serialized_start=32
  _globals['_VALUE']._serialized_end=108
  _globals['_NODE']._serialized_start=110
  _globals['_NODE']._serialized_end=216
# @@protoc_insertion_point(module_scope)
