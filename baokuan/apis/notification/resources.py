#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from models import Notification
from apis.base.authentications import UserAuthentication
from apis.base.resources import BaseResource
from tastypie_mongoengine import fields

class NotificationResource(BaseResource):
    user = fields.ReferenceField(to='apis.base.resources.UserResource', 
                                            attribute='user', full=True, null=True)
    
    class Meta:
        queryset = Notification.objects()
        allowed_methods = ('post', 'delete')
        authentication = UserAuthentication()
        excludes = ('resource_uri',)