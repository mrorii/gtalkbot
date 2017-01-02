# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import json
import sys

from scrapy import signals
from scrapy.exporters import BaseItemExporter
from scrapy.xlib.pydispatch import dispatcher

from gtalkbot.common import convert_to_utf8


def item_type(item):
    '''
    Converts an `Item` to its string representation.
    Example: ReviewItem => review
    '''
    return type(item).__name__.lower()


class UnicodeJsonLinesItemExporter(BaseItemExporter):
    '''
    Prints out JSON in utf8 symbols, not their code points.
    Refer to https://groups.google.com/forum/#!topic/scrapy-users/rJcfSFVZ3O4
    '''
    def __init__(self, file, **kwargs):
        self._configure(kwargs)
        self.file = file
        self.encoder = json.JSONEncoder(ensure_ascii=False,
                                        separators=(',', ':'),
                                        **kwargs)

    def export_item(self, item):
        itemdict = dict(self._get_serialized_fields(item))
        self.file.write(self.encoder.encode(convert_to_utf8(itemdict)) + '\n')


class StdoutUnicodeJsonLinesItemPipeline(object):
    def __init__(self):
        self.exporter = UnicodeJsonLinesItemExporter(sys.stdout)

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item


# Shamelessly copied from http://stackoverflow.com/q/12230332
class MultiJsonLinesItemPipeline(object):
    file_name = 'article.json'

    def __init__(self):
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    def spider_opened(self, spider):
        self.file = open(self.file_name, 'w+b')
        self.exporter = UnicodeJsonLinesItemExporter(self.file)
        self.exporter.start_exporting()

    def spider_closed(self, spider):
        self.exporter.finish_exporting()
        self.file.close()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item
