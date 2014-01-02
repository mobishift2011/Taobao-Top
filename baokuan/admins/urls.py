from django.conf.urls import patterns, include, url
from django.conf import settings

urlpatterns = patterns('admins.admin',
    url(r'^$', 'dashboard'),
    url(r'^dashboard/$', 'dashboard'),
    url(r'^users/$', 'usersHandle'),
    url(r'^papers/$', 'papersHandle'),
    url(r'^quiz/(?P<quiz_id>\w+)/product/$', 'quizProdsHandle'),
    url(r'^quiz/(?P<quiz_id>\w+)/product/(?P<product_id>\w+)/$', 'quizProdHandle'),
    url(r'^paper/(?P<paper_id>\w+)/quiz/$', 'paperQuizesHandle'),
    url(r'^paper/(?P<paper_id>\w+)/quiz/(?P<quiz_id>\w+)/$', 'paperQuizHandle'),
    url(r'^paper/(?P<paper_id>\w+)/$', 'paperHandle'),
    url(r'^paper/$', 'paperCreateHandle'),
    url(r'^lotteries/$', 'lotteriesHandle'),
    url(r'^mark/$', 'markHandle'),
    url(r'^baokuan/category/(?P<cat_id>\w+)/$', 'baokuan_by_category'),
    url(r'^baokuan/category/$', 'categories'),
)