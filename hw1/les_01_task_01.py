"""
https://github.com/avidbrain/parsing/pull/1
Примечание:
Чтобы не сваливать код в одну кучу, сделал несколько классов.
Я думаю, пригодится для будущих заданий.
- SiteDriver - низкоуровневые операции с сайтом (get)
- Stage - аккумулятор данных нескольких логически связанных страниц
- PageGroup - итератор, достающий данные нескольких страниц, с пагинацией
- Parse5kaCategories - собственно оркестратор всей работы
"""
import requests
import time
import json
from pathlib import Path


def wait(n=1, secs=0.25):
    time.sleep(n * secs)


class SiteDriver:
    """Implements simple fetching from a web site."""

    _max_retry = 15
    _headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
    }

    def get(self, url, params=None) -> requests.Response:
        if params is None:
            params = {}
        for i in range(self._max_retry):
            response = requests.get(url, params=params, headers=self._headers)
            if response.status_code == 200:
                return response
            wait(i + 1)
        raise TimeoutError('Похоже, сайт опять лежит.')

    def close(self):
        pass


class Stage:
    """Data from pages accumulate here."""

    def __init__(self, headers):
        self._headers = headers
        self._chunks = []

    def append(self, data):
        self._chunks.append(data)

    @property
    def data(self):
        result = {}
        result.update(self._headers)
        result['products'] = [p for chunk in self._chunks for p in chunk]
        return result

    def save(self, path):
        with open(path, 'w', encoding='UTF-8') as file:
            json.dump(self.data, file, ensure_ascii=False, indent='  ')


class PageGroup:
    """Iterator, returns pages' data."""

    def __init__(self, site_drv, start_url, start_params=None):
        self._site_drv = site_drv
        self._url = start_url
        self._params = start_params or {}

    def __iter__(self):
        return self

    def __next__(self):
        if not self._url:
            raise StopIteration
        response = self._site_drv.get(self._url, self._params)
        if self._params:
            self._params = {}
        data = response.json()
        if hasattr(data, 'get'):
            self._url = data.get('next')
            return data.get('results')
        else:  # list?
            self._url = None
            return data


class Parse5kaCategories:
    _categories_url = "https://5ka.ru/api/v2/categories/"
    _products_url = "https://5ka.ru/api/v2/special_offers/"

    def __init__(self):
        self._site_drv = SiteDriver()
        self._export_dir = Path.cwd() / 'categories'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._site_drv.close()

    def run(self):
        # get categories
        page_group = PageGroup(self._site_drv, self._categories_url)
        categories = next(page_group)
        wait()
        # get products
        if categories:
            Path.mkdir(self._export_dir, exist_ok=True)
            for cat_info in categories:
                cat_id = cat_info['parent_group_code']
                params = {
                    'records_per_page': 20,
                    'categories': cat_id
                }
                page_group = PageGroup(self._site_drv,
                                       self._products_url,
                                       params)
                stage = Stage(cat_info)
                for data in page_group:
                    stage.append(data)
                    wait()
                stage.save(self._export_dir / f"{cat_id}.json")
                wait(5)
                # TODO: Progress bar


if __name__ == '__main__':
    parser = Parse5kaCategories()
    with parser:
        parser.run()
