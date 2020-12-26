from scrapy.exceptions import DropItem
from .items import InstaFollowingsItem, ControlItem


class UserdbPipeline:

    def process_item(self, item, spider):
        if isinstance(item, InstaFollowingsItem):
            try:
                db_update = [item['user']] + item['following']
                graph_update = {
                    item['user']['id']: {flw['id'] for flw in item['following']}
                }
            except (TypeError, KeyError):
                raise DropItem()
            spider.user_db.update_db(db_update)
            spider.user_db.update_graph(graph_update)
            spider.user_db.save()
            print('.', end='')
        return item


class ControlPipeline:

    def process_item(self, item, spider):
        if isinstance(item, ControlItem):
            item['path'] = spider.user_db.get_handshake_path(
                spider.user_start, spider.user_finish)
            print('>', end='')
        return item
