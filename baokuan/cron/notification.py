#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from apis.base.models import Mark, Lottery
from apis.notification.models import Notification
from datetime import datetime, timedelta
import traceback

def main():
    today = datetime.utcnow().replace(hour=0,minute=0,second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    lotteries = Lottery.objects(period__gte=yesterday, period__lt=today)

    for lottery in lotteries:
        print u'Lottery: {}'.format(lottery.period)
        print 'user count: ', len(lottery.users)

        for notification in Notification.objects(user__in=lottery.users):
            if notification.is_on:
                mark = Mark.objects(user=notification.user, paper=lottery.paper).first()
                if not mark:
                    continue

                message = u'您在幸运猜爆款第{}期中的总分为{}分，\n \
                排名第{}名，可获得话费{}元。赶紧去看看吧~'.format(
                    mark.period.date(), mark.score, mark.rank, mark.bonus)

                print mark.user, message

                try:
                    getattr(notification, '{}_notify'.format(notification.platform))(alert=message, sound=1)
                except:
                    traceback.print_exc()


if __name__ == '__main__':
    main()