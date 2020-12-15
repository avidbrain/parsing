import datetime as dt
import json
import scrapy
from ..items import InstaItem


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    next_page_url = 'https://www.instagram.com/graphql/query/?query_hash=9b498c08113f1e09617a1703c22b2f32&variables='
    allowed_domains = ['www.instagram.com']
    start_urls = ['https://www.instagram.com/']

    def __init__(self, login, password, tag_list, *args, **kwargs):
        self.login = login
        self.password = password
        self.tag_list = tag_list
        super().__init__(*args, **kwargs)

    def parse(self, response, **kwargs):
        try:
            js_data = self.js_data_extract(response)
            yield scrapy.FormRequest(
                self.login_url,
                method='POST',
                callback=self.parse,
                formdata={
                    'username': self.login,
                    'enc_password': self.password,
                },
                headers={'X-CSRFToken': js_data['config']['csrf_token']}
            )
        except AttributeError:
            if response.json().get('authenticated'):
                for tag in self.tag_list:
                    yield response.follow(f'/explore/tags/{tag}',
                                          callback=self.tag_parse)

    def js_data_extract(self, response):
        xpath = '//script[contains(text(), "window._sharedData = ")]/text()'
        script = response.xpath(xpath).get()
        return json.loads(script.replace("window._sharedData = ", '')[:-1])

    def tag_parse(self, response, **kwargs):
        try:
            tag_node = response.json()['data']['hashtag']
        except json.JSONDecodeError:
            data = self.js_data_extract(response)
            tag_node = data['entry_data']['TagPage'][0]['graphql']['hashtag']
        tag_name = tag_node.get('name')
        page_node = tag_node['edge_hashtag_to_media']['page_info']
        edges_node = tag_node['edge_hashtag_to_media']['edges']
        # TAG PAGE
        item = InstaItem()
        item['date_parse'] = dt.datetime.utcnow()
        item['data'] = {
            'id': tag_node.get('id'),
            'name': tag_name,
            'profile_pic_url': tag_node.get('profile_pic_url')
        }
        item['image'] = tag_node.get('profile_pic_url')
        yield item
        # POSTS
        for edge in edges_node:
            item = InstaItem()
            item['date_parse'] = dt.datetime.utcnow()
            item['data'] = edge.get('node')
            item['image'] = edge.get('node').get('display_url')
            yield item
        # PAGINATION
        if page_node.get('has_next_page'):
            next_page_vars = {
                "tag_name": tag_name,
                "first": 100,
                "after": page_node.get('end_cursor')
            }
            variables = json.dumps(next_page_vars, separators=(',', ':'))
            yield response.follow(
                url=self.next_page_url + variables,
                callback=self.tag_parse
            )
