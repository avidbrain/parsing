from itemadapter import ItemAdapter
from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
import pymongo


class InstaImagePipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        yield Request(item.get('image'))

    def item_completed(self, results, item, info):
        if results and results[0][0]:
            item['image'] = results[0][1]
        return item


class MongoPipeline:
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = None
        self.db = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        collection = spider.name
        self.db[collection].insert_one(ItemAdapter(item).asdict())
        return item

