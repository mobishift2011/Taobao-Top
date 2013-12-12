#!/user/bin/env python
# -*- encoding: utf-8
from celery.schedules import crontab
from datetime import timedelta

CELERY_TIMEZONE = 'US/Eastern'
CELERY_IMPORTS = ("tasks",)
BROKER_TRANSPORT = "redis"
BROKER_URL = 'redis://127.0.0.1:6379/2'
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/1"
CELERY_REDIS_BACKEND_SETTINGS = {
    'host':'127.0.0.1',
    'port':6379,
}

# CELERYBEAT_SCHEDULE = {
#     # timedelta
#     "update_scores": {
#         "task": "tasks.update_scores",
#         "schedule":timedelta(days=1),
#     },

#     # crontab
#     "notification": {
#         "task": "tasks.notification",
#         "schedule":crontab(minute='1',hour='8'),
#         'args':(),
#     },
# }

