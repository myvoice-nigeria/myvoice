import mock

from django.test import TestCase

from .. import dashboard_scraper

main_html = '''
<div class="quality-b">
<article class="item">
<figure><img alt="No picture available for this entity" src="https://nphcda.thenewtechs.com/cside/images/portal/1Wayo_Matti.jpg"/></figure>
<h4>Top score quality</h4>
<p class="title"><span>1.</span><a href="https://nphcda.thenewtechs.com/data/showentity/5.html">Wayo Matti (HC) </a></p>
<p class="global"><span class="badge-a up">97%</span></p>
</article>
<div class="table">
<div class="head">
<p class="title"><span>Name</span></p>
<p class="global">Global</p>
</div>
<div class="item">
<p class="title">5. <a href="https://nphcda.thenewtechs.com/data/showentity/2.html">Wamba (GH) </a></p>
<p class="global"><i class="badge-b "></i> 76%</p>
</div>
</div>
</div>
'''


class TestScraper(TestCase):

    @mock.patch('requests.get')
    def test_get_links_count(self, get_mock):
        response_mock = mock.MagicMock()
        response_mock.content = main_html
        get_mock.return_value = response_mock
        link_dict = dashboard_scraper.get_links()
        self.assertEqual(2, len(link_dict))

    @mock.patch('requests.get')
    def test_get_links_keys(self, get_mock):
        response_mock = mock.MagicMock()
        response_mock.content = main_html
        get_mock.return_value = response_mock
        link_dict = dashboard_scraper.get_links()
        self.assertIn('Wayo Matti (HC)', link_dict)
        self.assertIn('Wamba (GH)', link_dict)

    @mock.patch('requests.get')
    def test_get_links_values(self, get_mock):
        href1 = 'https://nphcda.thenewtechs.com/data/showentity/2.html'
        href2 = 'https://nphcda.thenewtechs.com/data/showentity/5.html'
        response_mock = mock.MagicMock()
        response_mock.content = main_html
        get_mock.return_value = response_mock
        link_dict = dashboard_scraper.get_links()
        self.assertEqual(href2, link_dict.get('Wayo Matti (HC)'))
        self.assertEqual(href1, link_dict.get('Wamba (GH)'))
