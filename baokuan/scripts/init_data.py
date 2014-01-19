#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from apis.base.models import *
from datetime import datetime, timedelta
import pymongo
import os

def task1():
    today = datetime.utcnow()
    ago = today - timedelta(days=3)
    papers = Paper.objects(period__gt=ago)

    paper_list = []
    quiz_list = []
    product_list = []

    for paper in papers:
        paper_list.append(paper)
        print paper

        for quiz in paper.quizes:
            quiz_list.append(quiz)
            print quiz

            for product in quiz.products:
                product_list.append(product)
                print product


    for paper in Paper.objects():
        if paper not in paper_list:
            print paper
            paper.delete()


    for quiz in Quiz.objects():
        if quiz not in quiz_list:
            print quiz
            quiz.delete()

    for product in Product.objects():
        if product not in product_list:
            print product
            product.delete()

def task2():
    from django.conf import settings


    client = pymongo.MongoClient(host='luckytao.tk')
    db = client['baokuan']
    print db

    local_client = pymongo.MongoClient(host='localhost')
    local_db = local_client['baokuan_test']
    print local_db

    for paper in local_db.paper.find():
        print paper
        db.paper.save(paper)

    for quiz in local_db.quiz.find():
        print quiz
        db.quiz.save(quiz)

    for product in local_db.product.find():
        print product
        db.product.save(product)

    # for cate in db.cate.find():
    #     local_db.categories.save(cate)

if __name__ == '__main__':
    task2()