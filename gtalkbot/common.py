# -*- coding: utf-8 -*-

from datetime import tzinfo, timedelta
import string
import json
import unicodedata
from urlparse import urlparse

from scrapy import Item


class SimpleUtc(tzinfo):
    def tzname(self):
        return "UTC"

    def utcoffset(self, dt):
        return timedelta(0)


def is_url(text):
    parts = urlparse(text)
    return bool(parts.scheme and parts.netloc)


PUNCTUATION = set(string.punctuation)


def valid_sentence(sentence):
    s = u''.join(ch for ch in sentence if ch not in PUNCTUATION)
    s = u''.join(ch for ch in s if not unicodedata.category(ch).startswith('P'))
    return bool(s.strip())


def contains_needles(haystack, needles):
    for needle in needles:
        if needle in haystack:
            return True
    return False


class PrettyFloat(float):
    '''
    Used to format floats in json
    http://stackoverflow.com/a/1733105
    '''
    def __repr__(self):
        return '%.4g' % self


def convert_to_utf8(json_obj):
    '''
    Converts simple json python representations to utf-8 recursively.
    Refer to:
    - http://stackoverflow.com/a/13105359
    - http://stackoverflow.com/q/18337407
    '''
    if isinstance(json_obj, Item):
        return convert_to_utf8(dict(json_obj))
    if isinstance(json_obj, dict):
        return dict((convert_to_utf8(key), convert_to_utf8(value))
                    for key, value in json_obj.iteritems())
    elif isinstance(json_obj, list):
        return [convert_to_utf8(element) for element in json_obj]
    elif isinstance(json_obj, unicode):
        return json_obj.encode('utf-8')
    elif isinstance(json_obj, float):
        return PrettyFloat(json_obj)
    else:
        return json_obj


def json_dumps_utf8(json_obj):
    encoder = json.JSONEncoder(ensure_ascii=False, separators=(',', ':'))
    return encoder.encode(convert_to_utf8(json_obj))


def convert_to_int_if_int(value):
    if is_int(value):
        return int(value)
    else:
        return value


def is_int(value):
    try:
        int(value)
        return True
    except:
        return False
