from celery import shared_task
from cron.score_rank import score_and_rank as sar
from cron.paper_online import push_online
from cron.lottery_online import push_online as lottery_push_online
from cron.notification import notify
import time, sys

@shared_task
def score_and_rank(period=None):
    start_at = time.time()
    sar(period)

@shared_task
def paper_online(period=None):
    start_at = time.time()
    push_online(period)

@shared_task
def lottery_online(period=None):
    start_at = time.time()
    lottery_push_online(period)

@shared_task
def notification(period=None):
    start_at = time.time()
    notify(period)