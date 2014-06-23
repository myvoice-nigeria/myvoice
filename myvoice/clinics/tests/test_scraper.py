import mock
from datetime import date
import re
import requests

from django.test import TestCase

from .. import dashboard_scraper


region_page = '''
<div id="map_region">
<ul class="links-a grid-a link-list-inline">
<li class="column w100">
<strong></strong>
<ul class="list-unstyled link-list-inline">
<li><a href="https://nphcda.thenewtechs.com/data/showzone/1/5.html" onmouseout="unhighlight('area5');" onmouseover="highlight('area5');">Adamawa</a></li>
<li><a href="https://nphcda.thenewtechs.com/data/showzone/1/26.html" onmouseout="unhighlight('area26');" onmouseover="highlight('area26');">Nasarawa</a></li>
<li><a href="https://nphcda.thenewtechs.com/data/showzone/1/29.html" onmouseout="unhighlight('area29');" onmouseover="highlight('area29');">Ondo</a></li>
</ul>
</li>
</ul>
</div>
'''


lga_page = '''
<ul class="links-a grid-a">
<li class="column w100">
<strong></strong>
<ul class="list-unstyled link-list-inline">
<li>Health Center
    <ul>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/187.html">ARDO YAHAYA (MBAMBA) HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/188.html">BAKARI MBAMOI HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/183.html">BAKO HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/192.html">GONGOSHI HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/185.html">LAMIDO ALIYU HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/189.html">NAMTARI MANGA HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/186.html">NANA ASMAU HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/190.html">NGURORE HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/184.html">SHAGARI HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/191.html">TOUNGO HC</a></li>
    <li><a href="https://nphcda.thenewtechs.com/data/showentity/182.html">WURO-HAUSA HC</a></li>
    </ul>
    </li>
    </ul>
    </li>
    </ul>
'''


nav_page = '''
<nav class="crumbs-a">
<ul>
<li><a href="https://nphcda.thenewtechs.com/">Home</a></li>
<li><a href="https://nphcda.thenewtechs.com/data">Data</a></li>
<li><a href="https://nphcda.thenewtechs.com/data/showzone/1/26">Nasarawa</a></li>
<li><a href="https://nphcda.thenewtechs.com/data/showentities/779">Wamba</a></li>
<li class="active">Wamba</li>
</ul>
</nav>
'''


class TestGetLinks(TestCase):

    def setUp(self):
        self.mock_url = mock.Mock()
        self.params = {'elem': 'div', 'attr': 'id', 'value': 'map_region'}

    @mock.patch('requests.get')
    def test_get_links_count(self, get_mock):
        '''Make sure the correct number of links are extracted.'''
        response_mock = mock.MagicMock()
        response_mock.content = region_page
        get_mock.return_value = response_mock
        link_dict = dashboard_scraper.get_links(self.mock_url, **self.params)
        self.assertEqual(3, len(link_dict))

    @mock.patch('requests.get')
    def test_get_links_ul(self, get_mock):
        '''Make sure we can get links in lists too.'''
        response_mock = mock.MagicMock()
        response_mock.content = lga_page
        get_mock.return_value = response_mock
        params = {'elem': 'ul', 'attr': 'class', 'value': 'links-a'}
        link_dict = dashboard_scraper.get_links(self.mock_url, **params)
        self.assertEqual(11, len(link_dict))

    @mock.patch('requests.get')
    def test_get_region_links_keys(self, get_mock):
        '''Make sure the keys of the links are correct.'''
        response_mock = mock.MagicMock()
        response_mock.content = region_page
        get_mock.return_value = response_mock
        link_dict = dashboard_scraper.get_links(self.mock_url, **self.params)
        self.assertIn('Adamawa', link_dict)
        self.assertIn('Nasarawa', link_dict)
        self.assertIn('Ondo', link_dict)

    @mock.patch('requests.get')
    def test_get_links_values(self, get_mock):
        '''Make sure the values of the links are correct.'''
        href1 = 'https://nphcda.thenewtechs.com/data/showzone/1/5.html'
        href2 = 'https://nphcda.thenewtechs.com/data/showzone/1/26.html'
        href3 = 'https://nphcda.thenewtechs.com/data/showzone/1/29.html'
        response_mock = mock.MagicMock()
        response_mock.content = region_page
        get_mock.return_value = response_mock
        link_dict = dashboard_scraper.get_links(self.mock_url, **self.params)
        self.assertEqual(href1, link_dict.get('Adamawa'))
        self.assertEqual(href2, link_dict.get('Nasarawa'))
        self.assertEqual(href3, link_dict.get('Ondo'))

    @mock.patch('requests.get')
    def test_no_connection(self, get_mock):
        '''If there is no connection, send an empty dictionary.'''
        error = requests.ConnectionError()
        get_mock.side_effect = error
        link_dict = dashboard_scraper.get_links(self.mock_url, **self.params)
        self.assertEqual({}, link_dict)


class TestExtractPageData(TestCase):

    def setUp(self):
        self.soup_mock = mock.Mock()
        self.elem_mock = mock.Mock()
        self.soup_mock.find.return_value = self.elem_mock

    def test_extract_clinic_name(self):
        '''Scrape for the name of the clinic.'''
        self.elem_mock.find.return_value.text = 'Wamba'
        page = dashboard_scraper.ClinicPage(self.soup_mock)
        self.assertEqual('Wamba', page.get_clinic_name())
        self.soup_mock.find.assert_called_once_with('nav', class_='crumbs-a')
        self.elem_mock.find.assert_called_once_with('li', class_='active')

    def test_extract_lga_name(self):
        '''Extract the lga name from the page'''
        patt = re.compile('showentities')
        self.elem_mock.find.return_value.text = 'Wamba'
        page = dashboard_scraper.ClinicPage(self.soup_mock)
        self.assertEqual('Wamba', page.get_lga_name())
        self.soup_mock.find.assert_called_once_with('nav', class_='crumbs-a')
        self.elem_mock.find.assert_called_once_with(href=patt)

    def test_extract_region_name(self):
        '''Extract the region (state) name from the page'''
        patt = re.compile('showzone')
        self.elem_mock.find.return_value.text = 'Nasarawa'
        page = dashboard_scraper.ClinicPage(self.soup_mock)
        self.assertEqual('Nasarawa', page.get_region_name())
        self.soup_mock.find.assert_called_once_with('nav', class_='crumbs-a')
        self.elem_mock.find.assert_called_once_with(href=patt)

    def test_get_month_from_header_roman(self):
        '''The headers for the QTY, QLY and PAYMENT are irregular

        Get the month from headers.
        '''
        month_1 = dashboard_scraper.ClinicPage.get_month('Q.I 2014')
        month_2 = dashboard_scraper.ClinicPage.get_month('Q 4 2011')
        month_3 = dashboard_scraper.ClinicPage.get_month('Qu. IV 2011')
        self.assertEqual(date(2014, 1, 1), month_1)
        self.assertEqual(date(2011, 4, 1), month_2)
        self.assertEqual(date(2011, 10, 1), month_3)

    def test_extract_payment_data(self):
        '''Extract payment data from page

        Payment data should be in dict with the quarter as key
        and the amount as value.'''

    def test_no_payment_data(self):
        '''What happens when there is no data? Nothing I hope.'''
