#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import sys
from apis.base.models import Lottery
from datetime import datetime, timedelta

def push_online(period=None):
    if period:
        today = datetime.strptime(period, '%Y-%m-%d')
    else:
        now = datetime.now()
        today = now.replace(hour=0,minute=0,second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    Lottery.objects(period__gte=yesterday, period__lt=today).update(set__is_online=True)
    print Lottery.objects(period__gte=yesterday, period__lt=today)


if __name__ == '__main__':
    import time, sys
    start_at = time.time()
    period = sys.argv[1] if len(sys.argv) > 1 else None
    push_online(period)
    print u'Totally cost: {} s'.format(time.time()-start_at)