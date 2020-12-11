import os
import dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from hh_parse.spiders.hh import HhSpider

dotenv.load_dotenv('.env')

if __name__ == '__main__':
    settings = get_project_settings()
    settings['MONGO_URI'] = os.getenv('MONGO_URI')
    settings['MONGO_DATABASE'] = os.getenv('MONGO_DATABASE')
    crawl_proc = CrawlerProcess(settings)
    crawl_proc.crawl(HhSpider)
    crawl_proc.start()
