from base import *

COMMENT = "This is comment inside the CGI"
TEXT    = "It should be printed by the CGI"

CONF = """
vserver!default!rule!extensions!prio3!handler = file
vserver!default!rule!extensions!prio3!priority = 1090

vserver!default!rule!directory!/prio3/sub!handler = cgi
vserver!default!rule!directory!/prio3/sub!priority = 1091
"""

class Test (TestBase):
    def __init__ (self):
        TestBase.__init__ (self)
        self.name = "Priorities: Ext and then Dir"

        self.request           = "GET /prio3/sub/exec.prio3 HTTP/1.0\r\n"
        self.expected_error    = 200
        self.expected_content  = TEXT
        self.forbidden_content = COMMENT
        self.conf              = CONF

    def Prepare (self, www):
        d = self.Mkdir (www, "prio3/sub")
        f = self.WriteFile (d, "exec.prio3", 0555,
                            """#!/bin/sh

                            echo "Content-type: text/html"
                            echo ""
                            # %s
                            echo "%s"
                            """ % (COMMENT, TEXT))
