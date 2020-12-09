import re
from urllib.parse import unquote, urljoin
from base64 import b64decode
from scrapy import Selector
from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose
from .items import AutoYoulaItem


def decode_js(js_encoded):
    encoded_re = re.compile(r'decodeURIComponent\(\"(.*)\"\)')
    matched = re.findall(encoded_re, js_encoded)
    return unquote(matched[0]) if matched else None


def get_author(js_string):
    rules = [
        (r'\"sellerLink\",\"([^\"]*)\"', 'https://auto.youla.ru'),
        (r'youlaProfile.{0,12}\"youlaId\",\"([^\"]*)\"',
         'https://youla.ru/user/')
    ]
    author = None
    for regex, url_base in rules:
        author_re = re.compile(regex)
        matched = re.findall(author_re, js_string)
        if matched:
            author = urljoin(url_base, matched[0])
            break
    return author


def get_phone(js_string):
    phone_re = re.compile(r'salePointId.*\"phone\",\"([^\"]*)\"')
    matched = re.findall(phone_re, js_string)
    return b64decode(b64decode(matched[0])).decode('UTF-8') if matched else None


def get_specifications(itm):
    tag = Selector(text=itm)
    key_sel = tag.xpath('//div[contains(@class, "AdvertSpecs_label")]//text()')
    val_sel = tag.xpath('//div[contains(@class, "AdvertSpecs_data")]//text()')
    return {key_sel.get(): val_sel.get()}


def specifications_out(data: list):
    result = {}
    for itm in data:
        result.update(itm)
    return result


class AutoYoulaLoader(ItemLoader):
    default_item_class = AutoYoulaItem
    title_out = TakeFirst()
    url_out = TakeFirst()
    description_out = TakeFirst()
    author_in = MapCompose(decode_js, get_author)
    author_out = TakeFirst()
    phone_in = MapCompose(decode_js, get_phone)
    phone_out = TakeFirst()
    specifications_in = MapCompose(get_specifications)
    specifications_out = specifications_out
