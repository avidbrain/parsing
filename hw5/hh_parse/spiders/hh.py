from urllib.parse import urljoin, urlparse
from pathlib import Path
import scrapy
from ..loaders import HhVacancyLoader, HhAuthorLoader


class HhSpider(scrapy.Spider):
    name = 'hh'
    allowed_domains = ['hh.ru']
    start_urls = [
        'https://hh.ru/search/vacancy?schedule=remote&L_profession_id=0&area=113']

    dispatch_template = {
        'pagination': '//div[contains(@data-qa, "pager-block")]//a[contains(@data-qa, "pager-page")]',
        'vacancies': '//a[contains(@data-qa, "vacancy-serp__vacancy-title")]'
    }

    vacancy_template = {
        'title': 'normalize-space(//h1[1])',
        'salary': 'normalize-space(//div[contains(@class, "vacancy-title")]//p[contains(@class, "vacancy-salary")])',
        'description': 'normalize-space((//div[contains(@data-qa, "vacancy-description")])[1])',
        'skills': '(//div[contains(@class, "vacancy-description")])[2]//div[contains(@data-qa, "skills-element")]//text()',
        'author_link': '//a[contains(@class, "vacancy-company-name")]/@href'
    }

    author_template = {
        'title': '//meta[@name="description"]/@content',
        'website':
            '//a[contains(@data-qa, "company-site")]//@href'
            ' | //a[contains(@data-analytics-params, "to_clients_page")]//@href'
            ' | //div[@class="tmpl_hh_wrapper"]//a[1]//@href',
        'areas': '//div[normalize-space(text())="Сферы деятельности"]/following-sibling::p/text()',
        'description':
            'normalize-space((//div[contains(@class, "company-description")]'
            ' | //div[contains(@class, "tmpl_hh_about_text")]'
            ' | //div[contains(@class, "tmpl_hh_about__text")]'
            ' | //div[contains(@class, "tmpl_hh_about_content")]'
            ' | //div[contains(@class, "tmpl_hh_about__content")]'
            ' | //div[contains(@class, "tmpl_hh_subtab__content")]'
            ' | //div[contains(@class, "_page_slider_content")]'                        
            ')[1])'
    }

    def parse(self, response, **kwargs):
        for pag_page in response.xpath(self.dispatch_template['pagination']):
            yield response.follow(pag_page.attrib.get('href'),
                                  callback=self.parse)
        for vacancy in response.xpath(self.dispatch_template['vacancies']):
            yield response.follow(vacancy.attrib.get('href'),
                                  callback=self.vacancy_page_parse)

    def vacancy_page_parse(self, response, **kwargs):
        loader = HhVacancyLoader(response=response)
        loader.add_value('url', response.url)
        for name, selector in self.vacancy_template.items():
            loader.add_xpath(name, selector)
        item = loader.load_item()
        item['author_link'] = urljoin(response.url, item.get('author_link'))
        yield item
        # Переходим только на работодателя, не на департамент
        urlpath = urlparse(item.get('author_link', '')).path
        yield response.follow(urljoin(response.url, urlpath),
                              callback=self.author_page_parse)

    def author_page_parse(self, response, **kwargs):
        loader = HhAuthorLoader(response=response)
        loader.add_value('url', response.url)
        for name, selector in self.author_template.items():
            loader.add_xpath(name, selector)
        yield loader.load_item()
        author_id = Path(urlparse(response.url).path).name
        author_link = (
                '/search/vacancy?st=searchVacancy&from=employerPage' +
                f'&employer_id={author_id}'
        )
        yield response.follow(urljoin(response.url, author_link),
                              callback=self.parse)
