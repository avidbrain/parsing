import datetime as dt
import json
import scrapy
from ..items import InstaFollowingItem


def get_user_data(user_data):
    return {k: user_data.get(k) for k in ('id', 'username', 'full_name')}


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    graphql_url = 'https://www.instagram.com/graphql/query/'
    query_hash = {
        'followers': 'c76146de99bb02f6415203be841dd25a',
        'following': 'd04b0a864b4b54837c0d870b0e77e076'
    }
    allowed_domains = ['www.instagram.com']
    start_urls = ['https://www.instagram.com/']

    def __init__(self, login, password, user_list, *args, **kwargs):
        self.login = login
        self.password = password
        self.user_list = user_list
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
                for usr in self.user_list:
                    yield response.follow(f'/{usr}/', callback=self.user_parse)

    def js_data_extract(self, response):
        xpath = '//script[contains(text(), "window._sharedData = ")]/text()'
        script = response.xpath(xpath).get()
        return json.loads(script.replace("window._sharedData = ", '')[:-1])

    def user_parse(self, response, **kwargs):
        data = self.js_data_extract(response)
        user_node = data['entry_data']['ProfilePage'][0]['graphql']['user']
        user_data = get_user_data(user_node)
        yield from self.follow_pagination('followers', response, user_data)
        yield from self.follow_pagination('following', response, user_data)

    def follow_parse(self, response, **kwargs):
        date_parse = dt.datetime.utcnow()
        section = kwargs.get('section')
        user_data = kwargs.get('anchor_user')
        edge_follow_sfx = 'ed_by' if section == 'followers' else ''
        data = response.json()['data']['user']['edge_follow' + edge_follow_sfx]
        for edge in data['edges']:
            item = InstaFollowingItem()
            item['date_parse'] = date_parse
            if section == 'followers':
                item['user'] = get_user_data(edge['node'])
                item['following'] = user_data
            else:
                item['user'] = user_data
                item['following'] = get_user_data(edge['node'])
            yield item
        # PAGINATION
        page_node = data['page_info']
        if page_node.get('has_next_page'):
            yield from self.follow_pagination(
                section, response, user_data,
                end_cursor=page_node.get('end_cursor'))

    def follow_pagination(self, section, response, user_data, end_cursor=None):
        q_hash = self.query_hash[section]
        variables = {
            'id': user_data.get('id'),
            'include_reel': True,
            'fetch_mutual': False,
            'first': 24
        }
        if end_cursor:
            variables['after'] = end_cursor
        var_str = json.dumps(variables, separators=(',', ':'))
        following_url = (
                f"{self.graphql_url}?query_hash={q_hash}" +
                f"&variables={var_str}"
        )
        yield response.follow(
            url=following_url,
            callback=self.follow_parse,
            cb_kwargs={'section': section, 'anchor_user': user_data}
        )
