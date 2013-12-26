#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from apis.base.models import Mark, Lottery
from apis.notification.models import Notification

if __name__ == '__main__':
    device_token = '820451e8 bfd934ea 8b8896f7 c92122a4 6315a662 0cf54edb df86224f 468037c1'
    device_token = device_token.replace(' ', '')
    notification = Notification(device_token=device_token)
    notification.ios_notify(alert='allen asked to test', sound=1, sandbox=False)