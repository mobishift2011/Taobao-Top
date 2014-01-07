#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from django.conf import settings
from mongoengine import *
from apis.base.models import User
from APNSWrapper import *
from jpush import JPushClient
from datetime import datetime

import binascii
import os
import time

class Notification(Document):
    user = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    device_token = StringField(required=True)
    platform = StringField(required=True, unique_with=['user', 'device_token']) # ios / android
    configs = DictField() # badge type, sound type, etc., maybe never be used
    is_on = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow())

    meta = {
        'indexes': ['user']
    }

    def notify(self, **kwargs):
        try:
            getattr(self, u'{}_notify'.format(self.platform))(**kwargs)
        except AttributeError:
            self.ios_notify(**kwargs)

    def ios_notify(self, **kwargs):
        if not self.is_on:
            return

        badge = kwargs.get('badge', self.configs.get('badge'))
        sound = kwargs.get('sound', self.configs.get('sound'))
        device_token = binascii.unhexlify(self.device_token.replace(' ', ''))
        pem_path = os.path.join(os.path.dirname(__file__), u'cert_{}.pem'.format(settings.ENV).lower())
        wrapper = APNSNotificationWrapper(pem_path, settings.DEBUG)
        message = APNSNotification()
        message.token(device_token)
        message.alert(kwargs.get('alert', ''))

        if type(badge) == int:
            message.badge(badge)

        if sound:
            message.sound()
        
        wrapper.append(message)
        wrapper.notify()

    def android_notify(self, **kwargs):
        """
        JPush API 对访问次数，具有频率控制。即一定的时间窗口内，API 允许调用的次数是有限制的。

        频率控制定义
        一个时间窗口 T，当前定义为：1 分钟。

        频率控制基于 AppKey 来定义，每个 AppKey 有一个基础的调用频率限制数量。免费版本如下表：

        API 类型  频率（次/T）
        Push API v2 600
        Report Received API 2400
        收费版本根据终端用户规模的不同，具有不同级别的频率。如有需要，请访问 JPush价格说明了解更多
        """
        sendno = int(time.time())
        app_key = 'da2645a5d128839db1ae2029'
        master_secret = '233e2277f5a6bf6350c71104'

        jpush_client = JPushClient(master_secret)

        # Send message by tag
        jpush_client.send_notification_by_alias(self.device_token, app_key, sendno, 'user score and rank',
                                                                    '',
                                                                    kwargs.get('alert', ''), 'android')


class NotificationHistory(Document):
    user = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    notif_type = StringField(required=True, unique_with='user')
    lasted_at = DateTimeField(datetime.utcnow())

    meta = {
        'indexes': [('user', 'notif_type')]
    }