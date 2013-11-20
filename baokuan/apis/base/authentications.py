#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from tastypie.authentication import SessionAuthentication

class UserAuthentication(SessionAuthentication):
    def is_authenticated(self, request, **kwargs):
        # return super(UserAuthentication, self).is_authenticated(request, **kwargs) \
        #     or 'GET' == request.method
        return True # TODO remove
        return request.user.is_authenticated() or 'GET' == request.method