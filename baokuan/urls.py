from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^(baokuan/)?api/', include('apis.urls')),
    url(r'^(baokuan/)?admin/', include('admins.urls')),
    url(r'^(baokaun/)?share/', include('shares.urls'))
)
