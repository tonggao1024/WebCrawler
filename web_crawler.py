import requests
import pprint
import pytest
import requests_mock
import multiprocessing
import urllib.request
import validators
import threading

from mock import patch, Mock
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import defaultdict
from threading import Lock
from concurrent.futures import ThreadPoolExecutor


# Main class
class WebCrawler:
    def __init__(self):
        self.base_url = ""
        self.dic = defaultdict(list)
        self.lock = Lock()

    def parse_links(self, base, urls):
        if urls == []:
            return []
        filtered = set()
        for url in urls:
            # skip missing or bad urls
            if url is None or url.strip() == '':
                continue
            # skip other protocols
            if url.startswith('javascript'):
                continue
            # check if the url is relative
            if not url.startswith('http'):
                # join the base url with the absolute fragment
                url = urljoin(base, url)
            if not validators.url(url):
                continue
            # store in the filtered set
            filtered.add(url)
        return list(filtered)

    def get_links(self, url):
        try:
            r = requests.get(url, timeout=30)
        except:
            print(f'Warning: Can not reach {url}, skipping')
            return []
        html = r.text
        # parse html
        soup = BeautifulSoup(html, 'html.parser')
        # find all all of the <a href=""> tags in the document
        atags = soup.find_all('a')
        # get all links from a tags
        return [tag.get('href') for tag in atags]

    def crawler(self, url):
        if not url.startswith(self.base_url) or url.endswith('.pdf') or url in self.dic:
            return
        links = self.get_links(url)
        filtered_links = self.parse_links(url, links)
        self.dic[url] = filtered_links
        if filtered_links:
          with self.lock:
              text = f'[[[[[[URL: {url}]]]]]]' + '\n' + \
                  f'[[[[[[LINKS: {filtered_links}]]]]]]' + '\n'
              with open("tmp.txt", "a") as myfile:
                  myfile.write(text)
          # select the number of workers
          n_threads = len(filtered_links)
          # validate each link
          with ThreadPoolExecutor(n_threads) as executor:
              _ = [executor.submit(self.crawler, link) for link in filtered_links]

    def format_urls(self):
        for url, links in self.dic.items():
            if links:
                print(f'URL: \n{url}\n')
                print(f'LINKS: \n' + "\n".join(links) + "\n")

    def run(self, url):
        self.base_url = url
        self.crawler(self.base_url)
        self.format_urls()

# Tester
class TestWebCrawler():
    def setup_method(self):
        self.web_crawler = WebCrawler()
        self.test_url = 'http://argweryhwetest.com'
        self.test_links = [urljoin(self.test_url, i) for i in ['1', '2', '3']]
        self.test_html = f"""<html>
<head></head>
<body>
<a class="Header_skipToContent__P_Yug" href={self.test_links[0]}>Skip to Content</a>
<a class="Header_skipToContent__P_Yug" href={self.test_links[1]}>Skip to Content</a>
<a class="Header_skipToContent__P_Yug" href={self.test_links[2]}>Skip to Content</a>
</body>
</html>"""

    def test_get_links_with_mock(self, requests_mock):
        # mock request get
        requests_mock.get(self.test_url, text=self.test_html)
        res = self.web_crawler.get_links(self.test_url)
        assert res == self.test_links

    def test_get_links_with_invalid_url(self):
        # real request with invalid url
        res = self.web_crawler.get_links(self.test_url)
        assert res == []

    def test_parse_links(self):
        # valid urls
        links = self.test_links
        res = self.web_crawler.parse_links(self.test_url, self.test_links)
        assert sorted(res) == sorted(self.test_links)

        # filter invalid urls
        links = ['', 'javascript.com', 'aaa.com']
        res = self.web_crawler.parse_links(self.test_url, links)
        print(res)
        assert res == [urljoin(self.test_url, links[-1])]

    def test_format_urls(self, capsys):
        # full output
        self.web_crawler.dic = {
          'a':['a1','a2'],
          'b':['b1','b2'],
        }

        self.web_crawler.format_urls()

        captured = capsys.readouterr()
        assert captured.out == 'URL: \na\n\nLINKS: \na1\na2\n\nURL: \nb\n\nLINKS: \nb1\nb2\n\n'


        # empty links
        self.web_crawler.dic = {
          'a':['a1','a2'],
          'b':[],
        }

        self.web_crawler.format_urls()

        captured = capsys.readouterr()
        assert captured.out == 'URL: \na\n\nLINKS: \na1\na2\n\n'

    def test_crawler(self, capsys, mocker):
        # sanity checks
        self.web_crawler.dic = {
          urljoin(self.test_url, 'a'):['a1','a2'],
        }
        self.web_crawler.base_url = self.test_url
        links = ['a', 'a.pdf', urljoin(self.test_url, 'a')]
        for url in links:
          self.web_crawler.crawler(url)
          captured = capsys.readouterr()
          assert captured.out == ''

        # real checks
        self.web_crawler.dic = defaultdict(list)
        self.web_crawler.base_url = self.test_url


        self.web_crawler.get_links = Mock(return_value=['a','b'])
        self.web_crawler.parse_links = Mock(return_value=['a','b'])

        self.web_crawler.crawler(self.test_url)
        assert self.web_crawler.dic == {self.test_url:['a','b']}

        
if __name__ == '__main__':
    url = "https://monzo.com/"
    web_crawler = WebCrawler()
    web_crawler.run(url)
