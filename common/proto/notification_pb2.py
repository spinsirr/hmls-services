# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: common/proto/notification.proto
# Protobuf Python Version: 4.25.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1f\x63ommon/proto/notification.proto\x12\x0cnotification\"\x1d\n\x0cTokenRequest\x12\r\n\x05token\x18\x01 \x01(\t\"\x8d\x02\n\x13NotificationRequest\x12\r\n\x05token\x18\x01 \x01(\t\x12\x11\n\trecipient\x18\x02 \x01(\t\x12\x19\n\x11notification_type\x18\x03 \x01(\t\x12\x0f\n\x07subject\x18\x04 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x05 \x01(\t\x12Z\n\x15notification_metadata\x18\x06 \x03(\x0b\x32;.notification.NotificationRequest.NotificationMetadataEntry\x1a;\n\x19NotificationMetadataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"\xc4\x02\n\x14NotificationResponse\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x11\n\trecipient\x18\x02 \x01(\t\x12\x19\n\x11notification_type\x18\x03 \x01(\t\x12\x0f\n\x07subject\x18\x04 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x05 \x01(\t\x12[\n\x15notification_metadata\x18\x06 \x03(\x0b\x32<.notification.NotificationResponse.NotificationMetadataEntry\x12\x0e\n\x06status\x18\x07 \x01(\t\x12\x12\n\ncreated_at\x18\x08 \x01(\t\x12\x12\n\nupdated_at\x18\t \x01(\t\x1a;\n\x19NotificationMetadataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\"R\n\x15NotificationsResponse\x12\x39\n\rnotifications\x18\x01 \x03(\x0b\x32\".notification.NotificationResponse\"\x14\n\x12HealthCheckRequest\"6\n\x13HealthCheckResponse\x12\x0e\n\x06status\x18\x01 \x01(\t\x12\x0f\n\x07service\x18\x02 \x01(\t2\x99\x02\n\x13NotificationService\x12Y\n\x10SendNotification\x12!.notification.NotificationRequest\x1a\".notification.NotificationResponse\x12S\n\x10GetNotifications\x12\x1a.notification.TokenRequest\x1a#.notification.NotificationsResponse\x12R\n\x0bHealthCheck\x12 .notification.HealthCheckRequest\x1a!.notification.HealthCheckResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'common.proto.notification_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_NOTIFICATIONREQUEST_NOTIFICATIONMETADATAENTRY']._options = None
  _globals['_NOTIFICATIONREQUEST_NOTIFICATIONMETADATAENTRY']._serialized_options = b'8\001'
  _globals['_NOTIFICATIONRESPONSE_NOTIFICATIONMETADATAENTRY']._options = None
  _globals['_NOTIFICATIONRESPONSE_NOTIFICATIONMETADATAENTRY']._serialized_options = b'8\001'
  _globals['_TOKENREQUEST']._serialized_start=49
  _globals['_TOKENREQUEST']._serialized_end=78
  _globals['_NOTIFICATIONREQUEST']._serialized_start=81
  _globals['_NOTIFICATIONREQUEST']._serialized_end=350
  _globals['_NOTIFICATIONREQUEST_NOTIFICATIONMETADATAENTRY']._serialized_start=291
  _globals['_NOTIFICATIONREQUEST_NOTIFICATIONMETADATAENTRY']._serialized_end=350
  _globals['_NOTIFICATIONRESPONSE']._serialized_start=353
  _globals['_NOTIFICATIONRESPONSE']._serialized_end=677
  _globals['_NOTIFICATIONRESPONSE_NOTIFICATIONMETADATAENTRY']._serialized_start=291
  _globals['_NOTIFICATIONRESPONSE_NOTIFICATIONMETADATAENTRY']._serialized_end=350
  _globals['_NOTIFICATIONSRESPONSE']._serialized_start=679
  _globals['_NOTIFICATIONSRESPONSE']._serialized_end=761
  _globals['_HEALTHCHECKREQUEST']._serialized_start=763
  _globals['_HEALTHCHECKREQUEST']._serialized_end=783
  _globals['_HEALTHCHECKRESPONSE']._serialized_start=785
  _globals['_HEALTHCHECKRESPONSE']._serialized_end=839
  _globals['_NOTIFICATIONSERVICE']._serialized_start=842
  _globals['_NOTIFICATIONSERVICE']._serialized_end=1123
# @@protoc_insertion_point(module_scope)
