#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#      Copyright (C) 2016 Yllar Pajus
#      http://yllar.eu
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
import json
from bs4 import BeautifulSoup

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import buggalo

try:
    locale.setlocale(locale.LC_ALL, 'et_EE.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'C')

__settings__ = xbmcaddon.Addon(id='plugin.video.delfi.ee')

# show settings on first run so user could change portal and quality
if not __settings__.getSetting("firstrun"):
    __settings__.openSettings()
    __settings__.setSetting("firstrun", '1')

MAIN_URL = __settings__.getSetting('country')


class DelfiException(Exception):
    pass


class Delfi(object):
    def download_url(self, url):
        for retries in range(0, 5):
            try:
                r = urllib2.Request(url.encode('iso-8859-1', 'replace'))
                r.add_header('User-Agent',
                             'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:10.0.2) Gecko/20100101 Firefox/10.0.2')
                u = urllib2.urlopen(r, timeout=30)
                contents = u.read()
                u.close()
                return contents
            except Exception as ex:
                if retries > 5:
                    raise DelfiException(ex)

    def list_channels(self):
        url = 'http://tv.%s/saated/' % MAIN_URL
        items = list()

        html = self.download_url(url)
        if not html:
            raise DelfiException(ADDON.getLocalizedString(200).encode('utf-8'))

        html = html.replace('</li>', '</li>\r\n')

        regex = '\s<a href="/saated/([^\/]+).">([^<]+)</a>'
        item = xbmcgui.ListItem(ADDON.getLocalizedString(30007).encode('utf-8'), iconImage=FANART)
        item.setProperty('Fanart_Image', FANART)
        items.append((PATH + '?category=%s' % 'live', item, True))
        item = xbmcgui.ListItem(ADDON.getLocalizedString(30006).encode('utf-8'), iconImage=FANART)
        item.setProperty('Fanart_Image', FANART)
        items.append((PATH + '?category=%s&page=1' % 'live/sport', item, True))

        item = xbmcgui.ListItem(ADDON.getLocalizedString(30009).encode('utf-8'), iconImage=FANART)
        item.setProperty('Fanart_Image', FANART)
        items.append((PATH + '?category=%s&page=1' % 'saated', item, True))

        for m in re.finditer(regex, html):
            item = xbmcgui.ListItem(m.group(2), iconImage=FANART)
            item.setProperty('Fanart_Image', FANART)
            items.append((PATH + '?category=%s&page=1' % m.group(1), item, True))
        xbmcplugin.addDirectoryItems(HANDLE, items)
        xbmcplugin.endOfDirectory(HANDLE)

    def get_live_streams(self):
        url = 'http://tv.delfi.ee/live/'
        html = BeautifulSoup(self.download_url(url), 'html.parser')
        if not html:
            raise DelfiException(ADDON.getLocalizedString(202).encode('utf-8'))
        items = list()
        events = html.find_all(class_='stream-event')
        for event in events:
            if event.get('data-dschedule'):
                #print(event.attrs.get('data-dschedule'), event.text)
                title = '%s - %s' % (event.a.text, event.find(class_='stream-event__text').text)
                item = xbmcgui.ListItem(title, iconImage=FANART)
                item.setProperty('Fanart_Image', FANART)
                items.append((PATH + '?category=live&event=%s' % event.attrs.get('data-dschedule'), item, True))
        xbmcplugin.addDirectoryItems(HANDLE, items)
        xbmcplugin.endOfDirectory(HANDLE)

    def get_live_stream_url(self, event):
        url = 'https://www.delfi.ee/misc/export/streamblock.php?stream=%s' % event
        buggalo.addExtraData('url', url)
        html = BeautifulSoup(self.download_url(url), 'html.parser')
        if not html:
            raise DelfiException(ADDON.getLocalizedString(202).encode('utf-8'))

        urlid = html.find_all('script')
        for live_url in urlid:
            try:
                for m in re.findall('#stream=([^&]+)&', str(live_url), re.DOTALL):
                    data = json.loads(urllib.unquote(m))
                    title = data['title'].replace('+', ' ')
                    stream_hu = ''
                    stream_lu = ''
                    for streams in data['versions']:
                        if streams['caption'] == "HQ":
                            stream_hu = data['rtmp'] + streams['flash']
                        if streams['caption'] == "LQ":
                            stream_lu = data['rtmp'] + streams['flash']

                    # try to fall back sd if hd url is not available and vice versa
                    if not stream_hu and not stream_lu:
                        raise DelfiException(ADDON.getLocalizedString(30005).encode('utf-8'))
                    if not stream_hu:
                        stream_hu = stream_lu
                    if not stream_lu:
                        stream_lu = stream_hu

                    if __settings__.getSetting('hd'):
                        streamurl = stream_hu
                    else:
                        streamurl = stream_lu
                    return streamurl
            except:
                pass

    def play_live_stream(self, event):
        buggalo.addExtraData('event', event)
        streamurl = self.get_live_stream_url(event)
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
        playlist.add(streamurl)
        xbmc.Player().play(streamurl)

    def list_videos(self, categoryId, page):

        if "live/" in categoryId or "saated" in categoryId:
            url = 'http://tv.%s/%s/?page=%s' % (MAIN_URL, categoryId, page)
        else:
            url = 'http://tv.%s/saated/%s/?page=%s' % (MAIN_URL, categoryId, page)
        buggalo.addExtraData('url', url)
        html = self.download_url(url)
        if not html:
            raise DelfiException(ADDON.getLocalizedString(203).encode('utf-8'))

        items = list()
        html = html.replace('</div></div></div>', '</div></div></div>\r\n')
        regex = 'img class="responsive" src="([^"]+)".*c-block-art-title.*href="([^"]+)">([^<]+)</a'
        for node in re.finditer(regex, html):
            title = node.group(3)
            image = node.group(1)
            videoid = node.group(2)
            infoLabels = {
                'title': title
            }

            if image:
                fanart = image
            else:
                fanart = FANART

            item = xbmcgui.ListItem(title, iconImage=fanart)
            item.setInfo('video', infoLabels)
            item.setProperty('IsPlayable', 'true')
            item.setProperty('Fanart_Image', fanart)
            items.append((PATH + '?play=%s&title=%s' % (videoid, urllib.quote_plus(title.replace("'", "\'"))), item))
        try:
            pagex = '<a class="item item-next.*href="([^"]+)"'
            pagination = re.search(pagex, html)
            if pagination:
                if pagination.group(1) != "javascript:void(0)":
                    item = xbmcgui.ListItem(ADDON.getLocalizedString(30008).encode('utf-8'), iconImage=fanart)
                    item.setProperty('IsPlayable', 'true')
                    item.setProperty('Fanart_Image', fanart)
                    items.append(
                        (PATH + '?category=%s&%s' % (categoryId, pagination.group(1).replace('?', '')), item, True))
        except:
            pass
        xbmcplugin.addDirectoryItems(HANDLE, items)
        xbmcplugin.endOfDirectory(HANDLE)

    def get_video(self, url):
        html = self.download_url(url)
        if not html:
            raise DelfiException(ADDON.getLocalizedString(200).encode('utf-8'))

        regex = 'data-id="(\w+)"'
        for line in re.finditer(regex, html):
            id = line.group(1)
            return 'http://vodrtmp.nh.ee/delfivod/_definst_/%s/%s/smil:stream.smil/playlist.m3u8' % (id[0], id)

    def play_item(self, item, title):
        url = DelfiAddon.get_video(item)
        buggalo.addExtraData('url', url)
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
        item = xbmcgui.ListItem(urllib.unquote_plus(title), iconImage=ICON, path=url)
        playlist.add(url, item)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    def display_error(self, message='n/a'):
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

    buggalo.SUBMIT_URL = 'https://pilves.eu/exception/submit.php'

    DelfiAddon = Delfi()
    try:
        if PARAMS.has_key('category') and PARAMS['category'][0] == 'live' and PARAMS.has_key('event'):
            DelfiAddon.play_live_stream(PARAMS['event'][0])
        elif PARAMS.has_key('category') and PARAMS['category'][0] == 'live':
            DelfiAddon.get_live_streams()
        elif PARAMS.has_key('category'):
            DelfiAddon.list_videos(PARAMS['category'][0], PARAMS['page'][0])
        elif PARAMS.has_key('play'):
            DelfiAddon.play_item(PARAMS['play'][0], PARAMS['title'][0])
        else:
            DelfiAddon.list_channels()

    except DelfiException as ex:
        DelfiAddon.display_error(str(ex))
    except Exception:
        buggalo.onExceptionRaised()
