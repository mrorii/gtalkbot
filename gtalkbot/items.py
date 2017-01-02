# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class BlogEntry(Item):
    url = Field()
    heading = Field()
    theme = Field()
    post_timestamp = Field()
    body = Field()
    blogger_id = Field()

    heart_count = Field()
    comment_count = Field()
