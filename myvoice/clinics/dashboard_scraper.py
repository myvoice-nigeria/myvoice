'''
How Dashboard Scaper works:
    1. From the PBF dashboard, get the links to the different clinic pages
    2. For each clinic page find the ones that have changed since last scrape
    2. Scrape the changed clinic pages to get the required statistics
    3. Update the database with the statistics
#TODO: How to find if the page has changed?
'''
import requests
#from urllib2 import URLError
from bs4 import BeautifulSoup

DASHBOARD_URL = 'https://nphcda.thenewtechs.com/data.html'
DIV_LINKS_CLASS = 'quality-b'


def get_links():
    '''Returns dict of clinic_name: url'''
    try:
        resp = requests.get(DASHBOARD_URL)
    except requests.ConnectionError:
        content = ''
    else:
        content = resp.content
    soup = BeautifulSoup(content)
    div = soup.find('div', {'class': DIV_LINKS_CLASS})
    elems = div.findAll('a')
    links = {elem.get_text().strip(): elem.get('href') for elem in elems}
    return links
