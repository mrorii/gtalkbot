# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field

class TalkEntry(Item):
    url = Field()
    theme = Field()
    crawl_date = Field()
    post_date = Field()
    body = Field()
    user = Field()

    heart_count = Field()
    comment_count = Field()

    comments = Field()


class Comment(Item):
    body = Field()
    user = Field()
    heart_count = Field()


class User(Item):
    user_id = Field()
    name = Field()
    age = Field()


class BlogEntry(Item):
    url = Field()
    title = Field()
    theme = Field()
    crawl_date = Field()
    post_date = Field()
    body = Field()
    blogger_id = Field()

    heart_count = Field()
    comment_count = Field()
