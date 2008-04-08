from base import *

MAGIC = "Allow From test 2"

CONF = """
vserver!default!rule!directory!/allow2!allow_from = 127.0.0.1,::1
vserver!default!rule!directory!/allow2!priority = 740
vserver!default!rule!directory!/allow2!final = 0
"""

class Test (TestBase):
    def __init__ (self):
        TestBase.__init__ (self)
        self.name              = "Allow from test, allowed"
        self.request           = "GET /allow2/file HTTP/1.0\r\n"
        self.expected_error    = 200
        self.expected_content  = MAGIC
        self.conf              = CONF

    def Prepare (self, www):
        self.Mkdir (www, "allow2")
        self.WriteFile (www, "allow2/file", 0444, MAGIC)

