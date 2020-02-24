# -*- coding: utf-8 -*-
import re
from collections import namedtuple

# Coordinates order
ORDER_LATLON = 'LATLON'
ORDER_LONLAT = 'LONLAT'

# Coordinate format constants
DMSH_COMP = 'DMSH_COMP'
HDMS_COMP = 'HDMS_COMP'
DMSH_SEP = 'DMSH_SEP'
HDMS_SEP = 'HDMS_SEP'

# Separators constants - separates latitude and longitude in pair, not pairs!
SEP_NULL = r''
SEP_SPACE = r' '
SEP_HYPHEN = r'-'
SEP_SLASH = r'/'
SEP_BACKSLASH = r'\\'
SEP_USER = ''

coord_pair = namedtuple('coord_pair', 'lat lon')

coord_formats = {DMSH_COMP: coord_pair(r'\d{6}\.\d+[NS]|\d{6}[NS]', r'\d{7}\.\d+[EW]|\d{7}[EW]'),
                 HDMS_COMP: coord_pair(r'[NS]\d{6}\.\d+|[NS]\d{6}', r'[EW]\d{7}\.\d+|[EW]\d{7}'),
                 DMSH_SEP: coord_pair(r'''\d{1,2}\W\d{2}\W\d{1,2}\.\d+\W{1,2}[NS]|\d{1,2}\W\d{1,2}\W\d{1,2}\W{1,2}[NS]''',
                                      r'''\d{1,3}\W\d{1,2}\W\d{1,2}\.\d+\W{1,2}[EW]|\d{1,3}\W\d{1,2}\W\d{1,2}\W{1,2}[EW]'''),
                 HDMS_SEP: coord_pair(r'''[NS]\d{1,2}\W\d{2}\W\d{1,2}\.\d+\W{1,2}|[NS]\d{1,2}\W\d{1,2}\W\d{1,2}\W{1,2}''',
                                      r'''[EW]\d{1,3}\W\d{1,2}\W\d{1,2}\.\d+\W{1,2}|[EW]\d{1,3}\W\d{1,2}\W\d{1,2}\{1,2}W''')}


class CoordRegexBuilder:
    def __init__(self, coord_order, coord_format, coord_sep):
        self.coord_order = coord_order
        self.coord_format = coord_format
        self.coord_sep = coord_sep
        self.coord_regex_str = self.create_regex_str()

    def create_regex_str(self):
        regex_str = ''
        lat_format = coord_formats.get(self.coord_format).lat
        sep_format = self.coord_sep
        lon_format = coord_formats.get(self.coord_format).lon

        if self.coord_order == ORDER_LATLON:
            regex_str = r'(?P<lat>' + lat_format + ')' +\
                        '(?P<sep>' + re.escape(sep_format) + ')' +\
                        '(?P<lon>' + lon_format + ')'

        elif self.coord_order == ORDER_LONLAT:
            regex_str = r'(?P<lon>' + lon_format + ')' + \
                        '(?P<sep>' + re.escape(sep_format) + ')' + \
                        '(?P<lat>' + lat_format + ')'

        return regex_str

    def get_coord_regex(self):
        return re.compile(self.coord_regex_str)


def create_coord_raw_str(raw_str):
    shape_str = ''
    for line in raw_str:
        shape_str += line.strip('\n')
    return shape_str


class CoordinateExtractor:
    def __init__(self, raw_string, coord_pair_regex: CoordRegexBuilder):
        self.raw_string = raw_string
        self.coord_pair_regex = coord_pair_regex

    def get_coord_pair_list(self):
        coord_pair_list = re.findall(self.coord_pair_regex.get_coord_regex(), self.raw_string)
        return coord_pair_list
