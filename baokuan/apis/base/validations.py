#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from tastypie.validation import Validation

class UserValidation(Validation):
    def is_valid(self, bundle, request=None):
        if not bundle.data:
            return {'__all__': 'Not quite what I had in mind.'}

        errors = {}

        for key, value in bundle.data.items():
            if not isinstance(value, basestring):
                continue

            if not 'awesome' in value:
                errors[key] = ['NOT ENOUGH AWESOME. NEEDS MORE.']

        return errors


class MarkValidation(Validation):
    def is_valid(self, bundle, request=None):
        # print '~~~~~~~~~~~~~~~', bundle.data
        # if not bundle.data:
        #     return {'__all__': 'post params required'}

        errors = {}

        for f in ('user', 'quiz', 'answer'):
            if f not in bundle.data:
                errors[f] = ['required']
        return errors
        print '~~~~~~~~~~~~~~~~~~~~~', errors
        return errors