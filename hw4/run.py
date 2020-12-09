import os
import dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from gb_parse.spiders.autoyoula import AutoyoulaSpider

dotenv.load_dotenv('.env')

if __name__ == '__main__':
    settings = get_project_settings()
    settings['MONGO_URI'] = os.getenv('MONGO_URI')
    settings['MONGO_DATABASE'] = os.getenv('MONGO_DATABASE')
    crawl_proc = CrawlerProcess(settings)
    crawl_proc.crawl(AutoyoulaSpider)
    crawl_proc.start()
