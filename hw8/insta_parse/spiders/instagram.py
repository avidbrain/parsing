import json
import scrapy
from scrapy import signals
from scrapy.exceptions import CloseSpider
from ..items import InstaFollowingsItem, ControlItem


def get_user_data(user_data):
    result = {k: user_data.get(k) for k in ('id', 'username', 'full_name')}
    try:
        result['id'] = int(result.get('id'))
    except ValueError:
        pass
    return result


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

    def __init__(self, login, password, user_start, user_finish, user_db,
                 *args, **kwargs):
        self.login = login
        self.password = password
        self.user_start = user_start
        self.user_finish = user_finish
        self.user_db = user_db
        self.must_close = False
        self.auth_response = None
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
                self.auth_response = response
                yield from self._do_next_user()

    def _do_next_user(self):
        next_username = self.user_db.get_next_username(
            [self.user_start, self.user_finish])
        if not next_username:
            self.must_close = True
        else:
            yield self.auth_response.follow(f'/{next_username}/',
                                            callback=self.user_parse)

    def js_data_extract(self, response):
        xpath = '//script[contains(text(), "window._sharedData = ")]/text()'
        script = response.xpath(xpath).get()
        return json.loads(script.replace("window._sharedData = ", '')[:-1])

    def user_parse(self, response, **kwargs):
        try:
            data = self.js_data_extract(response)
            user_node = data['entry_data']['ProfilePage'][0]['graphql']['user']
            user_data = get_user_data(user_node)
            yield from self.follow_pagination('following', response, user_data)
        except (TypeError, KeyError, json.JSONDecodeError):
            self.must_close = True
            raise CloseSpider('Response structure error.')

    def follow_parse(self, response, **kwargs):
        section = kwargs.get('section')
        user_data = kwargs.get('anchor_user')
        if section == 'following':
            try:
                data = response.json()['data']['user']['edge_follow']
                following = [get_user_data(edge['node'])
                             for edge in data['edges']]
                item = InstaFollowingsItem()
                item['user'] = user_data
                item['following'] = following
                yield item
                # PAGINATION
                page_node = data['page_info']
                if page_node.get('has_next_page'):
                    yield from self.follow_pagination(
                        section, response, user_data,
                        end_cursor=page_node.get('end_cursor'))
                else:
                    ctrl_item = ControlItem()
                    ctrl_item['user'] = user_data
                    yield ctrl_item
                    if not self.must_close:
                        yield from self._do_next_user()
            except (TypeError, KeyError, json.JSONDecodeError):
                self.must_close = True
                raise CloseSpider('Response structure error.')

    def follow_pagination(self, section, response, user_data, end_cursor=None):
        q_hash = self.query_hash[section]
        variables = {
            'id': user_data.get('id'),
            'include_reel': True,
            'fetch_mutual': False,
            'first': 100
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

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(InstagramSpider, cls).from_crawler(
            crawler, *args, **kwargs)
        crawler.signals.connect(spider.item_scraped,
                                signal=signals.item_scraped)
        return spider

    def item_scraped(self, item):
        if isinstance(item, ControlItem) and item['path']:
            self.must_close = self.must_close or True

