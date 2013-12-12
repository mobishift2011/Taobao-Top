#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from django.shortcuts import render
from apis.base.models import *

def test(request):
    return render(request, 'dashboard.html')