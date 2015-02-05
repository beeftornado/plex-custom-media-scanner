#!/usr/bin/env python

#     Copyright (C) 2013  Casey Duquette
# 
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
# 
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

"""
Custom scanner plugin for Plex Media Server for transferred Tivo recordings.
"""

import re, os, os.path
import sys

# I needed some plex libraries, you may need to adjust your plex install location accordingly
sys.path.append("/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Scanners/Series")
sys.path.append("/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins/Scanners.bundle/Contents/Resources/Common/")
import Media, VideoFiles, Stack, Utils
from mp4file import mp4file, atomsearch

__author__ = "Casey Duquette"
__copyright__ = "Copyright 2013"
__credits__ = ["Casey Duquette"]

__license__ = "GPLv2"
__version__ = "1.0"
__maintainer__ = "Casey Duquette"
__email__ = ""


episode_regexps = [
    '^Ep[^0-9a-z](?P<season>[0-9]{1,2})(?P<ep>[0-9]{2})[_\s](?P<title>[\w\s,.\-:;\'\"]+?)\s\(Rec.*$',       # Ep#112_Bad Wolf (Rec 08_19_2012).mp4
    '^(?P<season>)(?P<ep>)(?P<title>.+?)\s\(Rec.*$',	                                                    # Blink (Rec 09_13_2012).mp4
    '^Ep[^0-9a-z](?P<season>[0-9]{1,2})(?P<ep>[0-9]{2})[_\s](?P<title>[\w\s,.\-:;\'\"]+)$',                 # Ep#112 Bad Wolf.mp4
    '(?P<show>.*?)([^0-9]|^)(?P<season>[0-9]{1,2})[Xx](?P<ep>[0-9]+)(-[0-9]+[Xx](?P<secondEp>[0-9]+))?',    # 3x03
    '^S(?P<season>[0-9]{1,2})[Xx]?[eE]?(?P<ep>[0-9]{2})',                                                   # S1E01
  ]

date_regexps = [
    '(?P<year>[0-9]{4})[^0-9a-zA-Z]+(?P<month>[0-9]{2})[^0-9a-zA-Z]+(?P<day>[0-9]{2})([^0-9]|$)',           # 2009-02-10
    '(?P<month>[0-9]{2})[^0-9a-zA-Z]+(?P<day>[0-9]{2})[^0-9a-zA-Z(]+(?P<year>[0-9]{4})([^0-9a-zA-Z]|$)',    # 02-10-2009
  ]

standalone_episode_regexs = [
  '(.*?)( \(([0-9]+)\))? - ([0-9]+)+x([0-9]+)(-[0-9]+[Xx]([0-9]+))?( - (.*))?',         # Newzbin style, no _UNPACK_
  '(.*?)( \(([0-9]+)\))?[Ss]([0-9]+)+[Ee]([0-9]+)(-[0-9]+[Xx]([0-9]+))?( - (.*))?'      # standard s00e00
  ]
  
season_regex = '.*?(?P<season>[0-9]+)$' # folder for a season

just_episode_regexs = [
    '(?P<ep>[0-9]{1,3})[\. -_]of[\. -_]+[0-9]{1,3}',       # 01 of 08
    '^(?P<ep>[0-9]{1,3})[^0-9]',                           # 01 - Foo
    'e[a-z]*[ \.\-_]*(?P<ep>[0-9]{2,3})([^0-9c-uw-z%]|$)', # Blah Blah ep234
    '.*?[ \.\-_](?P<ep>[0-9]{2,3})[^0-9c-uw-z%]+',         # Flah - 04 - Blah
    '.*?[ \.\-_](?P<ep>[0-9]{2,3})$',                      # Flah - 04
    '.*?[^0-9x](?P<ep>[0-9]{2,3})$'                        # Flah707
  ]

ends_with_number = '.*([0-9]{1,2})$'

ends_with_episode = ['[ ]*[0-9]{1,2}x[0-9]{1,3}$', '[ ]*S[0-9]+E[0-9]+$']

# Look for episodes.
def Scan(path, files, mediaList, subdirs):
  
  # Scan for video files.
  VideoFiles.Scan(path, files, mediaList, subdirs)
  
  # Take top two as show/season, but require at least the top one.
  paths = Utils.SplitPath(path)
  
  if len(paths) > 0 and len(paths[0]) > 0:
    done = False
        
    if done == False:

      # Not a perfect standalone match, so get information from directories. (e.g. "Lost/Season 1/s0101.mkv")
      season = None
      seasonNumber = None

      (show, year) = VideoFiles.CleanName(paths[0])
      
      for i in files:
        done = False
        file = os.path.basename(i)
        (file, ext) = os.path.splitext(file)
        
        # See if there's a pytivo metadata file to peek at
        meta = dict()
        metadata_filename = '{0}.txt'.format(i.replace('_LQ', ''))
        if os.path.isfile(metadata_filename):
          with open(metadata_filename, 'r') as f:
            for line in f:
              line = line.strip()
              if line and len(line):
                line_a = line.split(' : ')
                if len(line_a) > 1:
                  key, value = line.split(' : ')
                  meta[key] = value

        #print "pytivo metadata, ", meta

        # Skip tv shows based on pytivo metadata file and backup to filename if not present
        is_movie = False
        if 'isEpisode' in meta:
          if meta['isEpisode'] == 'false':
            is_movie = True
        elif file.strip().startswith('(Rec'):
          is_movie = True

        # Skip tivo recorded movies
        if is_movie == True:
          print "File {0} is determined to be a movie, skipping".format(file)
          continue

        # Test for matching tivo server files
        found = False
        for rx in episode_regexps:
          match = re.search(rx, file, re.IGNORECASE)
          if match:
            season = int(match.group('season')) if match.group('season') and match.group('season') != '' else None
            episode = int(match.group('ep')) if match.group('ep') and match.group('ep') != '' else None
            try:
              title = match.group('title') if match.group('title') else None
            except IndexError:
              title = None
            
            if 'episodeTitle' in meta:
              title = meta['episodeTitle']
            if 'seriesTitle' in meta:
              show = meta['seriesTitle']
            originalAirDate = None
            if 'originalAirDate' in meta:
              originalAirDate = meta['originalAirDate'].split('T')[0]
            if season is None and episode is None and title is None:
              continue
            if season is None and originalAirDate:
              season = int(originalAirDate.split('-')[0])
            found = True
            tv_show = Media.Episode(show, season, episode, title, None)
            if originalAirDate is not None:
              tv_show.released_at = originalAirDate
            tv_show.parts.append(i)
            mediaList.append(tv_show)
            break
        if found == True:
          continue
      
        if done == False:
          print "Got nothing for:", file
          
  # Stack the results.
  Stack.Scan(path, files, mediaList, subdirs)
  
def find_data(atom, name):
  child = atomsearch.find_path(atom, name)
  data_atom = child.find('data')
  if data_atom and 'data' in data_atom.attrs:
    return data_atom.attrs['data']

if __name__ == '__main__':
  print "Hello, world!"
  path = sys.argv[1]
  files = [os.path.join(path, file) for file in os.listdir(path)]
  media = []
  Scan(path[1:], files, media, [])
  print "Media:", media
