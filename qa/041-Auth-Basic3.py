from base import *

CONF = """
vserver!default!rule!410!match!type = directory
vserver!default!rule!410!match!directory = /auth3
vserver!default!rule!410!match!final = 0
vserver!default!rule!410!auth = plain
vserver!default!rule!410!auth!methods = basic
vserver!default!rule!410!auth!realm = Test
vserver!default!rule!410!auth!passwdfile = %s
"""

class Test (TestBase):
    def __init__ (self):
        TestBase.__init__ (self)
        self.name             = "Auth basic III"
        self.request          = "GET /auth3/ HTTP/1.0\r\n" + \
                                "Authorization: Basic WRONG_RpbjpvcGVuIHNlc2FtZQ==\r\n"
        self.expected_error   = 401

    def Prepare (self, www):
        d = self.Mkdir (www, "auth3")
        self.WriteFile (d, "passwd", 0444, 'Aladdin:open sesame\n')

        self.conf = CONF % (d+"/passwd")
