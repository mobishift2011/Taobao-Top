#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from settings import SECRET_KEY, EMAIL_HOST_USER, APP_NAME, AUTHENTICATION_BACKENDS
from models import *
from validations import *
from authentications import UserAuthentication

from django.conf.urls import url
from django.contrib.auth import authenticate, login, logout
from django.core import signing
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives
from django.template import loader, Context
from django.shortcuts import redirect

from mongoengine import Q
from tastypie_mongoengine import resources, fields
from tastypie.authorization import Authorization
from tastypie.constants import ALL
from tastypie.http import *
from tastypie.utils import dict_strip_unicode_keys, trailing_slash

from datetime import datetime, timedelta
from urllib import urlencode

import requests
import traceback

class BaseResource(resources.MongoEngineResource):
    pass


class AccountResource(BaseResource):
    class Meta:
        queryset = Account.objects()
        allowed_methods = ()


class UserResource(BaseResource):
    accounts = fields.ReferencedListField(of='apis.base.resources.AccountResource', 
                                            attribute='accounts', full=True, null=True)
    class Meta:
        queryset = User.objects()
        allowed_methods = ('get',)
        detail_allowed_methods = ('get', 'post')
        authentication = UserAuthentication()
        authorization = Authorization()
        always_return_data = True
        fields = ['id', 'username', 'email', 'screen_name', 'phone', 'device', 'accounts', 'is_active', 'last_login', 'date_joined']
        ordering = ('username', 'last_login', 'date_joined')

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/login%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('login'), name="api_login"),
            url(r"^(?P<resource_name>%s)/open_login%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('open_login'), name="api_open_login"),
            url(r"^(?P<resource_name>%s)/bind%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('bind'), name="api_bind"),
            url(r"^(?P<resource_name>%s)/logout%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('logout'), name="api_logout"),
            url(r"^(?P<resource_name>%s)/register%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('register'), name="api_register"),
            url(r"^(?P<resource_name>%s)/(?P<user_id>\w+)/chgpwd%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('change_password'), name="api_change_password"),
            url(r"^(?P<resource_name>%s)/fgtpwd%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('forget_password'), name="api_forget_password"),
            url(r"^(?P<resource_name>%s)/(?P<user_id>\w+)/rstpwd%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('reset_password'), name="api_reset_password"),
            url(r"^(?P<resource_name>%s)/auth%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('auth'), name="api_auth"),
        ]

    def post_detail(self, request, **kwargs):
        return self.patch_detail(request, **kwargs)

    def to_json(self, object_user):
        data = {field: getattr(object_user, field) for field in self._meta.fields if getattr(object_user, field)}
        if 'accounts' in data and len(data['accounts']):
            data['accounts'] = [{field: getattr(acc, field) for field in acc._fields} for acc in data['accounts']]
        return data

    def auth(self, request, **kwargs):
        """
        Just help check if the request is authenticated.
        """
        return self.create_response(request, {'response': request.user})

    def bind(self, request, **kwargs):
        self.method_check(request, allowed=('post', 'delete'))
        u = request.user
        if not u.is_authenticated():
            return self.create_response(request, {'error_message': 'no login user to bind'}, response_class=HttpUnauthorized)

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        aid = data.get('aid')
        platform = data.get('platform')
        screen_name = data.get('screen_name')
        token = data.get('token')
        validation_error = {}

        for var in ['aid', 'platform', 'screen_name']:
            if not locals().get(var):
                validation_error[var] = 'the param is required.'
                continue

        if validation_error:
            return self.create_response(request, validation_error, HttpBadRequest)

        Account.objects(aid=aid, platform=platform).update_one( \
            set__screen_name=screen_name, set__token=token, upsert=True)
        account = Account.objects(aid=aid, platform=platform).first()
        users = User.objects(accounts=account)

        for user in users:
            if user.id != u.id:
                user.accounts.remove(account)
                user.save()

        if request.method == 'POST':
            if account in u.accounts:
                return self.create_response(request, {'error_code':1, 'error_message': 'already binding'})
            u.accounts.append(account)
            u.save()

        elif request.method == 'DELETE':
            if account not in u.accounts:
                return self.create_response(request, {'error_code':2, 'error_message': 'already unbinding'})
            u.accounts.remove(account)
            u.save()
            account.delete()

        return self.create_response(request, self.to_json(u))

    def open_login(self, request, **kwargs):
        try:
            self.method_check(request, allowed=('post',))
            data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
            aid = str(data.get('aid'))
            platform = data.get('platform')
            screen_name = data.get('screen_name')
            token = data.get('token')
            device_platform = data.get('device_platform')
            device_id = data.get('device_id')
            device = u'{}_{}'.format(device_platform, device_id)

            if not aid or not platform or not screen_name:
                return self.create_response(request, \
                    {'error_code': 1, 'error_message': 'aid, platform, screen_name is not correct'}, HttpBadRequest)

            # old user
            account = Account.objects(aid=aid, platform=platform).first()
            if account:
                user = User.objects(accounts=account).first()
                if not user:
                    account.delete()
                    return self.create_response(request, \
                        {'error_code': 2, 'error_message': 'error existing account with no user binded, please retry'}, HttpBadRequest)

                account.screen_name = screen_name
                account.token = token
                account.save()
                user.backend = AUTHENTICATION_BACKENDS[0]
                login(request, user)
                return self.create_response(request, self.to_json(user))

            # new user
            if User.objects(device=device):
                return self.create_response(request, {'error_message': 'device has been registered'}, HttpForbidden)

            account = Account(
                aid=aid, 
                platform=platform,
                screen_name = screen_name,
                token = token,
            )
            account.save()
            new_user = User().create_user(
                #TODO change username generate as mongo id.
                username = str(ObjectId()), 
                password = SECRET_KEY,
                screen_name = screen_name,
                device = device,
                accounts = [account],
            )

            user = authenticate(username=new_user.username, password=SECRET_KEY)
            login(request, user)
            return self.create_response(request, self.to_json(user))
        except:
            traceback.print_exc()

    def login(self, request, **kwargs):
        self.method_check(request, allowed=('post',))
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        username = data.get('username')
        password = data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return self.create_response(request, self.to_json(user))
        else:
            return self.create_response(request, {'error_message': 'incorrect username or password'}, HttpUnauthorized)

    def logout(self, request, **kwargs):
        if request.user and request.user.is_authenticated():
            logout(request)
            return self.create_response(request, {'success': True})
        else:
            return self.create_response(request, {'error_message': 'no user to logout'}, HttpUnauthorized)

    def register(self, request, **kwargs):
        self.method_check(request, allowed=('post',))
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        password = data.get('password')
        screen_name = data.get('screen_name')
        email = data.get('email')
        username = email
        phone = data.get('phone')
        device_platform = data.get('device_platform')
        device_id = data.get('device_id')
        device = u'{}_{}'.format(device_platform, device_id)

        user = User.objects(Q(username=username)|Q(device=device)|Q(email=email)|Q(screen_name=screen_name)).first()
        if user:
            if user.username == username:
                return self.create_response(request, {'error_code': 1, 'error_message': 'user exists'})
            if user.email == email:
                return self.create_response(request, {'error_code': 2, 'error_message': 'email exists'})
            if user.device == device:
                return self.create_response(request, {'error_code': 3, 'error_message': 'device has been registered'})
            if user.screen_name == screen_name:
                return self.create_response(request, {'error_code': 4, 'error_message': 'screen_name exists'})

        try:
            new_user = User().create_user(
                username=username, 
                password=password,
                email=email,
                screen_name = screen_name,
                phone = phone,
                device = device,
            )
        except ValidationError:
            return self.create_response(request, {'error_message': 'email format not correct'}, HttpBadRequest)

        user = authenticate(username=username, password=password)
        login(request, user)
        return self.create_response(request, self.to_json(user))

    def change_password(self, request, **kwargs):
        self.method_check(request, allowed=('post',))
        user_id = kwargs.get('user_id')
        if not request.user.is_authenticated() or request.user.id != user_id:
            return self.create_response(request, {'error_code': 1, 'error_message': 'user errror'}, HttpUnauthorized)

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if old_password == new_password:
            return self.create_response(request, \
                {'error_code': 1, 'error_message': 'old password must be different from new password'}, HttpBadRequest)
        if new_password != confirm_password:
            return self.create_response(request, \
                {'error_code': 2, 'error_message': 'new password must be equal with confirm password'}, HttpBadRequest)

        u = User.objects(id=user_id).first()
        user = authenticate(username=u.username, password=old_password)
        if not user or not user.is_authenticated:
            return self.create_response(request, {'error_code': 2, 'error_message': 'old password error'}, HttpUnauthorized)

        u.set_password(new_password)
        u.save()
        return self.create_response(request, {'success': True})

    def forget_password(self, request, **kwargs):
        self.method_check(request, allowed=('post',))
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        user = User.objects(email=data.get('email')).first()
        if user is None:
            return self.create_response(request, {'error_message': 'email error'}, HttpBadRequest)
        
        token = signing.dumps(user.id, key=SECRET_KEY)
        # TODO put token in redis
        link = reverse('api_reset_password', kwargs={'resource_name': self._meta.resource_name, 'api_name': 'v1', 'user_id': user.id})
        url = u'{}?token={}'.format(request.build_absolute_uri(link), token)
        c = Context({'user': user,  'APP_NAME': APP_NAME, 'url': url})
        html_content = loader.get_template('fgtpwd.html').render(c)
        email = EmailMultiAlternatives(u'验证登录邮箱【{}安全中心 】'.format(APP_NAME), '', EMAIL_HOST_USER, [user.email])
        email.attach_alternative(html_content, "text/html")
        email.send()
        return self.create_response(request, {'success': True})

    def reset_password(self, request, **kwargs):
        #TODO
        return HttpResponse('ok')


class ProductResource(BaseResource):
    class Meta:
        queryset = Product.objects()
        allowed_methods = ('get',)
        authentication = UserAuthentication()
        authorization = Authorization()
        excludes = ('resource_uri',)


class QuizResource(BaseResource):
    products = fields.ReferencedListField(of='apis.base.resources.ProductResource', 
                                            attribute='products', full=True, null=True)
    class Meta:
        queryset = Quiz.objects()
        allowed_methods = ('get',)
        authentication = UserAuthentication()
        authorization = Authorization()
        excludes = ('resource_uri',)
        ordering = ('created_at',)


class PaperResource(BaseResource):
    quizes = fields.ReferencedListField(of='apis.base.resources.QuizResource', 
                                            attribute='quizes', full=True, null=True)
    class Meta:
        queryset = Paper.objects()
        allowed_methods = ('get',)
        authentication = UserAuthentication()
        authorization = Authorization()
        excludes = ('resource_uri',)
        filtering = {'period': ALL}
        ordering = ('period',)

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/current%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('current'), name="api_current"),
            url(r"^(?P<resource_name>%s)/history%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('history'), name="api_history"),
            url(r"^(?P<resource_name>%s)/yesterday%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('yesterday'), name="api_yesterday"),   
        ]

    def current(self, request, **kwargs):
        today = datetime.utcnow().replace(hour=0,minute=0,second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        params = dict(request.GET.dict().items() + {'period__gt': today, 'period__lt': tomorrow}.items())
        return redirect(u'/api/v1/paper/?{}'.format(urlencode(params)))

    def yesterday(self, request, **kwargs):
        today = datetime.utcnow().replace(hour=0,minute=0,second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        params = dict(request.GET.dict().items() + {'period__gt': yesterday, 'period__lt': today}.items())
        return redirect(u'/api/v1/paper/history/?{}'.format(urlencode(params)))

    def history(self, request, **kwargs):
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        param_dict = request.GET.dict()
        params = dict(param_dict.items() + {'period__lt': today}.items()) \
            if 'period__lt' not in param_dict else param_dict
        papers_url = u'http://{}/api/v1/paper/?{}'.format(request.META['HTTP_HOST'], urlencode(params))

        if not request.user.is_authenticated():
            res = requests.get(papers_url).json()
            for data in res['objects']:
                paper_id = data['id']
                paper_answers = data.get('answers', {})
                paper = Paper.objects(id=paper_id).first()
                if not paper:
                    continue

                for quiz in data.get('quizes', []):
                    for prod in quiz.get('products', []):
                        if quiz['id'] in paper_answers \
                            and prod['id'] in paper_answers[quiz['id']]:
                                prod['score'] = paper_answers[quiz['id']][prod['id']]

            return self.create_response(request, res)

        else:
            res = requests.get(papers_url).json()
            for data in res['objects']:
                paper_id = data['id']
                paper = Paper.objects(id=paper_id).first()
                if not paper:
                    continue

                mark = Mark.objects(paper=paper, user=request.user).first()
                paper_answers = data.get('answers', {})

                if mark:
                    mark_answers = mark.answers
                    data['mark'] = {}
                    data['mark']['score'] = mark.score
                    data['mark']['rank'] = mark.rank
                    data['mark']['answers'] = mark_answers
                    data['mark']['bonus'] = mark.bonus

                for quiz in data.get('quizes', []):
                    for prod in quiz.get('products', []):
                        if quiz['id'] in paper_answers \
                            and prod['id'] in paper_answers[quiz['id']]:
                                prod['score'] = paper_answers[quiz['id']][prod['id']]

                        if mark:
                            prod['is_mark'] = (quiz['id'] in mark_answers) \
                                and (prod['id'] == mark_answers[quiz['id']])

            return self.create_response(request, res)


class MarkResource(BaseResource):
    user = fields.ReferenceField(to='apis.base.resources.UserResource', 
                                            attribute='user', full=True, null=True)

    class Meta:
        queryset = Mark.objects()
        allowed_methods = ('get',)
        authentication = UserAuthentication()
        authorization = Authorization()
        excludes = ('resource_uri',)
        filtering = {'user': ALL}
        ordering = ('created_at', 'period')

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/submit%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('submit'), name="api_submit"),
            url(r"^(?P<resource_name>%s)/latest%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('latest'), name="api_latest")
        ]

    def submit(self, request, **kwargs):
        self.method_check(request, allowed=('post',))
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        validation_error = {}

        # Something about validations and authentications.
        for f in ['user_id', 'paper_id', 'answers']:
            if not data.get(f):
                validation_error[f] = u'the post param is required'
                continue

        if validation_error:
            return self.create_response(request, validation_error, HttpBadRequest)

        user_id = data['user_id']
        paper_id = data['paper_id']
        answers = data['answers']

        if not request.user.is_authenticated() or request.user.id != user_id:
            return self.create_response(request, \
                {'error_message': 'session user and submit user inconform'}, response_class=HttpUnauthorized)

        user = User.objects(id=user_id).first()
        paper = Paper.objects(id=paper_id).first()

        for error_var in ['user', 'paper']:
            if not locals().get(error_var):
                return self.create_response(request, \
                    {'error_code': 1, 'error_message': u'{} not exists'.format(error_var)})

        # Something about data validations posted.
        quizes = {str(q.id): q for q in paper.quizes}

        for quiz_id in answers.keys():
            if quiz_id not in quizes:
                return self.create_response(request, \
                    {'error_code': 2, 'error_message': u'quiz {} not exists for the paper'.format(quiz_id)})

            quiz_answers = [str(prod.id) for prod in quizes[quiz_id].products]
            product_id = answers[quiz_id]

            if product_id not in quiz_answers:
                return self.create_response(request, \
                    {'error_code': 3, 'error_message': u'product {} not exists for quiz {}'.format(product_id, quiz_id)})

        try:
            Mark(user=user, paper=paper, answers=answers, period=paper.period).save()
        except NotUniqueError:
            return self.create_response(request, \
                {'error_code': 4, 'error_message': u'user {} already answered {}'.format(user_id, paper_id)})

        return self.create_response(request, True)

    def latest(self, request, **kwargs):
        res = {}
        user = request.user

        if not user.is_authenticated():
            return self.create_response(request, {'error_message': 'not login'}, response_class=HttpUnauthorized)

        mark = Mark.objects(user=user).order_by('-period').first()

        if mark:
            res['rank'] = mark.rank
            res['score'] = mark.score
            res['bonus'] = mark.bonus
            res['period'] = mark.period

        return self.create_response(request, res)


class LotteryResource(BaseResource):
    users = fields.ReferencedListField(of='apis.base.resources.UserResource', 
                                            attribute='users', full=True, null=True)
    paper = fields.ReferenceField(to='apis.base.resources.PaperResource',
                                            attribute='paper', full=True, null=True)

    class Meta:
        queryset = Lottery.objects()
        allowed_methods = ('get',)
        authentication = UserAuthentication()
        authorization = Authorization()
        filtering = {'period': ALL}

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/yesterday%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('yesterday'), name="api_yesterday"),
        ]

    def yesterday(self, request, **kwargs):
        today = datetime.utcnow().replace(hour=0,minute=0,second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        params = dict(request.GET.dict().items() + {'period__gt': yesterday, 'period__lt': today}.items())
        return redirect(u'/api/v1/lottery/?{}'.format(urlencode(params)))