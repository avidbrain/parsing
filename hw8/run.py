import os
import dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from insta_parse.spiders.instagram import InstagramSpider
from instausers import InstaUsers

dotenv.load_dotenv('.env')

user_pair = ('pavelvolyaofficial', 'lexfridman')

if __name__ == '__main__':
    with InstaUsers(os.getenv('INSTAUSERS_PKL')) as user_db:
        user_db.load()
        user_start, user_finish = user_pair
        path = user_db.get_handshake_path(user_start, user_finish)
        if not path:  # do the crawl
            settings = get_project_settings()
            crawl_proc = CrawlerProcess(settings)
            crawl_proc.crawl(InstagramSpider,
                             login=os.getenv('LOGIN'),
                             password=os.getenv('PASSWORD'),
                             user_start=user_start,
                             user_finish=user_finish,
                             user_db=user_db)
            crawl_proc.start()
            path = user_db.get_handshake_path(user_start, user_finish)
        print('')
        if path:
            print(" <-> ".join(map(user_db.get_user_info, path)))
        else:
            print(f"No path from {user_start} to {user_finish}.")
