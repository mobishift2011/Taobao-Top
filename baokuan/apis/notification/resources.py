#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from models import Notification
from apis.base.authentications import UserAuthentication
from apis.base.authorizations import UserAuthorization
from apis.base.resources import BaseResource
from tastypie_mongoengine import fields
from tastypie.http import *
from tastypie.utils import trailing_slash
from mongoengine import NotUniqueError
from django.conf.urls import url

class NotificationResource(BaseResource):
    user = fields.ReferenceField(to='apis.base.resources.UserResource', 
                                            attribute='user', full=True, null=True)
    
    class Meta:
        queryset = Notification.objects()
        allowed_methods = ('post',)
        authentication = UserAuthentication()
        authorization = UserAuthorization()
        excludes = ('resource_uri',)

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/delete%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('delete'), name="api_delete"),
        ]

    def post_list(self, request, **kwargs):
        try:
            return super(NotificationResource, self).post_list(request, **kwargs)
        except NotUniqueError as e:
            return self.create_response(request, {}, 201)
            # return self.create_response(request, {'error_code': 1, 'error_message': e})

    def delete(self, request, **kwargs):
        user = request.user
        if not user.is_authenticated():
            return self.create_response(request, {}, HttpUnauthorized)

        self.method_check(request, allowed=('post',))
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        device_token = data.get('device_token')
        platform = data.get('platform')
        notification = Notification.objects(
            user = user,
            device_token = device_token,
            platform = platform,
        )

        if not notification:
            return self.create_response(request, \
                        {'error_code': 1, 'error_message': 'nothing to delete'})

        notification.delete()
        return self.create_response(request, {'success': True})