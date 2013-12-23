#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# from utils.mongo import IncludeUniqueIDField
from bson.objectid import ObjectId
from mongoengine import *
from mongoengine.django.auth import User

from datetime import datetime

class Account(Document):
    aid = StringField(required=True)
    platform = StringField(required=True, unique_with='aid')
    screen_name = StringField(required=True)
    token = StringField()
    
    meta = {
        'indexes': [('aid', 'platform')]
    }


class User(User):
    id = StringField(primary_key=True, default=str(ObjectId()))
    screen_name = StringField()
    phone = StringField()
    device = StringField()
    accounts = ListField(ReferenceField(Account, reverse_delete_rule=PULL))

    meta = {
        'indexes': ['device', 'accounts',]
    }

    def create_user(self, username=None, password=None, email=None, **kwargs):
        new_user = super(User, self).create_user(username=username, password=password, email=email)
        for k, v in kwargs.iteritems():
            setattr(new_user, k, v)
        
        new_user.save()
        return new_user


class PwdRstToken(Document):
    user = ReferenceField(User, required=True)
    token = StringField(required=True)
    generated_at = DateTimeField(required=True)
    expires = IntField(default=10) # Cell is minute.

    meta = {
        'indexes': ['user']
    }


class Product(Document):
    title = StringField()
    description = StringField()
    origin_url = URLField()
    url = URLField(verify_exists=True)
    images = ListField()
    price = FloatField()
    categories = ListField()
    shared = IntField(default=0)
    tid = StringField(unique=True) #taobao id


class Quiz(Document):
    title = StringField()
    description = StringField()
    images = ListField()
    products = ListField(ReferenceField(Product, reverse_delete_rule=PULL))
    categories = ListField()
    created_at = DateTimeField(default=datetime.utcnow())

    meta = {
        'indexes': ['created_at', 'categories']
    }


class Paper(Document):
    period = DateTimeField(required=True)
    quizes = ListField(ReferenceField(Quiz, reverse_delete_rule=PULL))
    categories = ListField()
    answers = DictField() # The answers to the certain quizes aggregated by all participants.
    bonus = FloatField(default=0.0)
    deadline = DateTimeField() # The time to get the bonus.
    is_online = BooleanField(default=False)

    meta = {
        'indexes': ['period', 'is_online']
    }


class Mark(Document):
    user = ReferenceField(User, required=True)
    paper = ReferenceField(Paper, required=True, unique_with='user')
    answers = DictField(required=True) # The answers to the paper by the user. eg. {quiz_id: user_id}
    period = DateTimeField(required=True)
    score = FloatField()
    rank = IntField()
    bonus = FloatField(default=0.0)
    is_get_bonus = IntField(default=0) # 0: unaccept, 1: beging processed, 2: accepted.
    total_awards = IntField(default=0)
    phone = StringField()
    created_at = DateTimeField(default=datetime.utcnow())

    meta = {
        'indexes': [('user', 'paper'), 'created_at', 'period']
    }


class Lottery(Document):
    users = ListField(ReferenceField(User, reverse_delete_rule=PULL))
    score = IntField() # the highest user score
    paper = ReferenceField(Paper, required=True, unique=True)
    period = DateTimeField(required=True)

    meta = {
        'indexes': ['period']
    }


class FavoriteCategory(Document):
    user = ReferenceField(User, required=True, unique=True)
    categories = ListField()

    meta = {
        'indexes': ['user']
    }
