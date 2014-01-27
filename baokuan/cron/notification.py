#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from apis.base.models import Mark, Lottery
from apis.notification.models import Notification
from datetime import datetime, timedelta
import traceback

def notify(period=None):
    if period:
        today = datetime.strptime(period, '%Y-%m-%d')
    else:
        now = datetime.now()
        today = now.replace(hour=0,minute=0,second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    lotteries = Lottery.objects(period__gte=yesterday, period__lt=today)

    lottery = lotteries.first()
    if not lottery:
        print u'no lottery for {}'.format(yesterday)
        return
    
    for mark in Mark.objects(paper=lottery.paper):
        notifications = Notification.objects(user=mark.user)
        for notification in notifications:
            print mark.user, notification.platform, notification.is_on
            if not notification.is_on:
                continue

            message = '您在幸运猜爆款第{}期中的总分为{}分，排名第{}名，可获得话费{}元。赶紧去看看吧~'.format( \
                mark.period.date(), mark.score, mark.rank, mark.bonus) if mark.user in lottery.users else \
                    '您在幸运猜爆款第{}期中的总分为{}分，排名第{}名。赶紧去看看吧~'.format( \
                        mark.period.date(), mark.score, mark.rank)

            print message
            try:
                getattr(notification, '{}_notify'.format(notification.platform))(alert=message, sound=1)
            except:
                traceback.print_exc()
                print notification.device_token


if __name__ == '__main__':
    import time, sys
    start_at = time.time()
    period = sys.argv[1] if len(sys.argv) > 1 else None
    notify(period)
    print u'Totally cost: {} s'.format(time.time()-start_at)