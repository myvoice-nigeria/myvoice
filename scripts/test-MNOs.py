#!/usr/bin/env python

import urllib2
import urllib
import datetime
import pytz

test_phones = [
    ('MTN', '2348142235832'),
    ('Etisalat', '2348183273915'),
    ('Glo', '2348117159357'),
    ('Airtel', '2347010915898'),
]

wat = pytz.timezone('Africa/Lagos')
for via_operator, _ in test_phones:
    for phone_operator, phone in test_phones:
        now = datetime.datetime.now(wat).strftime('%H:%M:%S on %d/%m/%Y')
        params = {
            'username': 'rapidsms',
            'password': '',  # XXX add password here
            'to': phone,
            'from': '55999',
            'smsc': 'starfish-%s' % via_operator.lower(),
            'text': 'Test message to %s via %s. Sent at %s' % (phone_operator, via_operator, now),
        }
        data = urllib.urlencode(params)
        url = 'https://myvoice-testing.caktusgroup.com/sendsms?%s' % data
        print 'Loading %s' % url
        try:
            result = urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            result = e
        print 'Status code and result for %s via %s: %s' % (phone_operator, via_operator, result.getcode())
        print result.read()
        print ''
