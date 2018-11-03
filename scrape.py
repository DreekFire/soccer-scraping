import urllib2
import re
import httplib2
import os
import requests
import mechanize
import cookielib
import getpass
from lxml import html
from time import mktime
from datetime import datetime
from datetime import timedelta
from bs4 import BeautifulSoup
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'
login_url = 'https://www.gotsport.com/asp/users/login_menu.asp'

def login():
	br = mechanize.Browser()

	cookiejar = cookielib.LWPCookieJar()
	br.set_cookiejar(cookiejar)
	br.set_handle_robots(False)
	br.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36')]
	br.open(login_url)
	for form in br.forms():  
	  if str(form.attrs.get("id")) == "ORGLoginForm":
	    br.form = form
	    break
	br.form['UserName'] = raw_input("Username: ")
	br.form['Password'] = getpass.getpass()
	br.submit()
	resp = br.open(r'http://www.gotsport.com/asp/directors/club/schedule_overview.asp')
	
	return resp.read()

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir, 'credentials.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
	credentials = get_credentials()
	http = credentials.authorize(httplib2.Http())
	service = discovery.build('calendar', 'v3', http=http)

	page = login()
	got_soccer = BeautifulSoup(page, 'html.parser')
	main_div = got_soccer.find("div", {"class": "PageTabBox"})
	tables = main_div.findAll("table", recursive = False)
	main_tr = tables[1].find("tr")
	main_td = main_tr.find("td")
	calendar_sections = main_td.findAll("table", recursive = False)
	month_and_year = datetime.strptime(unicode(calendar_sections[1].find("tr").find("td").find("div").string).replace(u'\xa0', ' ').strip(), '%B %Y')

	month = month_and_year.month
	year = month_and_year.year

	rows = calendar_sections[2].findAll("tr", recursive = False)

	days = []
	for row in rows[1:]:
		day_list = []
		columns = row.findAll("td", recursive = False)
		for day in columns:
			if day["bgcolor"] != "white":
				day_list.append(day) 
		days.extend(day_list)

	for day in days:
		i = 0
		events = []
		events_table = day.findAll("table", recursive = False)
		if len(events_table) > 1:
			rows = events_table[1].findAll("tr", recursive = False)
			if len(rows) > 0:
				date = int(unicode(day.find("table").find("tr").find("td").string))
				for event in rows:
					age_group = unicode(event.find("td", class_ = 'AgeGroupBox').string)
					event_name = unicode(event.find("td", class_ = 'TinyHeading').find("a").string)
					location_and_time = re.split(' @ ', unicode(event.find("td", "TinyText").find("div")['title']))
					location = location_and_time[0].strip()
					start_time = datetime.strptime(str(year)+' '+str(month)+' '+str(date).zfill(2)+' '+location_and_time[1].strip(),"%Y %m %d %I:%M %p")
					end_time = start_time+timedelta(hours = 2)
					event_meta = {
						'summary': age_group+' '+event_name,
						'start': {
							'dateTime': datetime.strftime(start_time, "%Y-%m-%dT%H:%M:%S"),
							'timeZone': 'America/Los_Angeles',
						},
						'end': {
						    'dateTime': datetime.strftime(end_time, "%Y-%m-%dT%H:%M:%S"),
						    'timeZone': 'America/Los_Angeles',
						},
						'location': location,
					}
					res = service.events().insert(calendarId='primary', body=event_meta).execute()
					print 'Event created: '+event_meta['summary']+'\n'+event_meta['start']['dateTime']+' - '+event_meta['end']['dateTime']+'\n'+event_meta['location'] 

if __name__ == '__main__':
    main()