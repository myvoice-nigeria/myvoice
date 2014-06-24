'''
How Dashboard Scaper works:
    1. From the PBF dashboard, get the links to the different clinic pages
    2. For each clinic page find the ones that have changed since last scrape
    2. Scrape the changed clinic pages to get the required statistics
    3. Update the database with the statistics
#TODO: How to find if the page has changed?
'''
import requests
import re
from datetime import date
from functools import partial
from itertools import chain
from multiprocessing import Pool
from bs4 import BeautifulSoup

# Does this go in the settings?
DASHBOARD_URL = 'https://nphcda.thenewtechs.com/data.html'


class WrongHeaderError(Exception):
    pass


def get_soup(url, **kwargs):
    '''
    Get the soup of elements we are interested in
    '''
    elem = kwargs.get('elem', 'div')
    attr = kwargs.get('attr', 'id')
    value = kwargs.get('value', 'map_region')

    resp = requests.get(url)
    content = resp.content
    soup = BeautifulSoup(content)
    return soup.find(elem, {attr: value})


def get_links(url, **kwargs):
    '''
    Return links from content of url.

    url: url to fetch
    elem: parent element of links, defaults to 'div'
    attr: the attribute to filter by, defaults to 'id'
    value: the filter value, defaults to 'map_region'
    '''
    try:
        parent = get_soup(url, **kwargs)
    except requests.ConnectionError:
        return {}
    elems = parent.find_all('a')
    return {elem.get_text().strip(): elem.get('href') for elem in elems}


def get_clinic_links():
    '''
    Get links for each clinic.

    We don't need corresponding name, lga and state(region?)
    because we can get these from the page we are going to scrape.
    '''
    #region_data = get_links(DASHBOARD_URL, elem='div', attr='id', value='map_region')
    region_data = get_links(DASHBOARD_URL)
    region_links = region_data.values()

    lga_func = partial(get_links, elem='div', attr='id', value='map_region')
    lga_pool = Pool()
    lga_data = lga_pool.map(lga_func, region_links)
    lga_links = chain(*[i.values() for i in lga_data])

    clinic_func = partial(get_links, elem='ul', attr='class', value='links-a')
    clinic_pool = Pool()
    clinic_data = clinic_pool.map(clinic_func, lga_links)
    clinic_links = chain(*[i.values() for i in clinic_data])
    return clinic_links


class ClinicPage(object):
    # Regexes to search for lga or region links in page
    LGA_PATT = re.compile('showentities')
    REGION_PATT = re.compile('showzone')

    # Regex to extract header information from table data
    HEADER_PATT = re.compile('[IV\d]+')

    # css-class selectors for payment, quality, quantity
    PAYMENT_SELECTOR = 'table-payment-a'
    QUALITY_SELECTOR = 'table-qualities-a'
    QUANTITY_SELECTOR = 'table-quantities-a'

    def __init__(self, soup):
        self.soup = soup
        self._nav_elem = None
        #self.nav_elem = self.extract_nav_elem()

    def get_nav_elem(self):
        '''Extract the nav element that contains clinic, lga and region info
        '''
        if self._nav_elem:
            return self._nav_elem
        return self.soup.find('nav', class_='crumbs-a')

    def get_clinic_name(self):
        return self.get_nav_elem().find('li', class_='active').text

    def get_lga_name(self):
        return self.get_nav_elem().find(href=self.LGA_PATT).text

    def get_region_name(self):
        return self.get_nav_elem().find(href=self.REGION_PATT).text

    def extract_table_content(self, div):
        '''Extract body data from soup

        Returns a list of lines
        each line is a list of text data from table
        '''
        data = []
        tr = div.find('tbody').find_all('tr')
        for row in tr:
            data.append([item.get_text() for item in row.find_all('td')])
        return data

    def extract_table_header(self, div):
        '''Extract header data from soup

        Returns a list of headers for the page section.
        '''
        th = div.find_all('th')
        first = th[0].get_text()
        rest = [self.get_month(item.get_text()) for item in th[1:]]
        return [first] + rest

    def find_table_div(self, selector_class):
        return self.soup.find('div', class_=selector_class)

    def merge_data(self, header, content):
        '''Return a list of dicts for each line of content

        The keys are the header.
        '''
        pass

    def extract_table_data(self, selector_class):
        '''Extract data from soup

        Extracts data from each of payment, quality and quantity.'''
        # Extract payment information
        payment_div = self.find_table_div(self.PAYMENT_SELECTOR)
        payment_header = self.extract_table_header(payment_div)
        payment_content = self.extract_table_content(payment_div)
        payment_data = self.merge_data(payment_header, payment_content)

        # Extract quality information
        qly_div = self.find_table_div(self.QUALITY_SELECTOR)
        qly_header = self.extract_table_header(qly_div)
        qly_content = self.extract_table_content(qly_div)
        qly_data = self.merge_data(qly_header, qly_content)

        # Extract quantity information
        qty_div = self.find_table_div(self.QUANTITY_SELECTOR)
        qty_header = self.extract_table_header(qty_div)
        qty_content = self.extract_table_content(qty_div)
        qty_data = self.merge_data(qty_header, qty_content)

        return payment_data, qly_data, qty_data

    @classmethod
    def get_month(self, header):
        '''Converts header to date'''
        roman_map = {
            'I': 1,
            'II': 4,
            'III': 7,
            'IV': 10
        }
        match = self.HEADER_PATT.findall(header)
        if len(match) == 2:
            qtr, year = match
        else:
            raise ValueError

        try:
            month = int(qtr)
        except ValueError:
            month = roman_map.get(qtr)

        if month:
            return date(int(year), month, 1)
