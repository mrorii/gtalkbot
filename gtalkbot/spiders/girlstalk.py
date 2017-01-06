# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import re

from scrapy.exceptions import CloseSpider
from scrapy.http import Request, FormRequest
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from gtalkbot.common import convert_to_int_if_int, SimpleUtc
from gtalkbot.items import BlogEntry, TalkEntry, User, Comment


class GirlsTalkTalkSpider(CrawlSpider):
    name = 'gt-talk'
    allowed_domains = [
        'ca-girlstalk.jp',
    ]
    age_verification_page = 'http://www.ca-girlstalk.jp/talk/answer_u18/1'
    custom_start_urls = [
        'http://www.ca-girlstalk.jp/new/10056',
    ]

    rules = [
        # Talk Entry
        # Example: http://www.ca-girlstalk.jp/talk/detail/815652
        Rule(LxmlLinkExtractor(allow=r'talk/detail/\d+',
                               restrict_css='#content'),
             follow=False, callback='parse_talk'),

        # Talk Theme
        # Example: http://www.ca-girlstalk.jp/new/100116
        Rule(LxmlLinkExtractor(allow=r'new/\d+'),
             follow=True),
    ]

    def start_requests(self):
        return [
            Request(url=self.age_verification_page,
                    callback=self.after_age_verification,
                    dont_filter=True,
                    errback=self.after_age_verification),  # returns 404
        ]

    def after_age_verification(self, response):
        for url in self.custom_start_urls:
            yield self.make_requests_from_url(url)

    def parse_talk(self, response):
        entry = TalkEntry()
        entry['url'] = response.url
        entry['theme'] = response.css('p.heading-a::text') \
                                 .extract_first('')

        entry['crawl_date'] = datetime.utcnow().replace(tzinfo=SimpleUtc()).isoformat()
        date = response.css('article p.grid__cell span.u-c-gray::text') \
                       .extract_first('') \
                       .split(u'・')
        if date and len(date) > 1:
            entry['post_date'] = date[1]

        entry['body'] = response.css('article > div > p:first-child::text') \
                                .extract()

        a_tag = response.css('article > div > div > p:nth-child(1) > a')
        if a_tag:
            entry['user'] = self.scrape_user(a_tag[0])

        entry['heart_count'] = convert_to_int_if_int(
            response.css('article p.js-ui-like span.js-ui-like__cnt::text')
                    .extract_first('')
        )
        entry['comment_count'] = convert_to_int_if_int(
            response.css('article > div > div:nth-child(3) > p > span > b::text')
                    .extract_first('')
        )

        entry['comments'] = self.scrape_comments(response)

        pagination_tag = response.css('ul.pagination li a.pagination__next')
        if pagination_tag:
            next_page_url = response.url + pagination_tag.css('::attr(href)') \
                                                         .extract_first('')
            yield Request(next_page_url, meta={'entry': entry},
                          callback=self.parse_next_page_comments)
        else:
            yield entry

    def parse_next_page_comments(self, response):
        entry = response.request.meta['entry']
        comments = self.scrape_comments(response)
        entry['comments'].extend(comments)

        pagination_tag = response.css('ul.pagination li a.pagination__next')
        if pagination_tag:
            next_page_url = (response.url[:response.url.find('?')] +
                             pagination_tag.css('::attr(href)')
                                           .extract_first(''))
            yield Request(next_page_url, meta={'entry': entry},
                          callback=self.parse_next_page_comments)
        else:
            yield entry

    def scrape_user(self, a_tag):
        user = User()
        user['user_id'] = a_tag.css('::attr(href)').extract_first('')

        text = a_tag.css('::text').extract_first('')
        ptn = re.compile(ur'(.+?)\((\d+)歳\)')
        match = ptn.search(text)
        if match:
            user['name'] = match.groups()[0]
            user['age'] = convert_to_int_if_int(match.groups()[1])

        return user

    def scrape_comments(self, response):
        comments = []
        prev_comment = None
        for li in response.css('.js-ui-ccomment li.list-a__item'):
            comment = Comment()
            comment['body'] = li.css('p:nth-child(2)::text').extract()
            a_tag = li.css('p:nth-child(1) > a')
            if a_tag:
                comment['user'] = self.scrape_user(a_tag[0])
            comment['heart_count'] = convert_to_int_if_int(
                li.css('ul.js-ui-like span.js-ui-like__cnt::text').extract_first('')
            )
            comment['replies'] = []

            is_child = bool(li.css('::attr(data-relation)'))
            if is_child and prev_comment:
                prev_comment['replies'].append(comment)
            else:
                comments.append(comment)
                prev_comment = comment

        return comments


class GirlsTalkBlogSpider(CrawlSpider):
    name = 'gt-blog'
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
             follow=False, callback='parse_blog'),

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

    def parse_blog(self, response):
        entry = BlogEntry()

        entry['url'] = response.url
        entry['title'] = response.css('h1.p-blog-article__heading::text') \
                                 .extract_first('').strip()
        entry['theme'] = response.css('header a.u-c-pink::text') \
                                 .extract_first('')
        entry['post_date'] = response.css('header p.u-c-gray::text') \
                                     .extract_first('')
        entry['body'] = response.css('p.p-blog-article__body::text').extract()
        entry['blogger_id'] = response.css(
            'li.p-blog-pagination__item--fixed > a::attr(href)'
        ).extract_first('')

        counts = response.css('header ul.actions > li.actions__icon::text').extract()
        entry['heart_count'] = convert_to_int_if_int(counts[0])
        entry['comment_count'] = convert_to_int_if_int(counts[1]) \
            if len(counts) > 1 else 0

        yield entry
