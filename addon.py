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
import urllib
import urllib2
import urlparse
import locale

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import buggalo

try:
  locale.setlocale(locale.LC_ALL, 'et_EE.UTF-8')
except locale.Error:
  locale.setlocale(locale.LC_ALL, 'C')

__settings__  = xbmcaddon.Addon(id='plugin.video.delfi.ee')

#show settings on first run so user could change portal and quality
if ( not __settings__.getSetting( "firstrun" ) ):
  __settings__.openSettings()
  __settings__.setSetting( "firstrun", '1' )

MAIN_URL = __settings__.getSetting('country')

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
      raise DelfiException(ADDON.getLocalizedString(200).encode('utf-8'))

    html = html.replace('</li>','</li>\r\n')

    if MAIN_URL == 'delfi.ee':
      regex = '.*href="/([^\/]+)/".*class=\"header-navi-link\">([^<]+)<.*'
      item = xbmcgui.ListItem(ADDON.getLocalizedString(30006).encode('utf-8'), iconImage=FANART)
      item.setProperty('Fanart_Image', FANART)
      items.append((PATH + '?category=%s' % 'live/vaatajargi', item, True))
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

  def getLiveStreams(self):
    url = 'http://' + MAIN_URL
    buggalo.addExtraData('url', url)
    html = self.downloadUrl(url)
    if not html:
      raise DelfiException(ADDON.getLocalizedString(202).encode('utf-8'))
    
    stream_name = list() # Stream name
    stream_lq = list() # Low quality stream
    stream_hq = list() # High quality stream
    stream_lu = list() # Low quality stream url
    stream_hu = list() # High quality stream url
    items = list()
    for m in re.findall('<div>([^<]+)</div>',html, re.DOTALL):
      stream_name.append(m)
    for loq in re.findall('\ssn = \'([^\']+)\'', html ,re.DOTALL):
      stream_lq.append(loq)
    for hiq in re.findall('\shqn = \'([^\']+)\'', html ,re.DOTALL):
      stream_hq.append(hiq)
    for lurl in re.findall('\ss = \'([^\']+)\'', html ,re.DOTALL):
      stream_lu.append(lurl)
    for hurl in re.findall('\shqs = \'([^\']+)\'', html ,re.DOTALL):
      stream_hu.append(hurl)

    # try to fall back sd if hd url is not available and vice versa
    if not stream_hu and not stream_lu:
      raise DelfiException(ADDON.getLocalizedString(30005).encode('utf-8'))
    if not stream_hu:
      stream_hu = stream_lu
    if not stream_lu:
      stream_lu = stream_hu
      
    while len(stream_name) > 0:
      if __settings__.getSetting('hd'):
	streamurl = "%s/%s" % (stream_hu.pop(0), stream_hq.pop(0))
      else:
	streamurl = "%s/%s" % (stream_lu.pop(0), stream_lq.pop(0))
	
      item = xbmcgui.ListItem(stream_name.pop(0),iconImage=FANART)
      item.setProperty('Fanart_Image', FANART)
      items.append((PATH + '?category=live&url=%s' % streamurl, item, True))
    xbmcplugin.addDirectoryItems(HANDLE, items)
    xbmcplugin.endOfDirectory(HANDLE)
    
  def playLiveStream(self,streamurl):
    buggalo.addExtraData('url', streamurl)

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    playlist.add(streamurl)
    xbmc.Player().play(streamurl)

  def listVideos(self,categoryId):
      
    url = 'http://tv.%s/%s/' % (MAIN_URL, categoryId)
    buggalo.addExtraData('url', url)
    html = self.downloadUrl(url)
    if not html:
      raise DelfiException(ADDON.getLocalizedString(203).encode('utf-8'))

    items = list()
    imgurl = 'http://tv.%s' % MAIN_URL
    html = html.replace('</div></div></div>','</div></div></div>\r\n')
    regex = 'video-title".*href="([^"]+)">([^<]+)<.*mg src="([^"]+)"'
    for node in re.finditer(regex,html):
      title = node.group(2)
      url = node.group(1)
      image = imgurl + node.group(3)
      videoid = node.group(1)
      infoLabels = {
	'title': title
      }
      
      if image:
	fanart = image
      else:
	fanart = FANART
      
      item = xbmcgui.ListItem(title, iconImage = fanart)
      item.setInfo('video', infoLabels)
      item.setProperty('IsPlayable', 'true')
      item.setProperty('Fanart_Image', fanart)
      items.append((PATH + '?play=%s&title=%s' % (videoid,urllib.quote_plus(title.replace("'","\'"))),item))
    del items[-1]
    del items[-1]
    xbmcplugin.addDirectoryItems(HANDLE, items)
    xbmcplugin.endOfDirectory(HANDLE)    

  def getVideo(self,url):
    html = self.downloadUrl(url)
    if not html:
      raise DelfiException(ADDON.getLocalizedString(200).encode('utf-8'))
    # <link rel="video_src" href="http://vodhttp.nh.ee/P/PRMkOb8P/v720.mp4"/>
    regex = 'rel="video_src" href="([^"]+)"'
    for line in re.finditer(regex,html):
      return line.group(1)
    
  def playItem(self,item,title):
    """if __settings__.getSetting('country') == "delfi.lv":
      prefix = 'yv'
    else:
      prefix = 'ytv' """
    url = DelfiAddon.getVideo(item)
    buggalo.addExtraData('url',url)
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    item = xbmcgui.ListItem(urllib.unquote_plus(title), iconImage = ICON, path = url)
    playlist.add(url,item)
    firstItem = item
    xbmcplugin.setResolvedUrl(HANDLE, True, item)
 
  def displayError(self, message = 'n/a'):
    heading = buggalo.getRandomHeading()
    line1 = ADDON.getLocalizedString(200).encode('utf-8')
    line2 = ADDON.getLocalizedString(201).encode('utf-8')
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
    if PARAMS.has_key('category') and PARAMS['category'][0] == 'live' and PARAMS.has_key('url'):
      DelfiAddon.playLiveStream(PARAMS['url'][0])
    elif PARAMS.has_key('category') and PARAMS['category'][0] == 'live':
      DelfiAddon.getLiveStreams()
    elif PARAMS.has_key('category'):
      DelfiAddon.listVideos(PARAMS['category'][0])
    elif PARAMS.has_key('play'):
      DelfiAddon.playItem(PARAMS['play'][0],PARAMS['title'][0])
    else:
      DelfiAddon.listChannels()
      
  except DelfiException, ex:
    DelfiAddon.displayError(str(ex))
  except Exception:
    buggalo.onExceptionRaised()
