import scrapy


class InstaFollowingsItem(scrapy.Item):
    user = scrapy.Field()
    following = scrapy.Field()


class ControlItem(scrapy.Item):
    user = scrapy.Field()
    path = scrapy.Field()
