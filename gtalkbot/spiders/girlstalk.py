# -*- coding: utf-8 -*-

import logging

from scrapy.exceptions import CloseSpider
from scrapy.http import Request, FormRequest
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from gtalkbot.common import convert_to_int_if_int
from gtalkbot.items import BlogEntry


class GirlsTalkSpider(CrawlSpider):
    name = 'girls-talk'
    allowed_domains = [
        'ameba.jp',
        'ca-girlstalk.jp',
    ]
    login_page = 'http://www.ca-girlstalk.jp/login/auth'
    custom_start_urls = [
        'http://www.ca-girlstalk.jp/blogs/articles/m_themes/100001',
    ]

    rules = [
        # Blog Entry
        # Example: http://www.ca-girlstalk.jp/blogs/articles/1495900
        Rule(LxmlLinkExtractor(allow=r'blogs/articles/\d+',
                               restrict_css='#content'),
             follow=False, callback='parse_article'),

        # Blog Theme
        # Example: http://www.ca-girlstalk.jp/blogs/articles/m_themes/500001
        Rule(LxmlLinkExtractor(allow=r'blogs/articles/m_themes/\d+'),
             follow=True),
    ]

    def start_requests(self):
        if 'GTALK_EMAIL' not in self.settings or 'GTALK_PASSWORD' not in self.settings:
            logging.error('GTALK_EMAIL and GTALK_PASSWORD settings must be set')
            raise CloseSpider()

        return [
            Request(url=self.login_page,
                    callback=self.redirect_to_login,
                    dont_filter=True),
        ]

    def redirect_to_login(self, response):
        return FormRequest.from_response(response,
                                         callback=self.login,
                                         dont_filter=True)

    def login(self, response):
        logging.info('Logging in')
        return FormRequest.from_response(
            response,
            formdata={
                'accountId': self.settings['GTALK_EMAIL'],
                'password': self.settings['GTALK_PASSWORD'],
            },
            callback=self.check_login_response,
            dont_filter=True)

    def check_login_response(self, response):
        if 'ca-girlstalk.jp' in response.url:
            logging.info('Successfully logged in. Starting crawling!')
            for url in self.custom_start_urls:
                yield self.make_requests_from_url(url)
        else:
            raise CloseSpider('Failed to login')

    def parse_article(self, response):
        entry = BlogEntry()

        entry['url'] = response.url
        entry['heading'] = response.css('h1.p-blog-article__heading::text') \
                                   .extract_first('').strip()
        entry['theme'] = response.css('header a.u-c-pink::text') \
                                 .extract_first('')
        entry['post_timestamp'] = response.css('header p.u-c-gray::text') \
                                          .extract_first('')
        entry['body'] = response.css('p.p-blog-article__body::text').extract()
        entry['blogger_id'] = response.css(
            'li.p-blog-pagination__item--fixed > a::attr(href)'
        ).extract_first('')

        counts = response.css('header ul.actions > li.actions__icon::text').extract()
        entry['heart_count'] = convert_to_int_if_int(counts[0])
        entry['comment_count'] = convert_to_int_if_int(counts[1]) if len(counts) > 1 else 0

        yield entry
