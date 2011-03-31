# -*- coding: utf-8 -*-
#
# Cherokee-admin
#
# Authors:
#      Alvaro Lopez Ortega <alvaro@alobbs.com>
#
# Copyright (C) 2001-2011 Alvaro Lopez Ortega
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 2 of the GNU General Public
# License as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

import CTK

import re
import os
import gzip
import time
import urllib2

from util import *
from consts import *
from ows_consts import *
from configured import *

class Index:
    def __init__ (self):
        self.local_file = "/tmp/index.py.gz"
        self.url        = REPO_MAIN + 'index.py.gz'
        self.content    = {}

    def Download (self):
        # Open the connection
        request = urllib2.Request (self.url)
        opener  = urllib2.build_opener()

        # Check previos version
        if os.path.exists (self.local_file):
            s = os.stat (self.local_file)
            t = time.strftime ("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(s.st_mtime))
            request.add_header ('If-Modified-Since', t)

        # Send request
        try:
            stream = opener.open (request)
        except urllib2.HTTPError, e:
            if e.code == 304:
                # 304: Not Modified
                return
            raise

        # Store
        f = open (self.local_file, "wb+")
        f.write (stream.read())
        f.close()

    def Parse (self):
        # Read
        f = gzip.open (self.local_file, 'rb')
        content = f.read()
        f.close()

        # Parse
        self.content = CTK.util.data_eval (content)

    def __getitem__ (self, k):
        return self.content[k]

    # Helpers
    #
    def get_package (self, pkg, prop=None):
        pkg = self.content.get('packages',{}).get(pkg)
        if pkg and prop:
            return pkg.get(prop)
        return pkg

    def get_package_list (self):
        return self.content.get('packages',{}).keys()


if __name__ == "__main__":
    i = Index()
    i.Download()
    i.Parse()

    print i['build_date']
    print i.get_package_list()
    print i.get_package('phpbb')
    print i.get_package('phpbb', 'installation')
