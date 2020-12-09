import scrapy
from ..loaders import AutoYoulaLoader


class AutoyoulaSpider(scrapy.Spider):
    name = 'autoyoula'
    allowed_domains = ['auto.youla.ru']
    start_urls = ['https://auto.youla.ru/']

    dispatch_template = {
        'brands': '//div[contains(@class, "ColumnItemList_container")]/div[contains(@class, "ColumnItemList")]//a[contains(@data-target, "brand")]',
        'pagination': '//div[contains(@class, "Paginator_block")]/a[contains(@class, "Paginator_button")]',
        'ads': '//article[contains(@class, "SerpSnippet_snippet")]//a[contains(@class, "SerpSnippet_name")]'
    }

    itm_template = {
        'title': '//div[@data-target="advert-title"]/text()',
        'images': '//figure[contains(@class, "PhotoGallery_photo")]//img/@src',
        'description': '//div[contains(@class, "AdvertCard_descriptionInner")]//text()',
        'author': '//script[contains(text(), "window.transitState =")]/text()',
        'phone': '//script[contains(text(), "window.transitState =")]/text()',
        'specifications': '//div[contains(@class, "AdvertCard_specs")]/div/div[contains(@class, "AdvertSpecs_row")]',
    }

    def parse(self, response, **kwargs):
        for brand in response.xpath(self.dispatch_template['brands']):
            yield response.follow(brand.attrib.get('href'),
                                  callback=self.brand_page_parse)

    def brand_page_parse(self, response):
        for pag_page in response.xpath(self.dispatch_template['pagination']):
            yield response.follow(pag_page.attrib.get('href'),
                                  callback=self.brand_page_parse)

        for ads_page in response.xpath(self.dispatch_template['ads']):
            yield response.follow(ads_page.attrib.get('href'),
                                  callback=self.ads_parse)

    def ads_parse(self, response):
        loader = AutoYoulaLoader(response=response)
        loader.add_value('url', response.url)
        for name, selector in self.itm_template.items():
            loader.add_xpath(name, selector)

        yield loader.load_item()
