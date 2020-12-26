BOT_NAME = 'insta_parse'
LOG_ENABLE = True
LOG_LEVEL = 'DEBUG'
#LOG_FILE = 'scrapy.log'
SPIDER_MODULES = ['insta_parse.spiders']
NEWSPIDER_MODULE = 'insta_parse.spiders'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0'
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 64
DOWNLOAD_DELAY = 3
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 16
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
}
ITEM_PIPELINES = {
    'insta_parse.pipelines.UserdbPipeline': 300,
    'insta_parse.pipelines.ControlPipeline': 500,
}
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3
AUTOTHROTTLE_MAX_DELAY = 15
AUTOTHROTTLE_DEBUG = False
