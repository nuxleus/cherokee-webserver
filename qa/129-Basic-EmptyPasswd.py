from base import *
from base64 import encodestring

LOGIN="Aladdin"
PASSWD="open sesame"

CONF = """
vserver!default!rule!1290!match!type = directory
vserver!default!rule!1290!match!directory = /auth_empty
vserver!default!rule!1290!match!final = 0
vserver!default!rule!1290!auth = plain
vserver!default!rule!1290!auth!methods = basic
vserver!default!rule!1290!auth!realm = Test Empty
vserver!default!rule!1290!auth!passwdfile = %s
"""

class Test (TestBase):
    def __init__ (self):
        TestBase.__init__ (self)
        self.name             = "Auth basic, emtpy passwd"
        self.request          = "GET /auth_empty/ HTTP/1.0\r\n" + \
                                "Authorization: Basic %s\r\n" % (encodestring ("%s:%s"%(LOGIN,""))[:-1])
        self.expected_error   = 401

    def Prepare (self, www):
        d = self.Mkdir (www, "auth_empty")
        f = self.WriteFile (d, "passwd", 0444, '%s:%s\n' %(LOGIN,PASSWD))

        self.conf = CONF % (f)
