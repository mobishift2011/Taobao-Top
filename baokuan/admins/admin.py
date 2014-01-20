#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import simplejson
from django.conf import settings
from apis.base.models import *
from functools import wraps
from datetime import datetime, timedelta
from .categories import cats

import pymongo
import requests
import os

def unauthed():
    response = HttpResponse("""<html><title>Auth required</title><body>
                            <h1>Authorization Required</h1></body></html>""", mimetype="text/html")
    response['WWW-Authenticate'] = 'Basic realm="Development"'
    response.status_code = 401
    return response

def http_basic_auth(func):
    @wraps(func)
    def process_request(request, *args, **kwargs):
        if not request.META.has_key('HTTP_AUTHORIZATION'):
            return unauthed()
        else:
            authentication = request.META['HTTP_AUTHORIZATION']
            (authmeth, auth) = authentication.split(' ',1)
            if 'basic' != authmeth.lower():
                return unauthed()
            auth = auth.strip().decode('base64')
            username, password = auth.split(':',1)
            if username == 'favbuy' and password == 'favbuy0208':
                try:
                    return func(request, *args, **kwargs)
                except TypeError:
                    return func(request)
            
            return unauthed()

    return process_request


def get_categories(request):
    return render(request, 'dashboard.html')


def convert_link(product):
    product.url = product.origin_url


@http_basic_auth
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


@http_basic_auth
def usersHandle(request):
    users = User.objects()
    return render(request, 'users.html', {'users': users})


@http_basic_auth
def papersHandle(request):
    papers = Paper.objects().order_by('-period')
    return render(request, 'papers.html', {'papers': papers})


@http_basic_auth
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


@http_basic_auth
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


@http_basic_auth
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


@http_basic_auth
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


@http_basic_auth
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
            elif k == 'images' or k == 'categories':
                v = [v]
            setattr(product, k, v)

        convert_link(product)
        product.save()

        if product not in quiz.products:
            quiz.products.append(product)
            quiz.save()

        return HttpResponse(simplejson.dumps({'success': (product in quiz.products)}))


@http_basic_auth
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
# category_dict = {cat['cid']: cat['name'] for cat in db.categories.find({'$or':[{'level':1}, {'level':2}]})}
category_dict = {cat['name']: cat['cid'] for cat in db.categories.find()}

sub_cats = cats.values()
count = 0
cc = 0
for values in sub_cats:
    for value in values:
        if value not in category_dict:
            cc += 1
        count += 1
print count, cc

com_cats = {}
for k,vs in cats.iteritems():
    com_cats.setdefault(k, {})
    for v in vs:
        com_cats[k][v] = category_dict[v]


@http_basic_auth
def baokuan_by_category(request, cat_id):
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))

    url = u'{}/api/v1/cate/hotproducts_list/?cid={}&format=json&page={}&limit={}'.format( \
        settings.BAOKUAN_HOST, cat_id, page, limit)
    res = requests.get(url, auth=('favbuy', 'tempfavbuy'))
    json_data = res.json()
    if json_data is None:
        ret = {}
        ret['products'] = []
        ret['categories'] = com_cats
        return HttpResponse(simplejson.dumps())

    items = json_data.get('items', [])
    total = json_data.get('total', 0)

    ret = paginate(count=total, page=page, limit=limit)
    ret['products'] = items
    ret['categories'] = com_cats
    return HttpResponse(simplejson.dumps(ret))


@http_basic_auth
def categories(request):
    return HttpResponse(simplejson.dumps({'categories': com_cats}))


@http_basic_auth
def lotteriesHandle(request):
    lotteries = Lottery.objects().order_by('-period')
    return render(request, 'lotteries.html', {'lotteries': lotteries})

@http_basic_auth
def markHandle(request):
    if request.method == 'GET':
        paper_id = request.GET.get('paper_id')
        user_id = request.GET.get('user_id')
        user = User.objects(id=user_id).first()
        paper = Paper.objects(id=paper_id).first()
        mark = Mark.objects(user=user, paper=paper).first()
        return HttpResponse(simplejson.dumps({
                'id': str(mark.id),
                'rank': mark.rank,
                'score': mark.score,
                'bonus': mark.bonus,
                'is_get_bonus': mark.is_get_bonus,
                'phone': mark.phone
            }))

    elif request.method == 'POST':
        mark_id = request.POST.get('mark_id')
        mark = Mark.objects(id=mark_id).first()
        mark.is_get_bonus = 2
        mark.save()
        return HttpResponse(mark.is_get_bonus)

    elif request.method == 'DELETE':
        mark_id = request.GET.get('mark_id')
        mark = Mark.objects(id=mark_id).first()
        mark.is_get_bonus = 1
        mark.save()
        return HttpResponse(mark.is_get_bonus)


def paginate(count=0, page=1, limit=20, **kwargs):
    offset = (page - 1) * limit
    next_offset = offset + limit
    pages = [page]
    prev_page = page - 1
    next_page = page + 1
    prev_page_limit = kwargs.get('prev_page_limit', 2)
    next_page_limit = kwargs.get('next_page_limit', 2)
    total_page = (count / limit) + int(bool(count % limit))

    while prev_page and prev_page_limit:
        pages.append(prev_page)
        prev_page -= 1
        prev_page_limit -= 1

    while (next_page <= total_page) and next_page_limit:
        pages.append(next_page)
        next_page +=1
        next_page_limit -= 1

    pages.sort()
    paginator = {
        'total_page': total_page,
        'count': count,
        'limit': limit,
        'current': page,
        'pages': pages,
        'next_offset': min(next_offset, count),
        'has_previous': bool(offset > 0),
        'has_next': bool(next_offset < count),
    }
    return paginator