"""
https://github.com/avidbrain/parsing/pull/3
"""

import os
import time
import datetime as dt
import requests
import bs4
import dotenv
from urllib.parse import urljoin, urlparse
from pathlib import Path
from database import DBStage

dotenv.load_dotenv('.env')


def wait(n=1, secs=0.25):
    time.sleep((n * secs))


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
            if response.status_code // 200 == 1:
                return response
            wait(i + 1)
        raise TimeoutError(f'Сайт сломался на {url}')

    def _soup(self, url) -> bs4.BeautifulSoup:
        response = self._get(url)
        wait()
        return bs4.BeautifulSoup(response.text, 'lxml')


class GbBlogParse(SiteDriver):
    def __init__(self, start_url, api_url):
        self.start_url = start_url
        self.api_url = api_url
        self.url_done = set()

    def __enter__(self):
        self._stage = DBStage(os.getenv('DB_URL'))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stage.close()

    def _soup(self, url):
        result = super()._soup(url)
        self.url_done.add(url)
        return result

    def parse(self, soup):
        pag_ul = soup.find('ul', attrs={'class': 'gb__pagination'})
        paginations = set(
            urljoin(self.start_url, p_url.get('href'))
            for p_url in pag_ul.find_all('a') if p_url.get('href')
        )
        posts_wrapper = soup.find('div', attrs={'class': 'post-items-wrapper'})

        posts = set(
            urljoin(self.start_url, post_url.get('href')) for post_url in
            posts_wrapper.find_all('a', attrs={'class': 'post-item__title'})
        )

        return posts, paginations

    def parse_post(self, soup, url):
        result = {
            'url': url,
            'title': soup.find('h1', attrs={'class': 'blogpost-title'}).text,
            'writer': {
                'name': soup.find('div', attrs={'itemprop': 'author'}).text,
                'url': urljoin(self.start_url,
                               soup.find('div', attrs={'itemprop': 'author'})
                               .parent.get('href'))
            }
        }
        try:
            result['posted_at'] = (
                dt.datetime.fromisoformat(
                    soup.find('div', attrs={'class': 'blogpost-date-views'})
                        .find('time')
                        .get('datetime')
                )
            )
        except AttributeError:
            pass
        try:
            result['img_src'] = (
                soup.find('div', attrs={'class': 'blogpost-content'})
                    .find('img')
                    .get('src')
            )
        except AttributeError:
            pass
        try:
            tags = (
                soup.find('i', attrs={'class': 'i-tag'})
                    .get('keywords', '')
                    .split(',')
            )
            result['tags'] = [tag.strip() for tag in tags if tag.strip()]
        except AttributeError:
            pass
        try:
            comments = (
                soup.find('div', attrs={'class': 'm-t-xl'}).find('comments')
            )
            if int(comments.attrs.get('total-comments-count', 0)) > 0:
                result['comments'] = comments.attrs  # pass to next processing
        except AttributeError:
            pass
        self.add_id(result)
        self.add_id(result['writer'])
        return result

    @staticmethod
    def add_id(dct: dict):
        if 'url' in dct and 'id' not in dct:
            id_str = Path(urlparse(dct['url']).path).name
            dct['id'] = int(id_str) if id_str.isdigit() else id_str

    def get_comments(self, attrs):
        params = {
            'commentable_type': attrs.get('commentable-type', ''),
            'commentable_id': attrs.get('commentable-id', ''),
            'order': attrs.get('order', '')
        }
        return self._get(self.api_url + 'comments', params=params).json()

    def parse_comments(self, comments):
        result = []
        for comment_tree in comments:
            comment = comment_tree.get('comment')
            if comment:
                writer = comment.get('user')
                result.append({
                    'id': comment.get('id'),
                    'parent_id': comment.get('parent_id'),
                    'created_at': dt.datetime.fromisoformat(
                        comment.get('created_at')
                    ),
                    'body': comment.get('body'),
                    'writer': {
                        'id': writer.get('id'),
                        'url': writer.get('url'),
                        'name': writer.get('full_name'),
                    }
                })
            children = comment.get('children')
            if children:
                result.extend(self.parse_comments(children))
        return result

    def run(self, url=None):
        if not url:
            url = self.start_url

        if url not in self.url_done:
            soup = self._soup(url)
            posts, pagination = self.parse(soup)
            for post_url in posts:
                if post_url not in self.url_done:
                    post_data = self.parse_post(self._soup(post_url), post_url)
                    if 'comments' in post_data:
                        comments = self.get_comments(post_data['comments'])
                        post_data['comments'] = self.parse_comments(comments)
                    self._stage.save(post_data)

            for page_url in pagination:
                self.run(page_url)


if __name__ == '__main__':
    parser = GbBlogParse('https://geekbrains.ru/posts',
                         'https://geekbrains.ru/api/v2/')
    with parser:
        parser.run()
