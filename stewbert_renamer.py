#!/usr/bin/python

"""
Copyright 2010 Evan Grim

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See <http://www.gnu.org/licenses/> for a copy of the GNU General Public License

"""

import sys
import os
import re
import urllib
import datetime
import HTMLParser as html

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# Change the following to point the script at the appropriate directory
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

TORRENT_DIRECTORY_TO_SEARCH = '/srv/Torrents'
"""Directory within which files will be searched and renamed as appropriate"""

SIMULATE = False
"""If set to "True" the script will only print proposed file renames"""

LINK_NOT_RENAME = True
"""If set to "True" the script will create a link instead of renaming"""
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

SCRIPT_VERSION = "1.0"

TV_RAGE_INFO_TABLE_CLASS = 'b'
TV_RAGE_INFO_TABLE_ROW_ID = 'brow'

TV_RAGE_INFO_TABLE_ROW_NUM_FIELDS = 15

FILE_EPISODE_NAMING_STYLE_1 = re.compile(r'S\d+\.?E\d+')
FILE_EPISODE_NAMING_STYLE_2 = re.compile(r'\d+x\d+')

FILE_EPISODE_DATE_STYLE = re.compile(r'(\d{4})\.?(\d{2})\.?(\d{2})')

        
TV_RAGE_INFO_PAGE_MAP = {}
"""
This structure maps file name strings as keys to the URL for ShowRSS info pages.

The keys to this mapping are strings which, when found within the filenames in
the directory to be scanned, will trigger a lookup for replacement of the date
with the correct episode number using the ShowRSS info page.  The key strings 
must be all lower case and unique for each show.

"""

TV_RAGE_INFO_PAGE_MAP['colbert'] = 'http://www.tvrage.com/The_Colbert_Report/episode_list/all'
TV_RAGE_INFO_PAGE_MAP['daily'] = 'http://www.tvrage.com/The_Daily_Show/episode_list/all'


show_date_maps = {}
"""
This structure will be updated with date maps (mapping dates to episode 
designations) as they are retrieved (and only as needed).

"""

TV_RAGE_MONTH_STR_MAP = {'Jan': 1,
                         'Feb': 2,
                         'Mar': 3,
                         'Apr': 4,
                         'May': 5,
                         'Jun': 6,
                         'Jul': 7,
                         'Aug': 8,
                         'Sep': 9,
                         'Oct': 10,
                         'Nov': 11,
                         'Dec': 12
                         }

def get_episode_date_map(tv_rage_info_page):
    info_page_fetcher = TvRageShowInfoFetcher(tv_rage_info_page)
    return info_page_fetcher.get_info_map()
    
    
class TvRageShowInfoFetcher(html.HTMLParser):
    def __init__(self, tv_rage_info_page):
        self.info_table_depth = 0
        self.info_row_fields_filling = False
        self.info_row_fields = []
        self.info_table_row_text = ''
        self.info_map = {}
        self.current_date = None
        
        # Get HTML and fix a couple of things in it the parser doesn't like
        info_page_content = urllib.urlopen(tv_rage_info_page).read()
        info_page_content = info_page_content.replace(r"</scr'+'ipt>","")
        info_page_content = info_page_content.replace(r"</scr' + 'ipt>","")
        
        html.HTMLParser.__init__(self)
        self.feed(info_page_content)
        
    def get_info_map(self):
        return self.info_map
    
    def process_table_row_fields(self):
        (
        _,
        episode_number,
        _,
        episode_designation,
        _,
        _,
        episode_day,
        _,
        _,
        episode_month_str,
        _,
        _,
        episode_year,
        _,
        episode_guest) = self.info_row_fields
        
        episode_month = TV_RAGE_MONTH_STR_MAP[episode_month_str]
        
        episode_date = datetime.date(int(episode_year),
                                     episode_month,
                                     int(episode_day))
        
        self.info_map[episode_date] = episode_designation
            
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            if self.info_table_depth is not 0:
                self.info_table_depth += 1
            else:
                for key,value in attrs:
                    if key == 'class' and value == TV_RAGE_INFO_TABLE_CLASS:
                        self.info_table_depth = 1
                        
        if tag == 'tr':
            for key,value in attrs:
                if key == 'id' and value == TV_RAGE_INFO_TABLE_ROW_ID:
                    self.info_row_fields = []
                    self.info_row_fields_filling = True
                        
                        
    def handle_endtag(self, tag):
        if tag == 'table':
            if self.info_table_depth is not 0:
                self.info_table_depth -= 1
                
    def handle_data(self, data):
        if self.info_table_depth is not 0:
            if self.info_row_fields_filling:
                self.info_row_fields.append(data)

                if len(self.info_row_fields) == TV_RAGE_INFO_TABLE_ROW_NUM_FIELDS:
                    self.info_row_fields_filling = False
                    try:
                        self.process_table_row_fields()
                    except Exception:
                        # skip this row (field processing not needed on all rows)
                        pass
            

def lookup_and_rename(filename):
    date_match = FILE_EPISODE_DATE_STYLE.search(filename)
    if date_match is not None:
        year, month, day = map(int, date_match.groups())
        date = datetime.date(year, month, day)
        if show_file_name_key not in show_date_maps:
            show_date_maps[show_file_name_key] = \
                get_episode_date_map(show_info_page)
        
        show_date_map = show_date_maps[show_file_name_key]
        episode_designation = show_date_map[date]
        new_file_name = FILE_EPISODE_DATE_STYLE.sub(episode_designation, 
                                                    filename)
        
        if SIMULATE:
            print "%s -> %s" % (os.path.join(dirpath, filename),
                                os.path.join(dirpath, new_file_name))
        else:
            if LINK_NOT_RENAME:
                operation = os.link
            else:
                operation = os.rename
                
            operation(os.path.join(dirpath, filename), 
                      os.path.join(dirpath, new_file_name))


def is_name_missing_episode_designator(episode_name):
    return FILE_EPISODE_NAMING_STYLE_1.search(filename) is None and \
           FILE_EPISODE_NAMING_STYLE_2.search(filename) is None
    

if __name__ == '__main__':
    for dirpath, dirnames, filenames in os.walk(TORRENT_DIRECTORY_TO_SEARCH):
        for filename in filenames:
            for show_file_name_key, show_info_page in TV_RAGE_INFO_PAGE_MAP.iteritems():
                if show_file_name_key in filename.lower():
                    if is_name_missing_episode_designator(filename):
                        try:
                            lookup_and_rename(filename)
                        except Exception:
                            sys.stderr.write("Lookup and rename failed for '%s'\n" % filename)
                            pass
