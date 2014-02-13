#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from settings import SECRET_KEY, EMAIL_HOST_USER, APP_NAME, AUTHENTICATION_BACKENDS, SUB_DOMAIN, DEBUG, HOST
from models import *
from apis.notification.models import Notification
from validations import *
from authentications import UserAuthentication

from django.conf.urls import url
from django.contrib.auth import authenticate, login, logout
from django.core import signing
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives
from django.template import loader, Context
from django.shortcuts import redirect, render

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

    def dehydrate(self, bundle):
        for k in bundle.data:
            if k == 'phone' and bundle.data[k] is None:
                bundle.data[k] = ''
        return bundle

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

    def validate_password(self, password=''):
        return (len(password)>=6 and len(password)<=20)

    def bind(self, request, **kwargs):
        self.method_check(request, allowed=('post',))
        u = request.user
        if not u.is_authenticated():
            return self.create_response(request, {'error_message': 'no login user to bind'}, response_class=HttpUnauthorized)

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        aid = data.get('aid')
        platform = data.get('platform')
        screen_name = data.get('screen_name')
        token = data.get('token')
        bind_type = data.get('bind_type')
        validation_error = {}

        for var in ['aid', 'platform', 'screen_name', 'bind_type']:
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

        if bind_type == 'add':
            if account in u.accounts:
                return self.create_response(request, {'error_code':1, 'error_message': 'already binding'})
            u.accounts.append(account)
            u.save()

        elif bind_type == 'delete':
            if account not in u.accounts:
                return self.create_response(request, {'error_code': 2, 'error_message': 'already unbinding'})
            if not u.email and len(u.accounts) == 1:
                return self.create_response(request, {'error_code': 3, 'error_message': 'open login user can not unbind the account'})
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
            Notification.objects(user = request.user).delete()
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
        validation_error = {}

        for var in ['password', 'device_id', 'device_platform', 'email', 'screen_name']:
            if not locals().get(var):
                validation_error[var] = u'the post param is required'
                continue

        if validation_error:
            return self.create_response(request, validation_error, HttpBadRequest)

        user = User.objects(Q(username=username)|Q(device=device)|Q(email=email)|Q(screen_name=screen_name)).first()
        if user:
            if user.username == username:
                return self.create_response(request, {'error_code': 1, 'error_message': 'user exists'})
            if user.email == email:
                return self.create_response(request, {'error_code': 2, 'error_message': 'email exists'})
            if user.device == device:
                return self.create_response(request, {'error_code': 3, 'error_message': u'device has been registered {}'.format(device)})
            if user.screen_name == screen_name:
                return self.create_response(request, {'error_code': 4, 'error_message': 'screen_name exists'})

        if not self.validate_password(password):
            return self.create_response(request, {'error_code': 5, 'error_message': 'password invalid'})

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
            return self.create_response(request, {'error_code': 6, 'error_message': 'email format not correct'})

        user = authenticate(username=username, password=password)
        login(request, user)
        return self.create_response(request, self.to_json(user))

    def change_password(self, request, **kwargs):
        self.method_check(request, allowed=('post',))
        user_id = kwargs.get('user_id')
        if not request.user.is_authenticated() or request.user.id != user_id:
            return self.create_response(request, {'error_code': 1, 'error_message': 'user error'}, HttpUnauthorized)

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
        if not self.validate_password(new_password):
            return self.create_response(request, \
                {'error_code': 3, 'error_message': 'new password invalid, should be 6-20 digits'}, HttpBadRequest)

        u = User.objects(id=user_id).first()
        user = authenticate(username=u.username, password=old_password)
        if not user or not user.is_authenticated:
            return self.create_response(request, {'error_code': 1, 'error_message': 'old password error'})

        u.set_password(new_password)
        u.save()
        return self.create_response(request, {'success': True})

    def forget_password(self, request, **kwargs):
        try:
            self.method_check(request, allowed=('post',))
            data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
            user = User.objects(email=data.get('email')).first()
            if user is None:
                return self.create_response(request, {'error_message': 'email error'}, HttpBadRequest)
            
            token = signing.dumps(user.id, key=SECRET_KEY)
            PwdRstToken.objects(user=user).update_one(
                set__token = token,
                set__generated_at = datetime.utcnow(),
                set__expires = 10,
                set__validated = False,
                upsert = True
            )

            if DEBUG:
                link = reverse('api_reset_password', kwargs={'resource_name': self._meta.resource_name, 'api_name': 'v1', 'user_id': user.id})
            else:
                link = u'http://{}/{}/api/v1/user/{}/rstpwd/'.format(HOST, APP_NAME, user.id)
            url = u'{}?token={}&format=json'.format(request.build_absolute_uri(link), token)
            c = Context({'user': user,  'APP_NAME': APP_NAME, 'url': url})
            html_content = loader.get_template('fgtpwd.html').render(c)
            email = EmailMultiAlternatives(u'验证登录邮箱【{}安全中心 】'.format(APP_NAME), '', EMAIL_HOST_USER, [user.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            return self.create_response(request, {'success': True})
        except:
            traceback.print_exc()
            raise

    def reset_password(self, request, **kwargs):
        user_id = kwargs.get('user_id')
        token = request.GET.get('token')
        user = User.objects.get(id=user_id)
        prt = PwdRstToken.objects(user=user, token=token).order_by('-generated_at').first()

        if request.method == 'GET':
            if prt is None:
                return HttpResponse(u'此链接不存在，用户不合法')
            elif (prt.generated_at + timedelta(minutes=prt.expires)) < datetime.utcnow():
                return HttpResponse(u'链接已过期')

            return render(request, 'rstpwd.html', {
                'username': user.username,
                'user_id': user.id,
                'token': token,
            })

        elif request.method == 'POST':
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            invalid_message = ''

            if prt is None or \
                (prt.generated_at + timedelta(minutes=prt.expires)) < datetime.utcnow():
                    invalid_message = u'此密码修改已经失效，请重新申请忘记密码'

            if prt.validated:
                invalid_message = u'已修改过密码'

            elif not password or not confirm_password:
                invalid_message = u'密码不得为空'

            elif password != confirm_password:
                invalid_message = u'新密码与确认密码不一致'

            elif not self.validate_password(password):
                invalid_message = u'密码应该在6-20 位'

            if invalid_message:
                return render(request, 'rstpwd.html', {
                    'invalid_message': invalid_message,
                    'username': user.username,
                    'user_id': user.id,
                    'token': token,
                })

            else:
                user.set_password(password)
                prt.validated = True
                user.save()
                prt.save()
                return HttpResponse('修改成功')


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
        queryset = Paper.objects(is_online=True)
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
        params = dict(request.GET.dict().items() + {'period__gte': today, 'period__lt': tomorrow}.items())
        return redirect(u'{}/api/v1/paper/?{}'.format(SUB_DOMAIN or '', urlencode(params)))

    def yesterday(self, request, **kwargs):
        today = datetime.utcnow().replace(hour=0,minute=0,second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        params = dict(request.GET.dict().items() + {'period__gte': yesterday, 'period__lt': today}.items())
        return redirect(u'{}/api/v1/paper/history/?{}'.format(SUB_DOMAIN or '', urlencode(params)))

    def history(self, request, **kwargs):
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        param_dict = request.GET.dict()
        params = dict(param_dict.items() + {'period__lt': today}.items()) \
            if 'period__lt' not in param_dict else param_dict
        params = param_dict
        papers_url = u'http://{}/api/v1/paper/?{}'.format(request.META['HTTP_HOST'], urlencode(params))
        earliest_paper = Paper.objects().order_by('period').first()
        earliest = earliest_paper.period if earliest_paper else None

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

                if 'answers' in data:
                    del data['answers']

            res['meta']['earliest'] = earliest
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

                if 'answers' in data:
                    del data['answers']

            res['meta']['earliest'] = earliest
            return self.create_response(request, res)


class MarkResource(BaseResource):
    user = fields.ReferenceField(to='apis.base.resources.UserResource', 
                                            attribute='user', full=True, null=True)
    paper = fields.ReferenceField(to='apis.base.resources.PaperResource', 
                                            attribute='paper', full=True, null=True)

    class Meta:
        queryset = Mark.objects(is_online=True)
        allowed_methods = ('get', 'post')
        authentication = UserAuthentication()
        authorization = Authorization()
        excludes = ('resource_uri',)
        filtering = {'user': ALL, 'period': ALL}
        ordering = ('created_at', 'period')

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/submit%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('submit'), name="api_submit"),
            url(r"^(?P<resource_name>%s)/latest%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('latest'), name="api_latest"),
            url(r"^(?P<resource_name>%s)/(?P<mark_id>\w+)/apply%s$" % (self._meta.resource_name, trailing_slash()), \
                self.wrap_view('apply'), name="api_apply")
        ]

    def dehydrate(self, bundle):
        paper = bundle.obj.paper
        paper_id = paper.id
        deadline = paper.deadline
        rank = bundle.obj.rank
        bundle.data['paper'] = paper_id
        bundle.data['deadline'] = deadline
        bundle.data['total_marks'] = Mark.objects(paper=paper).count()
        return bundle

    def apply(self, request, **kwargs):
        self.method_check(request, allowed=('post',))
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        phone = data.get('phone')
        user = request.user
        validation_error = {}
        mark_id = kwargs.get('mark_id')
        mark = Mark.objects(id=mark_id).first()

        if mark is None:
            return self.create_response(request, {'error_message': 'error mark id'}, HttpNotFound)

        if not user.is_authenticated() or user != mark.user:
            return self.create_response(request, {'error_message': 'error user'}, HttpUnauthorized)

        for var in ['phone']:
            if not locals().get(var):
                validation_error[var] = u'the post param is required'
                continue

        if validation_error:
            return self.create_response(request, validation_error, HttpBadRequest)

        mark.phone = phone
        mark.is_get_bonus = 1
        mark.save()
        return self.create_response(request, {'success': True})

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

        if Mark.objects(user=user, paper=paper).first():
            return self.create_response(request, \
                {'error_code': 4, 'error_message': u'user {} already answered {}'.format(user_id, paper_id)})

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

        today = datetime.utcnow().replace(hour=0,minute=0,second=0, microsecond=0)
        mark = Mark.objects(user=user, is_online=True).order_by('-period').first()

        if mark:
            res['rank'] = mark.rank
            res['score'] = mark.score
            res['bonus'] = mark.bonus
            res['period'] = mark.period
            res['is_get_bonus'] = mark.is_get_bonus
            res['total_marks'] = Mark.objects(period=mark.period).count()

        return self.create_response(request, res)


class LotteryResource(BaseResource):
    users = fields.ReferencedListField(of='apis.base.resources.UserResource', 
                                            attribute='users', full=True, null=True)
    paper = fields.ReferenceField(to='apis.base.resources.PaperResource',
                                            attribute='paper', full=True, null=True)

    class Meta:
        queryset = Lottery.objects(is_online=True)
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
        params = dict(request.GET.dict().items() + {'period__gte': yesterday, 'period__lt': today}.items())
        return redirect(u'{}/api/v1/lottery/?{}'.format(SUB_DOMAIN or '', urlencode(params)))


class FavoriteCategoryResource(BaseResource):
    user = fields.ReferenceField(to='apis.base.resources.UserResource', 
                                            attribute='user', full=False, null=True)

    class Meta:
        queryset = FavoriteCategory.objects()
        allowed_methods = ('get', 'post')
        detail_allowed_methods = ('get',)
        authentication = UserAuthentication()
        excludes = ('resource_uri',)
        filtering = {'user': ALL}

    def post_list(self, request, **kwargs):
        user = request.user
        content_type = request.META.get('CONTENT_TYPE', 'application/json')
        data = self.deserialize(request, request.body, format=content_type)
        categories = data.get('categories', None)
        success = False

        if categories or categories == []:
            FavoriteCategory.objects(user=user).update_one(set__categories=categories, upsert=True)
            success = True

        return self.create_response(request, {'success': success})


class ShareResource(BaseResource):
    user = fields.ReferenceField(to='apis.base.resources.UserResource', 
                                            attribute='user', full=False, null=True)
    product = fields.ReferenceField(to='apis.base.resources.ProductResource', 
                                            attribute='product', full=False, null=True)
    class Meta:
        queryset = Share.objects()
        allowed_methods = ('post',)
        # authentication = UserAuthentication()
        excludes = ('resource_uri',)
        filtering = {'user': ALL, 'product': ALL}

    def post_list(self, request, **kwargs):
        # if not request.user.is_authenticated():
        #     return self.create_response(request, {}, HttpUnauthorized)

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        product_id = data.get('product_id')
        num = data.get('num', 0)

        if not product_id:
            return self.create_response(request, {'product_id': 'post param is required'}, HttpBadRequest)

        product = Product.objects(id=product_id).first()
        if not product:
            return self.create_response(request, {'product_id': 'post param is not correct'}, HttpBadRequest)

        # Share.objects.get_or_create(user=request.user, product=product)
        # shared_count = Share.objects(product=product).count()
        # product.shared = shared_count
        shared_count = product.shared + num
        Product.objects(id=product_id).update_one(set__shared=shared_count)
        
        return self.create_response(request, {'shared': shared_count})