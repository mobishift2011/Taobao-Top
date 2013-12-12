from django.conf.urls import patterns, include, url

urlpatterns = patterns('admins.admin',
    url(r'^$', 'test'),
    url(r'^test/$', 'test')
)
