#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from django.conf import settings
import pymongo
import os

client = pymongo.MongoClient(host='repo.favbuy.org')
db = client['godzilla']
local_client = pymongo.MongoClient(host=settings.MONGOHOST)
local_db = local_client[settings.APP_NAME]
cate_dict = {}

for cate in db.cate.find():
    local_db.categories.save(cate)