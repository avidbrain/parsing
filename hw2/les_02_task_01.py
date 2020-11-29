"""
https://github.com/avidbrain/parsing/pull/2
"""

import os
import time
import datetime as dt
import requests
import bs4
import pymongo
import dotenv
import locale
import pytz
from urllib.parse import urljoin

dotenv.load_dotenv('.env')


def wait(n=1, secs=0.25):
    time.sleep((n * secs))


class MongoStage:
    """Temporary storage based on MongoDB."""

    def __init__(self, db_name, collection_name):
        self.client = pymongo.MongoClient(os.getenv('MONGO_URL'))
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def close(self):
        self.client.close()

    def save(self, item):
        self.collection.insert_one(item)


class SiteDriver:
    """Core site fetching and parsing code."""

    _max_retry = 15
    _headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
    }

    def _get(self, url, params=None) -> requests.Response:
        if params is None:
            params = {}
        for i in range(self._max_retry):
            response = requests.get(url, params=params, headers=self._headers)
            if response.status_code == 200:
                return response
            wait(i + 1)
        raise TimeoutError('Похоже, сайт опять лежит.')

    def _soup(self, url) -> bs4.BeautifulSoup:
        response = self._get(url)
        html_doc = response.text
        # with open('promo.html', 'w', encoding='UTF-8') as file:
        #    file.write(html_doc)
        # with open('promo.html', 'r', encoding='UTF-8') as file:
        #    html_doc = file.read()
        return bs4.BeautifulSoup(html_doc, 'lxml')


class ParseMagnit(SiteDriver):

    def __init__(self, start_url):
        self.product_template = {
            'url': lambda soup: urljoin(self.start_url, soup.get('href')),
            'promo_name': lambda soup: soup.find('div', attrs={
                'class': 'card-sale__header'}).get_text(),
            'product_name': lambda soup: soup.find('div', attrs={
                'class': 'card-sale__title'}).get_text(),
            'old_price': lambda soup: self.get_price(
                soup.find('div', attrs={'class': 'label__price_old'})),
            'new_price': lambda soup: self.get_price(
                soup.find('div', attrs={'class': 'label__price_new'})),
            'image_url': lambda soup: urljoin(self.start_url,
                                              soup.find('img').get('data-src')),
            'date_from': lambda soup: self.get_date(
                self.get_date_str(soup, 'с'), -1, 0, 0, self.tz),
            'date_to': lambda soup: self.get_date(
                self.get_date_str(soup, 'до'), 7, 23, 59, self.tz)
        }
        self.start_url = start_url
        locale.setlocale(locale.LC_TIME, 'ru')
        self.tz = pytz.timezone('Europe/Moscow')

    def __enter__(self):
        self._stage = MongoStage('magnit', 'promo')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stage.close()

    def parse(self, soup):
        catalog = soup.find('div', attrs={'class': 'сatalogue__main'})

        for product in catalog.find_all(
                name='a',
                attrs={'class': 'card-sale card-sale_catalogue'},
                recursive=False):
            yield self.get_product(product)

    def get_product(self, product_soup) -> dict:
        result = {}
        for key, value in self.product_template.items():
            try:
                result[key] = value(product_soup)
            except (AttributeError, ValueError) as e:
                continue
        return result

    @staticmethod
    def get_price(soup):
        _int = soup.find('span', attrs={'class': 'label__price-integer'})
        _dec = soup.find('span', attrs={'class': 'label__price-decimal'})
        return float(f"{_int.get_text()}.{_dec.get_text()}")

    @staticmethod
    def get_date_str(soup, start) -> str:
        date_div = soup.find('div', attrs={'class': 'card-sale__date'})
        for p in date_div.find_all('p'):
            if p.get_text().startswith(start):
                parts = map(lambda s: s.lower()[:3], p.get_text().split()[1:])
                return ' '.join(parts)
        return ''

    @staticmethod
    def get_date(date_str, tolerance=0,
                 hour=0, minute=0, tz=None) -> dt.datetime:
        this_year = dt.date.today().year
        result = dt.datetime.strptime(date_str, '%d %b')
        result = result.replace(year=this_year)
        # Next year if date is way earlier than today
        if tolerance >= 0 and ((dt.datetime.now() - result).days > tolerance):
            result = result.replace(year=this_year + 1)
        if tz is not None:
            result = tz.localize(result)
        result = result.replace(hour=hour, minute=minute)
        return result

    def run(self):
        soup = self._soup(self.start_url)
        for product in self.parse(soup):
            self._stage.save(product)


if __name__ == '__main__':
    parser = ParseMagnit('https://magnit.ru/promo/?geo=moskva')
    with parser:
        parser.run()
