#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
import logging
from errno import ENOENT
from stat import S_IFDIR, S_IFREG
from time import time
import urllib.parse as ul
import os
import re
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn, fuse_get_context
import requests


rubrikHost = "shrd1-rbk01.rubrikdemo.com"
rubrikKey = str("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIyOWNiNzFhMS0yZGIwLTRlZGQtYjA1Mi1kNmQ1NWRlMjBiOTRfMmY2MzFmYjItNzUyMi00ZTcwLWFjNzgtMzk1Y2EzNTIwMmRjIiwiaXNzIjoiMjljYjcxYTEtMmRiMC00ZWRkLWIwNTItZDZkNTVkZTIwYjk0IiwianRpIjoiYjNjYzUzYTUtNDIwMi00ZDc5LWE4ZDctMmFjNGI3ODk3YmU3In0.CyijHNB9H1-VTPD0MHcnvegHI0e0ZoA80y8n_W0yliI")
rubrikSnapshot = str("92281431-bfb6-4a76-aa75-e5c33a0d1958")


# Simple dump of a directory
class RubrikFS(LoggingMixIn, Operations):
    def __init__(self):
        self.rubrik = Rubrik(rubrikHost, rubrikKey)

    def getattr(self, path, fh=None):
        st = os.lstat('/tmp')
        if 'image/' in path:
            st = os.lstat('/tmp/vagrant_shell')

        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                                                        'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size',
                                                        'st_uid'))

    def readdir(self, path, fh):
        path = re.sub(r'^\/(\S+.*)', '\1', path)
        print("*****************************" + path)

        objs = ['.', '..']
        for obj in self.rubrik.browse_path(rubrikSnapshot, path)['data']:
            objs.append(obj['filename'])
        return objs


class Rubrik:
    class RubrikException(Exception):
        def __init__(self, msg):
            self.msg = msg

        def __str__(self):
            return self.msg

    def __init__(self, rubrik_addr, rubrik_api_key):
        # Prompt for configuration info
        self.rubrik_addr = rubrik_addr
        self.baseurl = "https://" + self.rubrik_addr + "/api/v1/"
        self.internal_baseurl = "https://" + self.rubrik_addr + "/api/internal/"
        self.rubrik_api_key = rubrik_api_key
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json',
                        'Authorization': 'Bearer ' + self.rubrik_api_key}
        self.callFileSets = "fileset"
        self.callFileSetDetail = "fileset/{}"
        self.callFilesetBrowse = "fileset/snapshot/{}/browse?path={}"

        # Disable ssl warnings for Requests
        requests.packages.urllib3.disable_warnings()

    def browse_path(self, snap="", path=""):
        return self.apicall(self.callFilesetBrowse.format(snap, ul.quote_plus(path)))

    def apicall(self, call, method="get", data="", internal=False):
      uri = self.baseurl + call
      if internal:
        uri = self.internal_baseurl + call
      else:
        uri = self.baseurl + call
      try:
        r = getattr(requests, method)(uri, data=data, verify=False, headers=self.headers)
        r.raise_for_status()
        return r.json()
      except requests.RequestException as e:
        print
        e
        raise self.RubrikException("Rubrik API Call Failed: " + str(e))
      except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as e:
        print
        e
        response = r.json()
        if response.has_key('message'):
          print
          response['message']
        raise self.RubrikException("Call Failed: " + response['message'])
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mount')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(
        RubrikFS(), args.mount, foreground=True, ro=True, allow_other=True)
