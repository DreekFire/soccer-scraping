"""python program for scraping GotSoccer website and transferring schedules to Google Calendar"""
import os
import re
import cookielib
from datetime import datetime
from datetime import timedelta
import getpass
import httplib2
import mechanize
from bs4 import BeautifulSoup
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    FLAGS = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    FLAGS = None

SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'
LOGIN_URL = 'https://www.gotsport.com/asp/users/login_menu.asp'

def login():
    """login to GotSoccer and open calendar page"""
    browser = mechanize.Browser()

    cookiejar = cookielib.LWPCookieJar()
    browser.set_cookiejar(cookiejar)
    browser.set_handle_robots(False)
    browser.addheaders = [('User-agent',
                           """Mozilla/5.0 (Windows NT 10.0; Win64; x64)
                           AppleWebKit/537.36 (KHTML, like Gecko)
                           Chrome/70.0.3538.77 Safari/537.36""")]
    browser.open(LOGIN_URL)
    for form in browser.forms():
        if str(form.attrs.get("id")) == "ORGLoginForm":
            browser.form = form
            break
    browser.form['UserName'] = raw_input("Username: ")
    browser.form['Password'] = getpass.getpass()
    browser.submit()
    resp = browser.open(r'http://www.gotsport.com/asp/directors/club/schedule_overview.asp')

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
        if FLAGS:
            credentials = tools.run_flow(flow, store, FLAGS)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print 'Storing credentials to ' + credential_path
    return credentials

def upload(day_list, month_and_year, service):
    """uploads events to Google Calendar"""
    for day in day_list:
        events_table = day.findAll("table", recursive=False)
        if len(events_table) > 1:
            rows = events_table[1].findAll("tr", recursive=False)
            if rows:
                date = int(unicode(day.find("table").find("tr").find("td").string))
                for event in rows:
                    event_meta = get_meta(event, month_and_year, date)
                    service.events().insert(calendarId='primary', body=event_meta).execute()

def get_meta(event, month_and_year, date):
    """extracts the event data from the GotSoccer calendar"""
    age_group = unicode(event.find("td", class_='AgeGroupBox').string)
    event_name = unicode(event.find("td", class_='TinyHeading').find("a").string)
    location_and_time = re.split(' @ ', unicode(event.find("td", "TinyText")
                                                .find("div")['title']))
    location = location_and_time[0].strip()
    start_time = datetime.strptime(str(month_and_year.year)+' '
                                   +str(month_and_year.month)+' '
                                   +str(date).zfill(2)+' '
                                   +location_and_time[1].strip(),
                                   "%Y %m %d %I:%M %p")
    end_time = start_time+timedelta(hours=2)
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
    return event_meta

def main():
    """begin scraping"""
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())

    service = discovery.build('calendar', 'v3', http=http)
    got_soccer = BeautifulSoup(login(), 'html.parser')
    calendar_sections = (got_soccer.find("div", {"class": "PageTabBox"})
                         .findAll("table", recursive=False)[1]
                         .find("tr")
                         .find("td")
                         .findAll("table", recursive=False))

    month_and_year = datetime.strptime(unicode(calendar_sections[1]
                                               .find("tr")
                                               .find("td")
                                               .find("div").string)
                                       .replace(u'\xa0', ' ').strip(), '%B %Y')

    rows = calendar_sections[2].findAll("tr", recursive=False)

    days = []
    for row in rows[1:]:
        day_list = []
        columns = row.findAll("td", recursive=False)
        for day in columns:
            if day["bgcolor"] != "white":
                day_list.append(day)
        days.extend(day_list)

    upload(days, month_and_year, service)

if __name__ == '__main__':
    main()
