import sqlite3
from sqlite3 import Error
from collections import namedtuple

Tag = namedtuple('Tag', ['id', 'pid', 'name', 'icon', 'iconkde'])
TagProperties = namedtuple('TagProperties', ['tagid', 'property', 'value'])
ImageTagProperty = namedtuple('ImageTagProperty', ['imageid', 'tagid', 'property', 'value'])
ImageTag = namedtuple('ImageTag', ['imageid', 'tagid'])


def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return None
