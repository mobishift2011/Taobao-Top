#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import simplejson
from django.conf import settings
from apis.base.models import *

from datetime import datetime, timedelta

import pymongo
import requests
import os

def get_categories(request):
    return render(request, 'dashboard.html')


def convert_link(product):
    product.url = product.origin_url


def dashboard(request):
    now = datetime.utcnow()
    today = now.replace(hour=0,minute=0,second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    total_user_counts = User.objects.count()
    new_user_counts = User.objects(date_joined__gt=today).count()
    lottery_user_counts = Lottery.objects.count()
    new_lottery_user_counts = Lottery.objects(period__gt=yesterday).count()
    return render(request, 'dashboard.html', {
            'total_user_counts': total_user_counts,
            'new_user_counts': new_user_counts,
            'lottery_user_counts': lottery_user_counts,
            'new_lottery_user_counts': new_lottery_user_counts
        })


def usersHandle(request):
    users = User.objects()
    return render(request, 'users.html', {'users': users})


def papersHandle(request):
    papers = Paper.objects().order_by('-period')
    return render(request, 'papers.html', {'papers': papers})


def paperCreateHandle(request):
    if request.method == 'GET':
        return render(request, 'paper.html')

    elif request.method == 'POST':
        period = request.POST.get('period')

        if period is None:
            return render(request, 'paper.html')

        period = datetime.strptime(period, '%m/%d/%Y')
        bonus = request.POST.get('bonus')
        deadline = request.POST.get('deadline')
        paper = Paper(period=period)

        if bonus:
            paper.bonus = float(bonus)

        if deadline:
            deadline = datetime.strptime(deadline, '%m/%d/%Y')
            paper.deadline = deadline

        paper.save()
        return render(request, 'paper.html')


def paperHandle(request, paper_id):
    paper = Paper.objects(id=paper_id).first()

    if request.method == 'GET':
        return render(request, 'paper.html', {'paper':paper})

    elif request.method == 'POST':
        period = request.POST.get('period')
        bonus = request.POST.get('bonus')
        deadline = request.POST.get('deadline')
        is_online = bool(int(request.POST.get('is_online', 0)))
        paper.is_online = is_online

        if period:
            period = datetime.strptime(period, '%m/%d/%Y')
            paper.period = period

        if bonus:
            paper.bonus = float(bonus)

        if deadline:
            deadline = datetime.strptime(deadline, '%m/%d/%Y')
            paper.deadline = deadline

        paper.save()
        return papersHandle(request)

    elif request.method == 'DELETE':
        paper.delete()
        return HttpResponse(simplejson.dumps({'success': True}))


def paperQuizesHandle(request, paper_id):
    paper = Paper.objects(id=paper_id).first()

    if request.method == 'GET':
        return render(request, 'quiz.html', {'paper': paper})

    elif request.method == 'POST':
        quiz = Quiz()
        for k,v in request.POST.iteritems():
            if k == 'images':
                v = [v]
            setattr(quiz, k, v)

        quiz.save()

        if quiz not in paper.quizes:
            paper.quizes.append(quiz)
            paper.save()

        return render(request, 'quiz.html', {'paper': paper})


def paperQuizHandle(request, paper_id, quiz_id):
    paper = Paper.objects(id=paper_id).first()
    quiz = Quiz.objects(id=quiz_id).first()

    if request.method == 'GET':
        return render(request, 'quiz.html', {'paper': paper, 'quiz': quiz})

    elif request.method == 'DELETE':
        paper.quizes.remove(quiz)
        paper.save()
        return HttpResponse(simplejson.dumps({'success': (quiz not in paper.quizes)}))

    elif request.method == 'POST':
        for k,v in request.POST.iteritems():
            if k == 'images':
                v = [v]
            setattr(quiz, k, v)

        quiz.save()
        return papersHandle(request)


def quizProdsHandle(request, quiz_id):
    quiz = Quiz.objects(id=quiz_id).first()

    if request.method == 'GET':
        return render(request, 'product.html', {'quiz': quiz})

    elif request.method == 'POST':
        tid = request.POST.get('tid')
        if not tid:
            return HttpResponse(simplejson.dumps({'success': False}))

        product = Product.objects(tid=tid).first()
        if not product:
            product = Product(tid=tid)

        for k,v in request.POST.iteritems():
            if k == 'price':
                v = float(v)
            elif k == 'images':
                v = [v]
            setattr(product, k, v)

        convert_link(product)
        product.save()

        if product not in quiz.products:
            quiz.products.append(product)
            quiz.save()

        return HttpResponse(simplejson.dumps({'success': (product in quiz.products)}))


def quizProdHandle(request, quiz_id, product_id):
    quiz = Quiz.objects(id=quiz_id).first()
    product = Product.objects(id=product_id).first()

    if request.method == 'GET':
        return render(request, 'product.html', {'product': product, 'quiz': quiz})

    elif request.method == 'POST':
        product = Product.objects(tid=request.POST.get('tid')).first()
        origin_url = request.POST.get('origin_url')
        is_convert_url = origin_url and origin_url != product.origin_url

        for k,v in request.POST.iteritems():
            if k == 'price':
                v = float(v)
            elif k == 'images':
                v = [v]
            setattr(product, k, v)

        if is_convert_url:
            convert_link(product)
        product.save()
        return papersHandle(request)

    elif request.method == 'DELETE':
        quiz.products.remove(product)
        quiz.save()
        return HttpResponse(simplejson.dumps({'success': (product not in quiz.products)}))


client = pymongo.MongoClient(host=settings.MONGOHOST)
db = client[settings.APP_NAME]
category_dict = {cat['cid']: cat['name'] for cat in db.categories.find({'$or':[{'level':1}, {'level':2}]})}

def baokuan_by_category(request, cat_id):
    url = u'{}/api/v1/cate/hotproducts_list/?cid={}&format=json'.format(settings.BAOKUAN_HOST, cat_id)
    res = requests.get(url, auth=('favbuy', 'tempfavbuy'))
    items = res.json().get('items', [])
    return HttpResponse(simplejson.dumps({'products': items, 'categories': category_dict}))


def categories(request):
    return HttpResponse(simplejson.dumps({'categories': category_dict}))


def lotteriesHandle(request):
    lotteries = Lottery.objects().order_by('-period')
    return render(request, 'lotteries.html', {'lotteries': lotteries})

def markHandle(request):
    paper_id = request.GET.get('paper_id')
    user_id = request.GET.get('user_id')
    user = User.objects(id=user_id).first()
    paper = Paper.objects(id=paper_id).first()
    mark = Mark.objects(user=user, paper=paper).first()
    return HttpResponse(simplejson.dumps({
            'rank': mark.rank,
            'score': mark.score,
            'bonus': mark.bonus,
            'is_get_bonus': mark.is_get_bonus,
        }))