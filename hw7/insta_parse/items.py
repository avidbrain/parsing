import scrapy


class InstaFollowingItem(scrapy.Item):
    date_parse = scrapy.Field()
    user = scrapy.Field()
    following = scrapy.Field()
