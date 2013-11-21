#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from models import User

from django.contrib import auth
from tastypie.authentication import SessionAuthentication

class BaokuanEngineBackend(object):
    """Authenticate using MongoEngine 
        and apis.base.models.User
        inheriting from mongoengine.django.auth.User.
    """

    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, username=None, password=None):
        user = User.objects(username=username).first()
        if user:
            if password and user.check_password(password):
                backend = auth.get_backends()[0]
                user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
                return user
        return None

    def get_user(self, user_id):
        return User.objects.with_id(user_id)


class UserAuthentication(SessionAuthentication):
    def is_authenticated(self, request, **kwargs):
        # return super(UserAuthentication, self).is_authenticated(request, **kwargs) \
        #     or 'GET' == request.method
        return request.user.is_authenticated() or 'GET' == request.method