#!/bin/bash

dt=$(date +"%H:%M %p")
msg="Hi,+this+is+a+direct+message+by+$dt.+Please+reply+with+the+time+you+received+it,+then+the+time+you+sent+your+response,+eg+4:03pm+4:15pm"
# Airtel users
curl "http://107.170.157.165:13013/cgi-bin/sendsms?user=$AIRTEL_KANNEL_USER&pass=$AIRTEL_KANNEL_PASS&to=2348122356701&text=$msg"
curl "http://107.170.157.165:13013/cgi-bin/sendsms?user=$AIRTEL_KANNEL_USER&pass=$AIRTEL_KANNEL_PASS&to=2347010915898&text=$msg"

# Mtn users
curl "http://107.170.157.165:13013/cgi-bin/sendsms?user=$MTN_KANNEL_USER&pass=$MTN_KANNEL_PASS&to=2348147536458&text=$msg"

# Etisalat users
curl "http://107.170.157.165:13013/cgi-bin/sendsms?user=$ETISALAT_KANNEL_USER&pass=$ETISALAT_KANNEL_PASS&to=2348183273915&text=$msg"
curl "http://107.170.157.165:13013/cgi-bin/sendsms?user=$ETISALAT_KANNEL_USER&pass=$ETISALAT_KANNEL_PASS&to=2348171284124&text=$msg"
