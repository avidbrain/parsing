from urllib.parse import urlparse
from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose
from .items import HhVacancyItem, HhAuthorItem


class HhVacancyLoader(ItemLoader):
    default_item_class = HhVacancyItem
    url_out = TakeFirst()
    title_out = TakeFirst()
    salary_out = TakeFirst()
    description_out = TakeFirst()
    author_link_out = TakeFirst()


class HhAuthorLoader(ItemLoader):
    default_item_class = HhAuthorItem
    url_out = TakeFirst()
    title_in = MapCompose(lambda x: (
        x.rsplit('.', 1)[0]
        .split('Работа в ''компании')[-1]
        .strip()
    ))
    title_out = TakeFirst()
    website_in = MapCompose(lambda x: x if x and urlparse(x).netloc else None)
    website_out = TakeFirst()
    areas_in = MapCompose(lambda x: x.split(', '))
    description_out = TakeFirst()
