# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class AutoYoulaItem(scrapy.Item):
    _id = scrapy.Field()
    title = scrapy.Field()
    images = scrapy.Field()
    description = scrapy.Field()
    url = scrapy.Field()
    author = scrapy.Field()
    phone = scrapy.Field()
    specifications = scrapy.Field()
