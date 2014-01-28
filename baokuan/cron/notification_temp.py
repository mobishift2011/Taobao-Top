#!/usr/bin/env python
# -*- coding: utf-8 -*-
from apis.base.models import Mark, Lottery, User
from apis.notification.models import Notification
from datetime import datetime, timedelta
import traceback

message = u'亲爱的淘友们，幸运淘团队的大大们回家过节啦！1月29日-2月7日期间将暂停发放奖金，期间获奖者将在我们恢复正常工作后统一发放，延迟发奖我们深感抱歉，幸运淘祝您新春快乐，马上有福！'

def notify_temp(period=None):
    if period:
        today = datetime.strptime(period, '%Y-%m-%d')
    else:
        now = datetime.now()
        today = now.replace(hour=0,minute=0,second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    lotteries = Lottery.objects(period__gte=yesterday, period__lt=today)

    lottery = lotteries.first()
    if not lottery:
        return

    for user in lottery.users:
        notifications = Notification.objects(user=user)
        for notification in notifications:
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
    notify_temp(period)
    print u'Totally cost: {} s'.format(time.time()-start_at)