#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from django.shortcuts import render
from apis.base.models import *

def productHandle(request, product_id):
    product = Product.objects(id=product_id).first()
    return render(request, 'share.html', {'product': product})