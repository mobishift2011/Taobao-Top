from django.conf.urls import patterns, include, url
from django.conf import settings

urlpatterns = patterns('admins.admin',
    url(r'^(baokuan/)?$', 'dashboard'),
    url(r'^(baokuan/)?dashboard/$', 'dashboard'),
    url(r'^(baokuan/)?users/$', 'usersHandle'),
    url(r'^(baokuan/)?papers/$', 'papersHandle'),
    url(r'^(baokuan/)?quiz/(?P<quiz_id>\w+)/product/$', 'quizProdsHandle'),
    url(r'^(baokuan/)?quiz/(?P<quiz_id>\w+)/product/(?P<product_id>\w+)/$', 'quizProdHandle'),
    url(r'^(baokuan/)?paper/(?P<paper_id>\w+)/quiz/$', 'paperQuizesHandle'),
    url(r'^(baokuan/)?paper/(?P<paper_id>\w+)/quiz/(?P<quiz_id>\w+)/$', 'paperQuizHandle'),
    url(r'^(baokuan/)?paper/(?P<paper_id>\w+)/$', 'paperHandle'),
    url(r'^(baokuan/)?paper/$', 'paperCreateHandle'),
    url(r'^(baokuan/)?lotteries/$', 'lotteriesHandle'),
    url(r'^(baokuan/)?mark/$', 'markHandle'),
    url(r'^(baokuan/)?baokuan/category/(?P<cat_id>\w+)/$', 'baokuan_by_category'),
    url(r'^(baokuan/)?baokuan/category/$', 'categories'),
)