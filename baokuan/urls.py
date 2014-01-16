from django.conf.urls import patterns, include, url

urlpatterns = patterns('baokuan',
    url(r'^api/', include('apis.urls')),
    url(r'^admin/', include('admins.urls')),
    url(r'^share/', include('shares.urls'))
)
