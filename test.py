#!/usr/bin/env python

from twilio.rest import TwilioRestClient
import time
from datetime import datetime, date
import urllib
import urllib2

def place_call(number, notification):
    account = "1234"
    token = "1234"
    _url = "http://www.williamslabs.com/alert/answer.py?text=%s" % \
	    (urllib.quote(notification))

    client = TwilioRestClient(account, token)

    call = client.calls.create(to=number,
			       from_="+14155992671",
			       url=_url,
			       method="GET",
			       if_machine="Hangup")
    sid = call.sid

    while True:
	call = client.calls.get(sid)
	print call.status
	print call.answered_by
	print call.caller_name
	print call.direction
	print call.duration
	print call.start_time
	print call.end_time
	print call.uri

	if (call.status == "completed"):
	    break
	else:
	    time.sleep(1)

    url_response = urllib2.urlopen("http://www.williamslabs.com/alert/query.py?CallSid=%s" % (sid))
    code = int(url_response.read())

    if code is 6:
	print "Recording identified"
	rec = call.recordings.list()[0]
	link = "https://api.twilio.com/2010-04-01/Accounts/%s/Recordings/%s.mp3" % (account, rec.sid)
	print link
    else:
	print "Other response %d" % (code)

def parse_users():
    f = open('users', 'r')
    users = {}
    for line in f:
	user = {}
	index = line.find("#")
	if index != -1:
	    line = line[:index]
	items = line.split()
	if len(items) == 2:
	    if items[0] in users:
		print "Duplicate user %s" % items[0]
		continue

	    user['number'] = items[1]
	    user['start_time'] = datetime(1900, 1, 1, 0, 0, 0)
	    user['end_time'] = datetime(1900, 1, 1, 23, 59, 59)
	    users[items[0]] = user
	elif len(items) == 3:
	    if items[0] in users:
		print "Duplicate user %s" % items[0]
		continue

	    user['name'] = items[0]
	    user['number'] = items[1]

	    start_str = items[2].split("-")[0]
	    end_str = items[2].split("-")[1]
	    if len(start_str) != 4 or len(end_str) != 4:
		print "Error parsing time: " + line
		continue

	    user['start_time'] = datetime.strptime(start_str + "00", "%H%M%S")
	    user['end_time'] = datetime.strptime(end_str + "59", "%H%M%S")

	    # Verify the time period is valid
	    if user['start_time'] >= datetime.strptime(end_str + "00", "%H%M%S"):
		print "Ignoring %s, Availability end_time must be after start_time" %\
			(user['name'])
		continue

	    users[items[0]] = user

	elif len(items) == 1 or len(items) > 3:
	    print "Error parsing: " + line
	    continue
	else:
	    continue
    return users

def check_availability(user, info):
    start = info['start_time']
    end = info['end_time']
    _now = datetime.now()
    now = datetime(1900, 1, 1, _now.hour, _now.minute, _now.second)

    if now <= end and now >= start:
	return True
    else:
	return False

def filter_users_on_availability(users):
    subset = {}
    for user, info in users.iteritems():
	if (check_availability(user, info)):
	    subset[user] = info
    return subset

def insert_group(group, groups):
    if 'name' in group:
	if group['name'] in groups:
	    print "Duplicate group found %s, ignoring." % (group['name'])
	else:
	    groups[group['name']] = group['members']
    return groups

def parse_groups(users):
    f = open('groups', 'r')
    groups = {}
    group = {}
    for line in f:
	index = line.find("#")
	if index != -1:
	    line = line[:index]
	items = line.split()
	if len(items) == 0 or len(items) > 2:
	    continue
	elif len(items) == 2:
	    if items[0] != "group":
		print "Group parse error: " + line
		continue

	    # If the group is complete, append it to the groups list.
	    groups = insert_group(group, groups)

	    group = {}
	    group['name'] = items[1]
	    group['members'] = []
	else:
	    if 'name' not in group:
		print "Group member %s has been stated before group" % (items[0])
		continue
	    if items[0] not in users:
		print "User %s is not in the user list" % (items[0])
		continue
	    group['members'].append(items[0])

    groups = insert_group(group, groups)
    return groups



responses = { 1 : {"text" : "Yes", "record" : False},\
	2 : {"text" : "No", "record" : False},\
	3 : {"text" : "Don't Care", "record" : False},\
	4 : {"text" : "Recorded Response", "record" : True} }
print responses



notification = """Test Message, Press 1 for Yes, 2 for No,
3 for Stop, 4 for No impact, 5 for don't care, or 6 to record a response."""
number = "5553755828"
#place_call(number, notification)

users = parse_users()
#print users

groups = parse_groups(users)
#print groups

avail_users = filter_users_on_availability(users)
print avail_users

call_request = {"src" : "pwilliams", \
	"dst" : avail_users, \
	"question" : "Is this a test message?"}

