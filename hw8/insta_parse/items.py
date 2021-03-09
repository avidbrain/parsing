import scrapy


class InstaFollowingsItem(scrapy.Item):
    user = scrapy.Field()
    following = scrapy.Field()


class ControlItem(scrapy.Item):
    user = scrapy.Field()
    flw_count = scrapy.Field()
    path = scrapy.Field()
