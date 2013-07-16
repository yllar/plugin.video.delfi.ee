#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#      Copyright (C) 2012 Yllar Pajus
#      http://loru.mine.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import re
import os
import sys
import urllib2
import urlparse
from xml.etree import ElementTree


import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import buggalo

__settings__  = xbmcaddon.Addon(id='plugin.video.delfi.ee')

MAIN_URL = __settings__.getSetting('country')

#show settings on first run so user could change portal and quality
if ( not __settings__.getSetting( "firstrun" ) ):
  __settings__.openSettings()
  __settings__.setSetting( "firstrun", '1' )

class DelfiException(Exception):
  pass

class Delfi(object):
  def downloadUrl(self,url):
    for retries in range(0, 5):
      try:
	r = urllib2.Request(url.encode('iso-8859-1', 'replace'))
	r.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:10.0.2) Gecko/20100101 Firefox/10.0.2')
	u = urllib2.urlopen(r, timeout = 30)
	contents = u.read()
	u.close()
	return contents
      except Exception, ex:
        if retries > 5:
	  raise DelfiException(ex)

  def listChannels(self):
    url = 'http://tv.%s' % MAIN_URL
    items = list()

    html = self.downloadUrl(url)
    if not html:
      raise DelfiException(ADDON.getLocalizedString(200))

    if MAIN_URL == 'delfi.ee':
      regex = '.*drawCategories\(\'([^\']+).*span>([^<]+)'
      item = xbmcgui.ListItem('Live TV', iconImage=FANART)
      item.setProperty('Fanart_Image', FANART)
      items.append((PATH + '?category=%s' % 'live', item, True))
    elif MAIN_URL == 'delfi.lv':
      regex = '.*category\/([^/]+).*>([^<]+)<span.*'
    elif MAIN_URL == 'delfi.lt':
      #<li><a href="category/59/" class="">Pilietis TV</a></li>
      regex = '.*category\/([^/]+).*class="">([^<]+)<\/a.*'

    for m in re.finditer(regex,html):
      item = xbmcgui.ListItem(m.group(2), iconImage=FANART)
      item.setProperty('Fanart_Image', FANART)
      items.append((PATH + '?category=%s' % m.group(1), item, True))
    xbmcplugin.addDirectoryItems(HANDLE, items)
    xbmcplugin.endOfDirectory(HANDLE)

  def playLiveStream(self):
    url = 'http://' + MAIN_URL
    buggalo.addExtraData('url', url)
    html = self.downloadUrl(url)
    if html:
      #hqs = 'rtmp://ajisaka.ml.ee:1935/delfi',
      hdurl = re.search('hqs = \'([^\']+).*([^\']+),', html, re.DOTALL)
      sdurl = re.search('s = \'([^\']+).*([^\']+),', html, re.DOTALL)
      #hqn = 'event2',
      hdevent = re.search('hqn = \'([^\']+).*([^\']+),', html, re.DOTALL)
      sdevent = re.search('sn = \'([^\']+).*([^\']+),', html, re.DOTALL)
    else:
      raise DelfiException(ADDON.getLocalizedString(200))
      
    if hdurl is None:
      raise DelfiException(ADDON.getLocalizedString(202))
    else:
      if __settings__.getSetting('hd'):
	stream = hdurl.group(1) + '/' + hdevent.group(1)
      else:
	stream = sdurl.group(1) + '/' + sdevent.group(1)
      
      playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
      playlist.clear()
      playlist.add(stream)
      xbmc.Player().play(stream)

  def listVideos(self,categoryId):
      
    url = 'http://tv.%s/categoryxml/%s/?type=xml&order=date' % (MAIN_URL, categoryId)
    buggalo.addExtraData('url', url)
    xmlData = self.downloadUrl(url)
    if not xmlData:
      raise DelfiException(ADDON.getLocalizedString(203))
    
    try:
      doc = ElementTree.fromstring(xmlData.replace('&', '&amp;'))
      doc = ElementTree.fromstring(xmlData.encode('utf-8'))
    except Exception, ex:
      raise DelfiException(str(MAIN_URL))

    items = list()
    group = doc.findall("videos")
    for node in group:
      title = node.get('title')
      url = node.get('url')
      image = node.get('image').replace('.s.','.')
      comments = node.get('comments')
      vid = re.search('.*/([^/]+)/',url,re.DOTALL)
      videoid = vid.group(1)
      infoLabels = {
	'title': title,
	'rating': comments
      }
      
      if image:
	fanart = image
      else:
	fanart = FANART
      
      item = xbmcgui.ListItem(title, iconImage = fanart)
      item.setInfo('video', infoLabels)
      item.setProperty('IsPlayable', 'true')
      item.setProperty('Fanart_Image', fanart)
      items.append((PATH + '?play=%s' % videoid,item))
    xbmcplugin.addDirectoryItems(HANDLE, items)
    xbmcplugin.endOfDirectory(HANDLE)    

  def playItem(self,item):
    if __settings__.getSetting('country') == "delfi.lv":
      prefix = 'yv'
    else:
      prefix = 'ytv'
    url = 'http://%s.%s/v/%s.mp4' % (prefix,MAIN_URL,item)
    buggalo.addExtraData('url',url)
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    item = xbmcgui.ListItem('Nimi', iconImage = ICON, path = url) # TODO: replace Nimi with the real name 
    playlist.add(url,item)
    firstItem = item
    xbmcplugin.setResolvedUrl(HANDLE, True, item)
 
  def displayError(self, message = 'n/a'):
    heading = buggalo.getRandomHeading()
    line1 = ADDON.getLocalizedString(200)
    line2 = ADDON.getLocalizedString(201)
    xbmcgui.Dialog().ok(heading, line1, line2, message)
    
if __name__ == '__main__':
  ADDON = xbmcaddon.Addon()
  PATH = sys.argv[0]
  HANDLE = int(sys.argv[1])
  PARAMS = urlparse.parse_qs(sys.argv[2][1:])
  
  ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')
  FANART = os.path.join(ADDON.getAddonInfo('path'), 'fanart.jpg')
  
  CACHE_PATH = xbmc.translatePath(ADDON.getAddonInfo("Profile"))
  if not os.path.exists(CACHE_PATH):
    os.makedirs(CACHE_PATH)
    

  buggalo.SUBMIT_URL = 'http://loru.mine.nu/exception/submit.php'
  
  DelfiAddon = Delfi()
  try:
    if PARAMS.has_key('category') and PARAMS['category'][0] == 'live':
      DelfiAddon.playLiveStream()
    elif PARAMS.has_key('category'):
      DelfiAddon.listVideos(PARAMS['category'][0])
    elif PARAMS.has_key('play'):
      DelfiAddon.playItem(PARAMS['play'][0])
    else:
      DelfiAddon.listChannels()
      
  except DelfiException, ex:
    DelfiAddon.displayError(str(ex))
  except Exception:
    buggalo.onExceptionRaised()
