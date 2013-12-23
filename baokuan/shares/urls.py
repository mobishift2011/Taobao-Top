from django.conf.urls import patterns, include, url

urlpatterns = patterns('shares.views',
    url(r'^product/(?P<product_id>\w+)/$', 'productHandle'),
)