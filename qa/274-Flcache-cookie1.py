from base import *

DIR     = "flcache-basic1"
FILE    = "test.cgi"
CONTENT = "Front-line cache boosts Cherokee performance"

CONF = """
vserver!1!rule!2730!match = directory
vserver!1!rule!2730!match!directory = /%(DIR)s
vserver!1!rule!2730!handler = cgi
vserver!1!rule!2730!flcache = 1
""" %(globals())


CGI_CODE = """#!/bin/sh

echo "Content-Type: text/plain"
echo "Set-cookie: foo=bar"
echo

echo "%(CONTENT)s"
""" %(globals())



class TestEntry (TestBase):
    def __init__ (self):
        TestBase.__init__ (self, __file__)
        self.request        = "GET /%s/%s HTTP/1.0\r\n" %(DIR, FILE) +\
                              "Connection: close\r\n"
        self.expected_error = 200


class Test (TestCollection):
    def __init__ (self):
        TestCollection.__init__ (self, __file__)

        self.name           = "Front-line cache: Cookie"
        self.conf           = CONF
        self.proxy_suitable = True

    def Prepare (self, www):
        d = self.Mkdir (www, DIR)
        self.WriteFile (d, FILE, 0755, CGI_CODE)

        # First request
        obj = self.Add (TestEntry())
        obj.expected_content = ['X-Cache: MISS', CONTENT]

        # Second request
        obj = self.Add (TestEntry())
        obj.expected_content = ['X-Cache: MISS', CONTENT]
